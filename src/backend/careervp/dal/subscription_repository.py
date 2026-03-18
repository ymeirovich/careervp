"""
Subscription Repository — single-table DAL for billing state.

All subscription records live in the **users table** alongside existing
TRIAL and PROFILE rows, following the DB_SINGLE_TABLE rule from
docs/best_practices/yaml/dynamodb_modeling_spec.yaml.

Key schema:
  pk  = USER#{user_id}
  sk  = SUBSCRIPTION#CURRENT

Payment-event deduplication uses the existing idempotency table:
  pk  = PAYMENT_EVENT#{event_id}
  sk  = EVENT_TYPE#{event_type}

No new DynamoDB tables are created.  Naming follows NamingUtils conventions.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from careervp.handlers.utils.observability import logger, tracer
from careervp.models.result import Result, ResultCode

# ─── SK constants (DB_SK_PREFIX_PATTERN) ─────────────────────────────────────
SUBSCRIPTION_SK = 'SUBSCRIPTION#CURRENT'
PAYMENT_EVENT_SK_PREFIX = 'EVENT_TYPE#'

# ─── Checkout-lock constants ──────────────────────────────────────────────────
# Stored in the idempotency table (which has TTL on ``expiration`` and PK=``id``).
# id = CHECKOUT_LOCK#{user_id}   (no sort key — idempotency table has none)
CHECKOUT_LOCK_TTL_SECONDS = 3600  # 1 hour — auto-cleaned if release is never called

# ─── Reserved DynamoDB keywords that require ExpressionAttributeNames aliasing
_RESERVED = frozenset(
    {
        'status',
        'plan',
        'name',
        'data',
        'type',
        'value',
        'timestamp',
        'date',
        'time',
        'year',
        'month',
        'error',
    }
)

# ─── User-table GSI for customer-id lookups (already on users table) ─────────
EMAIL_INDEX_NAME = 'email-index'


class SubscriptionRepository:
    """DAL for subscription records stored in the shared users table.

    Follows the same standalone-class pattern as UserRepository and
    JobsRepository: one boto3.resource per instance, table name resolved
    from environment variables with a NamingUtils fallback.
    """

    def __init__(
        self,
        table_name: str | None = None,
        idempotency_table_name: str | None = None,
        dynamodb_resource: Any | None = None,
    ) -> None:
        self._dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self._table_name = table_name or self._resolve_table_name('TABLE_NAME', 'users')
        self._idempotency_table_name = idempotency_table_name or self._resolve_table_name('IDEMPOTENCY_TABLE_NAME', 'idempotency')
        self._table = self._dynamodb.Table(self._table_name)
        self._idempotency_table = self._dynamodb.Table(self._idempotency_table_name)

    # ─── Public read methods ──────────────────────────────────────────────────

    @tracer.capture_method(capture_response=False)
    def get_subscription(self, user_id: str) -> Result[dict[str, Any]]:
        """Fetch SUBSCRIPTION#CURRENT for a user.

        Returns Result with data=None (success=True) when the user has no
        subscription yet — callers must handle the None data case.
        """
        try:
            response = self._table.get_item(Key={'pk': self._pk(user_id), 'sk': SUBSCRIPTION_SK})
            item: dict[str, Any] | None = response.get('Item')
            logger.info('get_subscription', user_id=user_id, found=item is not None)
            return Result(success=True, data=item, code=ResultCode.SUCCESS)
        except ClientError as exc:
            msg = f'DynamoDB error: {exc.response["Error"]["Message"]}'
            logger.error('get_subscription failed', user_id=user_id, error=str(exc))
            return Result(success=False, error=msg, code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def get_subscription_by_customer_id(self, customer_id: str) -> Result[dict[str, Any]]:
        """Scan the users table for a subscription row matching customer_id.

        This is an infrequent path (webhook fallback); it uses a FilterExpression
        scan on the users table subset that has sk = SUBSCRIPTION#CURRENT.

        In production, prefer caching customer_id→user_id in the user PROFILE row
        (see update_customer_id) and looking up that way.
        """
        try:
            response = self._table.query(
                IndexName=EMAIL_INDEX_NAME,
                KeyConditionExpression=Key('email').eq(customer_id),
                FilterExpression=Attr('sk').eq(SUBSCRIPTION_SK),
                Limit=1,
            )
            items = response.get('Items', [])
            item = items[0] if items else None
            return Result(success=True, data=item, code=ResultCode.SUCCESS)
        except ClientError:
            # Fall back to sk-filter scan (rare, only if no email-index match)
            pass

        try:
            response = self._table.scan(
                FilterExpression=(Attr('sk').eq(SUBSCRIPTION_SK) & Attr('customer_id').eq(customer_id)),
                Limit=10,
            )
            items = response.get('Items', [])
            item = items[0] if items else None
            logger.info(
                'get_subscription_by_customer_id (scan)',
                customer_id=customer_id,
                found=item is not None,
            )
            return Result(success=True, data=item, code=ResultCode.SUCCESS)
        except ClientError as exc:
            msg = f'DynamoDB error: {exc.response["Error"]["Message"]}'
            logger.error(
                'get_subscription_by_customer_id failed',
                customer_id=customer_id,
                error=str(exc),
            )
            return Result(success=False, error=msg, code=ResultCode.DYNAMODB_ERROR)

    # ─── Public write methods ─────────────────────────────────────────────────

    @tracer.capture_method(capture_response=False)
    def upsert_subscription(self, user_id: str, data: dict[str, Any]) -> Result[dict[str, Any]]:
        """Create or fully replace the SUBSCRIPTION#CURRENT record.

        Uses put_item (idempotent) — safe for duplicate webhook delivery.
        """
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            item: dict[str, Any] = {
                'pk': self._pk(user_id),
                'sk': SUBSCRIPTION_SK,
                'user_id': user_id,
                'updated_at': now_iso,
                **data,
            }
            item.setdefault('created_at', now_iso)
            self._table.put_item(Item=item)
            logger.info(
                'upsert_subscription',
                user_id=user_id,
                subscription_id=data.get('subscription_id'),
            )
            return Result(success=True, data=item, code=ResultCode.SUCCESS)
        except ClientError as exc:
            msg = f'DynamoDB error: {exc.response["Error"]["Message"]}'
            logger.error('upsert_subscription failed', user_id=user_id, error=str(exc))
            return Result(success=False, error=msg, code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def update_subscription_fields(self, user_id: str, updates: dict[str, Any]) -> Result[dict[str, Any]]:
        """Partial-update the SUBSCRIPTION#CURRENT record via UpdateExpression.

        Uses ConditionExpression to ensure the record exists before patching
        (DB_CONDITIONAL_WRITE from spec — avoids silent no-op on missing row).
        """
        try:
            update_expr, attr_names, attr_values = self._build_update_expression(updates)
            response = self._table.update_item(
                Key={'pk': self._pk(user_id), 'sk': SUBSCRIPTION_SK},
                UpdateExpression=update_expr,
                ConditionExpression='attribute_exists(pk)',
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_values,
                ReturnValues='ALL_NEW',
            )
            updated = response.get('Attributes', {})
            logger.info('update_subscription_fields', user_id=user_id, fields=list(updates.keys()))
            return Result(success=True, data=updated, code=ResultCode.SUCCESS)
        except ClientError as exc:
            error_code = exc.response.get('Error', {}).get('Code', '')
            if error_code == 'ConditionalCheckFailedException':
                return Result(
                    success=False,
                    error='Subscription record not found',
                    code=ResultCode.SUBSCRIPTION_NOT_FOUND,
                )
            msg = f'DynamoDB error: {exc.response["Error"]["Message"]}'
            logger.error('update_subscription_fields failed', user_id=user_id, error=str(exc))
            return Result(success=False, error=msg, code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def set_unlimited_usage(self, user_id: str) -> Result[None]:
        """Write usage = 9999 (unlimited) for a freshly activated subscriber.

        Stored as a separate sk=USAGE row on the same pk for clean separation.
        """
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            self._table.put_item(
                Item={
                    'pk': self._pk(user_id),
                    'sk': 'USAGE',
                    'user_id': user_id,
                    'remaining': 9999,
                    'updated_at': now_iso,
                }
            )
            logger.info('set_unlimited_usage', user_id=user_id)
            return Result(success=True, data=None, code=ResultCode.SUCCESS)
        except ClientError as exc:
            msg = f'DynamoDB error: {exc.response["Error"]["Message"]}'
            logger.error('set_unlimited_usage failed', user_id=user_id, error=str(exc))
            return Result(success=False, error=msg, code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def update_customer_id(self, user_id: str, customer_id: str) -> Result[None]:
        """Persist the payment-provider customer_id on the PROFILE row.

        Stored on the existing USER#{user_id}/PROFILE item so lookups stay
        within the same single table without a new table or GSI.
        """
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            expr, attr_names, attr_values = self._build_update_expression(
                {
                    'customer_id': customer_id,
                    'updated_at': now_iso,
                }
            )
            self._table.update_item(
                Key={'pk': self._pk(user_id), 'sk': 'PROFILE'},
                UpdateExpression=expr,
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_values,
            )
            logger.info('update_customer_id', user_id=user_id)
            return Result(success=True, data=None, code=ResultCode.SUCCESS)
        except ClientError as exc:
            msg = f'DynamoDB error: {exc.response["Error"]["Message"]}'
            logger.error('update_customer_id failed', user_id=user_id, error=str(exc))
            return Result(success=False, error=msg, code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method(capture_response=False)
    def get_customer_id(self, user_id: str) -> str | None:
        """Read customer_id from the PROFILE row.  Returns None when absent."""
        try:
            response = self._table.get_item(
                Key={'pk': self._pk(user_id), 'sk': 'PROFILE'},
                ProjectionExpression='customer_id',
            )
            item = response.get('Item') or {}
            return item.get('customer_id')
        except ClientError as exc:
            logger.warning('get_customer_id failed', user_id=user_id, error=str(exc))
            return None

    # ─── Payment-event deduplication (idempotency table) ─────────────────────

    @tracer.capture_method(capture_response=False)
    def record_payment_event(
        self,
        event_id: str,
        event_type: str,
        ttl_seconds: int = 86400 * 7,
    ) -> bool:
        """Atomically record a payment event; returns True if first delivery.

        Uses a conditional put_item on the existing idempotency table.
        The idempotency table's partition key is ``id`` (no sort key) —
        we encode event_id + event_type into a single composite id string.
        TTL defaults to 7 days — long enough to catch late webhook retries.
        """
        now = int(datetime.now(timezone.utc).timestamp())
        composite_id = f'PAYMENT_EVENT#{event_id}#{event_type}'
        try:
            self._idempotency_table.put_item(
                Item={
                    'id': composite_id,  # idempotency table PK is 'id' (no SK)
                    'event_id': event_id,
                    'event_type': event_type,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'expiration': now + ttl_seconds,
                },
                ConditionExpression='attribute_not_exists(id)',
            )
            logger.info('record_payment_event (new)', event_id=event_id, event_type=event_type)
            return True
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code', '')
            if code == 'ConditionalCheckFailedException':
                logger.info('record_payment_event (duplicate)', event_id=event_id, event_type=event_type)
                return False
            logger.error('record_payment_event failed', event_id=event_id, error=str(exc))
            return False

    # ─── Checkout-lock (concurrent checkout prevention) ───────────────────────

    @tracer.capture_method(capture_response=False)
    def create_checkout_intent(
        self,
        user_id: str,
        ttl_seconds: int = CHECKOUT_LOCK_TTL_SECONDS,
    ) -> None:
        """Atomically claim the checkout slot for this user.

        Raises ``ClientError`` (``ConditionalCheckFailedException``) when another
        checkout is already in progress for the same user.  The record lives in
        the idempotency table (which already has TTL on the ``expiration``
        attribute), so it auto-expires after ``ttl_seconds`` even if
        ``release_checkout_intent`` is never called — e.g. if the Lambda crashes
        mid-checkout.  The caller must invoke ``release_checkout_intent`` on both
        success and failure to avoid making the user wait up to 1 hour.
        """
        now = int(datetime.now(timezone.utc).timestamp())
        # idempotency table PK is 'id' (no sort key) — encode user_id into composite id
        lock_id = f'CHECKOUT_LOCK#{user_id}'
        try:
            self._idempotency_table.put_item(
                Item={
                    'id': lock_id,  # idempotency table PK is 'id' (no SK)
                    'user_id': user_id,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'expiration': now + ttl_seconds,
                },
                ConditionExpression='attribute_not_exists(id)',
            )
            logger.info('create_checkout_intent', user_id=user_id)
        except ClientError as exc:
            error_code = exc.response.get('Error', {}).get('Code', '')
            if error_code == 'ConditionalCheckFailedException':
                logger.warning('create_checkout_intent blocked (in-progress)', user_id=user_id)
                raise  # Caller maps this to 409 checkout_in_progress
            logger.error('create_checkout_intent failed', user_id=user_id, error=str(exc))
            raise

    @tracer.capture_method(capture_response=False)
    def release_checkout_intent(self, user_id: str) -> None:
        """Delete the checkout lock so the user can immediately attempt again.

        Call this on BOTH success and failure paths in the checkout handler.
        Safe to call when no lock exists (delete_item on a missing item is a no-op).
        """
        try:
            self._idempotency_table.delete_item(
                Key={'id': f'CHECKOUT_LOCK#{user_id}'},  # idempotency table PK is 'id'
            )
            logger.info('release_checkout_intent', user_id=user_id)
        except ClientError as exc:
            # Non-fatal — TTL auto-cleans within 1 hour regardless
            logger.warning('release_checkout_intent failed (non-fatal)', user_id=user_id, error=str(exc))

    # ─── Reconciliation support ───────────────────────────────────────────────

    @tracer.capture_method(capture_response=False)
    def scan_active_subscriptions(self) -> list[dict[str, Any]]:
        """Return all active subscription rows from the users table.

        Performs a paginated scan filtering on sk=SUBSCRIPTION#CURRENT and
        status=active.  Must scan self._table (users table), never the
        idempotency table.  A single scan page is capped at 1 MB, so
        pagination is mandatory for correctness at scale.
        """
        results: list[dict[str, Any]] = []
        filter_expr = Attr('sk').eq(SUBSCRIPTION_SK) & Attr('#s').eq('active')
        kwargs: dict[str, Any] = {
            'FilterExpression': filter_expr,
            'ExpressionAttributeNames': {'#s': 'status'},
        }
        while True:
            response = self._table.scan(**kwargs)
            results.extend(response.get('Items', []))
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break
            kwargs['ExclusiveStartKey'] = last_key
        logger.info('scan_active_subscriptions', count=len(results))
        return results

    # ─── Payment-event retry support ─────────────────────────────────────────

    @tracer.capture_method(capture_response=False)
    def delete_payment_event(self, event_id: str, event_type: str) -> None:
        """Remove an idempotency record so the payment provider can retry.

        Call this when partial work fails BEFORE the full event is processed.
        Without this, a retried webhook delivery would be silently discarded
        because the idempotency key already exists from the failed attempt.

        Pattern:
          1. ``record_payment_event`` → returns True (first delivery)
          2. Do work: ``upsert_subscription`` + ``set_unlimited_usage``
          3a. ALL work succeeds → leave idempotency record (blocks duplicates)
          3b. ANY work fails   → call ``delete_payment_event`` (allow provider retry)
        """
        try:
            self._idempotency_table.delete_item(
                Key={'id': f'PAYMENT_EVENT#{event_id}#{event_type}'},  # idempotency table PK is 'id'
            )
            logger.warning(
                'delete_payment_event (partial failure — allowing retry)',
                event_id=event_id,
                event_type=event_type,
            )
        except ClientError as exc:
            # Non-fatal; the payment provider retry will receive a duplicate
            # that won't be reprocessed — better than crashing the handler
            logger.error('delete_payment_event failed', event_id=event_id, error=str(exc))

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _build_update_expression(self, updates: dict[str, Any]) -> tuple[str, dict[str, str], dict[str, Any]]:
        """Build SET UpdateExpression with DB_RESERVED_WORDS aliasing."""
        parts: list[str] = []
        attr_names: dict[str, str] = {}
        attr_values: dict[str, Any] = {}

        for key, value in updates.items():
            val_token = f':{key}'
            if key.lower() in _RESERVED:
                name_token = f'#{key}'
                attr_names[name_token] = key
                parts.append(f'{name_token} = {val_token}')
            else:
                parts.append(f'{key} = {val_token}')
            attr_values[val_token] = value

        return 'SET ' + ', '.join(parts), attr_names, attr_values

    @staticmethod
    def _pk(user_id: str) -> str:
        return f'USER#{user_id}'

    @staticmethod
    def _resolve_table_name(env_var: str, feature: str) -> str:
        env_val = os.environ.get(env_var, '').strip()
        if env_val:
            return env_val
        environment = os.environ.get('ENVIRONMENT', 'dev')
        return f'careervp-{feature}-table-{environment}'


__all__ = [
    'SubscriptionRepository',
    'SUBSCRIPTION_SK',
    'PAYMENT_EVENT_SK_PREFIX',
    'CHECKOUT_LOCK_TTL_SECONDS',
]

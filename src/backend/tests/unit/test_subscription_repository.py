"""
Unit tests for SubscriptionRepository DAL.

Mirrors TypeScript tests: checkout.test.ts, subscription-status.test.ts
Spec compliance: docs/best_practices/yaml/dynamodb_modeling_spec.yaml
                 docs/best_practices/yaml/testing_spec.yaml
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from careervp.dal.subscription_repository import (
    SUBSCRIPTION_SK,
    SubscriptionRepository,
)
from careervp.models.result import ResultCode

# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_repo(
    *,
    get_item_return: dict | None = None,
    put_item_side_effect: Exception | None = None,
    update_item_return: dict | None = None,
    update_item_side_effect: Exception | None = None,
    scan_return: dict | None = None,
) -> tuple[SubscriptionRepository, MagicMock, MagicMock]:
    """Build a SubscriptionRepository backed by a fully mocked DynamoDB resource."""
    dynamo_resource = MagicMock()

    users_table = MagicMock()
    idempotency_table = MagicMock()

    dynamo_resource.Table.side_effect = lambda name: idempotency_table if 'idempotency' in name else users_table

    # Defaults
    users_table.get_item.return_value = {'Item': get_item_return} if get_item_return else {}
    users_table.update_item.return_value = {'Attributes': update_item_return or {}}
    users_table.scan.return_value = {'Items': [scan_return] if scan_return else []}

    if put_item_side_effect:
        users_table.put_item.side_effect = put_item_side_effect
    if update_item_side_effect:
        users_table.update_item.side_effect = update_item_side_effect

    repo = SubscriptionRepository(
        table_name='test-users-table',
        idempotency_table_name='test-idempotency-table',
        dynamodb_resource=dynamo_resource,
    )
    return repo, users_table, idempotency_table


def _dynamodb_error(code: str, message: str = 'test error') -> ClientError:
    return ClientError({'Error': {'Code': code, 'Message': message}}, 'Operation')


def _subscription_item(user_id: str = 'user-001', status: str = 'active') -> dict:
    return {
        'pk': f'USER#{user_id}',
        'sk': SUBSCRIPTION_SK,
        'user_id': user_id,
        'subscription_id': 'sub_test001',
        'customer_id': 'cus_test001',
        'status': status,
        'plan': 'monthly',
        'current_period_end': '2026-04-14T00:00:00+00:00',
        'cancel_at_period_end': False,
        'trial_end': None,
        'payment_failed_count': 0,
        'created_at': '2026-03-15T00:00:00+00:00',
        'updated_at': '2026-03-15T00:00:00+00:00',
    }


# ─── get_subscription ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetSubscription:
    def test_returns_subscription_when_found(self) -> None:
        item = _subscription_item()
        repo, table, _ = _make_repo(get_item_return=item)

        result = repo.get_subscription('user-001')

        assert result.success is True
        assert result.data is not None
        assert result.data['subscription_id'] == 'sub_test001'
        assert result.data['status'] == 'active'

    def test_uses_single_table_pk_sk_pattern(self) -> None:
        repo, table, _ = _make_repo()

        repo.get_subscription('user-001')

        table.get_item.assert_called_once_with(Key={'pk': 'USER#user-001', 'sk': SUBSCRIPTION_SK})

    def test_returns_none_data_when_no_subscription(self) -> None:
        repo, table, _ = _make_repo()

        result = repo.get_subscription('user-no-sub')

        assert result.success is True
        assert result.data is None

    def test_returns_dynamodb_error_on_client_error(self) -> None:
        repo, table, _ = _make_repo()
        table.get_item.side_effect = _dynamodb_error('InternalServerError')

        result = repo.get_subscription('user-001')

        assert result.success is False
        assert result.code == ResultCode.DYNAMODB_ERROR

    def test_sk_is_subscription_current(self) -> None:
        repo, table, _ = _make_repo()

        repo.get_subscription('any-user')

        _, kwargs = table.get_item.call_args
        assert kwargs['Key']['sk'] == 'SUBSCRIPTION#CURRENT'


# ─── upsert_subscription ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestUpsertSubscription:
    def test_puts_item_with_correct_pk_sk(self) -> None:
        repo, table, _ = _make_repo()

        repo.upsert_subscription(
            'user-010',
            {
                'subscription_id': 'sub_1Pxyz',
                'customer_id': 'cus_Nabc',
                'status': 'active',
                'plan': 'monthly',
                'payment_failed_count': 0,
            },
        )

        table.put_item.assert_called_once()
        item = table.put_item.call_args.kwargs['Item']
        assert item['pk'] == 'USER#user-010'
        assert item['sk'] == SUBSCRIPTION_SK

    def test_returns_success_with_item_data(self) -> None:
        repo, table, _ = _make_repo()

        result = repo.upsert_subscription('user-010', {'status': 'active', 'plan': 'monthly'})

        assert result.success is True
        assert result.data is not None
        assert result.data['user_id'] == 'user-010'

    def test_is_idempotent_on_duplicate_call(self) -> None:
        """put_item is idempotent — calling twice is safe (F-SUB-011)."""
        repo, table, _ = _make_repo()
        data = {'subscription_id': 'sub_1Pxyz', 'status': 'active', 'plan': 'monthly'}

        repo.upsert_subscription('user-010', data)
        repo.upsert_subscription('user-010', data)

        assert table.put_item.call_count == 2

    def test_injects_updated_at_timestamp(self) -> None:
        repo, table, _ = _make_repo()

        repo.upsert_subscription('user-010', {'status': 'active'})

        item = table.put_item.call_args.kwargs['Item']
        assert 'updated_at' in item
        # Verify it's a valid ISO timestamp
        datetime.fromisoformat(item['updated_at'])

    def test_returns_dynamodb_error_on_failure(self) -> None:
        repo, table, _ = _make_repo(put_item_side_effect=_dynamodb_error('ProvisionedThroughputExceededException'))

        result = repo.upsert_subscription('user-010', {'status': 'active'})

        assert result.success is False
        assert result.code == ResultCode.DYNAMODB_ERROR


# ─── update_subscription_fields ──────────────────────────────────────────────


@pytest.mark.unit
class TestUpdateSubscriptionFields:
    def test_uses_conditional_write_to_guard_existence(self) -> None:
        repo, table, _ = _make_repo(update_item_return={'pk': 'USER#user-014', 'sk': SUBSCRIPTION_SK})

        repo.update_subscription_fields('user-014', {'status': 'active', 'plan': 'quarterly'})

        kwargs = table.update_item.call_args.kwargs
        assert 'attribute_exists(pk)' in kwargs['ConditionExpression']

    def test_escapes_reserved_keyword_status(self) -> None:
        repo, table, _ = _make_repo(update_item_return={})

        repo.update_subscription_fields('user-014', {'status': 'active'})

        kwargs = table.update_item.call_args.kwargs
        assert '#status' in kwargs['ExpressionAttributeNames'].values() or 'status' in kwargs.get('ExpressionAttributeNames', {}).values()

    def test_escapes_reserved_keyword_plan(self) -> None:
        repo, table, _ = _make_repo(update_item_return={})

        repo.update_subscription_fields('user-014', {'plan': 'quarterly'})

        kwargs = table.update_item.call_args.kwargs
        assert '#plan' in kwargs.get('ExpressionAttributeNames', {}) or 'plan' in kwargs.get('ExpressionAttributeNames', {}).values()

    def test_returns_not_found_on_condition_failure(self) -> None:
        error = _dynamodb_error('ConditionalCheckFailedException')
        repo, table, _ = _make_repo(update_item_side_effect=error)

        result = repo.update_subscription_fields('user-014', {'status': 'active'})

        assert result.success is False
        assert result.code == ResultCode.SUBSCRIPTION_NOT_FOUND

    def test_returns_dynamodb_error_on_other_client_error(self) -> None:
        error = _dynamodb_error('InternalServerError')
        repo, table, _ = _make_repo(update_item_side_effect=error)

        result = repo.update_subscription_fields('user-014', {'status': 'active'})

        assert result.success is False
        assert result.code == ResultCode.DYNAMODB_ERROR

    def test_cancel_at_period_end_update(self) -> None:
        updated = {'pk': 'USER#user-015', 'sk': SUBSCRIPTION_SK, 'cancel_at_period_end': True}
        repo, table, _ = _make_repo(update_item_return=updated)

        result = repo.update_subscription_fields('user-015', {'cancel_at_period_end': True})

        assert result.success is True
        assert result.data.get('cancel_at_period_end') is True


# ─── set_unlimited_usage ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestSetUnlimitedUsage:
    def test_stores_remaining_9999(self) -> None:
        repo, table, _ = _make_repo()

        repo.set_unlimited_usage('user-010')

        item = table.put_item.call_args.kwargs['Item']
        assert item['remaining'] == 9999

    def test_stores_usage_on_same_pk(self) -> None:
        repo, table, _ = _make_repo()

        repo.set_unlimited_usage('user-010')

        item = table.put_item.call_args.kwargs['Item']
        assert item['pk'] == 'USER#user-010'
        assert item['sk'] == 'USAGE'

    def test_returns_success(self) -> None:
        repo, table, _ = _make_repo()

        result = repo.set_unlimited_usage('user-010')

        assert result.success is True

    def test_returns_error_on_dynamo_failure(self) -> None:
        repo, table, _ = _make_repo(put_item_side_effect=_dynamodb_error('ServiceUnavailable'))

        result = repo.set_unlimited_usage('user-010')

        assert result.success is False
        assert result.code == ResultCode.DYNAMODB_ERROR


# ─── update_customer_id / get_customer_id ────────────────────────────────────


@pytest.mark.unit
class TestCustomerId:
    def test_update_customer_id_writes_to_profile_row(self) -> None:
        repo, table, _ = _make_repo(update_item_return={})

        repo.update_customer_id('user-005', 'cus_existing001')

        kwargs = table.update_item.call_args.kwargs
        assert kwargs['Key'] == {'pk': 'USER#user-005', 'sk': 'PROFILE'}

    def test_get_customer_id_returns_value_when_present(self) -> None:
        repo, table, _ = _make_repo(get_item_return={'customer_id': 'cus_existing001'})

        result = repo.get_customer_id('user-005')

        assert result == 'cus_existing001'

    def test_get_customer_id_returns_none_when_absent(self) -> None:
        repo, table, _ = _make_repo()

        result = repo.get_customer_id('user-new')

        assert result is None

    def test_get_customer_id_returns_none_on_dynamo_error(self) -> None:
        repo, table, _ = _make_repo()
        table.get_item.side_effect = _dynamodb_error('InternalServerError')

        result = repo.get_customer_id('user-new')

        assert result is None


# ─── record_payment_event (idempotency) ───────────────────────────────────────


@pytest.mark.unit
class TestRecordPaymentEvent:
    def test_returns_true_on_first_delivery(self) -> None:
        repo, _, idempotency_table = _make_repo()
        idempotency_table.put_item.return_value = {}

        first = repo.record_payment_event('evt_001', 'checkout.session.completed')

        assert first is True

    def test_returns_false_on_duplicate_delivery(self) -> None:
        repo, _, idempotency_table = _make_repo()
        idempotency_table.put_item.side_effect = _dynamodb_error('ConditionalCheckFailedException')

        duplicate = repo.record_payment_event('evt_001', 'checkout.session.completed')

        assert duplicate is False

    def test_uses_attribute_not_exists_condition(self) -> None:
        repo, _, idempotency_table = _make_repo()

        repo.record_payment_event('evt_001', 'checkout.session.completed')

        kwargs = idempotency_table.put_item.call_args.kwargs
        assert kwargs['ConditionExpression'] == 'attribute_not_exists(id)'

    def test_stores_pk_with_payment_event_prefix(self) -> None:
        repo, _, idempotency_table = _make_repo()

        repo.record_payment_event('evt_abc123', 'invoice.payment_succeeded')

        item = idempotency_table.put_item.call_args.kwargs['Item']
        assert item['id'] == 'PAYMENT_EVENT#evt_abc123#invoice.payment_succeeded'

    def test_sets_ttl_expiration(self) -> None:
        repo, _, idempotency_table = _make_repo()

        repo.record_payment_event('evt_001', 'checkout.session.completed', ttl_seconds=3600)

        item = idempotency_table.put_item.call_args.kwargs['Item']
        assert 'expiration' in item
        assert isinstance(item['expiration'], int)
        assert item['expiration'] > 0

    def test_returns_false_on_other_dynamo_error(self) -> None:
        repo, _, idempotency_table = _make_repo()
        idempotency_table.put_item.side_effect = _dynamodb_error('ServiceUnavailable')

        result = repo.record_payment_event('evt_001', 'checkout.session.completed')

        assert result is False


# ─── scan_active_subscriptions ────────────────────────────────────────────────


@pytest.mark.unit
class TestScanActiveSubscriptions:
    def test_returns_active_items(self) -> None:
        repo, users_table, _ = _make_repo()
        item = _subscription_item(status='active')
        users_table.scan.return_value = {'Items': [item]}

        results = repo.scan_active_subscriptions()

        assert results == [item]

    def test_returns_empty_list_when_no_active_subscriptions(self) -> None:
        repo, users_table, _ = _make_repo()
        users_table.scan.return_value = {'Items': []}

        results = repo.scan_active_subscriptions()

        assert results == []

    def test_scans_users_table_not_idempotency(self) -> None:
        repo, users_table, idempotency_table = _make_repo()
        users_table.scan.return_value = {'Items': []}

        repo.scan_active_subscriptions()

        users_table.scan.assert_called_once()
        idempotency_table.scan.assert_not_called()

    def test_aliases_reserved_word_status(self) -> None:
        """status is a DynamoDB reserved word — must use ExpressionAttributeNames."""
        repo, users_table, _ = _make_repo()
        users_table.scan.return_value = {'Items': []}

        repo.scan_active_subscriptions()

        kwargs = users_table.scan.call_args.kwargs
        assert '#s' in kwargs.get('ExpressionAttributeNames', {})
        assert kwargs['ExpressionAttributeNames']['#s'] == 'status'

    def test_paginates_until_no_last_evaluated_key(self) -> None:
        """Must loop pages — a single scan is capped at 1 MB."""
        repo, users_table, _ = _make_repo()
        page1_item = _subscription_item(user_id='u1')
        page2_item = _subscription_item(user_id='u2')
        users_table.scan.side_effect = [
            {'Items': [page1_item], 'LastEvaluatedKey': {'pk': 'USER#u1'}},
            {'Items': [page2_item]},
        ]

        results = repo.scan_active_subscriptions()

        assert len(results) == 2
        assert users_table.scan.call_count == 2
        second_kwargs = users_table.scan.call_args_list[1].kwargs
        assert second_kwargs.get('ExclusiveStartKey') == {'pk': 'USER#u1'}

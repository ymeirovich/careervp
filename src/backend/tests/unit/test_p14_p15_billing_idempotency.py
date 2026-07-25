"""RED contract tests for P-14 billing/worker idempotency and P-15 Query-only lookup."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

from careervp.dal.subscription_repository import SubscriptionRepository
from careervp.handlers import company_research_worker_handler
from careervp.logic.webhook_service import WebhookService
from careervp.payment_providers.mock_provider import MockProvider

_IDEMPOTENCY_TABLE_NAME = 'careervp-idempotency-table-test'
_USERS_TABLE_NAME = 'careervp-users-table-test'
_IDEMPOTENCY_INDEX_NAME = 'idempotency-key-index'
_CUSTOMER_ID_INDEX_NAME = 'customer-id-index'
_WEBHOOK_SECRET_PARAMETER_NAME = '/careervp/test/payment-provider-webhook-secret'
_WORKER_APPLICATION_ID = 'app-p14-001'
_WORKER_ARTIFACT_TYPE = 'company_research'
_WORKER_OPERATION = 'generate'
_WORKER_IDEMPOTENCY_KEY = f'WORKER_OPERATION#{_WORKER_APPLICATION_ID}#{_WORKER_ARTIFACT_TYPE}#{_WORKER_OPERATION}'
_PAYMENT_EVENT_RETENTION_SECONDS = 604800


def _create_idempotency_table(dynamodb: Any) -> Any:
    """Create the idempotency table with its named duplicate-detection GSI."""
    return dynamodb.create_table(
        TableName=_IDEMPOTENCY_TABLE_NAME,
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'idempotency_key', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': _IDEMPOTENCY_INDEX_NAME,
                'KeySchema': [{'AttributeName': 'idempotency_key', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
        BillingMode='PAY_PER_REQUEST',
    )


def _create_users_table(dynamodb: Any) -> Any:
    return dynamodb.create_table(
        TableName=_USERS_TABLE_NAME,
        KeySchema=[
            {'AttributeName': 'pk', 'KeyType': 'HASH'},
            {'AttributeName': 'sk', 'KeyType': 'RANGE'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'pk', 'AttributeType': 'S'},
            {'AttributeName': 'sk', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )


def _runtime_webhook_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    """Model P-06: env carries only the parameter name; value is resolved at runtime."""
    monkeypatch.setenv(
        'PAYMENT_PROVIDER_WEBHOOK_SECRET_SSM_PARAM',
        _WEBHOOK_SECRET_PARAMETER_NAME,
    )
    return secrets.token_urlsafe(32)


def _signed_checkout_event(
    *,
    secret: str,
    event_id: str | None,
    timestamp: int,
) -> tuple[bytes, str]:
    body: dict[str, Any] = {
        'type': 'checkout.session.completed',
        'created': timestamp,
        'data': {
            'object': {
                'subscription': 'sub_p14_001',
                'customer': 'cus_p14_001',
                'metadata': {'user_id': 'user-p14-001', 'plan': 'monthly'},
            }
        },
    }
    if event_id is not None:
        body['id'] = event_id
    payload = json.dumps(body, separators=(',', ':')).encode()
    signed_payload = f'{timestamp}.'.encode() + payload
    signature = hmac.new(
        secret.encode(),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    return payload, f't={timestamp},v1={signature}'


def _real_subscription_repository(dynamodb: Any) -> SubscriptionRepository:
    return SubscriptionRepository(
        table_name=_USERS_TABLE_NAME,
        idempotency_table_name=_IDEMPOTENCY_TABLE_NAME,
        dynamodb_resource=dynamodb,
    )


def test_p14_webhook_replay_same_event_id_single_side_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-P14-1: replay returns {'status_code': 200} twice and performs one upsert."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        _create_users_table(dynamodb)
        _create_idempotency_table(dynamodb)
        repository = _real_subscription_repository(dynamodb)
        secret = _runtime_webhook_secret(monkeypatch)
        timestamp = int(time.time())
        payload, signature = _signed_checkout_event(
            secret=secret,
            event_id='evt_p14_replay_001',
            timestamp=timestamp,
        )
        service = WebhookService(
            subscription_repo=repository,
            payment_provider=MockProvider(),
            primary_secret=secret,
        )

        with patch.object(
            repository,
            'upsert_subscription',
            wraps=repository.upsert_subscription,
        ) as upsert_subscription:
            first = service.handle_webhook(payload, signature)
            replay = service.handle_webhook(payload, signature)

        assert upsert_subscription.call_count == 1, 'AC-P14-1 requires exactly one subscription mutation for duplicate delivery'
        assert first == {'status_code': 200}, 'AC-P14-1 pins the recorded success result'
        assert replay == first, "AC-P14-1 requires the replay to return the recorded {'status_code': 200} result"


def test_p14_worker_replay_same_business_id_single_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-P14-2: one company-research generation for one stable business operation."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = _create_idempotency_table(dynamodb)
        monkeypatch.setenv('IDEMPOTENCY_TABLE_NAME', _IDEMPOTENCY_TABLE_NAME)
        record = {
            'messageId': 'message-p14-worker-001',
            'body': json.dumps(
                {
                    'user_id': 'user-p14-001',
                    'job_id': _WORKER_APPLICATION_ID,
                    'application_id': _WORKER_APPLICATION_ID,
                    'company_name': 'Example Company',
                }
            ),
            'attributes': {'ApproximateReceiveCount': '1'},
        }
        app_repository = MagicMock()
        app_repository.get.return_value = {'artifact_statuses': {_WORKER_ARTIFACT_TYPE: 'pending'}}
        process_artifact = MagicMock()

        with (
            patch.object(
                company_research_worker_handler,
                '_get_app_repo',
                return_value=app_repository,
            ),
            patch.object(
                company_research_worker_handler,
                '_async_process_record',
                new=process_artifact,
            ),
            patch('careervp.handlers.company_research_worker_handler.asyncio.run'),
        ):
            company_research_worker_handler._process_record(record)
            company_research_worker_handler._process_record(record)

        assert process_artifact.call_count == 1, 'AC-P14-2 requires replay suppression before a second artifact side effect'
        response = table.scan()
        assert response['Count'] == 1, 'AC-P14-2 requires exactly one durable idempotency record'
        assert response['Items'][0]['id'] == _WORKER_IDEMPOTENCY_KEY, (
            f'AC-P14-2 stable key must be exactly {_WORKER_IDEMPOTENCY_KEY}, never request-timestamp-derived'
        )


def test_p15_billing_lookup_uses_query_not_scan() -> None:
    """AC-P15-1: customer lookup queries customer-id-index and never scans."""
    dynamodb = MagicMock()
    users_table = MagicMock()
    idempotency_table = MagicMock()
    dynamodb.Table.side_effect = lambda name: idempotency_table if name == _IDEMPOTENCY_TABLE_NAME else users_table
    users_table.query.return_value = {'Items': []}
    repository = SubscriptionRepository(
        table_name=_USERS_TABLE_NAME,
        idempotency_table_name=_IDEMPOTENCY_TABLE_NAME,
        dynamodb_resource=dynamodb,
    )

    repository.get_subscription_by_customer_id('cus_p15_001')

    users_table.query.assert_called_once()
    query = users_table.query.call_args.kwargs
    assert query['IndexName'] == _CUSTOMER_ID_INDEX_NAME, 'AC-P15-1 requires the customer-id-index, not email-index'
    expression = query['KeyConditionExpression'].get_expression()
    partition_key, expected_customer_id = expression['values']
    assert partition_key.name == 'customer_id', 'AC-P15-1 requires customer_id as the GSI partition key'
    assert expected_customer_id == 'cus_p15_001', 'AC-P15-1 requires an equality query for the provider customer id'
    users_table.scan.assert_not_called()


def test_p14_idempotency_ttl_is_set() -> None:
    """AC-P14-1: expiration is exactly 604800 seconds after the claim epoch."""
    claim_time = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)
    claim_epoch = int(claim_time.timestamp())
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = _create_idempotency_table(dynamodb)
        _create_users_table(dynamodb)
        repository = _real_subscription_repository(dynamodb)

        with patch('careervp.dal.subscription_repository.datetime') as mocked_datetime:
            mocked_datetime.now.return_value = claim_time
            is_new = repository.record_payment_event(
                'evt_p14_ttl_001',
                'checkout.session.completed',
            )

        assert is_new is True, 'AC-P14-1 requires the first event claim to succeed'
        item = table.get_item(Key={'id': ('PAYMENT_EVENT#evt_p14_ttl_001#checkout.session.completed')})['Item']
        assert 'expiration' in item, 'AC-P14-1 requires the DynamoDB TTL attribute named expiration'
        assert item['expiration'] - claim_epoch == _PAYMENT_EVENT_RETENTION_SECONDS, (
            'AC-P14-1 requires an exact 604800-second (7-day) retention window'
        )

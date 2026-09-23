"""RED B-2-2 coverage reassigned to P-14 by Wave 2 step 2.1."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from typing import Any
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from careervp.dal.subscription_repository import SubscriptionRepository
from careervp.logic.webhook_service import WebhookService
from careervp.payment_providers.mock_provider import MockProvider

_IDEMPOTENCY_TABLE_NAME = 'careervp-idempotency-table-b22-test'
_USERS_TABLE_NAME = 'careervp-users-table-b22-test'
_WEBHOOK_SECRET_PARAMETER_NAME = '/careervp/test/payment-provider-webhook-secret'


def _create_tables(dynamodb: Any) -> Any:
    dynamodb.create_table(
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
    return dynamodb.create_table(
        TableName=_IDEMPOTENCY_TABLE_NAME,
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )


def _same_logical_event_retry(secret: str) -> tuple[bytes, str]:
    timestamp = int(time.time())
    payload = json.dumps(
        {
            'type': 'checkout.session.completed',
            'created': timestamp,
            'data': {
                'object': {
                    'subscription': 'sub_b22_001',
                    'customer': 'cus_b22_001',
                    'metadata': {
                        'user_id': 'user-b22-001',
                        'plan': 'monthly',
                    },
                }
            },
        },
        separators=(',', ':'),
    ).encode()
    digest = hmac.new(
        secret.encode(),
        f'{timestamp}.'.encode() + payload,
        hashlib.sha256,
    ).hexdigest()
    return payload, f't={timestamp},v1={digest}'


def test_p25_mock_event_id_is_stable_across_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-P14-1 / B-2-2: one logical provider event keeps one id and one side effect."""
    monkeypatch.setenv(
        'PAYMENT_PROVIDER_WEBHOOK_SECRET_SSM_PARAM',
        _WEBHOOK_SECRET_PARAMETER_NAME,
    )
    secret = secrets.token_urlsafe(32)
    provider = MockProvider()
    payload, signature = _same_logical_event_retry(secret)

    first_verified = provider.construct_webhook_event(payload, signature, secret)
    retry_verified = provider.construct_webhook_event(payload, signature, secret)

    assert retry_verified.event_id == first_verified.event_id, (
        'AC-P14-1 / B-2-2 requires the same logical provider event to retain the same event_id across delivery attempts'
    )

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        idempotency_table = _create_tables(dynamodb)
        repository = SubscriptionRepository(
            table_name=_USERS_TABLE_NAME,
            idempotency_table_name=_IDEMPOTENCY_TABLE_NAME,
            dynamodb_resource=dynamodb,
        )
        service = WebhookService(
            subscription_repo=repository,
            payment_provider=provider,
            primary_secret=secret,
        )

        with patch.object(
            repository,
            'upsert_subscription',
            wraps=repository.upsert_subscription,
        ) as upsert_subscription:
            service.handle_webhook(payload, signature)
            service.handle_webhook(payload, signature)

        assert upsert_subscription.call_count == 1, 'AC-P14-1 / B-2-2 requires the second provider retry to be suppressed'
        assert idempotency_table.scan()['Count'] == 1, 'AC-P14-1 / B-2-2 requires one durable payment-event claim'

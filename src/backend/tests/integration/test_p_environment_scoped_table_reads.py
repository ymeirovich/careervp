"""A repository built without an explicit table-name override must read the
table belonging to its own ENVIRONMENT, never a sibling environment's.

Live archetype (HANDOFF-09): SubscriptionRepository reads TABLE_NAME, which
job-api/gap-api/application-api never set — before the fix this always fell
back to ``careervp-users-table-dev`` regardless of the real deploy
environment. A test that only creates one table cannot detect a cross-
environment read; this one stands up both ``-dev`` and ``-devx`` users tables
with different data and proves ``ENVIRONMENT=devx`` reads the devx row.

Spec: docs/handoff/2026-09-21-HANDOFF-09-environment-coupling.md, Step 3.5.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import boto3
import pytest
from moto import mock_aws

from careervp.dal.subscription_repository import SUBSCRIPTION_SK, SubscriptionRepository
from careervp.logic.quota_service import QuotaError, QuotaService

pytestmark = pytest.mark.integration

USER_ID = 'user-cross-env-001'


def _create_users_table(dynamodb: Any, table_name: str) -> Any:
    table = dynamodb.create_table(
        TableName=table_name,
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
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    return table


def _seed_subscription(table: Any, status: str) -> None:
    table.put_item(
        Item={
            'pk': f'USER#{USER_ID}',
            'sk': SUBSCRIPTION_SK,
            'user_id': USER_ID,
            'status': status,
            'plan': 'monthly',
        }
    )


class _AlwaysTrialExhausted:
    """A trial service that would always block — used to prove which
    subscription row (dev's ``active`` or devx's ``canceled``) was read,
    since only the subscription path can grant or block before this is
    ever consulted."""

    def get_usage(self, user_id: str) -> dict[str, Any]:
        return {'trial_active': False, 'credits_remaining': 0}


@pytest.fixture
def dual_environment_users_tables(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, Any]]:
    monkeypatch.delenv('TABLE_NAME', raising=False)
    monkeypatch.delenv('IDEMPOTENCY_TABLE_NAME', raising=False)
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dev_table = _create_users_table(dynamodb, 'careervp-users-table-dev')
        devx_table = _create_users_table(dynamodb, 'careervp-users-table-devx')

        # The dev row is active (would be granted access); the devx row is
        # canceled (must be blocked). Any test that reads the wrong table
        # gets the wrong verdict.
        _seed_subscription(dev_table, status='active')
        _seed_subscription(devx_table, status='canceled')

        yield {'dev': dev_table, 'devx': devx_table}


def test_check_access_reads_its_own_environments_table_not_devs(
    dual_environment_users_tables: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('ENVIRONMENT', 'devx')

    repo = SubscriptionRepository()
    quota = QuotaService(subscription_repo=repo, trial_service=_AlwaysTrialExhausted())

    with pytest.raises(QuotaError, match='subscription_required'):
        quota.check_access(USER_ID)


def test_check_access_in_dev_reads_devs_table(
    dual_environment_users_tables: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('ENVIRONMENT', 'dev')

    repo = SubscriptionRepository()
    quota = QuotaService(subscription_repo=repo, trial_service=_AlwaysTrialExhausted())

    quota.check_access(USER_ID)  # active subscription — must not raise

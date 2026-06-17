"""FE-UI-044 red integration tests for legacy Company Research dual-read."""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import boto3
import pytest
from moto import mock_aws

pytestmark = pytest.mark.integration


def _create_artifacts_table(dynamodb: Any, table_name: str) -> Any:
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'applicationId', 'KeyType': 'HASH'},
            {'AttributeName': 'artifactId', 'KeyType': 'RANGE'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'applicationId', 'AttributeType': 'S'},
            {'AttributeName': 'artifactId', 'AttributeType': 'S'},
            {'AttributeName': 'artifactType', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'type-index',
                'KeySchema': [
                    {'AttributeName': 'applicationId', 'KeyType': 'HASH'},
                    {'AttributeName': 'artifactType', 'KeyType': 'RANGE'},
                ],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    return table


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


def _create_knowledge_table(dynamodb: Any, table_name: str) -> Any:
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'userEmail', 'KeyType': 'HASH'},
            {'AttributeName': 'knowledgeType', 'KeyType': 'RANGE'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'userEmail', 'AttributeType': 'S'},
            {'AttributeName': 'knowledgeType', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    return table


@pytest.fixture
def legacy_store_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-cr-dual-read-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('POWERTOOLS_TRACE_DISABLED', 'true')
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'careervp-artifacts-table-test')
    monkeypatch.setenv('TABLE_NAME', 'careervp-users-table-test')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
    monkeypatch.setenv('KNOWLEDGE_TABLE_NAME', 'careervp-knowledge-table-test')
    monkeypatch.setenv('CR_CONFIDENCE_THRESHOLD', '0.85')

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        _create_artifacts_table(dynamodb, 'careervp-artifacts-table-test')
        users_table = _create_users_table(dynamodb, 'careervp-users-table-test')
        _create_knowledge_table(dynamodb, 'careervp-knowledge-table-test')
        yield users_table


def _seed_legacy_cr(users_table: Any, *, user_id: str = 'user-1', cr_job_id: str = 'app-1') -> None:
    users_table.put_item(
        Item={
            'pk': user_id,
            'sk': f'ARTIFACT#COMPANY_RESEARCH#{cr_job_id}',
            'user_id': user_id,
            'job_id': cr_job_id,
            'company_research_id': 'legacy-cr-1',
            'company_name': 'Acme',
            'confidence_score': Decimal('0.91'),
            'created_at': '2026-06-14T09:05:00+00:00',
            'research_data': {
                'company_name': 'Acme',
                'overview': 'Acme builds reliable workflow automation for enterprise teams.',
                'mission': 'Make enterprise work easier to operate.',
                'values': ['Reliability', 'Customer focus'],
                'strategic_priorities': ['Workflow automation', 'Enterprise AI'],
                'recent_news': ['Launched an AI operations suite'],
                'financial_summary': 'Privately held',
                'confidence_score': Decimal('0.91'),
                'research_timestamp': '2026-06-14T09:00:00+00:00',
            },
            'entity_type': 'COMPANY_RESEARCH',
        }
    )


def test_legacy_dual_read_resolves_when_feature_flag_enabled(monkeypatch: pytest.MonkeyPatch, legacy_store_env: Any) -> None:
    from careervp.logic.company_research_store import read_cr_artifact

    _seed_legacy_cr(legacy_store_env)
    monkeypatch.setenv('COMPANY_RESEARCH_LEGACY_READ_ENABLED', 'true')

    item = read_cr_artifact(application_id='app-1', user_id='user-1')

    assert item is not None
    assert item['user_id'] == 'user-1'
    assert item['company_research_id'] == 'legacy-cr-1'
    assert item['company_name'] == 'Acme'


def test_legacy_dual_read_does_not_resolve_when_feature_flag_disabled(monkeypatch: pytest.MonkeyPatch, legacy_store_env: Any) -> None:
    from careervp.logic.company_research_store import read_cr_artifact

    _seed_legacy_cr(legacy_store_env)
    monkeypatch.setenv('COMPANY_RESEARCH_LEGACY_READ_ENABLED', 'false')

    assert read_cr_artifact(application_id='app-1', user_id='user-1') is None

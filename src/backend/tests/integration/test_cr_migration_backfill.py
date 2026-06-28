"""FE-UI-044 T5 integration tests for Company Research migration backfill."""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import boto3
import pytest
from moto import mock_aws

pytestmark = pytest.mark.integration


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


def _create_applications_table(dynamodb: Any, table_name: str) -> Any:
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'userId', 'KeyType': 'HASH'},
            {'AttributeName': 'applicationId', 'KeyType': 'RANGE'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'userId', 'AttributeType': 'S'},
            {'AttributeName': 'applicationId', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    return table


@pytest.fixture
def migration_tables(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, Any]]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-cr-migration-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('POWERTOOLS_TRACE_DISABLED', 'true')
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'careervp-artifacts-table-dev')

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        yield {
            'users': _create_users_table(dynamodb, 'careervp-users-table-dev'),
            'artifacts': _create_artifacts_table(dynamodb, 'careervp-artifacts-table-dev'),
            'applications': _create_applications_table(dynamodb, 'careervp-applications-table-dev'),
        }


def _seed_application(applications_table: Any) -> None:
    applications_table.put_item(
        Item={
            'userId': 'user-1',
            'applicationId': 'app-real-1',
            'application_id': 'app-real-1',
            'user_id': 'user-1',
            'company_name': 'Acme',
            'state': 'artifacts_generating',
            'entity_type': 'APPLICATION',
        }
    )


def _seed_legacy_cr(users_table: Any, *, company_name: str, cr_job_id: str, confidence_score: Decimal) -> None:
    users_table.put_item(
        Item={
            'pk': 'user-1',
            'sk': f'ARTIFACT#COMPANY_RESEARCH#{cr_job_id}',
            'user_id': 'user-1',
            'job_id': cr_job_id,
            'company_research_id': f'legacy-{cr_job_id}',
            'company_name': company_name,
            'overview': f'{company_name} builds reliable workflow automation for enterprise teams.',
            'mission': 'Make enterprise work easier to operate.',
            'values': ['Reliability', 'Customer focus'],
            'strategic_priorities': ['Workflow automation', 'Enterprise AI'],
            'recent_news': ['Launched an AI operations suite'],
            'financial_summary': 'Privately held',
            'confidence_score': confidence_score,
            'created_at': '2026-06-14T09:05:00+00:00',
            'research_data': {
                'company_name': company_name,
                'overview': f'{company_name} builds reliable workflow automation for enterprise teams.',
                'confidence_score': confidence_score,
                'research_timestamp': '2026-06-14T09:00:00+00:00',
            },
            'entity_type': 'COMPANY_RESEARCH',
        }
    )


def test_cr_migration_backfills_by_resolved_application_id_and_is_idempotent(
    migration_tables: dict[str, Any],
    tmp_path: Path,
) -> None:
    from scripts.cr_migration_backfill import MigrationConfig, run_migration

    _seed_application(migration_tables['applications'])
    _seed_legacy_cr(migration_tables['users'], company_name='Acme', cr_job_id='cr-job-1', confidence_score=Decimal('0.91'))
    _seed_legacy_cr(migration_tables['users'], company_name='Unmapped Co', cr_job_id='cr-job-2', confidence_score=Decimal('0.72'))

    report_path = tmp_path / 'quarantine.json'
    first_result = run_migration(
        MigrationConfig(
            apply=True,
            quarantine_report_path=report_path,
        )
    )

    assert first_result.scanned_count == 2
    assert first_result.migrate_count == 1
    assert first_result.skip_already_present_count == 0
    assert first_result.quarantine_count == 1

    stored = migration_tables['artifacts'].get_item(
        Key={
            'applicationId': 'app-real-1',
            'artifactId': 'ARTIFACT#COMPANY_RESEARCH#app-real-1',
        }
    )['Item']
    assert stored['applicationId'] == 'app-real-1'
    assert stored['artifactType'] == 'company_research'
    assert stored['user_id'] == 'user-1'
    assert stored['company_name'] == 'Acme'
    assert float(stored['confidence_score']) == pytest.approx(0.91)

    assert report_path.exists()
    assert 'cr-job-2' in report_path.read_text(encoding='utf-8')

    second_result = run_migration(
        MigrationConfig(
            apply=True,
            quarantine_report_path=report_path,
        )
    )

    assert second_result.scanned_count == 2
    assert second_result.migrate_count == 0
    assert second_result.skip_already_present_count == 1
    assert second_result.quarantine_count == 1
    scan = migration_tables['artifacts'].scan()['Items']
    assert len(scan) == 1

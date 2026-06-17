"""FE-UI-044 red integration tests for canonical Company Research storage."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

import boto3
import pytest
from moto import mock_aws

from careervp.models.company import CompanyResearchResult, ResearchSource

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
            {'AttributeName': 'entityId', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'entity-index',
                'KeySchema': [
                    {'AttributeName': 'knowledgeType', 'KeyType': 'HASH'},
                    {'AttributeName': 'entityId', 'KeyType': 'RANGE'},
                ],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    return table


@pytest.fixture
def canonical_store_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-cr-canonical-store-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('POWERTOOLS_TRACE_DISABLED', 'true')
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'careervp-artifacts-table-test')
    monkeypatch.setenv('TABLE_NAME', 'careervp-users-table-test')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
    monkeypatch.setenv('KNOWLEDGE_TABLE_NAME', 'careervp-knowledge-table-test')
    monkeypatch.setenv('COMPANY_RESEARCH_LEGACY_READ_ENABLED', 'true')
    monkeypatch.setenv('CR_CONFIDENCE_THRESHOLD', '0.85')

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        artifacts_table = _create_artifacts_table(dynamodb, 'careervp-artifacts-table-test')
        _create_users_table(dynamodb, 'careervp-users-table-test')
        _create_knowledge_table(dynamodb, 'careervp-knowledge-table-test')
        yield artifacts_table


def _research_result(*, company_name: str = 'Acme', confidence_score: float = 0.91) -> CompanyResearchResult:
    return CompanyResearchResult(
        company_name=company_name,
        overview='Acme builds reliable workflow automation for enterprise teams.',
        mission='Make enterprise work easier to operate.',
        values=['Reliability', 'Customer focus'],
        strategic_priorities=['Workflow automation', 'Enterprise AI'],
        recent_news=['Launched an AI operations suite'],
        financial_summary='Privately held',
        source=ResearchSource.WEBSITE_SCRAPE,
        source_urls=['https://acme.example/about'],
        confidence_score=confidence_score,
        research_timestamp=datetime(2026, 6, 14, 9, 0, tzinfo=timezone.utc),
    )


def test_canonical_store_roundtrip_uses_artifacts_table_despite_knowledge_table(canonical_store_env: Any) -> None:
    from careervp.logic.company_research import load_confident_company_research_artifact
    from careervp.logic.company_research_store import read_cr_artifact, write_cr_artifact

    write_cr_artifact(application_id='app-1', user_id='user-1', result=_research_result())

    raw_item = read_cr_artifact(application_id='app-1', user_id='user-1')
    confident_artifact = load_confident_company_research_artifact(application_id='app-1', user_id='user-1')

    assert raw_item is not None
    assert raw_item['applicationId'] == 'app-1'
    assert raw_item['artifactId'] == 'ARTIFACT#COMPANY_RESEARCH#app-1'
    assert raw_item['artifactType'] == 'company_research'
    assert raw_item['user_id'] == 'user-1'
    assert raw_item['company_name'] == 'Acme'
    assert float(raw_item['confidence_score']) == pytest.approx(0.91)

    assert confident_artifact is not None
    assert confident_artifact.company_context.company_name == 'Acme'
    assert confident_artifact.company_context.mission == 'Make enterprise work easier to operate.'
    assert confident_artifact.company_research_id


def test_canonical_store_enforces_ownership(canonical_store_env: Any) -> None:
    from careervp.logic.company_research_store import read_cr_artifact, write_cr_artifact

    write_cr_artifact(application_id='app-1', user_id='user-1', result=_research_result())

    assert read_cr_artifact(application_id='app-1', user_id='other-user') is None


def test_confident_loader_preserves_confidence_gate(canonical_store_env: Any) -> None:
    from careervp.logic.company_research import load_confident_company_research_artifact
    from careervp.logic.company_research_store import write_cr_artifact

    write_cr_artifact(application_id='app-1', user_id='user-1', result=_research_result(confidence_score=0.7))

    assert load_confident_company_research_artifact(application_id='app-1', user_id='user-1') is None

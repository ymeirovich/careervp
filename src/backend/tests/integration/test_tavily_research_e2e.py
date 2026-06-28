"""Integration tests for Tavily-backed company research confidence gating."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Mapping, cast
from unittest.mock import AsyncMock, MagicMock, patch

import boto3
import pytest
from moto import mock_aws
from pydantic import HttpUrl

from careervp.handlers.company_research_worker_handler import CRWorkerInput, _async_process_record
from careervp.logic.company_research import load_confident_company_research_artifact
from careervp.logic.company_research_store import read_cr_artifact
from careervp.models.company import SearchResult
from careervp.models.result import Result, ResultCode

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


@pytest.fixture
def canonical_store_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-tavily-research-e2e-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('POWERTOOLS_TRACE_DISABLED', 'true')
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'careervp-artifacts-table-test')
    monkeypatch.setenv('TABLE_NAME', 'careervp-users-table-test')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
    monkeypatch.setenv('APPLICATIONS_TABLE_NAME', 'careervp-users-table-test')
    monkeypatch.setenv('CR_CONFIDENCE_THRESHOLD', '0.85')
    monkeypatch.setenv('VPR_JOBS_QUEUE_URL', '')

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        artifacts_table = _create_artifacts_table(dynamodb, 'careervp-artifacts-table-test')
        users_table = dynamodb.create_table(
            TableName='careervp-users-table-test',
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
        users_table.meta.client.get_waiter('table_exists').wait(TableName='careervp-users-table-test')
        yield artifacts_table


class _DummyRouter:
    def __init__(self, payload: Mapping[str, object]) -> None:
        self._payload = payload

    def invoke(self, **kwargs: object) -> Result[dict[str, str]]:
        import json

        return Result(success=True, data={'text': json.dumps(self._payload)}, code=ResultCode.SUCCESS)


def _app_repo() -> MagicMock:
    repo = MagicMock()
    repo.get.return_value = {'artifact_statuses': {}}
    return repo


def _search_result(title: str, url: str, snippet: str) -> SearchResult:
    return SearchResult(title=title, url=cast(HttpUrl, url), snippet=snippet)


@pytest.mark.asyncio
async def test_research_company_persists_completed_with_web_api(canonical_store_env: Any) -> None:
    input_data = CRWorkerInput(
        user_id='user-1',
        job_id='app-1',
        company_name='Acme Corp',
        domain='acme.com',
    )
    search_results = [
        {
            'title': 'Acme About',
            'url': 'https://acme.com/about',
            'snippet': ' '.join(['Acme Corp builds workflow software for enterprise teams.'] * 60),
        },
        {
            'title': 'Acme News',
            'url': 'https://news.example/acme',
            'snippet': ' '.join(['Acme Corp recently expanded leadership and launched new products.'] * 40),
        },
    ]
    llm_payload = {
        'overview': 'Acme Corp builds workflow software for enterprise teams.',
        'mission': 'Make enterprise work easier to operate.',
        'values': ['Reliability', 'Customer focus'],
        'strategic_priorities': ['Workflow automation', 'Enterprise AI'],
        'recent_news': ['Expanded leadership team'],
        'financial_summary': 'Privately held',
        'key_products': ['Workflow Cloud'],
        'company_size': '201-500 employees',
        'key_executives': ['Alex Rivera, CEO'],
        'competitive_positioning': 'Enterprise workflow automation for regulated teams.',
        'growth_signals': ['Launched new products', 'Expanded leadership team'],
    }
    app_repo = _app_repo()

    with (
        patch('careervp.logic.company_research.get_llm_router', return_value=_DummyRouter(llm_payload)),
        patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=app_repo),
        patch('careervp.handlers.company_research_worker_handler._enqueue_vpr_standalone'),
        patch(
            'careervp.logic.company_research.search_company_info',
            new_callable=AsyncMock,
            return_value=Result(
                success=True,
                data=[_search_result(item['title'], item['url'], item['snippet']) for item in search_results],
                code=ResultCode.SUCCESS,
            ),
        ),
    ):
        await _async_process_record(input_data, receive_count=1)

    raw_item = read_cr_artifact(application_id='app-1', user_id='user-1')
    confident_artifact = load_confident_company_research_artifact(application_id='app-1', user_id='user-1')

    assert raw_item is not None
    assert raw_item['artifactType'] == 'company_research'
    assert raw_item['company_name'] == 'Acme Corp'
    assert float(raw_item['confidence_score']) >= 0.85
    assert raw_item['research_data']['source'] == 'web_api'
    assert raw_item['research_data']['key_products'] == ['Workflow Cloud']
    assert confident_artifact is not None
    assert confident_artifact.company_context.key_products == ['Workflow Cloud']
    app_repo.update_artifact_status.assert_called_once()


@pytest.mark.asyncio
async def test_second_company_with_ambiguous_name_degrades(canonical_store_env: Any) -> None:
    input_data = CRWorkerInput(
        user_id='user-1',
        job_id='app-2',
        company_name='Acme Corp',
        domain='acme.com',
    )
    llm_payload = {
        'overview': 'A different company overview.',
        'mission': 'Do something else.',
        'values': ['Speed'],
        'strategic_priorities': ['Growth'],
        'recent_news': ['Wrong company news'],
        'financial_summary': 'Unknown',
        'key_products': ['Other product'],
        'company_size': '51-200 employees',
        'key_executives': ['Someone Else'],
        'competitive_positioning': 'Wrong market positioning',
        'growth_signals': ['General search momentum'],
    }
    app_repo = _app_repo()

    with (
        patch(
            'careervp.logic.company_research.search_company_info',
            new_callable=AsyncMock,
            side_effect=[
                Result(success=False, error='site miss', code=ResultCode.NO_RESULTS),
                Result(
                    success=True,
                    data=[
                        _search_result(
                            'Another Acme',
                            'https://other.example/about',
                            ' '.join(['This company serves a different market entirely.'] * 80),
                        )
                    ],
                    code=ResultCode.SUCCESS,
                ),
            ],
        ),
        patch('careervp.logic.company_research.get_llm_router', return_value=_DummyRouter(llm_payload)),
        patch('careervp.handlers.company_research_worker_handler._get_app_repo', return_value=app_repo),
        patch('careervp.handlers.company_research_worker_handler._enqueue_vpr_standalone'),
    ):
        await _async_process_record(input_data, receive_count=3)

    assert read_cr_artifact(application_id='app-2', user_id='user-1') is None
    app_repo.set_company_research_error.assert_called_once_with(application_id='app-2', user_id='user-1', error=True)
    app_repo.update_artifact_status.assert_called_once_with(
        application_id='app-2',
        user_id='user-1',
        artifact_type='company_research',
        status='failed',
    )

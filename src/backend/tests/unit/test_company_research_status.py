"""Unit tests for company research GET status endpoint."""

import json
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def company_research_status_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-company-research-status-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('ENV', 'local')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-company-research-table')
    yield


@pytest.fixture
def company_research_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-company-research-table',
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
        table.meta.client.get_waiter('table_exists').wait(TableName='test-company-research-table')
        yield table


def _event(path: str, method: str, user_id: str = 'user-1', path_parameters: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        'resource': path,
        'path': path,
        'httpMethod': method,
        'headers': {
            'Content-Type': 'application/json',
            'x-user-id': user_id,
        },
        'multiValueHeaders': {},
        'queryStringParameters': None,
        'multiValueQueryStringParameters': None,
        'pathParameters': path_parameters,
        'stageVariables': None,
        'requestContext': {
            'resourcePath': path,
            'httpMethod': method,
            'path': path,
            'stage': 'test',
            'requestId': 'req-1',
            'authorizer': {'claims': {'sub': user_id}},
        },
        'body': None,
        'isBase64Encoded': False,
    }


def _context() -> Any:
    context = MagicMock()
    context.aws_request_id = 'req-1'
    context.function_name = 'company-research-handler'
    return context


def test_get_company_research_returns_200_ok(company_research_table: Any) -> None:
    """GET /company-research/{jobId} should return 200 (not 201)."""
    from careervp.handlers.company_research_handler import lambda_handler

    now = datetime.now(timezone.utc).isoformat()
    company_research_table.put_item(
        Item={
            'pk': 'user-1',
            'sk': 'ARTIFACT#COMPANY_RESEARCH#job-123',
            'user_id': 'user-1',
            'job_id': 'job-123',
            'company_research_id': 'job-123',
            'company_name': 'Acme Corp',
            'mission': 'Build reliable tooling for developers.',
            'values': ['Ownership', 'Curiosity'],
            'recent_news': [{'title': 'Acme expands EU team', 'date': '2026-01-20'}],
            'culture': 'Collaborative and high-accountability.',
            'products': ['Acme Cloud', 'Acme CLI'],
            'funding_status': 'Series C',
            'size_range': '201-500',
            'industry': 'Developer Tools',
            'created_at': now,
            'updated_at': now,
            'ttl': 9999999999,
        }
    )

    event = _event(
        path='/company-research/job-123',
        method='GET',
        path_parameters={'jobId': 'job-123'},
    )
    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200


def test_get_company_research_matches_openapi_schema(company_research_table: Any) -> None:
    """GET /company-research/{jobId} should match OpenAPI CompanyResearchResultResponse shape."""
    from careervp.handlers.company_research_handler import lambda_handler

    now = datetime.now(timezone.utc).isoformat()
    company_research_table.put_item(
        Item={
            'pk': 'user-1',
            'sk': 'ARTIFACT#COMPANY_RESEARCH#job-456',
            'user_id': 'user-1',
            'job_id': 'job-456',
            'research_data': {
                'company_name': 'Beta Labs',
                'mission': 'Advance applied AI safely.',
                'values': ['Integrity', 'Impact'],
                'recent_news': ['Beta opens new R&D center'],
                'overview': 'Product-first culture with strong experimentation mindset.',
                'products': ['Beta Studio'],
                'financial_summary': 'Profitable since 2025',
                'size_range': '51-200',
                'industry': 'AI Software',
            },
            'created_at': now,
            'updated_at': now,
            'ttl': 9999999999,
        }
    )

    event = _event(
        path='/company-research/job-456',
        method='GET',
        path_parameters={'jobId': 'job-456'},
    )
    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])

    expected_keys = {
        'id',
        'company_name',
        'mission',
        'values',
        'recent_news',
        'culture',
        'products',
        'funding_status',
        'size_range',
        'industry',
    }
    assert expected_keys.issubset(payload.keys())
    assert payload['id'] == 'job-456'
    assert payload['company_name'] == 'Beta Labs'
    assert payload['mission'] == 'Advance applied AI safely.'
    assert payload['values'] == ['Integrity', 'Impact']
    assert isinstance(payload['recent_news'], list)
    assert payload['recent_news'][0]['title'] == 'Beta opens new R&D center'
    assert payload['recent_news'][0]['date'] == ''

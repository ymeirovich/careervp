"""Unit tests for gap analysis handler endpoints."""

import json
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def gap_test_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-gap-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-gap-table')
    yield


@pytest.fixture
def gap_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-gap-table',
            KeySchema=[
                {'AttributeName': 'applicationId', 'KeyType': 'HASH'},
                {'AttributeName': 'artifactId', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'applicationId', 'AttributeType': 'S'},
                {'AttributeName': 'artifactId', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        table.meta.client.get_waiter('table_exists').wait(TableName='test-gap-table')
        yield table


def _event(
    path: str,
    method: str,
    body: dict[str, Any] | None = None,
    user_id: str = 'user-1',
    path_parameters: dict[str, str] | None = None,
) -> dict[str, Any]:
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
            'authorizer': {'principalId': user_id},
        },
        'body': json.dumps(body) if body is not None else None,
        'isBase64Encoded': False,
    }


def _context() -> Any:
    context = MagicMock()
    context.aws_request_id = 'req-1'
    context.function_name = 'gap-handler'
    return context


def test_generate_questions_returns_200_and_persists(gap_table: Any) -> None:
    """POST /gap-analysis/questions returns 200 and stores generated questions."""
    from careervp.handlers.gap_handler import lambda_handler

    event = _event(
        path='/gap-analysis/questions',
        method='POST',
        body={
            'cv_id': 'cv-123',
            'job_id': 'job-123',
            'max_questions': 3,
            'focus_areas': ['python', 'system design'],
        },
    )

    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['job_id'] == 'job-123'
    assert payload['cv_id'] == 'cv-123'
    assert len(payload['questions']) == 3

    stored = gap_table.get_item(
        Key={
            'applicationId': 'GAP_ANALYSIS#cv-123#job-123',
            'artifactId': 'QUESTION_SET',
        }
    ).get('Item')
    assert isinstance(stored, dict)
    assert stored.get('job_id') == 'job-123'
    assert len(stored.get('questions', [])) == 3


def test_get_questions_returns_200(gap_table: Any) -> None:
    """GET /gap-analysis/{jobId}/questions returns stored questions."""
    from careervp.handlers.gap_handler import lambda_handler

    now = datetime.now(timezone.utc).isoformat()
    gap_table.put_item(
        Item={
            'applicationId': 'GAP_ANALYSIS#cv-123#job-555',
            'artifactId': 'QUESTION_SET',
            'artifactType': 'gap_analysis',
            'user_id': 'user-1',
            'cv_id': 'cv-123',
            'job_id': 'job-555',
            'questions': [
                {
                    'id': 'gap-q1',
                    'text': 'Question text',
                    'tags': ['python'],
                    'strategic_intent': 'Intent',
                    'evidence_gap': 'Gap',
                }
            ],
            'created_at': now,
            'updated_at': now,
            'expiration': 9999999999,
        }
    )

    event = _event(
        path='/gap-analysis/job-555/questions',
        method='GET',
        path_parameters={'jobId': 'job-555'},
    )

    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['job_id'] == 'job-555'
    assert len(payload['questions']) == 1


def test_submit_response_returns_200(gap_table: Any) -> None:
    """POST /gap-analysis/responses returns 200 and persists responses."""
    from careervp.handlers.gap_handler import lambda_handler

    event = _event(
        path='/gap-analysis/responses',
        method='POST',
        body={
            'job_id': 'job-222',
            'responses': [
                {
                    'question_id': 'q1',
                    'response': 'I improved latency by 30%.',
                    'quantifiable_data': {'percentage': 30},
                }
            ],
        },
    )

    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['status'] == 'saved'
    assert payload['job_id'] == 'job-222'

    stored = gap_table.get_item(
        Key={
            'applicationId': 'GAP_RESPONSES#job-222',
            'artifactId': 'RESPONSE_SET',
        }
    ).get('Item')
    assert isinstance(stored, dict), f'Expected dict but got None. Stored keys: {list(stored.keys()) if stored else "None"}'
    assert stored.get('job_id') == 'job-222'
    assert len(stored.get('responses', [])) == 1


def test_submit_response_infers_job_id_from_latest_questions(gap_table: Any) -> None:
    """POST /gap-analysis/responses infers missing job_id from latest question set."""
    from careervp.handlers.gap_handler import lambda_handler

    now = datetime.now(timezone.utc).isoformat()
    gap_table.put_item(
        Item={
            'applicationId': 'GAP_ANALYSIS#cv-older#job-older',
            'artifactId': 'QUESTION_SET',
            'artifactType': 'gap_analysis',
            'user_id': 'user-1',
            'cv_id': 'cv-older',
            'job_id': 'job-older',
            'questions': [{'id': 'gap-q1', 'text': 'older'}],
            'created_at': now,
            'updated_at': '2024-01-01T00:00:00+00:00',
            'expiration': 9999999999,
        }
    )
    gap_table.put_item(
        Item={
            'applicationId': 'GAP_ANALYSIS#cv-latest#job-latest',
            'artifactId': 'QUESTION_SET',
            'artifactType': 'gap_analysis',
            'user_id': 'user-1',
            'cv_id': 'cv-latest',
            'job_id': 'job-latest',
            'questions': [{'id': 'gap-q1', 'text': 'latest'}],
            'created_at': now,
            'updated_at': '2026-01-01T00:00:00+00:00',
            'expiration': 9999999999,
        }
    )

    event = _event(
        path='/gap-analysis/responses',
        method='POST',
        body={
            'responses': [
                {
                    'question_id': 'gap-q1',
                    'response': 'Evidence-backed response.',
                }
            ],
        },
    )

    response = lambda_handler(event, _context())
    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['job_id'] == 'job-latest'

    stored = gap_table.get_item(
        Key={
            'applicationId': 'GAP_RESPONSES#job-latest',
            'artifactId': 'RESPONSE_SET',
        }
    ).get('Item')
    assert isinstance(stored, dict)
    assert stored.get('job_id') == 'job-latest'


def test_get_responses_returns_200(gap_table: Any) -> None:
    """GET /gap-analysis/responses/{jobId} returns saved responses."""
    from careervp.handlers.gap_handler import lambda_handler

    now = datetime.now(timezone.utc).isoformat()
    gap_table.put_item(
        Item={
            'applicationId': 'GAP_RESPONSES#job-999',
            'artifactId': 'RESPONSE_SET',
            'artifactType': 'gap_responses',
            'user_id': 'user-1',
            'job_id': 'job-999',
            'responses': [
                {'question_id': 'q9', 'response': 'Built distributed systems.'},
            ],
            'created_at': now,
            'updated_at': now,
            'expiration': 9999999999,
        }
    )

    event = _event(
        path='/gap-analysis/responses/job-999',
        method='GET',
        path_parameters={'jobId': 'job-999'},
    )

    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['job_id'] == 'job-999'
    assert len(payload['responses']) == 1

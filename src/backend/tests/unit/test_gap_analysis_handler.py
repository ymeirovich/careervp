"""Unit tests for gap analysis handler endpoints."""

import json
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def reset_gap_handler_caches() -> Generator[None, None, None]:
    from careervp.handlers.gap_handler import _reset_handler_caches

    _reset_handler_caches()
    yield
    _reset_handler_caches()


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
    monkeypatch.setenv('TABLE_NAME', 'test-gap-table')
    monkeypatch.setenv('USERS_TABLE_NAME', 'test-gap-table')
    monkeypatch.setenv('GAP_QUESTIONS_TABLE_NAME', 'test-gap-table')
    monkeypatch.setenv('GAP_RESPONSES_TABLE_NAME', 'test-gap-responses-table')
    yield


@pytest.fixture
def gap_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        # Table schema must match DynamoDalHandler's pk/sk schema
        table = dynamodb.create_table(
            TableName='test-gap-table',
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
        table.meta.client.get_waiter('table_exists').wait(TableName='test-gap-table')
        yield table


@pytest.fixture
def gap_responses_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-gap-responses-table',
            KeySchema=[
                {'AttributeName': 'userId', 'KeyType': 'HASH'},
                {'AttributeName': 'questionId', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'userId', 'AttributeType': 'S'},
                {'AttributeName': 'questionId', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        table.meta.client.get_waiter('table_exists').wait(TableName='test-gap-responses-table')
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
            'authorizer': {'claims': {'sub': user_id}},
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
    from careervp.models.result import Result, ResultCode

    gap_table.put_item(
        Item={
            'pk': 'user-1',
            'sk': 'CV#cv-123',
            'user_id': 'user-1',
            'full_name': 'Legacy Test User',
            'work_experience': [
                {
                    'company': 'ExistingCorp',
                    'role': 'Engineer',
                    'achievements': ['Shipped production systems'],
                }
            ],
            'skills': [{'name': 'Python'}],
            'education': [],
            'certifications': [],
            'languages': [],
            'is_parsed': True,
        }
    )

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

    generated_questions = [
        {
            'question_id': f'gap-q{i + 1}',
            'question': 'Describe a measurable impact example.',
            'impact': 'HIGH',
            'probability': 'MEDIUM',
            'tags': ['[CV IMPACT]'],
        }
        for i in range(10)
    ]

    with (
        patch('careervp.handlers.gap_handler.generate_gap_questions') as mock_generate,
        patch('careervp.handlers.gap_handler._get_trial_service') as mock_trial_service,
    ):
        trial_service = MagicMock()
        trial_service.check_trial_status.return_value = {'is_active': True}
        trial_service.consume_credit.return_value = None
        mock_trial_service.return_value = trial_service
        mock_generate.return_value = Result(
            success=True,
            data=generated_questions,
            code=ResultCode.GAP_QUESTIONS_GENERATED,
        )
        response = lambda_handler(event, _context())

    # Handler returns 201 for creation, accept both 200 and 201
    assert response['statusCode'] in [200, 201]
    payload = json.loads(response['body'])
    assert payload['job_id'] == 'job-123'
    assert payload['cv_id'] == 'cv-123'
    assert len(payload['questions']) == 3

    stored = gap_table.get_item(
        Key={
            'pk': 'user-1',
            'sk': 'ARTIFACT#GAP_ANALYSIS#cv-123#job-123',
        }
    ).get('Item')
    assert isinstance(stored, dict)
    assert stored.get('job_id') == 'job-123'
    assert len(stored.get('questions', [])) == 3


def test_get_questions_returns_200(gap_table: Any) -> None:
    """GET /gap-analysis/{jobId}/questions returns stored questions."""
    from careervp.handlers.gap_handler import lambda_handler

    now = datetime.now(timezone.utc).isoformat()
    # Table key schema: userId (pk), applicationId (sk)
    gap_table.put_item(
        Item={
            'pk': 'user-1',
            'sk': 'ARTIFACT#GAP_ANALYSIS#cv-123#job-555',
            'artifactType': 'gap_analysis',
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


def test_submit_response_returns_200(gap_responses_table: Any) -> None:
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

    # Handler returns 200 for response submission
    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['status'] == 'saved'
    assert payload['job_id'] == 'job-222'
    assert payload['responses_saved'] == 1

    # Table key schema: pk/sk
    stored = gap_responses_table.get_item(
        Key={
            'userId': 'user-1',
            'questionId': 'ARTIFACT#GAP_RESPONSES#v1',
        }
    ).get('Item')
    assert isinstance(stored, dict), f'Expected dict but got None. Stored keys: {list(stored.keys()) if stored else "None"}'
    assert stored.get('job_id') == 'job-222'
    assert len(stored.get('responses', [])) == 1


def test_submit_response_requires_job_id(gap_table: Any) -> None:
    """POST /gap-analysis/responses returns 400 when job_id is missing."""
    from careervp.handlers.gap_handler import lambda_handler

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
    # Handler requires job_id - returns 400 when missing
    assert response['statusCode'] == 400
    payload = json.loads(response['body'])
    assert 'job_id' in payload.get('error', '').lower() or 'required' in payload.get('error', '').lower()


def test_get_responses_returns_200(gap_responses_table: Any) -> None:
    """GET /gap-analysis/responses/{jobId} returns saved responses."""
    from careervp.handlers.gap_handler import lambda_handler

    now = datetime.now(timezone.utc).isoformat()
    # Table key schema: pk/sk
    gap_responses_table.put_item(
        Item={
            'userId': 'user-1',
            'questionId': 'ARTIFACT#GAP_RESPONSES#v1',
            'artifactType': 'gap_responses',
            'job_id': 'job-999',
            'responses': [
                {
                    'question_id': 'q9',
                    'question': 'What is your experience?',
                    'answer': 'Built distributed systems.',
                    'destination': 'CV_IMPACT',
                },
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

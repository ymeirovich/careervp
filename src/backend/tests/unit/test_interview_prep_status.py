"""Unit tests for interview prep status endpoint."""

import json
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def interview_prep_status_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-interview-prep-status-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('AUTHORIZER_DISABLED', 'true')
    monkeypatch.setenv('TABLE_NAME', 'test-interview-prep-table')
    yield


@pytest.fixture
def interview_prep_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-interview-prep-table',
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
        table.meta.client.get_waiter('table_exists').wait(TableName='test-interview-prep-table')
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
        },
        'body': None,
        'isBase64Encoded': False,
    }


def _context() -> Any:
    context = MagicMock()
    context.aws_request_id = 'req-1'
    context.function_name = 'interview-prep-handler'
    return context


def test_get_interview_prep_status_returns_prep_data(interview_prep_table: Any) -> None:
    """GET /interview-prep/{interviewPrepId} should return prep status/result payload."""
    from careervp.handlers.interview_prep_handler import lambda_handler

    prep_artifact_id = 'ARTIFACT#INTERVIEW_PREP#prep-123#v1'
    now = datetime.now(timezone.utc).isoformat()
    interview_prep_table.put_item(
        Item={
            'pk': 'user-1',
            'sk': prep_artifact_id,
            'artifact_type': 'interview_prep',
            'user_id': 'user-1',
            'status': 'completed',
            'interview_prep': {
                'prep_id': 'prep-123',
                'questions': [
                    {
                        'question_id': 'q1',
                        'question': 'Tell me about a scaling challenge you solved.',
                        'suggested_answer': {
                            'format': 'STAR',
                            'situation': 'Legacy service had peak outages.',
                            'task': 'Stabilize the platform.',
                            'action': 'Implemented queue-based backpressure.',
                            'result': 'Reduced incidents by 70%.',
                        },
                    }
                ],
            },
            'created_at': now,
            'updated_at': now,
            'ttl': 9999999999,
        }
    )

    event = _event(
        path='/interview-prep/prep-123',
        method='GET',
        path_parameters={'interviewPrepId': 'prep-123'},
    )
    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['id'] == 'prep-123'
    assert payload['status'] == 'completed'
    assert len(payload['result']['questions']) == 1
    question = payload['result']['questions'][0]
    assert question['id'] == 'q1'
    assert question['text'] == 'Tell me about a scaling challenge you solved.'
    assert question['suggested_answer']['format'] == 'STAR'


def test_get_interview_prep_status_is_user_scoped(interview_prep_table: Any) -> None:
    """GET /interview-prep/{interviewPrepId} should not return another user's artifact."""
    from careervp.handlers.interview_prep_handler import lambda_handler

    now = datetime.now(timezone.utc).isoformat()
    interview_prep_table.put_item(
        Item={
            'pk': 'owner-user',
            'sk': 'ARTIFACT#INTERVIEW_PREP#prep-private#v1',
            'artifact_type': 'interview_prep',
            'user_id': 'owner-user',
            'status': 'completed',
            'interview_prep': {'prep_id': 'prep-private', 'questions': []},
            'created_at': now,
            'updated_at': now,
            'ttl': 9999999999,
        }
    )

    event = _event(
        path='/interview-prep/prep-private',
        method='GET',
        user_id='different-user',
        path_parameters={'interviewPrepId': 'prep-private'},
    )
    response = lambda_handler(event, _context())

    assert response['statusCode'] == 404

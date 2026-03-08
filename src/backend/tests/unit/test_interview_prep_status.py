"""Unit tests for interview prep status endpoint."""

import json
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import boto3  # type: ignore[import-untyped]
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
    monkeypatch.setenv('ENV', 'local')
    monkeypatch.setenv('TABLE_NAME', 'test-interview-prep-table')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-interview-prep-table')
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'test-interview-prep-table')
    yield


@pytest.fixture
def interview_prep_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-interview-prep-table',
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
            'authorizer': {'claims': {'sub': user_id}},
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
    """GET /interview-prep/{interviewPrepId}/status returns prep status/result payload."""
    from careervp.handlers.interview_prep_handler import lambda_handler

    prep_artifact_id = 'ARTIFACT#INTERVIEW_PREP#prep-123'
    now = datetime.now(timezone.utc).isoformat()
    interview_prep_table.put_item(
        Item={
            'applicationId': 'user-1',
            'artifactId': prep_artifact_id,
            'artifactType': 'interview_prep',
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
            'expiration': 9999999999,
            'pk': 'user-1',
            'sk': prep_artifact_id,
        }
    )

    event = _event(
        path='/interview-prep/prep-123/status',
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
    """GET /interview-prep/{interviewPrepId}/status does not return another user's artifact."""
    from careervp.handlers.interview_prep_handler import lambda_handler
    from careervp.models.result import ResultCode

    now = datetime.now(timezone.utc).isoformat()
    interview_prep_table.put_item(
        Item={
            'applicationId': 'owner-user',
            'artifactId': 'ARTIFACT#INTERVIEW_PREP#prep-private',
            'artifactType': 'interview_prep',
            'user_id': 'owner-user',
            'status': 'completed',
            'interview_prep': {'prep_id': 'prep-private', 'questions': []},
            'created_at': now,
            'updated_at': now,
            'expiration': 9999999999,
        }
    )

    event = _event(
        path='/interview-prep/prep-private/status',
        method='GET',
        user_id='different-user',
        path_parameters={'interviewPrepId': 'prep-private'},
    )
    response = lambda_handler(event, _context())

    assert response['statusCode'] == 404
    payload = json.loads(response['body'])
    assert payload['code'] == ResultCode.INTERVIEW_PREP_NOT_FOUND


def test_unknown_interview_prep_id_returns_domain_not_found_code(interview_prep_table: Any) -> None:
    """Unknown interview prep ID returns interview-prep-specific 404 code."""
    from careervp.handlers.interview_prep_handler import lambda_handler
    from careervp.models.result import ResultCode

    event = _event(
        path='/interview-prep/does-not-exist/status',
        method='GET',
        path_parameters={'interviewPrepId': 'does-not-exist'},
    )
    response = lambda_handler(event, _context())

    assert response['statusCode'] == 404
    payload = json.loads(response['body'])
    assert payload['code'] == ResultCode.INTERVIEW_PREP_NOT_FOUND


def test_interview_prep_dal_prefers_artifacts_table_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """Status/read path should use the same table precedence as submit path."""
    from careervp.handlers import interview_prep_handler as module

    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'artifacts-table')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'dynamodb-table')

    with patch.object(module, 'DynamoDalHandler') as mock_dal_cls:
        module._get_dal()

    mock_dal_cls.assert_called_once_with('artifacts-table')


def test_artifacts_schema_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Status lookup uses artifacts-table key schema {applicationId, artifactId}."""
    from careervp.handlers import interview_prep_handler as module

    mock_table = MagicMock()
    mock_table.get_item.return_value = {
        'Item': {
            'applicationId': 'user-1',
            'artifactId': 'ARTIFACT#INTERVIEW_PREP#prep-123',
            'status': 'PENDING',
        }
    }
    mock_dal = MagicMock()
    mock_dal._get_db_handler.return_value = mock_table
    mock_dal.table_name = 'artifacts-table'

    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'artifacts-table')

    with patch.object(module, '_get_dal', return_value=mock_dal):
        item = module._get_interview_prep_item('user-1', 'prep-123')

    assert item is not None
    mock_table.get_item.assert_called_once_with(Key={'applicationId': 'user-1', 'artifactId': 'ARTIFACT#INTERVIEW_PREP#prep-123'})

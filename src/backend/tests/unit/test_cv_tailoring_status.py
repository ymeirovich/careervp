"""Unit tests for CV tailoring status and list endpoints."""

import json
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def cv_tailoring_status_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-cv-tailoring-status-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('AUTHORIZER_DISABLED', 'true')
    monkeypatch.setenv('TABLE_NAME', 'test-tailoring-table')
    yield


@pytest.fixture
def tailoring_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-tailoring-table',
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
        table.meta.client.get_waiter('table_exists').wait(TableName='test-tailoring-table')
        yield table


def _event(
    path: str,
    method: str,
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
        },
        'body': None,
        'isBase64Encoded': False,
    }


def _context() -> Any:
    context = MagicMock()
    context.aws_request_id = 'req-1'
    context.function_name = 'cv-tailoring-handler'
    return context


def test_get_cv_tailoring_status_returns_status_and_result(tailoring_table: Any) -> None:
    """GET /cv-tailoring/{cvTailoringId} returns status payload for a stored artifact."""
    from careervp.handlers.cv_tailoring_handler import lambda_handler

    tailoring_id = 'TAILORED_CV#cv-1#1700000000#v1'
    now = datetime.now(timezone.utc).isoformat()
    tailoring_table.put_item(
        Item={
            'pk': 'user-1',
            'sk': tailoring_id,
            'entity_type': 'CV_TAILORING',
            'user_id': 'user-1',
            'cv_id': 'cv-1',
            'status': 'completed',
            'tailored_cv': {'summary': 'Tailored summary text'},
            'estimated_ats_score': 91,
            'keyword_matches': {'matched': ['python'], 'missing': ['kubernetes']},
            'fvs_validation': {'is_valid': True, 'violations': []},
            'created_at': now,
            'updated_at': now,
            'ttl': 9999999999,
        }
    )

    event = _event(
        path=f'/cv-tailoring/{tailoring_id}',
        method='GET',
        path_parameters={'cvTailoringId': tailoring_id},
    )

    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['id'] == tailoring_id
    assert payload['status'] == 'completed'
    assert payload['result']['tailored_cv']['summary'] == 'Tailored summary text'
    assert payload['result']['ats_score'] == 91


def test_get_users_me_tailored_cvs_returns_only_user_items(tailoring_table: Any) -> None:
    """GET /users/me/tailored-cvs returns only the authenticated user's artifacts."""
    from careervp.handlers.cv_tailoring_handler import lambda_handler

    now = datetime.now(timezone.utc).isoformat()
    tailoring_table.put_item(
        Item={
            'pk': 'user-1',
            'sk': 'TAILORED_CV#cv-1#1700000000#v1',
            'entity_type': 'CV_TAILORING',
            'cv_id': 'cv-1',
            'status': 'completed',
            'created_at': now,
            'updated_at': now,
            'ttl': 9999999999,
        }
    )
    tailoring_table.put_item(
        Item={
            'pk': 'user-1',
            'sk': 'TAILORED_CV#cv-2#1700000001#v1',
            'entity_type': 'CV_TAILORING',
            'cv_id': 'cv-2',
            'status': 'processing',
            'created_at': now,
            'updated_at': now,
            'ttl': 9999999999,
        }
    )
    tailoring_table.put_item(
        Item={
            'pk': 'other-user',
            'sk': 'TAILORED_CV#cv-9#1700000002#v1',
            'entity_type': 'CV_TAILORING',
            'cv_id': 'cv-9',
            'status': 'completed',
            'created_at': now,
            'updated_at': now,
            'ttl': 9999999999,
        }
    )

    event = _event(path='/users/me/tailored-cvs', method='GET', user_id='user-1')
    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    ids = {entry['id'] for entry in payload['tailored_cvs']}
    assert ids == {
        'TAILORED_CV#cv-1#1700000000#v1',
        'TAILORED_CV#cv-2#1700000001#v1',
    }
    assert all(entry['status'] in {'completed', 'processing'} for entry in payload['tailored_cvs'])

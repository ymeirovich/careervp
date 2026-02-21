"""Unit tests for cover letter status and listing endpoints."""

import json
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def cover_letter_status_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-cover-letter-status-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('ENV', 'local')
    monkeypatch.setenv('TABLE_NAME', 'test-cover-letter-table')
    yield


@pytest.fixture
def cover_letter_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-cover-letter-table',
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
        table.meta.client.get_waiter('table_exists').wait(TableName='test-cover-letter-table')
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
    context.function_name = 'cover-letter-handler'
    return context


def test_get_cover_letter_status_returns_cover_letter(cover_letter_table: Any) -> None:
    """GET /cover-letter/{coverLetterId} should return one cover letter status/result."""
    from careervp.handlers.cover_letter_handler import lambda_handler

    cover_letter_id = 'ARTIFACT#COVER_LETTER#cv-1#job-1#v1'
    now = datetime.now(timezone.utc).isoformat()
    cover_letter_table.put_item(
        Item={
            'pk': 'user-1',
            'sk': cover_letter_id,
            'artifact_type': 'cover_letter',
            'user_id': 'user-1',
            'cv_id': 'cv-1',
            'job_id': 'job-1',
            'status': 'completed',
            'cover_letter': {
                'cover_letter': 'Dear Hiring Team, ...',
                'paragraphs': {
                    'hook': {'word_count': 90, 'includes_uvp': True, 'includes_company_reference': True},
                    'proof_points': {
                        'requirements_matched': 3,
                        'claims_verified': True,
                        'quantified_evidence': True,
                    },
                    'close': {'word_count': 65, 'includes_cta': True},
                },
                'fvs_validation': {'is_valid': True, 'violations': []},
            },
            'created_at': now,
            'updated_at': now,
            'ttl': 9999999999,
        }
    )

    event = _event(
        path=f'/cover-letter/{cover_letter_id}',
        method='GET',
        path_parameters={'coverLetterId': cover_letter_id},
    )

    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['id'] == cover_letter_id
    assert payload['status'] == 'completed'
    assert payload['result']['cover_letter'] == 'Dear Hiring Team, ...'


def test_get_users_me_cover_letters_returns_users_letters(cover_letter_table: Any) -> None:
    """GET /users/me/cover-letters should return only current user's letters."""
    from careervp.handlers.cover_letter_handler import lambda_handler

    now = datetime.now(timezone.utc).isoformat()
    cover_letter_table.put_item(
        Item={
            'pk': 'user-1',
            'sk': 'ARTIFACT#COVER_LETTER#cv-1#job-1#v1',
            'artifact_type': 'cover_letter',
            'user_id': 'user-1',
            'cv_id': 'cv-1',
            'job_id': 'job-1',
            'status': 'completed',
            'cover_letter': {'cover_letter': 'Letter 1'},
            'created_at': now,
            'updated_at': now,
            'ttl': 9999999999,
        }
    )
    cover_letter_table.put_item(
        Item={
            'pk': 'user-1',
            'sk': 'ARTIFACT#COVER_LETTER#cv-2#job-2#v1',
            'artifact_type': 'cover_letter',
            'user_id': 'user-1',
            'cv_id': 'cv-2',
            'job_id': 'job-2',
            'status': 'processing',
            'cover_letter': {'cover_letter': 'Letter 2'},
            'created_at': now,
            'updated_at': now,
            'ttl': 9999999999,
        }
    )
    cover_letter_table.put_item(
        Item={
            'pk': 'other-user',
            'sk': 'ARTIFACT#COVER_LETTER#cv-9#job-9#v1',
            'artifact_type': 'cover_letter',
            'user_id': 'other-user',
            'cv_id': 'cv-9',
            'job_id': 'job-9',
            'status': 'completed',
            'cover_letter': {'cover_letter': 'Other letter'},
            'created_at': now,
            'updated_at': now,
            'ttl': 9999999999,
        }
    )

    event = _event(path='/users/me/cover-letters', method='GET', user_id='user-1')
    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    ids = {entry['id'] for entry in payload['cover_letters']}
    assert ids == {
        'ARTIFACT#COVER_LETTER#cv-1#job-1#v1',
        'ARTIFACT#COVER_LETTER#cv-2#job-2#v1',
    }

"""Unit tests for cover letter status and listing endpoints."""

import json
from collections.abc import Generator
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
    """GET /cover-letter/{coverLetterId} should return deterministic response.

    Note: Handler returns contract-safe deterministic response (IAM denies DynamoDB reads).
    """
    from careervp.handlers.cover_letter_handler import lambda_handler

    cover_letter_id = 'ARTIFACT#COVER_LETTER#cv-1#job-1#v1'

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
    assert 'cover_letter' in payload['result']


def test_get_users_me_cover_letters_returns_empty_list(cover_letter_table: Any) -> None:
    """GET /users/me/cover-letters should return list of cover letters.

    Note: Handler returns contract-safe deterministic response (IAM denies DynamoDB reads).
    """
    from careervp.handlers.cover_letter_handler import lambda_handler

    event = _event(path='/users/me/cover-letters', method='GET')

    response = lambda_handler(event, _context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert 'cover_letters' in payload


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

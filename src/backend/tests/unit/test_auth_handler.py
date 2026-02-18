"""
Unit tests for auth API endpoints.
"""

from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import boto3
import jwt
import pytest
from boto3.dynamodb.conditions import Key
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from moto import mock_aws


def _generate_rsa_key_pair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('utf-8')
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode('utf-8')
    )
    return private_pem, public_pem


TEST_PRIVATE_KEY, TEST_PUBLIC_KEY = _generate_rsa_key_pair()


@pytest.fixture(autouse=True)
def auth_test_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-auth-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('POWERTOOLS_TRACE_DISABLED', 'true')
    monkeypatch.setenv('TABLE_NAME', 'test-users-table')
    monkeypatch.setenv('JWT_PRIVATE_KEY', TEST_PRIVATE_KEY)
    monkeypatch.setenv('JWT_PUBLIC_KEY', TEST_PUBLIC_KEY)

    from careervp.handlers.auth_handler import _reset_auth_service_cache

    _reset_auth_service_cache()
    yield
    _reset_auth_service_cache()


@pytest.fixture
def users_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-users-table',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'email', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'email-index',
                    'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        table.meta.client.get_waiter('table_exists').wait(TableName='test-users-table')
        yield table


def _generate_api_gw_event(
    path: str,
    method: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    request_headers = {'Content-Type': 'application/json'}
    if headers:
        request_headers.update(headers)

    return {
        'version': '1.0',
        'resource': path,
        'path': path,
        'httpMethod': method,
        'headers': request_headers,
        'multiValueHeaders': {},
        'queryStringParameters': None,
        'multiValueQueryStringParameters': None,
        'requestContext': {
            'accountId': '123456789012',
            'apiId': 'testapi',
            'domainName': 'testapi.execute-api.us-east-1.amazonaws.com',
            'domainPrefix': 'testapi',
            'httpMethod': method,
            'path': path,
            'protocol': 'HTTP/1.1',
            'requestId': 'test-request-id',
            'requestTime': '01/Jan/2026:00:00:00 +0000',
            'requestTimeEpoch': 1767225600000,
            'stage': 'test',
        },
        'pathParameters': None,
        'stageVariables': None,
        'body': json.dumps(body) if body is not None else None,
        'isBase64Encoded': False,
    }


def _generate_lambda_context() -> Any:
    context = MagicMock()
    context.aws_request_id = 'test-request-id'
    context.function_name = 'auth-handler'
    context.memory_limit_in_mb = 256
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:auth-handler'
    return context


def test_register_creates_user(users_table: Any) -> None:
    """POST /auth/register should create a user and return RS256 JWTs."""
    from careervp.handlers.auth_handler import lambda_handler

    event = _generate_api_gw_event(
        path='/auth/register',
        method='POST',
        body={
            'email': 'new.user@example.com',
            'password': 'StrongPass123!',
            'name': 'New User',
        },
    )

    response = lambda_handler(event, _generate_lambda_context())

    assert response['statusCode'] == 201
    payload = json.loads(response['body'])
    assert payload['token_type'] == 'Bearer'
    assert payload['expires_in'] == 3600
    assert payload['access_token']
    assert payload['refresh_token']

    access_claims = jwt.decode(payload['access_token'], TEST_PUBLIC_KEY, algorithms=['RS256'])
    refresh_claims = jwt.decode(payload['refresh_token'], TEST_PUBLIC_KEY, algorithms=['RS256'])

    assert access_claims['user_id']
    assert access_claims['exp'] - access_claims['iat'] == 3600
    assert refresh_claims['exp'] - refresh_claims['iat'] == 604800

    query_response = users_table.query(
        IndexName='email-index',
        KeyConditionExpression=Key('email').eq('new.user@example.com'),
    )
    items = query_response.get('Items', [])
    assert len(items) == 1
    assert items[0]['name'] == 'New User'
    assert 'password_hash' in items[0]


def test_login_returns_jwt(users_table: Any) -> None:
    """POST /auth/login should authenticate and return JWT payload."""
    from careervp.handlers.auth_handler import lambda_handler

    register_event = _generate_api_gw_event(
        path='/auth/register',
        method='POST',
        body={
            'email': 'login.user@example.com',
            'password': 'LoginPass123!',
            'name': 'Login User',
        },
    )
    register_response = lambda_handler(register_event, _generate_lambda_context())
    assert register_response['statusCode'] == 201

    login_event = _generate_api_gw_event(
        path='/auth/login',
        method='POST',
        body={
            'email': 'login.user@example.com',
            'password': 'LoginPass123!',
        },
    )
    login_response = lambda_handler(login_event, _generate_lambda_context())

    assert login_response['statusCode'] == 200
    payload = json.loads(login_response['body'])
    assert payload['token_type'] == 'Bearer'
    assert payload['expires_in'] == 3600

    access_claims = jwt.decode(payload['access_token'], TEST_PUBLIC_KEY, algorithms=['RS256'])
    assert access_claims['user_id']
    assert access_claims['exp'] - access_claims['iat'] == 3600


def test_refresh_returns_new_jwt(users_table: Any) -> None:
    """POST /auth/refresh should issue a new token pair from refresh token."""
    from careervp.handlers.auth_handler import lambda_handler

    register_event = _generate_api_gw_event(
        path='/auth/register',
        method='POST',
        body={
            'email': 'refresh.user@example.com',
            'password': 'RefreshPass123!',
            'name': 'Refresh User',
        },
    )
    register_response = lambda_handler(register_event, _generate_lambda_context())
    assert register_response['statusCode'] == 201
    register_payload = json.loads(register_response['body'])

    refresh_event = _generate_api_gw_event(
        path='/auth/refresh',
        method='POST',
        headers={'Authorization': f'Bearer {register_payload["refresh_token"]}'},
    )
    refresh_response = lambda_handler(refresh_event, _generate_lambda_context())

    assert refresh_response['statusCode'] == 200
    payload = json.loads(refresh_response['body'])
    assert payload['access_token']
    assert payload['refresh_token']
    assert payload['token_type'] == 'Bearer'
    assert payload['expires_in'] == 3600

    access_claims = jwt.decode(payload['access_token'], TEST_PUBLIC_KEY, algorithms=['RS256'])
    refresh_claims = jwt.decode(payload['refresh_token'], TEST_PUBLIC_KEY, algorithms=['RS256'])
    assert access_claims['user_id']
    assert access_claims['exp'] - access_claims['iat'] == 3600
    assert refresh_claims['exp'] - refresh_claims['iat'] == 604800

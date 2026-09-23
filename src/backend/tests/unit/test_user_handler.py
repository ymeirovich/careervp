"""
Unit tests for user management endpoints.
"""

import json
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import boto3
import jwt
import pytest
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
def user_test_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-user-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('POWERTOOLS_TRACE_DISABLED', 'true')
    monkeypatch.setenv('TABLE_NAME', 'test-users-table')
    monkeypatch.setenv('CVS_TABLE_NAME', 'test-cvs-table')
    monkeypatch.setenv('JWT_PRIVATE_KEY', TEST_PRIVATE_KEY)
    monkeypatch.setenv('JWT_PUBLIC_KEY', TEST_PUBLIC_KEY)

    from careervp.handlers.user_handler import _reset_handler_caches

    _reset_handler_caches()
    yield
    _reset_handler_caches()


@pytest.fixture
def db_tables() -> Generator[dict[str, Any], None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        users_table = dynamodb.create_table(
            TableName='test-users-table',
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
        cvs_table = dynamodb.create_table(
            TableName='test-cvs-table',
            KeySchema=[
                {'AttributeName': 'userId', 'KeyType': 'HASH'},
                {'AttributeName': 'cvId', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'userId', 'AttributeType': 'S'},
                {'AttributeName': 'cvId', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        users_table.meta.client.get_waiter('table_exists').wait(TableName='test-users-table')
        cvs_table.meta.client.get_waiter('table_exists').wait(TableName='test-cvs-table')
        yield {'users': users_table, 'cvs': cvs_table}


def _generate_api_gw_event(
    path: str,
    method: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    query: dict[str, str] | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    request_headers = {'Content-Type': 'application/json'}
    if headers:
        request_headers.update(headers)

    request_context = {
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
    }

    # Add Cognito authorizer claims if user_id is provided
    if user_id:
        request_context['authorizer'] = {'claims': {'sub': user_id}}

    return {
        'version': '1.0',
        'resource': path,
        'path': path,
        'httpMethod': method,
        'headers': request_headers,
        'multiValueHeaders': {},
        'queryStringParameters': query,
        'multiValueQueryStringParameters': None,
        'requestContext': request_context,
        'pathParameters': None,
        'stageVariables': None,
        'body': json.dumps(body) if body is not None else None,
        'isBase64Encoded': False,
    }


def _generate_lambda_context() -> Any:
    context = MagicMock()
    context.aws_request_id = 'test-request-id'
    context.function_name = 'user-handler'
    context.memory_limit_in_mb = 256
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:user-handler'
    return context


def _create_access_token(user_id: str, email: str) -> str:
    issued_at = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'email': email,
        'token_type': 'access',
        'iat': int(issued_at.timestamp()),
        'exp': int((issued_at + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, TEST_PRIVATE_KEY, algorithm='RS256')


def _insert_user(table: Any, user_id: str, email: str, name: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    table.put_item(
        Item={
            'pk': f'USER#{user_id}',
            'sk': 'PROFILE',
            'user_id': user_id,
            'email': email,
            'name': name,
            'preferences': {},
            'created_at': now,
            'updated_at': now,
        }
    )


def test_get_current_user_returns_profile(db_tables: dict[str, Any]) -> None:
    """GET /users/me returns current user's profile."""
    from careervp.handlers.user_handler import lambda_handler

    user_id = 'user-123'
    email = 'user123@example.com'
    _insert_user(db_tables['users'], user_id=user_id, email=email, name='User 123')
    access_token = _create_access_token(user_id=user_id, email=email)

    event = _generate_api_gw_event(
        path='/users/me',
        method='GET',
        headers={'Authorization': f'Bearer {access_token}'},
        user_id=user_id,
    )
    response = lambda_handler(event, _generate_lambda_context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['user_id'] == user_id
    assert payload['email'] == email
    assert payload['name'] == 'User 123'


def test_update_current_user_modifies_profile(db_tables: dict[str, Any]) -> None:
    """PUT /users/me updates current user's profile fields."""
    from careervp.handlers.user_handler import lambda_handler

    user_id = 'user-456'
    email = 'user456@example.com'
    _insert_user(db_tables['users'], user_id=user_id, email=email, name='Old Name')
    access_token = _create_access_token(user_id=user_id, email=email)

    event = _generate_api_gw_event(
        path='/users/me',
        method='PUT',
        headers={'Authorization': f'Bearer {access_token}'},
        body={'name': 'Updated Name', 'timezone': 'UTC'},
        user_id=user_id,
    )
    response = lambda_handler(event, _generate_lambda_context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['user_id'] == user_id
    assert payload['name'] == 'Updated Name'
    assert payload['preferences']['timezone'] == 'UTC'

    item_response = db_tables['users'].get_item(Key={'pk': f'USER#{user_id}', 'sk': 'PROFILE'})
    stored = item_response.get('Item', {})
    assert stored.get('name') == 'Updated Name'
    assert stored.get('preferences', {}).get('timezone') == 'UTC'


def test_list_user_cvs_returns_own_records(db_tables: dict[str, Any]) -> None:
    """GET /users/me/cvs should return only authenticated user's CV records."""
    from careervp.handlers.user_handler import lambda_handler

    user_id = 'user-cvs'
    other_user_id = 'other-user'
    email = 'usercvs@example.com'
    _insert_user(db_tables['users'], user_id=user_id, email=email, name='CV User')
    access_token = _create_access_token(user_id=user_id, email=email)

    # CVs live in the CV table (userId/cvId), which is what GET /users/me/cv
    # now queries. Seeding the users table here would pass vacuously.
    db_tables['cvs'].put_item(Item={'userId': user_id, 'cvId': 'cv-1', 'fileName': 'resume-1.pdf'})
    db_tables['cvs'].put_item(Item={'userId': user_id, 'cvId': 'cv-2', 'fileName': 'resume-2.pdf'})
    db_tables['cvs'].put_item(Item={'userId': other_user_id, 'cvId': 'cv-3', 'fileName': 'other.pdf'})

    event = _generate_api_gw_event(
        path='/users/me/cvs',
        method='GET',
        headers={'Authorization': f'Bearer {access_token}'},
        user_id=user_id,
    )
    response = lambda_handler(event, _generate_lambda_context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    returned_ids = {item.get('cvId') or item.get('sk', '').replace('CV#', '') for item in payload['cvs']}
    assert returned_ids == {'cv-1', 'cv-2'}


def test_list_user_cvs_surfaces_query_failure_instead_of_an_empty_list(
    db_tables: dict[str, Any],
    monkeypatch: Any,
) -> None:
    """A failed CV query must be a 5xx, never a 200 with zero CVs.

    This is the trap the CV re-home walks into. users-table is keyed pk/sk and
    cvs-table is keyed userId/cvId, so pointing the reader at the new table
    while still sending the old key condition raises ValidationException. The
    previous implementation caught every exception here and returned
    ``[], None``, which renders as "you have no CVs" with a 200 — the user's CV
    list silently empties and nothing alarms.
    """
    from botocore.exceptions import ClientError

    from careervp.handlers.user_handler import lambda_handler

    user_id = 'user-cv-query-fail'
    email = 'cvqueryfail@example.com'
    _insert_user(db_tables['users'], user_id=user_id, email=email, name='CV User')
    access_token = _create_access_token(user_id=user_id, email=email)

    from unittest.mock import MagicMock

    import careervp.handlers.user_handler as user_handler_module

    failing_table = MagicMock()
    failing_table.query.side_effect = ClientError(
        {'Error': {'Code': 'ValidationException', 'Message': 'key element does not match the schema'}},
        'Query',
    )
    failing_resource = MagicMock()
    failing_resource.Table.return_value = failing_table
    monkeypatch.setattr(user_handler_module.boto3, 'resource', lambda *_a, **_k: failing_resource)

    event = _generate_api_gw_event(
        path='/users/me/cvs',
        method='GET',
        headers={'Authorization': f'Bearer {access_token}'},
        user_id=user_id,
    )
    # Loud by design: the error reaches Lambda, so it lands on the Errors metric
    # and the caller sees a 5xx. The failure mode being guarded against is the
    # opposite -- a 200 carrying {"cvs": []}.
    with pytest.raises(ClientError):
        lambda_handler(event, _generate_lambda_context())


def test_user_endpoints_require_auth(db_tables: dict[str, Any]) -> None:
    """Missing bearer token should return 401 for /users/me."""
    from careervp.handlers.user_handler import lambda_handler

    _insert_user(db_tables['users'], user_id='user-no-auth', email='noauth@example.com', name='No Auth')
    event = _generate_api_gw_event(path='/users/me', method='GET')
    response = lambda_handler(event, _generate_lambda_context())

    assert response['statusCode'] == 401


def test_user_can_only_access_own_data(db_tables: dict[str, Any]) -> None:
    """PUT /users/me ignores user_id in payload and uses authenticated user_id."""
    from careervp.handlers.user_handler import lambda_handler

    user_id = 'user-own'
    _insert_user(db_tables['users'], user_id=user_id, email='own@example.com', name='Own User')
    access_token = _create_access_token(user_id=user_id, email='own@example.com')

    # Even if payload contains different user_id, handler uses authenticated user_id
    event = _generate_api_gw_event(
        path='/users/me',
        method='PUT',
        headers={'Authorization': f'Bearer {access_token}'},
        body={'name': 'Updated Name', 'user_id': 'different-user'},
        user_id=user_id,
    )
    response = lambda_handler(event, _generate_lambda_context())

    # Handler should succeed using authenticated user_id, ignoring user_id in payload
    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['user_id'] == user_id
    assert payload['name'] == 'Updated Name'

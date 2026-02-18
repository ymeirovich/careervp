"""
Unit tests for job CRUD handler endpoints.
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
def job_test_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-job-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('POWERTOOLS_TRACE_DISABLED', 'true')
    monkeypatch.setenv('JOBS_TABLE_NAME', 'test-jobs-table')
    monkeypatch.setenv('VPR_JOBS_TABLE_NAME', 'test-jobs-table')
    monkeypatch.setenv('JWT_PRIVATE_KEY', TEST_PRIVATE_KEY)
    monkeypatch.setenv('JWT_PUBLIC_KEY', TEST_PUBLIC_KEY)

    from careervp.handlers.job_handler import _reset_handler_caches

    _reset_handler_caches()
    yield
    _reset_handler_caches()


@pytest.fixture
def jobs_table() -> Generator[Any, None, None]:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-jobs-table',
            KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'job_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        table.meta.client.get_waiter('table_exists').wait(TableName='test-jobs-table')
        yield table


def _generate_api_gw_event(
    path: str,
    method: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    query: dict[str, str] | None = None,
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
        'queryStringParameters': query,
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
    context.function_name = 'job-handler'
    context.memory_limit_in_mb = 256
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:job-handler'
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


def test_create_job_returns_201(jobs_table: Any) -> None:
    """POST /jobs returns 201 and persists a job."""
    from careervp.handlers.job_handler import lambda_handler

    access_token = _create_access_token(user_id='user-1', email='user1@example.com')
    event = _generate_api_gw_event(
        path='/jobs',
        method='POST',
        headers={'Authorization': f'Bearer {access_token}'},
        body={
            'title': 'Senior Backend Engineer',
            'company_name': 'Acme Corp',
            'description': 'Design and build backend services.',
        },
    )

    response = lambda_handler(event, _generate_lambda_context())

    assert response['statusCode'] == 201
    payload = json.loads(response['body'])
    assert payload['title'] == 'Senior Backend Engineer'
    assert payload['company_name'] == 'Acme Corp'
    assert payload['description'] == 'Design and build backend services.'
    assert payload['user_id'] == 'user-1'

    stored = jobs_table.get_item(Key={'job_id': payload['id']}).get('Item')
    assert isinstance(stored, dict)
    assert stored.get('user_id') == 'user-1'


def test_list_jobs_returns_user_jobs(jobs_table: Any) -> None:
    """GET /jobs returns only authenticated user's jobs."""
    from careervp.handlers.job_handler import lambda_handler

    jobs_table.put_item(
        Item={
            'job_id': 'job-1',
            'user_id': 'user-1',
            'title': 'Engineer',
            'company_name': 'Acme',
            'description': 'desc',
            'status': 'active',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
    )
    jobs_table.put_item(
        Item={
            'job_id': 'job-2',
            'user_id': 'user-1',
            'title': 'Manager',
            'company_name': 'Acme',
            'description': 'desc',
            'status': 'active',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
    )
    jobs_table.put_item(
        Item={
            'job_id': 'job-3',
            'user_id': 'user-2',
            'title': 'Other',
            'company_name': 'Other Co',
            'description': 'desc',
            'status': 'active',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
    )

    access_token = _create_access_token(user_id='user-1', email='user1@example.com')
    event = _generate_api_gw_event(path='/jobs', method='GET', headers={'Authorization': f'Bearer {access_token}'})
    response = lambda_handler(event, _generate_lambda_context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    job_ids = {job['id'] for job in payload['jobs']}
    assert job_ids == {'job-1', 'job-2'}


def test_get_job_returns_single_job(jobs_table: Any) -> None:
    """GET /jobs/{jobId} returns one job for the owner."""
    from careervp.handlers.job_handler import lambda_handler

    jobs_table.put_item(
        Item={
            'job_id': 'job-123',
            'user_id': 'user-1',
            'title': 'Engineer',
            'company_name': 'Acme',
            'description': 'desc',
            'status': 'active',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
    )
    access_token = _create_access_token(user_id='user-1', email='user1@example.com')

    event = _generate_api_gw_event(path='/jobs/job-123', method='GET', headers={'Authorization': f'Bearer {access_token}'})
    response = lambda_handler(event, _generate_lambda_context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['id'] == 'job-123'
    assert payload['user_id'] == 'user-1'


def test_users_can_only_access_own_jobs(jobs_table: Any) -> None:
    """GET /jobs/{jobId} rejects access to another user's job."""
    from careervp.handlers.job_handler import lambda_handler

    jobs_table.put_item(
        Item={
            'job_id': 'job-private',
            'user_id': 'owner-user',
            'title': 'Private Job',
            'company_name': 'Private Co',
            'description': 'desc',
            'status': 'active',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
    )

    access_token = _create_access_token(user_id='other-user', email='other@example.com')
    event = _generate_api_gw_event(path='/jobs/job-private', method='GET', headers={'Authorization': f'Bearer {access_token}'})
    response = lambda_handler(event, _generate_lambda_context())

    assert response['statusCode'] == 403

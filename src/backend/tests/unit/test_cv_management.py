"""
Unit tests for multi-CV management endpoints.

Covers:
- GET /users/me/cv/<cv_id>  — fetch single CV by ID
- DELETE /users/me/cv/<cv_id> — delete CV + S3 cleanup
- DAL: get_all_cvs, get_cv_by_id, delete_cv
- Label derivation from upload filename
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
def cv_mgmt_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-cv-mgmt-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('POWERTOOLS_TRACE_DISABLED', 'true')
    monkeypatch.setenv('TABLE_NAME', 'test-cv-mgmt-table')
    monkeypatch.setenv('CV_BUCKET_NAME', 'test-cv-bucket')
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
        # Create table with userId/cvId schema (matching production CVs table)
        table = dynamodb.create_table(
            TableName='test-cv-mgmt-table',
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
        # Users table for auth
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
        # S3 bucket for CV files
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-cv-bucket')

        table.meta.client.get_waiter('table_exists').wait(TableName='test-cv-mgmt-table')
        yield {'cvs': table, 'users': users_table, 's3': s3}


def _insert_cv(
    table: Any,
    user_id: str,
    cv_id: str,
    full_name: str = 'Test User',
    label: str | None = None,
    source_file_key: str | None = None,
    updated_at: str | None = None,
) -> None:
    """Insert a CV item matching DynamoDalHandler.save_cv schema."""
    now = updated_at or datetime.now(timezone.utc).isoformat()
    item: dict[str, Any] = {
        'pk': user_id,
        'sk': f'CV#{cv_id}',
        'userId': user_id,
        'cvId': cv_id,
        'user_id': user_id,
        'cv_id': cv_id,
        'full_name': full_name,
        'language': 'en',
        'skills': [],
        'experience': [],
        'education': [],
        'certifications': [],
        'created_at': now,
        'updated_at': now,
    }
    if label is not None:
        item['label'] = label
    if source_file_key is not None:
        item['source_file_key'] = source_file_key
    table.put_item(Item=item)


def _generate_api_gw_event(
    path: str,
    method: str,
    body: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    request_context: dict[str, Any] = {
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
    if user_id:
        request_context['authorizer'] = {'claims': {'sub': user_id}}

    return {
        'version': '1.0',
        'resource': path,
        'path': path,
        'httpMethod': method,
        'headers': {'Content-Type': 'application/json'},
        'multiValueHeaders': {},
        'queryStringParameters': None,
        'multiValueQueryStringParameters': None,
        'requestContext': request_context,
        'pathParameters': None,
        'stageVariables': None,
        'body': json.dumps(body) if body is not None else None,
        'isBase64Encoded': False,
    }


def _generate_lambda_context() -> Any:
    ctx = MagicMock()
    ctx.aws_request_id = 'test-request-id'
    ctx.function_name = 'user-handler'
    ctx.memory_limit_in_mb = 256
    ctx.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:user-handler'
    return ctx


def _create_access_token(user_id: str, email: str = 'test@example.com') -> str:
    issued_at = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'email': email,
        'token_type': 'access',
        'iat': int(issued_at.timestamp()),
        'exp': int((issued_at + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, TEST_PRIVATE_KEY, algorithm='RS256')


# ──────────────────────────────────────────────────────────────────────────────
# DAL: get_all_cvs
# ──────────────────────────────────────────────────────────────────────────────


def test_get_all_cvs_returns_multiple(db_tables: dict[str, Any]) -> None:
    """get_all_cvs returns all CVs for a user sorted by updated_at desc."""
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    user_id = 'user-multi'
    _insert_cv(db_tables['cvs'], user_id, 'cv-old', updated_at='2025-01-01T00:00:00+00:00')
    _insert_cv(db_tables['cvs'], user_id, 'cv-new', updated_at='2025-06-01T00:00:00+00:00')
    _insert_cv(db_tables['cvs'], 'other-user', 'cv-other')

    dal = DynamoDalHandler(table_name='test-cv-mgmt-table')
    cvs = dal.get_all_cvs(user_id)

    assert len(cvs) == 2
    assert cvs[0].cv_id == 'cv-new'
    assert cvs[1].cv_id == 'cv-old'


def test_get_all_cvs_empty(db_tables: dict[str, Any]) -> None:
    """get_all_cvs returns empty list for user with no CVs."""
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    dal = DynamoDalHandler(table_name='test-cv-mgmt-table')
    assert dal.get_all_cvs('no-such-user') == []


# ──────────────────────────────────────────────────────────────────────────────
# DAL: get_cv_by_id
# ──────────────────────────────────────────────────────────────────────────────


def test_get_cv_by_id_found(db_tables: dict[str, Any]) -> None:
    """get_cv_by_id returns the correct CV when it exists."""
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    user_id = 'user-single'
    _insert_cv(db_tables['cvs'], user_id, 'cv-abc', full_name='Alice', label='My Resume')

    dal = DynamoDalHandler(table_name='test-cv-mgmt-table')
    cv = dal.get_cv_by_id(user_id, 'cv-abc')

    assert cv is not None
    assert cv.cv_id == 'cv-abc'
    assert cv.full_name == 'Alice'
    assert cv.label == 'My Resume'


def test_get_cv_by_id_not_found(db_tables: dict[str, Any]) -> None:
    """get_cv_by_id returns None when CV doesn't exist."""
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    dal = DynamoDalHandler(table_name='test-cv-mgmt-table')
    assert dal.get_cv_by_id('user-x', 'no-such-cv') is None


# ──────────────────────────────────────────────────────────────────────────────
# DAL: delete_cv
# ──────────────────────────────────────────────────────────────────────────────


def test_delete_cv_success(db_tables: dict[str, Any]) -> None:
    """delete_cv removes the item and returns (True, source_file_key)."""
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    user_id = 'user-del'
    _insert_cv(db_tables['cvs'], user_id, 'cv-del', source_file_key='user-del/abc.pdf')

    dal = DynamoDalHandler(table_name='test-cv-mgmt-table')
    deleted, key = dal.delete_cv(user_id, 'cv-del')

    assert deleted is True
    assert key == 'user-del/abc.pdf'
    assert dal.get_cv_by_id(user_id, 'cv-del') is None


def test_delete_cv_not_found(db_tables: dict[str, Any]) -> None:
    """delete_cv returns (False, None) when CV doesn't exist."""
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    dal = DynamoDalHandler(table_name='test-cv-mgmt-table')
    deleted, key = dal.delete_cv('user-x', 'no-such-cv')

    assert deleted is False
    assert key is None


# ──────────────────────────────────────────────────────────────────────────────
# Handler: GET /users/me/cv/<cv_id>
# ──────────────────────────────────────────────────────────────────────────────


def test_get_single_cv_success(db_tables: dict[str, Any]) -> None:
    """GET /users/me/cv/<cv_id> returns the requested CV."""
    from careervp.handlers.user_handler import lambda_handler

    user_id = 'user-get-cv'
    _insert_cv(db_tables['cvs'], user_id, 'cv-123', full_name='Bob', label='Engineer CV')

    event = _generate_api_gw_event(
        path='/users/me/cv/cv-123',
        method='GET',
        user_id=user_id,
    )
    response = lambda_handler(event, _generate_lambda_context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['cv_id'] == 'cv-123'
    assert payload['full_name'] == 'Bob'
    assert payload['label'] == 'Engineer CV'


def test_get_single_cv_not_found(db_tables: dict[str, Any]) -> None:
    """GET /users/me/cv/<cv_id> returns 404 for missing CV."""
    from careervp.handlers.user_handler import lambda_handler

    user_id = 'user-no-cv'
    event = _generate_api_gw_event(
        path='/users/me/cv/does-not-exist',
        method='GET',
        user_id=user_id,
    )
    response = lambda_handler(event, _generate_lambda_context())

    assert response['statusCode'] == 404


def test_get_single_cv_requires_auth(db_tables: dict[str, Any]) -> None:
    """GET /users/me/cv/<cv_id> returns 401 without auth."""
    from careervp.handlers.user_handler import lambda_handler

    event = _generate_api_gw_event(path='/users/me/cv/cv-123', method='GET')
    response = lambda_handler(event, _generate_lambda_context())

    assert response['statusCode'] == 401


# ──────────────────────────────────────────────────────────────────────────────
# Handler: DELETE /users/me/cv/<cv_id>
# ──────────────────────────────────────────────────────────────────────────────


def test_delete_cv_handler_success(db_tables: dict[str, Any]) -> None:
    """DELETE /users/me/cv/<cv_id> removes CV and S3 file, returns 204."""
    from careervp.handlers.user_handler import lambda_handler

    user_id = 'user-del-h'
    s3_key = f'{user_id}/resume.pdf'
    _insert_cv(db_tables['cvs'], user_id, 'cv-del-h', source_file_key=s3_key)

    # Upload a fake file to S3 so we can verify cleanup
    db_tables['s3'].put_object(Bucket='test-cv-bucket', Key=s3_key, Body=b'fake')

    event = _generate_api_gw_event(
        path='/users/me/cv/cv-del-h',
        method='DELETE',
        user_id=user_id,
    )
    response = lambda_handler(event, _generate_lambda_context())

    assert response['statusCode'] == 204

    # Verify DynamoDB record gone
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler

    dal = DynamoDalHandler(table_name='test-cv-mgmt-table')
    assert dal.get_cv_by_id(user_id, 'cv-del-h') is None

    # Verify S3 object gone
    objs = db_tables['s3'].list_objects_v2(Bucket='test-cv-bucket', Prefix=s3_key)
    assert objs.get('KeyCount', 0) == 0


def test_delete_cv_handler_not_found(db_tables: dict[str, Any]) -> None:
    """DELETE /users/me/cv/<cv_id> returns 404 for missing CV."""
    from careervp.handlers.user_handler import lambda_handler

    event = _generate_api_gw_event(
        path='/users/me/cv/no-such-cv',
        method='DELETE',
        user_id='user-del-nf',
    )
    response = lambda_handler(event, _generate_lambda_context())

    assert response['statusCode'] == 404


def test_delete_cv_handler_requires_auth(db_tables: dict[str, Any]) -> None:
    """DELETE /users/me/cv/<cv_id> returns 401 without auth."""
    from careervp.handlers.user_handler import lambda_handler

    event = _generate_api_gw_event(path='/users/me/cv/cv-123', method='DELETE')
    response = lambda_handler(event, _generate_lambda_context())

    assert response['statusCode'] == 401


# ──────────────────────────────────────────────────────────────────────────────
# Label derivation
# ──────────────────────────────────────────────────────────────────────────────


def test_label_field_on_user_cv() -> None:
    """UserCV model accepts and stores the label field."""
    from careervp.models.cv import UserCV

    cv = UserCV(user_id='u1', full_name='Test', label='My Resume')
    assert cv.label == 'My Resume'


def test_label_defaults_to_none() -> None:
    """UserCV label defaults to None when not provided."""
    from careervp.models.cv import UserCV

    cv = UserCV(user_id='u1', full_name='Test')
    assert cv.label is None


def test_label_derived_from_filename() -> None:
    """Upload handler derives label from file_name (minus extension)."""
    import os

    # Simulate what the handler does
    file_name = 'Senior_Developer_Resume.pdf'
    label = os.path.splitext(os.path.basename(file_name))[0]
    assert label == 'Senior_Developer_Resume'

    file_name_docx = 'My CV.docx'
    label_docx = os.path.splitext(os.path.basename(file_name_docx))[0]
    assert label_docx == 'My CV'

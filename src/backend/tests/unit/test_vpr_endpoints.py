"""
Unit tests for VPR OpenAPI-aligned submit/status endpoints.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from careervp.models.result import Result, ResultCode


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
def vpr_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-vpr-endpoints-test')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    monkeypatch.setenv('POWERTOOLS_TRACE_DISABLED', 'true')
    monkeypatch.setenv('JWT_PRIVATE_KEY', TEST_PRIVATE_KEY)
    monkeypatch.setenv('JWT_PUBLIC_KEY', TEST_PUBLIC_KEY)
    monkeypatch.setenv('SQS_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue')

    import careervp.handlers.vpr_status_handler as vpr_status_handler
    import careervp.handlers.vpr_submit_handler as vpr_submit_handler

    vpr_submit_handler._auth_service = None
    vpr_status_handler._auth_service = None


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


def _lambda_context() -> Any:
    context = MagicMock()
    context.function_name = 'test-vpr-handler'
    context.memory_limit_in_mb = 256
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-vpr-handler'
    context.aws_request_id = 'req-123'
    return context


def test_post_vpr_generate_returns_202() -> None:
    """POST /vpr/generate should return 202 with request_id/job_id."""
    from careervp.handlers.vpr_submit_handler import lambda_handler

    access_token = _create_access_token(user_id='user-123', email='user@example.com')
    event = {
        'httpMethod': 'POST',
        'path': '/vpr/generate',
        'headers': {'Content-Type': 'application/json', 'Authorization': f'Bearer {access_token}'},
        'body': json.dumps(
            {
                'cv_id': 'cv-1',
                'job_id': 'job-abc',
                'gap_response_ids': ['gap-1'],
                'options': {'include_company_research': True, 'tone': 'professional'},
            }
        ),
    }

    with (
        patch('careervp.handlers.vpr_submit_handler.JobsRepository') as repo_cls,
        patch('careervp.handlers.vpr_submit_handler.uuid.uuid4', return_value='vpr-job-123'),
        patch('careervp.handlers.vpr_submit_handler.sqs.send_message') as send_message_mock,
    ):
        repo = repo_cls.return_value
        repo.get_job_by_idempotency_key.return_value = None
        repo.create_job.return_value = Result(success=True, data={'job_id': 'vpr-job-123'}, code=ResultCode.SUCCESS)
        send_message_mock.return_value = {'MessageId': 'msg-1'}

        response = lambda_handler(event, _lambda_context())

    assert response['statusCode'] == 202
    payload = json.loads(response['body'])
    assert payload['request_id'] == 'vpr-job-123'
    assert payload['job_id'] == 'vpr-job-123'
    assert payload['status'] == 'processing'
    assert payload['estimated_time_seconds'] == 120


def test_get_vpr_id_returns_job_status() -> None:
    """GET /vpr/{vprId} should return VPR status payload."""
    from careervp.handlers.vpr_status_handler import lambda_handler

    access_token = _create_access_token(user_id='user-123', email='user@example.com')
    event = {
        'httpMethod': 'GET',
        'path': '/vpr/vpr-123',
        'pathParameters': {'vprId': 'vpr-123'},
        'headers': {'Authorization': f'Bearer {access_token}'},
    }

    with patch('careervp.handlers.vpr_status_handler.JobsRepository') as repo_cls:
        repo = repo_cls.return_value
        repo.get_job.return_value = {
            'job_id': 'vpr-123',
            'user_id': 'user-123',
            'status': 'PROCESSING',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }

        response = lambda_handler(event, _lambda_context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['id'] == 'vpr-123'
    assert payload['status'] == 'processing'


def test_get_users_me_vprs_returns_user_vpr_list() -> None:
    """GET /users/me/vprs should return list of current user's VPR jobs."""
    from careervp.handlers.vpr_status_handler import lambda_handler

    access_token = _create_access_token(user_id='user-123', email='user@example.com')
    event = {
        'httpMethod': 'GET',
        'path': '/users/me/vprs',
        'headers': {'Authorization': f'Bearer {access_token}'},
    }

    with patch('careervp.handlers.vpr_status_handler.JobsRepository') as repo_cls:
        repo = repo_cls.return_value
        repo.get_vpr_jobs_by_user.return_value = [
            {
                'job_id': 'vpr-1',
                'user_id': 'user-123',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'input_data': {'job_posting': {'role_title': 'Engineer', 'company_name': 'Acme'}},
            },
            {
                'job_id': 'vpr-2',
                'user_id': 'user-123',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'input_data': {'job_posting': {'role_title': 'Manager', 'company_name': 'Beta'}},
            },
        ]

        response = lambda_handler(event, _lambda_context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert len(payload['vprs']) == 2
    assert payload['vprs'][0]['id'] == 'vpr-1'
    assert payload['vprs'][0]['job_title'] == 'Engineer'
    assert payload['vprs'][0]['company_name'] == 'Acme'

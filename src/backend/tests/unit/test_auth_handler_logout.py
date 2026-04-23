"""Unit tests for POST /auth/logout in auth_handler.py."""

from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def _make_jwt(claims: dict) -> str:
    """Build a minimal unsigned JWT (verify_signature=False is used by the handler)."""

    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b'=').decode()

    return f'{b64({"alg": "RS256", "typ": "JWT"})}.{b64(claims)}.fakesig'


def _event(auth_header: str | None = None) -> dict:
    headers: dict = {'Content-Type': 'application/json'}
    if auth_header is not None:
        headers['Authorization'] = auth_header
    return {
        'path': '/auth/logout',
        'httpMethod': 'POST',
        'requestContext': {'authorizer': {'claims': {'sub': 'test-user'}}},
        'headers': headers,
        'body': None,
    }


def _context() -> SimpleNamespace:
    return SimpleNamespace(
        function_name='auth-api',
        function_version='$LATEST',
        invoked_function_arn='arn:aws:lambda:us-east-1:123456789012:function:auth-api',
        memory_limit_in_mb='256',
        aws_request_id='req-logout-test',
        log_group_name='/aws/lambda/auth-api',
        log_stream_name='2026/04/23/[$LATEST]test',
    )


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('COGNITO_USER_POOL_ID', 'us-east-1_TestPool')
    monkeypatch.setenv('COGNITO_CLIENT_ID', 'test-client-id')
    monkeypatch.setenv('TABLE_NAME', 'test-users-table')
    monkeypatch.setenv('TOKEN_BLACKLIST_TABLE_NAME', 'test-idempotency-table')
    monkeypatch.setenv('JWT_PRIVATE_KEY', 'dummy-key')
    monkeypatch.setenv('JWT_PUBLIC_KEY', 'dummy-key')


def test_logout_returns_200_and_calls_admin_sign_out() -> None:
    """POST /auth/logout calls AdminUserGlobalSignOut and returns 200."""
    token = _make_jwt({'cognito:username': 'testuser@example.com', 'email': 'testuser@example.com'})
    mock_cognito = MagicMock()

    with patch('boto3.client', return_value=mock_cognito):
        from careervp.handlers import auth_handler as module

        module.COGNITO_USER_POOL_ID = 'us-east-1_TestPool'

        response = module.lambda_handler(_event(f'Bearer {token}'), _context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == 'Logged out successfully'
    mock_cognito.admin_user_global_sign_out.assert_called_once_with(
        UserPoolId='us-east-1_TestPool',
        Username='testuser@example.com',
    )


def test_logout_returns_401_when_no_authorization_header() -> None:
    """POST /auth/logout returns 401 when Authorization header is missing."""
    from careervp.handlers import auth_handler as module

    response = module.lambda_handler(_event(auth_header=None), _context())

    assert response['statusCode'] == 401
    body = json.loads(response['body'])
    assert 'error' in body


def test_logout_returns_401_when_token_malformed() -> None:
    """POST /auth/logout returns 401 when token cannot be decoded."""
    from careervp.handlers import auth_handler as module

    response = module.lambda_handler(_event('Bearer not.a.valid.jwt.here'), _context())

    assert response['statusCode'] == 401
    body = json.loads(response['body'])
    assert 'error' in body

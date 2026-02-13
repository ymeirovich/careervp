"""Tests for auth_handler - SEC-001 API Authorizer."""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest

# Constants for tests
TEST_SECRET = "test-secret-key-for-unit-tests"
TEST_EMAIL = "testuser@example.com"
TEST_ALGORITHM = "HS256"
TEST_BLACKLIST_TABLE = "test-blacklist-table"

# Common env vars dict
TEST_ENV = {
    "POWERTOOLS_SERVICE_NAME": "test-auth",
    "LOG_LEVEL": "DEBUG",
    "TOKEN_BLACKLIST_TABLE_NAME": TEST_BLACKLIST_TABLE,
    "JWT_SECRET": TEST_SECRET,
    "JWT_ALGORITHM": TEST_ALGORITHM,
}

METHOD_ARN = "arn:aws:execute-api:us-east-1:123456789012:abcdef123/prod/GET/resource"


def _make_token(payload: dict, secret: str = TEST_SECRET) -> str:
    return jwt.encode(payload, secret, algorithm=TEST_ALGORITHM)


@pytest.fixture
def valid_token():
    """Generate a valid JWT token for testing."""
    payload = {
        "user_email": TEST_EMAIL,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    return _make_token(payload)


@pytest.fixture
def expired_token():
    """Generate an expired JWT token for testing."""
    payload = {
        "user_email": TEST_EMAIL,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    return _make_token(payload)


@pytest.fixture
def token_without_email():
    """Generate a JWT token without user_email claim."""
    payload = {
        "sub": "some-user-id",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    return _make_token(payload)


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB boto3 client via _get_dynamodb_client."""
    with patch("careervp.handlers.auth_handler._get_dynamodb_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        yield mock_client


# ---------- validate_token ----------


@patch.dict(os.environ, TEST_ENV)
def test_validate_token_valid(valid_token, mock_dynamodb):
    """Test validate_token returns True for valid JWT."""
    from careervp.handlers.auth_handler import validate_token

    mock_dynamodb.get_item.return_value = {}

    assert validate_token(valid_token) is True


@patch.dict(os.environ, TEST_ENV)
def test_validate_token_expired(expired_token, mock_dynamodb):
    """Test validate_token returns False for expired JWT."""
    from careervp.handlers.auth_handler import validate_token

    assert validate_token(expired_token) is False


@patch.dict(os.environ, TEST_ENV)
def test_validate_token_invalid_signature(mock_dynamodb):
    """Test validate_token returns False for JWT with wrong secret."""
    from careervp.handlers.auth_handler import validate_token

    payload = {
        "user_email": TEST_EMAIL,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    wrong_secret_token = _make_token(payload, secret="wrong-secret")

    assert validate_token(wrong_secret_token) is False


@patch.dict(os.environ, TEST_ENV)
def test_validate_token_malformed(mock_dynamodb):
    """Test validate_token returns False for malformed JWT."""
    from careervp.handlers.auth_handler import validate_token

    assert validate_token("not-a-valid-jwt-token") is False


@patch.dict(os.environ, TEST_ENV)
def test_validate_token_blacklisted(valid_token, mock_dynamodb):
    """Test validate_token returns False for blacklisted token."""
    from careervp.handlers.auth_handler import validate_token

    mock_dynamodb.get_item.return_value = {"Item": {"token": {"S": valid_token}}}

    assert validate_token(valid_token) is False


# ---------- get_user_from_token ----------


@patch.dict(os.environ, TEST_ENV)
def test_get_user_from_token_valid(valid_token):
    """Test get_user_from_token returns User with correct email."""
    from careervp.handlers.auth_handler import get_user_from_token

    user = get_user_from_token(valid_token)
    assert user.user_email == TEST_EMAIL
    assert user.entity_type == "USER"


@patch.dict(os.environ, TEST_ENV)
def test_get_user_from_token_invalid():
    """Test get_user_from_token raises ValueError for invalid token."""
    from careervp.handlers.auth_handler import get_user_from_token

    with pytest.raises(ValueError):
        get_user_from_token("garbage-token")


@patch.dict(os.environ, TEST_ENV)
def test_get_user_from_token_missing_email(token_without_email):
    """Test get_user_from_token raises ValueError when user_email claim missing."""
    from careervp.handlers.auth_handler import get_user_from_token

    with pytest.raises(ValueError, match="missing user_email"):
        get_user_from_token(token_without_email)


# ---------- lambda_handler ----------


@patch.dict(os.environ, TEST_ENV)
def test_lambda_handler_valid_token(valid_token, mock_dynamodb):
    """Test lambda_handler returns Allow policy for valid token."""
    from careervp.handlers.auth_handler import lambda_handler

    mock_dynamodb.get_item.return_value = {}

    event = {
        "type": "TOKEN",
        "methodArn": METHOD_ARN,
        "authorizationToken": f"Bearer {valid_token}",
    }

    response = lambda_handler(event, MagicMock())

    assert response["principalId"] == TEST_EMAIL
    assert response["policyDocument"]["Statement"][0]["Effect"] == "Allow"
    assert response["context"]["user_email"] == TEST_EMAIL


@patch.dict(os.environ, TEST_ENV)
def test_lambda_handler_missing_token(mock_dynamodb):
    """Test lambda_handler returns Deny policy when token missing."""
    from careervp.handlers.auth_handler import lambda_handler

    event = {
        "type": "TOKEN",
        "methodArn": METHOD_ARN,
    }

    response = lambda_handler(event, MagicMock())

    assert response["principalId"] == "unknown"
    assert response["policyDocument"]["Statement"][0]["Effect"] == "Deny"


@patch.dict(os.environ, TEST_ENV)
def test_lambda_handler_invalid_token(mock_dynamodb):
    """Test lambda_handler returns Deny policy for invalid token."""
    from careervp.handlers.auth_handler import lambda_handler

    mock_dynamodb.get_item.return_value = {}

    event = {
        "type": "TOKEN",
        "methodArn": METHOD_ARN,
        "authorizationToken": "Bearer invalid-token-string",
    }

    response = lambda_handler(event, MagicMock())

    assert response["principalId"] == "unknown"
    assert response["policyDocument"]["Statement"][0]["Effect"] == "Deny"

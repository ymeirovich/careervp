"""
Unit tests for auth_handler module.
Per Phase 0: Security Foundation validation.
"""

import os
import time
from unittest.mock import MagicMock, patch

import jwt
import pytest

from careervp.handlers.auth_handler import (
    User,
    _generate_policy,
    _is_token_blacklisted,
    get_user_from_token,
    lambda_handler,
    validate_token,
)

# =============================================================================
# Test Fixtures
# =============================================================================

TEST_JWT_SECRET = 'test-secret-key'
TEST_JWT_ALGORITHM = 'HS256'


def create_test_token(payload: dict, secret: str = TEST_JWT_SECRET) -> str:
    """Helper to create valid JWT tokens for testing."""
    return jwt.encode(payload, secret, algorithm=TEST_JWT_ALGORITHM)


# =============================================================================
# Test validate_token
# =============================================================================


class TestValidateToken:
    """Tests for validate_token function."""

    @patch.dict(os.environ, {'JWT_SECRET': TEST_JWT_SECRET, 'JWT_ALGORITHM': TEST_JWT_ALGORITHM, 'TOKEN_BLACKLIST_TABLE_NAME': 'test-table'})
    @patch('careervp.handlers.auth_handler._is_token_blacklisted')
    def test_valid_token_returns_true(self, mock_blacklist):
        """Valid JWT token should return True."""
        mock_blacklist.return_value = False
        token = create_test_token({'user_email': 'test@example.com', 'exp': int(time.time()) + 3600})

        result = validate_token(token)

        assert result is True
        mock_blacklist.assert_called_once()

    @patch.dict(os.environ, {'JWT_SECRET': TEST_JWT_SECRET, 'JWT_ALGORITHM': TEST_JWT_ALGORITHM, 'TOKEN_BLACKLIST_TABLE_NAME': 'test-table'})
    def test_expired_token_returns_false(self):
        """Expired JWT token should return False."""
        # Create token that's already expired
        token = create_test_token({'user_email': 'test@example.com', 'exp': int(time.time()) - 3600})

        result = validate_token(token)

        assert result is False

    @patch.dict(os.environ, {'JWT_SECRET': TEST_JWT_SECRET, 'JWT_ALGORITHM': TEST_JWT_ALGORITHM, 'TOKEN_BLACKLIST_TABLE_NAME': 'test-table'})
    def test_invalid_signature_returns_false(self):
        """Token with wrong signature should return False."""
        token = create_test_token({'user_email': 'test@example.com'}, secret='wrong-secret')

        result = validate_token(token)

        assert result is False

    @patch.dict(os.environ, {'JWT_SECRET': TEST_JWT_SECRET, 'JWT_ALGORITHM': TEST_JWT_ALGORITHM, 'TOKEN_BLACKLIST_TABLE_NAME': 'test-table'})
    def test_malformed_token_returns_false(self):
        """Malformed token string should return False."""
        result = validate_token('not-a-valid-jwt-token')

        assert result is False

    @patch.dict(os.environ, {'JWT_SECRET': TEST_JWT_SECRET, 'JWT_ALGORITHM': TEST_JWT_ALGORITHM, 'TOKEN_BLACKLIST_TABLE_NAME': 'test-table'})
    @patch('careervp.handlers.auth_handler._is_token_blacklisted')
    def test_blacklisted_token_returns_false(self, mock_blacklist):
        """Blacklisted token should return False."""
        mock_blacklist.return_value = True
        token = create_test_token({'user_email': 'test@example.com', 'exp': int(time.time()) + 3600})

        result = validate_token(token)

        assert result is False


# =============================================================================
# Test get_user_from_token
# =============================================================================


class TestGetUserFromToken:
    """Tests for get_user_from_token function."""

    @patch.dict(os.environ, {'JWT_SECRET': TEST_JWT_SECRET, 'JWT_ALGORITHM': TEST_JWT_ALGORITHM})
    def test_valid_token_returns_user(self):
        """Valid token should return User object."""
        token = create_test_token({'user_email': 'test@example.com', 'entity_type': 'USER'})

        user = get_user_from_token(token)

        assert isinstance(user, User)
        assert user.user_email == 'test@example.com'
        assert user.entity_type == 'USER'

    @patch.dict(os.environ, {'JWT_SECRET': TEST_JWT_SECRET, 'JWT_ALGORITHM': TEST_JWT_ALGORITHM})
    def test_token_without_email_raises_value_error(self):
        """Token missing user_email should raise ValueError."""
        token = create_test_token({'entity_type': 'USER'})

        with pytest.raises(ValueError, match='missing user_email'):
            get_user_from_token(token)

    @patch.dict(os.environ, {'JWT_SECRET': TEST_JWT_SECRET, 'JWT_ALGORITHM': TEST_JWT_ALGORITHM})
    def test_invalid_token_raises_value_error(self):
        """Invalid token should raise ValueError."""
        with pytest.raises(ValueError, match='Invalid token'):
            get_user_from_token('not-a-valid-token')

    @patch.dict(os.environ, {'JWT_SECRET': TEST_JWT_SECRET, 'JWT_ALGORITHM': TEST_JWT_ALGORITHM})
    def test_default_entity_type(self):
        """Should default to USER entity type."""
        token = create_test_token({'user_email': 'test@example.com'})

        user = get_user_from_token(token)

        assert user.entity_type == 'USER'


# =============================================================================
# Test _is_token_blacklisted
# =============================================================================


class TestIsTokenBlacklisted:
    """Tests for _is_token_blacklisted function."""

    @patch('careervp.handlers.auth_handler._get_dynamodb_client')
    def test_token_in_blacklist_returns_true(self, mock_get_client):
        """Token found in blacklist should return True."""
        mock_client = MagicMock()
        mock_client.get_item.return_value = {'Item': {'token': {'S': 'test-token'}}}
        mock_get_client.return_value = mock_client

        result = _is_token_blacklisted('test-token', 'test-table')

        assert result is True

    @patch('careervp.handlers.auth_handler._get_dynamodb_client')
    def test_token_not_in_blacklist_returns_false(self, mock_get_client):
        """Token not in blacklist should return False."""
        mock_client = MagicMock()
        mock_client.get_item.return_value = {}
        mock_get_client.return_value = mock_client

        result = _is_token_blacklisted('test-token', 'test-table')

        assert result is False

    @patch('careervp.handlers.auth_handler._get_dynamodb_client')
    def test_dynamodb_error_returns_true(self, mock_get_client):
        """DynamoDB error should fail-closed (return True)."""
        mock_get_client.side_effect = Exception('DynamoDB error')

        result = _is_token_blacklisted('test-token', 'test-table')

        assert result is True


# =============================================================================
# Test _generate_policy
# =============================================================================


class TestGeneratePolicy:
    """Tests for _generate_policy function."""

    def test_allow_policy(self):
        """Should generate Allow policy."""
        policy = _generate_policy('user@example.com', 'Allow', 'arn:aws:execute-api:us-east-1:123456789012:api/*/*/*')

        assert policy['principalId'] == 'user@example.com'
        assert policy['policyDocument']['Statement'][0]['Effect'] == 'Allow'
        assert policy['policyDocument']['Statement'][0]['Resource'] == 'arn:aws:execute-api:us-east-1:123456789012:api/*/*/*'

    def test_deny_policy(self):
        """Should generate Deny policy."""
        policy = _generate_policy('user@example.com', 'Deny', 'arn:aws:execute-api:us-east-1:123456789012:api/*/*/*')

        assert policy['principalId'] == 'user@example.com'
        assert policy['policyDocument']['Statement'][0]['Effect'] == 'Deny'

    def test_policy_with_context(self):
        """Should include context in policy."""
        context = {'user_email': 'user@example.com', 'entity_type': 'USER'}
        policy = _generate_policy('user@example.com', 'Allow', 'arn:aws:execute-api:us-east-1:123456789012:api/*/*/*', context)

        assert 'context' in policy
        assert policy['context'] == context


# =============================================================================
# Test lambda_handler
# =============================================================================


class TestLambdaHandler:
    """Tests for lambda_handler function."""

    def test_missing_token_returns_deny(self):
        """Missing authorizationToken should return Deny policy."""
        # Create a mock Lambda context
        mock_context = MagicMock()
        mock_context.function_name = 'test_function'
        mock_context.memory_limit_in_mb = 128
        mock_context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test'
        mock_context.aws_request_id = 'test-request-id'

        event = {
            'methodArn': 'arn:aws:execute-api:us-east-1:123456789012:api/prod/GET /users',
        }

        result = lambda_handler(event, mock_context)

        assert result['policyDocument']['Statement'][0]['Effect'] == 'Deny'
        assert result['principalId'] == 'unknown'

    def test_empty_token_returns_deny(self):
        """Empty authorizationToken should return Deny policy."""
        # Create a mock Lambda context
        mock_context = MagicMock()
        mock_context.function_name = 'test_function'
        mock_context.memory_limit_in_mb = 128
        mock_context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test'
        mock_context.aws_request_id = 'test-request-id'

        event = {
            'authorizationToken': '',
            'methodArn': 'arn:aws:execute-api:us-east-1:123456789012:api/prod/GET /users',
        }

        result = lambda_handler(event, mock_context)

        assert result['policyDocument']['Statement'][0]['Effect'] == 'Deny'
        assert result['principalId'] == 'unknown'

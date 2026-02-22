"""Unit tests for API Gateway Lambda authorizer."""

from __future__ import annotations

from unittest.mock import Mock

from careervp.handlers import api_gateway_authorizer


def test_authorizer_allows_valid_access_token_with_user_id_context() -> None:
    auth_service = Mock()
    auth_service.validate_token.return_value = {'user_id': 'user-123'}
    api_gateway_authorizer._auth_service = auth_service

    result = api_gateway_authorizer.lambda_handler(
        {
            'authorizationToken': 'Bearer test-token',
            'methodArn': 'arn:aws:execute-api:us-east-1:123456789012:api/dev/GET/jobs',
        },
        None,
    )

    assert result['principalId'] == 'user-123'
    assert result['policyDocument']['Statement'][0]['Effect'] == 'Allow'
    assert result['context']['user_id'] == 'user-123'
    assert result['context']['sub'] == 'user-123'


def test_authorizer_uses_sub_claim_when_user_id_missing() -> None:
    auth_service = Mock()
    auth_service.validate_token.return_value = {'sub': 'sub-user-999'}
    api_gateway_authorizer._auth_service = auth_service

    result = api_gateway_authorizer.lambda_handler(
        {
            'authorizationToken': 'Bearer test-token',
            'methodArn': 'arn:aws:execute-api:us-east-1:123456789012:api/dev/POST/vpr/generate',
        },
        None,
    )

    assert result['principalId'] == 'sub-user-999'
    assert result['policyDocument']['Statement'][0]['Effect'] == 'Allow'
    assert result['context']['user_id'] == 'sub-user-999'
    assert result['context']['sub'] == 'sub-user-999'


def test_authorizer_denies_request_without_bearer_token() -> None:
    api_gateway_authorizer._auth_service = Mock()

    result = api_gateway_authorizer.lambda_handler(
        {'authorizationToken': 'invalid-token', 'methodArn': 'arn:aws:execute-api:::*'},
        None,
    )

    assert result['principalId'] == 'unauthorized'
    assert result['policyDocument']['Statement'][0]['Effect'] == 'Deny'

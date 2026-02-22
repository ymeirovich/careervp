"""Custom REST API Gateway Lambda authorizer for CareerVP JWT access tokens."""

from __future__ import annotations

from typing import Any

from careervp.handlers.utils.observability import logger
from careervp.logic.auth_service import AuthService, ConfigurationError, InvalidTokenError

_auth_service: AuthService | None = None


def _get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService.from_env()
    return _auth_service


def _extract_bearer_token(event: dict[str, Any]) -> str | None:
    token_value = event.get('authorizationToken')
    if not isinstance(token_value, str):
        return None
    if not token_value.startswith('Bearer '):
        return None
    token = token_value[7:].strip()
    return token if token else None


def _build_policy(principal_id: str, method_arn: str, effect: str) -> dict[str, Any]:
    return {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': method_arn,
                }
            ],
        },
    }


def _expected_token_type(method_arn: str) -> str:
    """Return required token type for the requested REST route."""
    arn_parts = method_arn.split('/')
    route = '/' + '/'.join(arn_parts[3:]) if len(arn_parts) >= 4 else ''
    if route == '/auth/refresh':
        return 'refresh'
    return 'access'


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    _ = context
    method_arn = str(event.get('methodArn') or '*')
    token = _extract_bearer_token(event)
    if token is None:
        logger.warning('Authorizer reject: missing bearer token')
        return _build_policy('unauthorized', method_arn, 'Deny')

    try:
        claims = _get_auth_service().validate_token(
            token,
            expected_token_type=_expected_token_type(method_arn),
        )
    except (InvalidTokenError, ConfigurationError) as exc:
        logger.warning('Authorizer reject: invalid token', error=str(exc))
        return _build_policy('unauthorized', method_arn, 'Deny')

    user_id = claims.get('user_id') or claims.get('sub')
    if not isinstance(user_id, str) or not user_id.strip():
        logger.warning('Authorizer reject: token missing user identity claims')
        return _build_policy('unauthorized', method_arn, 'Deny')

    normalized_user_id = user_id.strip()
    policy = _build_policy(normalized_user_id, method_arn, 'Allow')
    policy['context'] = {
        # Keep both keys for backward compatibility during handler migration.
        'user_id': normalized_user_id,
        'sub': normalized_user_id,
        'principal_id': normalized_user_id,
    }
    return policy

"""Custom REST API Gateway Lambda authorizer for CareerVP JWT access tokens."""

from __future__ import annotations

import os
from typing import Any

from careervp.dal.identity_map_repository import (
    IDENTITY_MAP_TABLE_ENV,
    IdentityMapRepository,
    UsersDirectory,
)
from careervp.handlers.utils.observability import logger
from careervp.logic.auth_service import AuthService, ConfigurationError, InvalidTokenError
from careervp.logic.identity_resolver import IdentityResolver, LinkDecision

_auth_service: AuthService | None = None
_identity_resolver: IdentityResolver | None = None


def _get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService.from_env()
    return _auth_service


def _build_identity_resolver_from_env() -> IdentityResolver | None:
    """Wire the surrogate resolver only when a mapping table is configured."""
    table_name = os.environ.get(IDENTITY_MAP_TABLE_ENV)
    if not table_name:
        return None
    identity_map = IdentityMapRepository(table_name=table_name)
    directory = UsersDirectory()
    return IdentityResolver(identity_map=identity_map, email_lookup=directory.find_owners)


def _get_identity_resolver() -> IdentityResolver | None:
    global _identity_resolver
    if _identity_resolver is None:
        _identity_resolver = _build_identity_resolver_from_env()
    return _identity_resolver


def _resolve_identity(claims: dict[str, Any]) -> tuple[str, str] | None:
    """Resolve claims to ``(internal_user_id, raw_sub)`` or ``None`` to deny.

    When no mapping table is wired the authorizer keeps its legacy passthrough
    (``user_id`` else ``sub``) so the change is additive and dormant until the
    surrogate table is deployed and the custom authorizer is activated.
    """
    raw_sub = claims.get('sub')
    raw_sub = raw_sub.strip() if isinstance(raw_sub, str) and raw_sub.strip() else ''

    resolver = _get_identity_resolver()
    if resolver is None:
        candidate = claims.get('user_id') or claims.get('sub')
        user_id = candidate.strip() if isinstance(candidate, str) and candidate.strip() else ''
        if not user_id:
            return None
        return user_id, (raw_sub or user_id)

    result = resolver.resolve(claims)
    if result.decision is LinkDecision.STEP_UP_REQUIRED or not result.user_id:
        return None
    return result.user_id, (raw_sub or result.user_id)


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

    resolved = _resolve_identity(claims)
    if resolved is None:
        logger.warning('Authorizer reject: identity could not be resolved (missing claims or step-up required)')
        return _build_policy('unauthorized', method_arn, 'Deny')

    internal_user_id, raw_sub = resolved
    policy = _build_policy(internal_user_id, method_arn, 'Allow')
    policy['context'] = {
        # The internal surrogate is the durable tenant identity handlers must use.
        'user_id': internal_user_id,
        # The raw Cognito sub is preserved (equals user_id in the legacy path)
        # for audit and account-link flows.
        'sub': raw_sub,
        'principal_id': internal_user_id,
    }
    return policy

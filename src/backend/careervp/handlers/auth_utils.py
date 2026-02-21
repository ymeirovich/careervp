"""Shared authentication extraction helpers for API handlers."""

from __future__ import annotations

import os
from typing import Any

from careervp.handlers.utils.observability import logger


def _coerce_non_empty_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _get_header_case_insensitive(headers: dict[str, Any], target_header: str) -> str | None:
    normalized_target = target_header.lower()
    for key, value in headers.items():
        if isinstance(key, str) and key.lower() == normalized_target:
            return _coerce_non_empty_string(value)
    return None


def extract_user_id(event: dict[str, Any]) -> str | None:
    """
    Extract a user ID from API Gateway/Lambda auth context.

    Priority:
    1. HTTP API v2 JWT claims: requestContext.authorizer.jwt.claims.sub
    2. Lambda authorizer: requestContext.authorizer.principalId
    3. Local-only fallback: X-User-Id header when ENV=local
    """
    request_context = event.get('requestContext')
    if isinstance(request_context, dict):
        authorizer = request_context.get('authorizer')
        if isinstance(authorizer, dict):
            jwt_context = authorizer.get('jwt')
            if isinstance(jwt_context, dict):
                claims = jwt_context.get('claims')
                if isinstance(claims, dict):
                    user_id = _coerce_non_empty_string(claims.get('sub'))
                    if user_id:
                        return user_id

            principal_id = _coerce_non_empty_string(authorizer.get('principalId'))
            if principal_id:
                return principal_id

    if os.getenv('ENV', '').strip().lower() == 'local':
        headers = event.get('headers')
        if isinstance(headers, dict):
            user_id = _get_header_case_insensitive(headers, 'x-user-id')
            if user_id:
                return user_id

    logger.warning('Failed to extract user id from auth context')
    return None


__all__ = ['extract_user_id']

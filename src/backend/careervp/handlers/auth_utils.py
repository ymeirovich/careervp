"""Shared Cognito identity extraction helpers for API handlers."""

from __future__ import annotations

from typing import Any

from careervp.handlers.utils.observability import logger


def _coerce_non_empty_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def extract_user_id(event: dict[str, Any]) -> str | None:
    """
    Extract user id from Cognito claims only.

    Accepted shapes:
    1. requestContext.authorizer.jwt.claims.sub (HTTP API v2)
    2. requestContext.authorizer.claims.sub (REST API / proxy integrations)
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

            claims = authorizer.get('claims')
            if isinstance(claims, dict):
                user_id = _coerce_non_empty_string(claims.get('sub'))
                if user_id:
                    return user_id

    headers = event.get('headers')
    if isinstance(headers, dict):
        for header_name in ('x-user-id', 'X-User-Id'):
            user_id = _coerce_non_empty_string(headers.get(header_name))
            if user_id:
                return user_id

    logger.warning('Failed to extract user id from auth context')
    return None


__all__ = ['extract_user_id']

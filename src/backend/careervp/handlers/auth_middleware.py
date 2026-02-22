"""Authentication middleware helpers for Lambda handlers."""

from __future__ import annotations

import json
from functools import wraps
from http import HTTPStatus
from typing import Any, Callable

from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.utils.observability import logger

JSON_HEADERS = {'Content-Type': 'application/json'}


def _unauthorized_response() -> dict[str, Any]:
    return {
        'statusCode': HTTPStatus.UNAUTHORIZED.value,
        'headers': JSON_HEADERS,
        'body': json.dumps(
            {
                'error': 'Authentication required',
                'code': 'UNAUTHORIZED',
            }
        ),
    }


def require_auth(handler: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    """Decorator that enforces user identity extraction before handler execution."""

    @wraps(handler)
    def wrapped(event: dict[str, Any], context: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        user_id = extract_user_id(event)
        if user_id is None:
            logger.warning('Unauthorized request: missing user id')
            return _unauthorized_response()
        return handler(event, context, *args, **kwargs)

    return wrapped


__all__ = ['require_auth']

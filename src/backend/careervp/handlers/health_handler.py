"""Lambda handler for API health checks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any

from careervp.handlers.cors_utils import get_cors_headers

API_VERSION = '1.0.0'


def health_check() -> dict[str, Any]:
    """Return service health payload."""
    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    return {
        'status': 'healthy',
        'timestamp': timestamp,
        'version': API_VERSION,
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle GET /health requests without authentication."""
    _ = context
    method = str(event.get('httpMethod', 'GET')).upper()
    path = str(event.get('path', '')).rstrip('/')

    if method == 'OPTIONS':
        return _build_response(HTTPStatus.OK, {'status': 'healthy'})

    if method == 'GET' and path == '/health':
        return _build_response(HTTPStatus.OK, health_check())

    return _build_response(
        HTTPStatus.NOT_FOUND,
        {
            'error': 'Endpoint not found',
        },
    )


def _build_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    headers = get_cors_headers(None)
    headers['Content-Type'] = 'application/json'
    return {
        'statusCode': status_code.value,
        'headers': headers,
        'body': json.dumps(body),
    }


__all__ = ['lambda_handler', 'health_check']

"""Unit tests for health endpoint handler."""

import json
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

from careervp.handlers.health_handler import lambda_handler


def _event(path: str = '/health', method: str = 'GET', headers: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        'resource': path,
        'path': path,
        'httpMethod': method,
        'headers': headers,
        'multiValueHeaders': {},
        'queryStringParameters': None,
        'multiValueQueryStringParameters': None,
        'pathParameters': None,
        'stageVariables': None,
        'requestContext': {
            'resourcePath': path,
            'httpMethod': method,
            'path': path,
            'stage': 'test',
            'requestId': 'req-1',
        },
        'body': None,
        'isBase64Encoded': False,
    }


def _context() -> Any:
    context = MagicMock()
    context.aws_request_id = 'req-1'
    context.function_name = 'health-handler'
    return context


def test_get_health_returns_200_ok() -> None:
    """GET /health should return 200."""
    response = lambda_handler(_event(), _context())

    assert response['statusCode'] == 200


def test_health_requires_no_authentication() -> None:
    """GET /health should succeed without auth headers or authorizer context."""
    response = lambda_handler(
        {
            'path': '/health',
            'httpMethod': 'GET',
            'headers': None,
            'requestContext': {},
            'body': None,
        },
        _context(),
    )

    assert response['statusCode'] == 200


def test_health_response_matches_openapi_schema() -> None:
    """Health response should include status, timestamp, and version fields."""
    response = lambda_handler(_event(), _context())

    assert response['statusCode'] == 200
    payload = json.loads(response['body'])
    assert payload['status'] == 'healthy'
    assert payload['version'] == '1.0.0'

    parsed_timestamp = datetime.fromisoformat(payload['timestamp'].replace('Z', '+00:00'))
    assert parsed_timestamp.tzinfo is not None

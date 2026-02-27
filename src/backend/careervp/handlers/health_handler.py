"""Lambda handler for API health checks."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any

import anthropic
import boto3

from careervp.handlers.cors_utils import get_cors_headers

API_VERSION = '1.0.0'


def health_check() -> dict[str, Any]:
    """Return service health payload with live connectivity checks."""
    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    services: dict[str, str] = {}

    # Check Anthropic API
    try:
        client = anthropic.Anthropic()
        client.models.list()
        services['anthropic'] = 'healthy'
    except Exception:  # noqa: BLE001
        services['anthropic'] = 'degraded'

    # Check DynamoDB
    try:
        table_name = os.environ.get('DYNAMODB_TABLE_NAME', '')
        ddb = boto3.client('dynamodb', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
        ddb.describe_table(TableName=table_name)
        services['dynamodb'] = 'healthy'
    except Exception:  # noqa: BLE001
        services['dynamodb'] = 'degraded'

    overall = 'healthy' if all(v == 'healthy' for v in services.values()) else 'degraded'
    return {
        'status': overall,
        'timestamp': timestamp,
        'version': API_VERSION,
        'services': services,
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

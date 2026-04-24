"""
Lambda handler for the Export API endpoint.
Stub — returns 501 Not Implemented until document generation is built.
Endpoint is registered now so frontend integration requires no future API Gateway changes.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from careervp.handlers.cors_utils import get_cors_headers
from careervp.handlers.utils.observability import logger


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route export requests."""
    _ = context
    method = str(event.get('httpMethod', 'GET')).upper()

    if method == 'OPTIONS':
        return _json_response(HTTPStatus.OK, {'status': 'ok'})

    if method == 'GET':
        return _handle_export(event)

    return _json_response(HTTPStatus.METHOD_NOT_ALLOWED, {'error': 'Method not allowed'})


def _handle_export(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /jobs/{job_id}/artifacts/{module_type}/export."""
    path_params = event.get('pathParameters') or {}
    job_id = str(path_params.get('job_id') or path_params.get('jobId') or '')
    module_type = str(path_params.get('module_type') or path_params.get('moduleType') or '')

    query_params = event.get('queryStringParameters') or {}
    export_format = str(query_params.get('format', ''))

    if export_format not in ('docx', 'pdf'):
        return _json_response(
            HTTPStatus.BAD_REQUEST,
            {'error': 'Unsupported format. Use docx or pdf.'},
        )

    logger.info(
        'Export requested (not yet implemented)',
        job_id=job_id,
        module_type=module_type,
        format=export_format,
    )

    return _json_response(
        HTTPStatus.NOT_IMPLEMENTED,
        {'error': 'Export is coming soon. This endpoint will return a download URL once ready.'},
    )


def _json_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    headers = get_cors_headers(None)
    headers['Content-Type'] = 'application/json'
    return {
        'statusCode': status_code.value,
        'headers': headers,
        'body': json.dumps(body),
    }


__all__ = ['lambda_handler']

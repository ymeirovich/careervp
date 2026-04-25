"""Unit tests for export_handler.py — stub endpoint."""

from __future__ import annotations

import json

from careervp.handlers.export_handler import lambda_handler


def _make_event(
    job_id: str = 'job1',
    module_type: str = 'vpr',
    fmt: str = 'docx',
    method: str = 'GET',
) -> dict:
    return {
        'httpMethod': method,
        'path': f'/jobs/{job_id}/artifacts/{module_type}/export',
        'pathParameters': {'job_id': job_id, 'module_type': module_type},
        'queryStringParameters': {'format': fmt},
        'headers': {},
        'body': None,
    }


def test_returns_501_stub_for_docx():
    event = _make_event(fmt='docx')
    response = lambda_handler(event, None)
    assert response['statusCode'] == 501
    body = json.loads(response['body'])
    assert 'coming soon' in body['error'].lower()


def test_returns_501_stub_for_pdf():
    event = _make_event(fmt='pdf')
    response = lambda_handler(event, None)
    assert response['statusCode'] == 501


def test_returns_400_for_unsupported_format():
    event = _make_event(fmt='xlsx')
    response = lambda_handler(event, None)
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'format' in body['error'].lower() or 'unsupported' in body['error'].lower()


def test_endpoint_is_registered_and_reachable():
    """Endpoint must return something other than 404."""
    event = _make_event(fmt='docx')
    response = lambda_handler(event, None)
    assert response['statusCode'] != 404


def test_options_returns_200():
    event = _make_event(method='OPTIONS')
    response = lambda_handler(event, None)
    assert response['statusCode'] == 200


def test_missing_format_returns_400():
    event = _make_event()
    event['queryStringParameters'] = {}
    response = lambda_handler(event, None)
    assert response['statusCode'] == 400

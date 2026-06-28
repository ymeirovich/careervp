"""Unit tests for the client error-report handler."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

from careervp.handlers import error_report_handler
from careervp.handlers.error_report_handler import lambda_handler


def _event(
    *,
    body: str | None = None,
    method: str = 'POST',
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        'resource': '/errors',
        'path': '/errors',
        'httpMethod': method,
        'headers': headers,
        'requestContext': {'requestId': 'req-1', 'stage': 'test'},
        'body': body,
        'isBase64Encoded': False,
    }


def _context() -> Any:
    context = MagicMock()
    context.aws_request_id = 'req-1'
    context.function_name = 'error-report-handler'
    return context


def _report_body(**overrides: Any) -> str:
    payload = {
        'boundary_key': 'company-research-page',
        'error': "Cannot read properties of undefined (reading 'length')",
        'stack': 'TypeError: ...\n    at i (...)',
        'user_agent': 'Mozilla/5.0',
        'url': 'https://app.example.com/applications/abc/company-research/',
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_post_returns_202_received() -> None:
    response = lambda_handler(_event(body=_report_body()), _context())

    assert response['statusCode'] == 202
    assert json.loads(response['body']) == {'status': 'received'}


def test_options_preflight_returns_200() -> None:
    response = lambda_handler(_event(method='OPTIONS'), _context())

    assert response['statusCode'] == 200


def test_logs_client_error_with_report_fields() -> None:
    captured: dict[str, Any] = {}

    def _fake_warning(message: str, **kwargs: Any) -> None:
        captured['message'] = message
        captured.update(kwargs)

    original = error_report_handler.logger.warning
    error_report_handler.logger.warning = _fake_warning  # type: ignore[method-assign]
    try:
        lambda_handler(_event(body=_report_body(boundary_key='billing-page')), _context())
    finally:
        error_report_handler.logger.warning = original  # type: ignore[method-assign]

    assert captured['message'] == 'client_error'
    assert captured['boundary_key'] == 'billing-page'
    assert "reading 'length'" in captured['client_error']
    assert captured['url'].endswith('/company-research/')


def test_oversized_stack_is_truncated() -> None:
    captured: dict[str, Any] = {}

    def _fake_warning(message: str, **kwargs: Any) -> None:
        captured.update(kwargs)

    huge_stack = 'x' * 50_000
    original = error_report_handler.logger.warning
    error_report_handler.logger.warning = _fake_warning  # type: ignore[method-assign]
    try:
        lambda_handler(_event(body=_report_body(stack=huge_stack)), _context())
    finally:
        error_report_handler.logger.warning = original  # type: ignore[method-assign]

    assert len(captured['stack']) < len(huge_stack)
    assert 'truncated' in captured['stack']


def test_malformed_json_body_still_acks() -> None:
    response = lambda_handler(_event(body='{not json'), _context())

    assert response['statusCode'] == 202


def test_empty_body_still_acks() -> None:
    response = lambda_handler(_event(body=None), _context())

    assert response['statusCode'] == 202


def test_non_dict_json_body_is_tolerated() -> None:
    response = lambda_handler(_event(body=json.dumps(['not', 'a', 'dict'])), _context())

    assert response['statusCode'] == 202

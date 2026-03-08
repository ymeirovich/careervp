"""
L1.3 — Health Check Unit Tests

Validates deterministic /health contract output without live dependency checks.
"""

from __future__ import annotations

from datetime import datetime

import pytest


def _make_health_event() -> dict[str, object]:
    return {
        'httpMethod': 'GET',
        'path': '/health',
        'requestContext': {},
        'headers': {},
        'queryStringParameters': None,
        'body': None,
    }


def _call_health_handler(event: dict[str, object] | None = None) -> dict[str, object]:
    from careervp.handlers import health_handler

    return health_handler.lambda_handler(event or _make_health_event(), None)


def _call_health_check() -> dict[str, object]:
    from careervp.handlers import health_handler

    return health_handler.health_check()


@pytest.mark.unit
def test_health_handler_returns_200() -> None:
    response = _call_health_handler()
    assert response['statusCode'] == 200


@pytest.mark.unit
def test_health_payload_is_healthy() -> None:
    payload = _call_health_check()
    assert payload['status'] == 'healthy'


@pytest.mark.unit
def test_health_services_contract() -> None:
    payload = _call_health_check()
    services = payload.get('services')
    assert isinstance(services, dict)
    assert services.get('anthropic') == 'healthy'
    assert services.get('dynamodb') == 'healthy'
    assert 'bedrock' not in services
    assert 'lambda' not in services


@pytest.mark.unit
def test_health_metadata_contract() -> None:
    payload = _call_health_check()
    assert payload.get('version') == '1.0.0'
    timestamp = str(payload.get('timestamp'))
    parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    assert parsed.tzinfo is not None


@pytest.mark.unit
def test_health_requires_no_auth() -> None:
    event = _make_health_event()
    event['requestContext'] = {}
    response = _call_health_handler(event)
    assert response['statusCode'] == 200

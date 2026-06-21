"""Unit tests for FE-UI-046 POST /ai/assist handler error/success paths.

Covers AC-001, AC-006..AC-012.
"""

from __future__ import annotations

import concurrent.futures
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from careervp.handlers import ai_assist_handler as module
from careervp.handlers.ai_assist_handler import UpstreamMissingError
from careervp.logic.llm_client import BedrockInvocationError, CircuitBreakerOpen
from careervp.logic.prompts.ai_assist_prompt import AssistContext


@pytest.fixture(autouse=True)
def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-artifacts-table')


def _context() -> SimpleNamespace:
    return SimpleNamespace(
        aws_request_id='req-1',
        function_name='ai-assist-handler',
        memory_limit_in_mb=512,
        invoked_function_arn='arn:aws:lambda:us-east-1:1:function:ai-assist-handler',
    )


def _event(body: dict[str, Any] | None = None, user_id: str | None = 'user-1') -> dict[str, Any]:
    request_context: dict[str, Any] = {}
    if user_id is not None:
        request_context = {'authorizer': {'claims': {'sub': user_id}}}
    return {
        'httpMethod': 'POST',
        'path': '/ai/assist',
        'requestContext': request_context,
        'body': json.dumps(body if body is not None else _valid_body()),
    }


def _valid_body() -> dict[str, Any]:
    return {
        'artifact_type': 'cover_letter',
        'artifact_id': 'cl-1',
        'application_id': 'app-1',
        'field_key': 'body',
        'current_text': 'Dear hiring team',
        'locale': 'en',
    }


def test_no_auth_returns_401() -> None:
    response = module.lambda_handler(_event(user_id=None), _context())
    assert response['statusCode'] == 401


def test_bad_request_returns_400() -> None:
    # Unknown artifact_type fails validation (AC-011).
    body = {**_valid_body(), 'artifact_type': 'nope'}
    response = module.lambda_handler(_event(body), _context())
    assert response['statusCode'] == 400


def test_ownership_denied_returns_403() -> None:
    # AC-006
    with patch.object(module, '_user_owns_application', return_value=False):
        response = module.lambda_handler(_event(), _context())
    assert response['statusCode'] == 403


def test_ai_assist_does_not_require_subscription() -> None:
    # AI Assist is free — any authenticated user who owns the application can use it.
    fake_cache = SimpleNamespace(get=lambda key: None, set=lambda key, value: True)
    with (
        patch.object(module, '_user_owns_application', return_value=True),
        patch.object(module, '_resolve_context', return_value=AssistContext()),
        patch.object(module, '_get_cache', return_value=fake_cache),
        patch.object(module, '_call_llm', return_value='Some content'),
    ):
        response = module.lambda_handler(_event(), _context())
    assert response['statusCode'] == 200


def test_success_returns_200_with_resolved_context() -> None:
    # AC-001
    fake_cache = SimpleNamespace(get=lambda key: None, set=lambda key, value: True)
    with (
        patch.object(module, '_user_owns_application', return_value=True),
        patch.object(module, '_resolve_context', return_value=AssistContext()) as mock_ctx,
        patch.object(module, '_get_cache', return_value=fake_cache),
        patch.object(module, '_call_llm', return_value='Rewritten letter body'),
    ):
        response = module.lambda_handler(_event(), _context())
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['generated_markdown'] == 'Rewritten letter body'
    assert body['model']
    assert body['tokens'] >= 1
    mock_ctx.assert_called_once()


def test_timeout_returns_504() -> None:
    # AC-008
    fake_cache = SimpleNamespace(get=lambda key: None, set=lambda key, value: True)
    with (
        patch.object(module, '_user_owns_application', return_value=True),
        patch.object(module, '_resolve_context', return_value=AssistContext()),
        patch.object(module, '_get_cache', return_value=fake_cache),
        patch.object(module, '_call_llm', side_effect=concurrent.futures.TimeoutError()),
    ):
        response = module.lambda_handler(_event(), _context())
    assert response['statusCode'] == 504


def test_circuit_open_returns_503_with_retry_after() -> None:
    # AC-009
    fake_cache = SimpleNamespace(get=lambda key: None, set=lambda key, value: True)
    with (
        patch.object(module, '_user_owns_application', return_value=True),
        patch.object(module, '_resolve_context', return_value=AssistContext()),
        patch.object(module, '_get_cache', return_value=fake_cache),
        patch.object(module, '_call_llm', side_effect=CircuitBreakerOpen(retry_after=7.5)),
    ):
        response = module.lambda_handler(_event(), _context())
    assert response['statusCode'] == 503
    assert json.loads(response['body'])['retry_after'] == pytest.approx(7.5)


def test_provider_error_returns_503() -> None:
    fake_cache = SimpleNamespace(get=lambda key: None, set=lambda key, value: True)
    with (
        patch.object(module, '_user_owns_application', return_value=True),
        patch.object(module, '_resolve_context', return_value=AssistContext()),
        patch.object(module, '_get_cache', return_value=fake_cache),
        patch.object(module, '_call_llm', side_effect=BedrockInvocationError('overloaded')),
    ):
        response = module.lambda_handler(_event(), _context())
    assert response['statusCode'] == 503


def test_bedrock_timeout_message_returns_504() -> None:
    fake_cache = SimpleNamespace(get=lambda key: None, set=lambda key, value: True)
    with (
        patch.object(module, '_user_owns_application', return_value=True),
        patch.object(module, '_resolve_context', return_value=AssistContext()),
        patch.object(module, '_get_cache', return_value=fake_cache),
        patch.object(module, '_call_llm', side_effect=BedrockInvocationError('request timeout exceeded')),
    ):
        response = module.lambda_handler(_event(), _context())
    assert response['statusCode'] == 504


def test_upstream_missing_returns_409_deep_link() -> None:
    # AC-010
    with (
        patch.object(module, '_user_owns_application', return_value=True),
        patch.object(
            module,
            '_resolve_context',
            side_effect=UpstreamMissingError('cover_letter', 'vpr', 'app-1'),
        ),
    ):
        response = module.lambda_handler(_event(), _context())
    assert response['statusCode'] == 409
    body = json.loads(response['body'])
    assert body['missing_artifact'] == 'vpr'
    assert body['application_id'] == 'app-1'


def test_generic_exception_returns_500() -> None:
    # AC-011 (server error)
    fake_cache = SimpleNamespace(get=lambda key: None, set=lambda key, value: True)
    with (
        patch.object(module, '_user_owns_application', return_value=True),
        patch.object(module, '_resolve_context', return_value=AssistContext()),
        patch.object(module, '_get_cache', return_value=fake_cache),
        patch.object(module, '_call_llm', side_effect=RuntimeError('boom')),
    ):
        response = module.lambda_handler(_event(), _context())
    assert response['statusCode'] == 500


def test_cache_key_differs_per_field_and_text() -> None:
    # AC-012
    from careervp.models.api_models import AIAssistRequest

    base = _valid_body()
    req_a = AIAssistRequest.model_validate({**base, 'field_key': 'field_a', 'current_text': 'aaa'})
    req_b = AIAssistRequest.model_validate({**base, 'field_key': 'field_b', 'current_text': 'aaa'})
    req_c = AIAssistRequest.model_validate({**base, 'field_key': 'field_a', 'current_text': 'bbb'})

    key_a = module._cache_key(req_a, 'user message', 'model-x', 0.3)
    key_b = module._cache_key(req_b, 'user message', 'model-x', 0.3)
    key_c = module._cache_key(req_c, 'user message', 'model-x', 0.3)

    assert key_a != key_b
    assert key_a != key_c
    assert key_b != key_c


def test_cache_hit_short_circuits_llm() -> None:
    cached_payload = json.dumps({'generated_markdown': 'cached', 'model': 'm', 'tokens': 3})
    fake_cache = SimpleNamespace(get=lambda key: cached_payload, set=lambda key, value: True)
    with (
        patch.object(module, '_user_owns_application', return_value=True),
        patch.object(module, '_resolve_context', return_value=AssistContext()),
        patch.object(module, '_get_cache', return_value=fake_cache),
        patch.object(module, '_call_llm') as mock_llm,
    ):
        response = module.lambda_handler(_event(), _context())
    assert response['statusCode'] == 200
    assert json.loads(response['body'])['generated_markdown'] == 'cached'
    mock_llm.assert_not_called()

"""Unit tests for transient retry behavior in logic.utils.llm_client."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import httpx
import pytest
from anthropic import APIError

from careervp.logic.utils.llm_client import LLMRouter, retry_on_transient_error


def _api_error(message: str, status_code: int | None = None) -> APIError:
    error = APIError(
        message=message,
        request=httpx.Request('POST', 'https://example.com'),
        body=None,
    )
    if status_code is not None:
        cast_error = error
        cast_error_any: Any = cast_error
        cast_error_any.status_code = status_code
    return error


def test_retry_decorator_retries_on_529_overloaded() -> None:
    call_count = 0

    @retry_on_transient_error(max_retries=3, base_delay=0.0)
    def flaky_call() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise _api_error('Error code: 529 - overloaded_error')
        return 'ok'

    with patch('careervp.logic.utils.llm_client.sleep') as mock_sleep:
        result = flaky_call()

    assert result == 'ok'
    assert call_count == 2
    mock_sleep.assert_called_once()


def test_retry_decorator_does_not_retry_non_transient_api_error() -> None:
    call_count = 0

    @retry_on_transient_error(max_retries=3, base_delay=0.0)
    def flaky_call() -> str:
        nonlocal call_count
        call_count += 1
        raise _api_error('Bad request', status_code=400)

    with patch('careervp.logic.utils.llm_client.sleep') as mock_sleep:
        with pytest.raises(APIError):
            flaky_call()

    assert call_count == 1
    mock_sleep.assert_not_called()


def test_retry_decorator_retries_on_generic_overloaded_exception() -> None:
    class OverloadedError(Exception):
        status_code = 529

    call_count = 0

    @retry_on_transient_error(max_retries=3, base_delay=0.0)
    def flaky_call() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OverloadedError("Error code: 529 - {'type': 'overloaded_error', 'message': 'Overloaded'}")
        return 'ok'

    with patch('careervp.logic.utils.llm_client.sleep') as mock_sleep:
        result = flaky_call()

    assert result == 'ok'
    assert call_count == 2
    mock_sleep.assert_called_once()


def test_retry_decorator_raises_after_generic_overloaded_retries_exhausted() -> None:
    class OverloadedError(Exception):
        status_code = 529

    call_count = 0

    @retry_on_transient_error(max_retries=3, base_delay=0.0)
    def flaky_call() -> str:
        nonlocal call_count
        call_count += 1
        raise OverloadedError("Error code: 529 - {'type': 'overloaded_error', 'message': 'Overloaded'}")

    with patch('careervp.logic.utils.llm_client.sleep') as mock_sleep:
        with pytest.raises(OverloadedError):
            flaky_call()

    assert call_count == 3
    assert mock_sleep.call_count == 3


def test_llm_router_initializes_anthropic_with_retry_timeout() -> None:
    with patch('careervp.logic.utils.llm_client.Anthropic') as mock_anthropic:
        LLMRouter(api_key='test-key')

    mock_anthropic.assert_called_once_with(
        api_key='test-key',
        max_retries=3,
        timeout=60.0,
    )

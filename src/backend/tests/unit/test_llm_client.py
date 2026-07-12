"""
LLM Router unit tests per docs/specs/00-llm-router.md:14 test coverage.
"""

import json
import os
from time import monotonic
from unittest.mock import MagicMock, patch

import pytest
from anthropic import Anthropic

import careervp.logic.utils.llm_client as llm_client_module
from careervp.logic.circuit_breaker import CircuitBreaker, CircuitState
from careervp.logic.llm_cache import LLMResponseCache
from careervp.logic.llm_client import BedrockInvocationError, CircuitBreakerOpen, LLMClient
from careervp.logic.utils.llm_client import (
    HAIKU_MODEL_ID,
    SONNET_MODEL_ID,
    LLMRouter,
    TaskMode,
    get_llm_router,
)
from careervp.logic.utils.llm_metering import COST_PER_APP_ALARM_THRESHOLD, PRICE_PER_APP
from careervp.models.result import ResultCode


# Helper to calculate expected cost (mirrors private method)
def _calculate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost based on model and token usage."""
    if model_id == SONNET_MODEL_ID:
        input_cost = (input_tokens / 1_000_000) * 3.0
        output_cost = (output_tokens / 1_000_000) * 15.0
    else:  # Haiku
        input_cost = (input_tokens / 1_000_000) * 1.0
        output_cost = (output_tokens / 1_000_000) * 5.0
    return input_cost + output_cost


def _anthropic_text_response(text: str) -> MagicMock:
    """Build a mock Anthropic response object with a single text content block."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type='text', text=text)]
    return mock_response


class TestModelIds:
    """Verify model IDs match CLAUDE.md Decision 1.2."""

    def test_sonnet_model_id_format(self):
        """Sonnet model ID should be claude-sonnet-4-6 (latest available)."""
        assert SONNET_MODEL_ID == 'claude-sonnet-4-6'

    def test_haiku_model_id_format(self):
        """Haiku model ID should follow claude-haiku-4-5-YYYYMMDD format."""
        assert HAIKU_MODEL_ID.startswith('claude-haiku-4-5-')
        assert len(HAIKU_MODEL_ID) == len('claude-haiku-4-5-20251001')


class TestCostCalculation:
    """Verify cost calculation per CLAUDE.md pricing model."""

    def test_sonnet_cost_calculation(self):
        """Sonnet 4.5: $3/1M input, $15/1M output."""
        cost = _calculate_cost(SONNET_MODEL_ID, input_tokens=1_000_000, output_tokens=1_000_000)
        assert cost == 18.0  # $3 + $15

    def test_haiku_cost_calculation(self):
        """Haiku 4.5: $1.00/1M input, $5.00/1M output."""
        cost = _calculate_cost(HAIKU_MODEL_ID, input_tokens=1_000_000, output_tokens=1_000_000)
        assert cost == 6.0  # $1.00 + $5.00

    def test_small_token_count(self):
        """Verify fractional costs for small token counts."""
        cost = _calculate_cost(SONNET_MODEL_ID, input_tokens=1000, output_tokens=2000)
        # 1000/1M * $3 = $0.003, 2000/1M * $15 = $0.03
        assert cost == pytest.approx(0.033)


class TestTaskMode:
    """Verify task mode routing."""

    def test_strategic_mode_returns_sonnet(self):
        """STRATEGIC tasks should route to Sonnet."""
        router = LLMRouter(api_key='test-key')
        assert router._resolve_model(TaskMode.STRATEGIC) == SONNET_MODEL_ID

    def test_template_mode_returns_haiku(self):
        """TEMPLATE tasks should route to Haiku."""
        router = LLMRouter(api_key='test-key')
        assert router._resolve_model(TaskMode.TEMPLATE) == HAIKU_MODEL_ID


class TestLLMRouter:
    """Test LLMRouter core functionality with mocked Anthropic client."""

    def setup_method(self):
        """Reset singleton before each test."""
        llm_client_module._llm_router = None
        # Clear env vars that might interfere
        env_to_clear = ['ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY_SSM_PARAM']
        self.original_env = {k: os.environ.get(k) for k in env_to_clear}
        for k in env_to_clear:
            os.environ.pop(k, None)

    def teardown_method(self):
        """Restore env vars after each test."""
        for k, v in self.original_env.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)

    def test_init_with_explicit_api_key(self):
        """Router should use explicit API key."""
        router = LLMRouter(api_key='explicit-key')
        assert router._api_key == 'explicit-key'

    def test_init_with_env_var(self):
        """Router should fall back to environment variable."""
        os.environ['ANTHROPIC_API_KEY'] = 'env-key'
        router = LLMRouter()
        assert router._api_key == 'env-key'

    def test_init_without_api_key_raises(self):
        """Router should raise ValueError when no API key available."""
        with pytest.raises(ValueError, match='ANTHROPIC_API_KEY not found'):
            LLMRouter()

    @patch.object(Anthropic, 'messages')
    def test_invoke_success_returns_result(self, mock_messages):
        """Successful LLM call should return Result with data."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type='text', text='Test response')]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 200
        mock_response.stop_reason = 'end_turn'
        mock_messages.create.return_value = mock_response

        router = LLMRouter(api_key='test-key')
        result = router.invoke(
            mode=TaskMode.TEMPLATE,
            system_prompt='You are helpful.',
            user_prompt='Hello!',
        )

        assert result.success is True
        assert result.data is not None
        assert result.data['text'] == 'Test response'
        assert result.data['input_tokens'] == 100
        assert result.data['output_tokens'] == 200
        assert result.code == ResultCode.SUCCESS

    @patch.object(Anthropic, 'messages')
    def test_invoke_cost_calculation(self, mock_messages):
        """Verify cost is calculated and logged."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type='text', text='Response')]
        mock_response.usage.input_tokens = 1000
        mock_response.usage.output_tokens = 1000
        mock_response.stop_reason = 'end_turn'
        mock_messages.create.return_value = mock_response

        router = LLMRouter(api_key='test-key')
        result = router.invoke(
            mode=TaskMode.TEMPLATE,
            system_prompt='System',
            user_prompt='User',
        )

        # Haiku: 1000 input * 1.0/1M + 1000 output * 5.0/1M = $0.006
        expected_cost = (1000 / 1_000_000) * 1.0 + (1000 / 1_000_000) * 5.0
        assert result.data is not None
        assert result.data['cost'] == pytest.approx(expected_cost)

    @patch.object(Anthropic, 'messages')
    def test_invoke_records_prompt_cache_usage_fields(self, mock_messages):
        """Provider cache-read usage should be surfaced directly, not re-estimated."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type='text', text='Response')]
        mock_response.usage.input_tokens = 120
        mock_response.usage.output_tokens = 45
        mock_response.usage.cache_read_input_tokens = 80
        mock_response.usage.cache_creation_input_tokens = 0
        mock_response.stop_reason = 'end_turn'
        mock_messages.create.return_value = mock_response

        router = LLMRouter(api_key='test-key')
        result = router.invoke(
            mode=TaskMode.TEMPLATE,
            system_prompt='System',
            user_prompt='User',
            use_system_cache=True,
        )

        assert result.data is not None
        assert result.data['input_tokens'] == 120
        assert result.data['output_tokens'] == 45
        assert result.data['cache_read_input_tokens'] == 80
        assert result.data['cache_creation_input_tokens'] == 0
        assert result.data['prompt_cache_hit'] is True

    def test_invoke_without_api_key_returns_error(self):
        """Invoke without API key should return error Result."""
        router = LLMRouter(api_key='test-key')
        router._api_key = None  # Simulate missing key after init

        # Patch messages.create to avoid real API call
        with patch.object(router._client, 'messages') as mock_messages:
            mock_messages.create.side_effect = Exception('API call failed')

            result = router.invoke(
                mode=TaskMode.TEMPLATE,
                system_prompt='System',
                user_prompt='User',
            )

            assert result.success is False
            assert result.code == ResultCode.INTERNAL_ERROR

    def test_singleton_pattern(self):
        """get_llm_router should return singleton instance."""
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        with patch.object(Anthropic, '__init__', return_value=None):
            with patch.object(Anthropic, 'messages', create=MagicMock()):
                llm_client_module._llm_router = None  # Reset singleton
                router1 = get_llm_router()
                router2 = get_llm_router()
                assert router1 is router2


class TestCostThresholds:
    """Test cost alerting thresholds per CLAUDE.md."""

    def test_max_cost_per_application(self):
        """MAX_COST_PER_APPLICATION should be $0.25 per spec (raised from $0.15 to cover VPR baseline cost)."""
        from careervp.logic.utils.llm_client import MAX_COST_PER_APPLICATION

        assert MAX_COST_PER_APPLICATION == 0.25

    # scope_lock_clause: Q-10
    def test_q10_price_per_app_threshold_is_derived_from_subscription_midpoint(self):
        assert PRICE_PER_APP == pytest.approx(1.25)
        assert COST_PER_APP_ALARM_THRESHOLD == pytest.approx(0.375)


class TestLLMClientCircuitBreaker:
    """Circuit-breaker integration tests for careervp.logic.llm_client.LLMClient."""

    @staticmethod
    def _build_client(
        *,
        cache: LLMResponseCache | None = None,
        create_side_effect: Exception | None = None,
        create_return_value: MagicMock | None = None,
    ) -> tuple[LLMClient, MagicMock]:
        mock_client = MagicMock()
        if create_side_effect is not None:
            mock_client.messages.create.side_effect = create_side_effect
        if create_return_value is not None:
            mock_client.messages.create.return_value = create_return_value

        circuit_breaker = CircuitBreaker(
            name='test_llm_client',
            failure_threshold=5,
            failure_window_seconds=60.0,
            recovery_timeout_seconds=30.0,
            expected_exception=BedrockInvocationError,
        )
        llm_client = LLMClient(client=mock_client, cache=cache, circuit_breaker=circuit_breaker)
        return llm_client, mock_client

    def test_circuit_breaker_opens_after_threshold(self):
        llm_client, _ = self._build_client(create_side_effect=RuntimeError('provider unavailable'))

        for _ in range(5):
            with pytest.raises(BedrockInvocationError):
                llm_client.generate(prompt='return {"ok": true}')

        with pytest.raises(CircuitBreakerOpen) as exc_info:
            llm_client.generate(prompt='return {"ok": true}')

        assert llm_client._circuit_breaker.state == CircuitState.OPEN
        assert exc_info.value.retry_after > 0

    def test_circuit_breaker_half_open_after_timeout(self):
        llm_client, _ = self._build_client(create_side_effect=RuntimeError('provider unavailable'))

        for _ in range(5):
            with pytest.raises(BedrockInvocationError):
                llm_client.generate(prompt='return {"ok": true}')

        llm_client._circuit_breaker._opened_at = monotonic() - 31.0
        assert llm_client._circuit_breaker.can_proceed() is True
        assert llm_client._circuit_breaker.state == CircuitState.HALF_OPEN

    def test_generate_returns_real_provider_usage_metadata(self):
        response = _anthropic_text_response('{"ok": true}')
        response.usage.input_tokens = 321
        response.usage.output_tokens = 123
        response.usage.cache_read_input_tokens = 0
        response.usage.cache_creation_input_tokens = 0

        llm_client, _ = self._build_client(create_return_value=response)
        payload = llm_client.generate(prompt='return {"ok": true}')

        assert payload['input_tokens'] == 321
        assert payload['output_tokens'] == 123
        assert payload['cost'] > 0

    def test_complete_returns_real_provider_usage_metadata(self):
        response = _anthropic_text_response('hello')
        response.usage.input_tokens = 222
        response.usage.output_tokens = 111
        response.usage.cache_read_input_tokens = 75
        response.usage.cache_creation_input_tokens = 0

        llm_client, _ = self._build_client(create_return_value=response)
        payload = llm_client.complete(
            prompt='hello',
            system_prompt='system',
            use_system_cache=True,
        )

        assert payload.text == 'hello'
        assert payload.input_tokens == 222
        assert payload.output_tokens == 111
        assert payload.prompt_cache_hit is True

    def test_circuit_breaker_closed_after_success(self):
        llm_client, mock_client = self._build_client(create_side_effect=RuntimeError('provider unavailable'))

        for _ in range(5):
            with pytest.raises(BedrockInvocationError):
                llm_client.generate(prompt='return {"ok": true}')

        llm_client._circuit_breaker._opened_at = monotonic() - 31.0
        mock_client.messages.create.side_effect = None
        mock_client.messages.create.return_value = _anthropic_text_response('{"status": "ok"}')

        result = llm_client.generate(prompt='return {"ok": true}')

        assert result['status'] == 'ok'
        assert result['input_tokens'] >= 0
        assert llm_client._circuit_breaker.state == CircuitState.CLOSED
        assert llm_client._circuit_breaker.failure_count == 0

    def test_llm_client_returns_fallback_on_open_circuit(self):
        cache = LLMResponseCache(table=None)
        with patch.object(cache, 'get', side_effect=[None, json.dumps({'text': 'cached fallback'})]) as mock_cache_get:
            llm_client, mock_client = self._build_client(cache=cache, create_side_effect=RuntimeError('should not be called'))
            llm_client._circuit_breaker._state = CircuitState.OPEN
            llm_client._circuit_breaker._opened_at = monotonic()

            result = llm_client.generate(prompt='return {"ok": true}')

        assert result == {'text': 'cached fallback'}
        assert mock_cache_get.call_count == 2
        assert mock_client.messages.create.call_count == 0

    @patch('careervp.logic.llm_client.time.sleep', autospec=True)
    def test_llm_client_retries_on_transient_529_and_recovers(self, mock_sleep: MagicMock):
        class OverloadedError(Exception):
            status_code = 529

        transient_error = OverloadedError("Error code: 529 - {'type': 'overloaded_error', 'message': 'Overloaded'}")
        llm_client, mock_client = self._build_client()
        mock_client.messages.create.side_effect = [transient_error, _anthropic_text_response('{"status":"ok"}')]

        result = llm_client.generate(prompt='return {"ok": true}')

        assert result['status'] == 'ok'
        assert result['input_tokens'] >= 0
        assert mock_client.messages.create.call_count == 2
        mock_sleep.assert_called_once()

    @patch('careervp.logic.llm_client.time.sleep', autospec=True)
    def test_llm_client_exhausts_transient_retries_and_raises(self, mock_sleep: MagicMock):
        class OverloadedError(Exception):
            status_code = 529

        transient_error = OverloadedError("Error code: 529 - {'type': 'overloaded_error', 'message': 'Overloaded'}")
        llm_client, mock_client = self._build_client(create_side_effect=transient_error)

        with pytest.raises(BedrockInvocationError, match='Failed to invoke LLM model'):
            llm_client.generate(prompt='return {"ok": true}')

        assert mock_client.messages.create.call_count == 3
        assert mock_sleep.call_count == 2

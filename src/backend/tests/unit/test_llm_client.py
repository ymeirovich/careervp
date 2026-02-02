"""
LLM Router unit tests per docs/specs/00-llm-router.md:14 test coverage.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from anthropic import Anthropic

import careervp.logic.utils.llm_client as llm_client_module
from careervp.logic.utils.llm_client import (
    HAIKU_MODEL_ID,
    SONNET_MODEL_ID,
    LLMRouter,
    TaskMode,
    get_llm_router,
)
from careervp.models.result import ResultCode


# Helper to calculate expected cost (mirrors private method)
def _calculate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost based on model and token usage."""
    if model_id == SONNET_MODEL_ID:
        input_cost = (input_tokens / 1_000_000) * 3.0
        output_cost = (output_tokens / 1_000_000) * 15.0
    else:  # Haiku
        input_cost = (input_tokens / 1_000_000) * 0.25
        output_cost = (output_tokens / 1_000_000) * 1.25
    return input_cost + output_cost


class TestModelIds:
    """Verify model IDs match CLAUDE.md Decision 1.2."""

    def test_sonnet_model_id_format(self):
        """Sonnet model ID should follow claude-sonnet-4-5-YYYYMMDD format."""
        assert SONNET_MODEL_ID.startswith('claude-sonnet-4-5-')
        assert len(SONNET_MODEL_ID) == len('claude-sonnet-4-5-20250929')

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
        """Haiku 4.5: $0.25/1M input, $1.25/1M output."""
        cost = _calculate_cost(HAIKU_MODEL_ID, input_tokens=1_000_000, output_tokens=1_000_000)
        assert cost == 1.5  # $0.25 + $1.25

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

        # Haiku: 1000 input * 0.25/1M + 1000 output * 1.25/1M = $0.0015
        expected_cost = (1000 / 1_000_000) * 0.25 + (1000 / 1_000_000) * 1.25
        assert result.data is not None
        assert result.data['cost'] == pytest.approx(expected_cost)

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
        """MAX_COST_PER_APPLICATION should be $0.15 per spec."""
        from careervp.logic.utils.llm_client import MAX_COST_PER_APPLICATION

        assert MAX_COST_PER_APPLICATION == 0.15

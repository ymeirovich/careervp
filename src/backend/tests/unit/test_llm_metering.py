from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from careervp.logic.utils import llm_metering


def test_record_llm_usage_emits_cost_per_application_metric() -> None:
    emitted: list[dict[str, object]] = []
    mock_repo = MagicMock()
    mock_repo.record_llm_usage.return_value = {
        'cost_per_application_usd': 0.41,
        'input_tokens_total': 300,
        'output_tokens_total': 120,
        'prompt_cache_hit_rate': 0.5,
    }

    def _capture(*, dimensions: dict[str, str], metric_values: dict[str, float | int]) -> None:
        emitted.append({'dimensions': dimensions, 'metric_values': metric_values})

    with (
        patch.object(llm_metering, '_emit_metric_set', side_effect=_capture),
        patch.object(llm_metering, '_get_application_repository', return_value=mock_repo),
        llm_metering.bind_llm_usage_context(application_id='app-1', user_id='user-1'),
    ):
        totals = llm_metering.record_llm_usage(
            model_id='claude-haiku-4-5-20251001',
            task_mode='TEMPLATE',
            input_tokens=100,
            output_tokens=40,
            cost_usd=0.20,
            prompt_cache_hit=False,
            prompt_cache_lookup=True,
        )

    assert totals is not None
    mock_repo.record_llm_usage.assert_called_once()
    assert any('CostPerApplicationUSD' in entry['metric_values'] for entry in emitted)
    assert any('PromptCacheLookups' in entry['metric_values'] for entry in emitted)
    assert any('CostPerApplicationThresholdBreaches' in entry['metric_values'] for entry in emitted)


def test_record_llm_usage_uses_prompt_cache_hit_for_hit_rate_metric() -> None:
    emitted: list[dict[str, object]] = []

    def _capture(*, dimensions: dict[str, str], metric_values: dict[str, float | int]) -> None:
        emitted.append({'dimensions': dimensions, 'metric_values': metric_values})

    with patch.object(llm_metering, '_emit_metric_set', side_effect=_capture):
        llm_metering.record_llm_usage(
            model_id='claude-sonnet-4-6',
            task_mode='STRATEGIC',
            input_tokens=500,
            output_tokens=200,
            cost_usd=0.10,
            prompt_cache_hit=True,
            prompt_cache_lookup=True,
        )

    matching = [entry for entry in emitted if 'PromptCacheHitRate' in entry['metric_values']]
    assert matching
    assert matching[0]['metric_values']['PromptCacheHits'] == 1
    assert matching[0]['metric_values']['PromptCacheHitRate'] == pytest.approx(100.0)

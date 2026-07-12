from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from aws_lambda_powertools.metrics import Metrics, MetricUnit

from careervp.dal.application_repository import ApplicationRepository
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.utils.observability import METRICS_NAMESPACE, logger

PROVISIONAL_SUBSCRIPTION_PRICE_USD = 25.0
PAID_APPS_PER_SUBSCRIBER_PER_MONTH = 20
PRICE_PER_APP = PROVISIONAL_SUBSCRIPTION_PRICE_USD / PAID_APPS_PER_SUBSCRIBER_PER_MONTH
COST_PER_APP_ALARM_RATIO = 0.30
COST_PER_APP_ALARM_THRESHOLD = COST_PER_APP_ALARM_RATIO * PRICE_PER_APP
_DEFAULT_TRAFFIC_ORIGIN = 'product'
_VALID_TRAFFIC_ORIGINS = {'product', 'dev-eval'}
_usage_context: ContextVar['LLMUsageContext | None'] = ContextVar('llm_usage_context', default=None)


@dataclass(frozen=True)
class LLMUsageContext:
    application_id: str
    user_id: str
    traffic_origin: str = _DEFAULT_TRAFFIC_ORIGIN


@contextmanager
def bind_llm_usage_context(
    *,
    application_id: str,
    user_id: str,
    traffic_origin: str | None = None,
) -> Any:
    token = _usage_context.set(
        LLMUsageContext(
            application_id=application_id,
            user_id=user_id,
            traffic_origin=resolve_traffic_origin(traffic_origin),
        )
    )
    try:
        yield
    finally:
        _usage_context.reset(token)


def current_llm_usage_context() -> LLMUsageContext | None:
    return _usage_context.get()


def resolve_traffic_origin(value: str | None) -> str:
    candidate = str(value or os.environ.get('LLM_TRAFFIC_ORIGIN', _DEFAULT_TRAFFIC_ORIGIN)).strip().lower()
    if candidate in _VALID_TRAFFIC_ORIGINS:
        return candidate
    return _DEFAULT_TRAFFIC_ORIGIN


def calculate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    normalized = model_id.lower()
    if 'sonnet' in normalized:
        input_cost = (input_tokens / 1_000_000) * 3.0
        output_cost = (output_tokens / 1_000_000) * 15.0
    else:
        input_cost = (input_tokens / 1_000_000) * 1.0
        output_cost = (output_tokens / 1_000_000) * 5.0
    return input_cost + output_cost


def record_llm_usage(
    *,
    model_id: str,
    task_mode: str | None,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    prompt_cache_hit: bool,
    prompt_cache_lookup: bool,
    cache_read_input_tokens: int = 0,
    cache_creation_input_tokens: int = 0,
    traffic_origin: str | None = None,
) -> dict[str, float | int] | None:
    resolved_origin = resolve_traffic_origin(traffic_origin)
    metric_values: dict[str, float | int] = {
        'InputTokens': input_tokens,
        'OutputTokens': output_tokens,
        'TotalTokens': input_tokens + output_tokens,
        'CostUSD': round(cost_usd, 6),
        'PromptCacheLookups': 1 if prompt_cache_lookup else 0,
        'PromptCacheHits': 1 if prompt_cache_hit else 0,
        'CacheReadInputTokens': cache_read_input_tokens,
        'CacheCreationInputTokens': cache_creation_input_tokens,
    }
    if prompt_cache_lookup:
        metric_values['PromptCacheHitRate'] = 100.0 if prompt_cache_hit else 0.0

    _emit_metric_set(dimensions={'TrafficOrigin': resolved_origin}, metric_values=metric_values)

    context = current_llm_usage_context()
    totals: dict[str, float | int] | None = None
    if context is not None:
        repository = _get_application_repository()
        if repository is not None:
            totals = repository.record_llm_usage(
                application_id=context.application_id,
                user_id=context.user_id,
                model_id=model_id,
                traffic_origin=resolved_origin,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                prompt_cache_hit=prompt_cache_hit,
                prompt_cache_lookup=prompt_cache_lookup,
            )
            _emit_metric_set(
                dimensions={'TrafficOrigin': resolved_origin},
                metric_values={
                    'CostPerApplicationUSD': float(totals['cost_per_application_usd']),
                    'ApplicationInputTokens': int(totals['input_tokens_total']),
                    'ApplicationOutputTokens': int(totals['output_tokens_total']),
                    'PromptCacheHitRate': float(totals['prompt_cache_hit_rate']) * 100.0,
                },
            )
            if float(totals['cost_per_application_usd']) > COST_PER_APP_ALARM_THRESHOLD:
                _emit_metric_set(
                    dimensions={'TrafficOrigin': resolved_origin},
                    metric_values={'CostPerApplicationThresholdBreaches': 1},
                )

    logger.info(
        'LLM usage metered',
        model_id=model_id,
        task_mode=task_mode,
        traffic_origin=resolved_origin,
        application_id=context.application_id if context else None,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=round(cost_usd, 6),
        prompt_cache_hit=prompt_cache_hit,
        prompt_cache_lookup=prompt_cache_lookup,
        cache_read_input_tokens=cache_read_input_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cost_per_application_usd=float(totals['cost_per_application_usd']) if totals else None,
    )
    return totals


def _get_application_repository() -> ApplicationRepository | None:
    table_name = str(os.environ.get('APPLICATIONS_TABLE_NAME', '')).strip()
    if not table_name:
        return None
    return ApplicationRepository(DynamoDalHandler(table_name))


def _emit_metric_set(*, dimensions: dict[str, str], metric_values: dict[str, float | int]) -> None:
    metric_logger = Metrics(namespace=METRICS_NAMESPACE)
    for key, value in dimensions.items():
        metric_logger.add_dimension(name=key, value=value)
    for metric_name, metric_value in metric_values.items():
        unit = MetricUnit.Count
        if metric_name in {'CostUSD', 'CostPerApplicationUSD'}:
            unit = MetricUnit.NoUnit
        elif metric_name == 'PromptCacheHitRate':
            unit = MetricUnit.Percent
        metric_logger.add_metric(name=metric_name, unit=unit, value=float(metric_value))
    metric_logger.flush_metrics()


__all__ = [
    'COST_PER_APP_ALARM_THRESHOLD',
    'COST_PER_APP_ALARM_RATIO',
    'LLMUsageContext',
    'PAID_APPS_PER_SUBSCRIBER_PER_MONTH',
    'PRICE_PER_APP',
    'PROVISIONAL_SUBSCRIPTION_PRICE_USD',
    'bind_llm_usage_context',
    'calculate_cost',
    'current_llm_usage_context',
    'record_llm_usage',
    'resolve_traffic_origin',
]

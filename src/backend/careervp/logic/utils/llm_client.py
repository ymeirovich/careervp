"""
LLM Router Utility - Hybrid Model Strategy.
Per docs/specs/00-llm-router.md: Centralized model switching for 91% profit margins.

STRATEGIC tasks (Sonnet 4.5): VPR Generation, Gap Analysis
TEMPLATE tasks (Haiku 4.5): CV Tailoring, Cover Letter, Interview Prep
"""

import os
from enum import Enum
from functools import wraps
from time import sleep
from typing import Any

from anthropic import Anthropic, APIError, RateLimitError
from aws_lambda_powertools.metrics import MetricUnit

from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.models.result import Result, ResultCode

# Model IDs per Decision 1.2 in CLAUDE.md
SONNET_MODEL_ID = 'claude-sonnet-4-5-20250514'
HAIKU_MODEL_ID = 'claude-haiku-4-5-20250514'

# Cost thresholds for alerting (per CLAUDE.md Emergency Contacts)
MAX_COST_PER_APPLICATION = 0.15


class TaskMode(str, Enum):
    """Task complexity modes for model routing."""

    STRATEGIC = 'STRATEGIC'  # VPR, Gap Analysis -> Sonnet 4.5
    TEMPLATE = 'TEMPLATE'  # CV, Cover Letter, Interview -> Haiku 4.5


def retry_on_transient_error(max_retries: int = 3, base_delay: float = 1.0):
    """
    Retry decorator for transient API errors.
    Per spec: Wrap all calls in retry decorator for transient 500 errors.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    last_exception = e
                    delay = base_delay * (2**attempt)
                    logger.warning('Rate limited, retrying', attempt=attempt + 1, delay=delay)
                    sleep(delay)
                except APIError as e:
                    if e.status_code and e.status_code >= 500:
                        last_exception = e
                        delay = base_delay * (2**attempt)
                        logger.warning('Transient API error, retrying', attempt=attempt + 1, status_code=e.status_code, delay=delay)
                        sleep(delay)
                    else:
                        raise
            raise last_exception

        return wrapper

    return decorator


class LLMRouter:
    """
    Centralized LLM client with hybrid model routing.
    Logs token usage as custom metrics via AWS Powertools.
    """

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self._api_key:
            raise ValueError('ANTHROPIC_API_KEY environment variable not set')
        self._client = Anthropic(api_key=self._api_key)

    def _resolve_model(self, mode: TaskMode) -> str:
        """Route to appropriate model based on task complexity."""
        if mode == TaskMode.STRATEGIC:
            return SONNET_MODEL_ID
        return HAIKU_MODEL_ID

    def _calculate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost based on model and token usage.
        Sonnet 4.5: $3/1M input, $15/1M output
        Haiku 4.5: $0.25/1M input, $1.25/1M output
        """
        if model_id == SONNET_MODEL_ID:
            input_cost = (input_tokens / 1_000_000) * 3.0
            output_cost = (output_tokens / 1_000_000) * 15.0
        else:  # Haiku
            input_cost = (input_tokens / 1_000_000) * 0.25
            output_cost = (output_tokens / 1_000_000) * 1.25
        return input_cost + output_cost

    @tracer.capture_method(capture_response=False)
    @retry_on_transient_error(max_retries=3)
    def invoke(
        self,
        mode: TaskMode,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> Result[dict[str, Any]]:
        """
        Invoke the LLM with automatic model routing.

        Args:
            mode: TaskMode.STRATEGIC for Sonnet, TaskMode.TEMPLATE for Haiku
            system_prompt: System context and instructions
            user_prompt: User message/input
            max_tokens: Maximum output tokens
            temperature: Creativity parameter (lower = more consistent)

        Returns:
            Result with response text, token usage, and cost
        """
        model_id = self._resolve_model(mode)

        logger.info('Invoking LLM', mode=mode.value, model=model_id, max_tokens=max_tokens)

        try:
            response = self._client.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{'role': 'user', 'content': user_prompt}],
            )

            # Extract usage metrics
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = self._calculate_cost(model_id, input_tokens, output_tokens)

            # Log metrics via Powertools
            self._log_metrics(mode, model_id, input_tokens, output_tokens, cost)

            # Check cost threshold
            if cost > MAX_COST_PER_APPLICATION:
                logger.error('Cost threshold exceeded', cost=cost, threshold=MAX_COST_PER_APPLICATION)

            # Extract text content
            text_content = ''
            for block in response.content:
                if block.type == 'text':
                    text_content = block.text
                    break

            return Result(
                success=True,
                data={
                    'text': text_content,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'cost': cost,
                    'model': model_id,
                    'stop_reason': response.stop_reason,
                },
                code=ResultCode.SUCCESS,
            )

        except RateLimitError as e:
            logger.error('Rate limit exceeded after retries', error=str(e))
            return Result(success=False, error=str(e), code=ResultCode.LLM_RATE_LIMITED)

        except APIError as e:
            logger.error('LLM API error', error=str(e), status_code=getattr(e, 'status_code', None))
            return Result(success=False, error=str(e), code=ResultCode.LLM_API_ERROR)

        except Exception as e:
            logger.exception('Unexpected LLM error', error=str(e))
            return Result(success=False, error=str(e), code=ResultCode.INTERNAL_ERROR)

    def _log_metrics(self, mode: TaskMode, model_id: str, input_tokens: int, output_tokens: int, cost: float) -> None:
        """Log token usage as custom CloudWatch metrics."""
        metrics.add_dimension(name='TaskMode', value=mode.value)
        metrics.add_dimension(name='Model', value=model_id.split('-')[1])  # 'sonnet' or 'haiku'

        metrics.add_metric(name='InputTokens', unit=MetricUnit.Count, value=input_tokens)
        metrics.add_metric(name='OutputTokens', unit=MetricUnit.Count, value=output_tokens)
        metrics.add_metric(name='TotalTokens', unit=MetricUnit.Count, value=input_tokens + output_tokens)
        metrics.add_metric(name='CostUSD', unit=MetricUnit.Count, value=cost * 100)  # Store as cents for precision

        logger.info(
            'LLM metrics logged',
            mode=mode.value,
            model=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=f'${cost:.6f}',
        )


# Singleton instance for Lambda warm starts
_llm_router: LLMRouter | None = None


def get_llm_router() -> LLMRouter:
    """Get or create singleton LLM router instance."""
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router

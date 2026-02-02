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
from typing import Any, Callable, ParamSpec, TypeVar, cast

import boto3
from anthropic import Anthropic, APIError, RateLimitError
from aws_lambda_powertools.metrics import MetricUnit
from botocore.exceptions import BotoCoreError, ClientError

from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.models.result import Result, ResultCode

P = ParamSpec('P')
R = TypeVar('R')

# Model IDs per Decision 1.2 in CLAUDE.md - Updated to current available versions
SONNET_MODEL_ID = 'claude-sonnet-4-5-20250929'
HAIKU_MODEL_ID = 'claude-haiku-4-5-20251001'

# Cost thresholds for alerting (per CLAUDE.md Emergency Contacts)
MAX_COST_PER_APPLICATION = 0.15


class TaskMode(str, Enum):
    """Task complexity modes for model routing."""

    STRATEGIC = 'STRATEGIC'  # VPR, Gap Analysis -> Sonnet 4.5
    TEMPLATE = 'TEMPLATE'  # CV, Cover Letter, Interview -> Haiku 4.5


def retry_on_transient_error(max_retries: int = 3, base_delay: float = 1.0) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Retry decorator for transient API errors.
    Per spec: Wrap all calls in retry decorator for transient 500 errors.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exception: Exception | None = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    last_exception = e
                    delay = base_delay * (2**attempt)
                    logger.warning('Rate limited, retrying', attempt=attempt + 1, delay=delay)
                    sleep(delay)
                except APIError as e:
                    status_code = getattr(e, 'status_code', None)
                    if isinstance(status_code, int) and status_code >= 500:
                        last_exception = e
                        delay = base_delay * (2**attempt)
                        logger.warning('Transient API error, retrying', attempt=attempt + 1, status_code=status_code, delay=delay)
                        sleep(delay)
                    else:
                        raise
            if last_exception is not None:
                raise last_exception
            raise RuntimeError('Retry attempts exhausted without capturing an exception')

        return wrapper

    return decorator


def _capture_method_typed(*decorator_args: Any, **decorator_kwargs: Any) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Typed shim for tracer.capture_method to satisfy mypy."""
    decorator = tracer.capture_method(*decorator_args, **decorator_kwargs)
    return cast(Callable[[Callable[P, R]], Callable[P, R]], decorator)


class LLMRouter:
    """
    Centralized LLM client with hybrid model routing.
    Logs token usage as custom metrics via AWS Powertools.
    """

    def __init__(self, api_key: str | None = None):
        # Priority: explicit api_key > direct env var > SSM Parameter Store
        self._api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')

        if not self._api_key:
            # Try to fetch from SSM Parameter Store
            ssm_param_name = os.environ.get('ANTHROPIC_API_KEY_SSM_PARAM')
            if ssm_param_name:
                logger.info('Fetching ANTHROPIC_API_KEY from SSM Parameter Store', parameter=ssm_param_name)
                self._api_key = self._fetch_from_ssm(ssm_param_name)

        if not self._api_key:
            raise ValueError('ANTHROPIC_API_KEY not found in environment variable or SSM Parameter Store')

        self._client = Anthropic(api_key=self._api_key)

    def _fetch_from_ssm(self, parameter_name: str) -> str | None:
        """
        Fetch API key from SSM Parameter Store.

        Args:
            parameter_name: SSM parameter path (e.g., /careervp/dev/anthropic-api-key)

        Returns:
            The parameter value or None if fetch fails
        """
        try:
            ssm_client = boto3.client('ssm')
            response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
            api_key: str = response['Parameter']['Value']
            logger.info('Successfully fetched ANTHROPIC_API_KEY from SSM', parameter=parameter_name)
            return api_key
        except (ClientError, BotoCoreError) as e:
            logger.error('Failed to fetch parameter from SSM', parameter=parameter_name, error=str(e))
            return None
        except KeyError as e:
            logger.error('Unexpected SSM response structure', parameter=parameter_name, error=str(e))
            return None

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

    @_capture_method_typed(capture_response=False)
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

"""
LLM Router Utility - Hybrid Model Strategy.
Per docs/specs/00-llm-router.md: Centralized model switching for 91% profit margins.

STRATEGIC tasks (Sonnet 4.6): VPR Generation, Gap Analysis
TEMPLATE tasks (Haiku 4.5): CV Tailoring, Cover Letter, Interview Prep
"""

import os
from enum import Enum
from functools import wraps
from time import sleep
from typing import Any, Callable, ParamSpec, TypeVar, cast

import boto3  # type: ignore[import-untyped]
from anthropic import Anthropic, APIError, RateLimitError
from anthropic.types import TextBlockParam
from botocore.exceptions import BotoCoreError, ClientError  # type: ignore[import-untyped]

from careervp.handlers.utils.observability import logger, tracer
from careervp.logic.utils.llm_metering import calculate_cost, record_llm_usage
from careervp.models.result import Result, ResultCode

P = ParamSpec('P')
R = TypeVar('R')

# Model IDs — injected by CDK as env vars so swapping models needs only cdk deploy
SONNET_MODEL_ID = os.environ.get('STRATEGIC_MODEL_ID', 'claude-sonnet-4-6')
HAIKU_MODEL_ID = os.environ.get('TEMPLATE_MODEL_ID', 'claude-haiku-4-5-20251001')

# Cost thresholds for alerting (per CLAUDE.md Emergency Contacts)
# VPR Sonnet baseline ~$0.16/run; $0.25 gives headroom for one retry
MAX_COST_PER_APPLICATION = 0.25


class TaskMode(str, Enum):
    """Task complexity modes for model routing."""

    STRATEGIC = 'STRATEGIC'  # VPR, Gap Analysis -> Sonnet 4.6
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
                    logger.warning(
                        'Rate limited, retrying attempt=%s delay=%.2f',
                        attempt + 1,
                        delay,
                    )
                    sleep(delay)
                except APIError as e:
                    is_transient = _is_transient_error(e)
                    if is_transient:
                        last_exception = e
                        delay = base_delay * (2**attempt)
                        logger.warning(
                            'Transient API error, retrying attempt=%s status_code=%s delay=%.2f',
                            attempt + 1,
                            getattr(e, 'status_code', None),
                            delay,
                        )
                        sleep(delay)
                    else:
                        raise
                except Exception as e:  # noqa: BLE001 - allow retry for overloaded transient provider errors.
                    if _is_transient_error(e):
                        last_exception = e
                        delay = base_delay * (2**attempt)
                        logger.warning(
                            'Transient provider error, retrying attempt=%s error_type=%s delay=%.2f',
                            attempt + 1,
                            type(e).__name__,
                            delay,
                        )
                        sleep(delay)
                    else:
                        raise
            if last_exception is not None:
                raise last_exception
            raise RuntimeError('Retry attempts exhausted without capturing an exception')

        return wrapper

    return decorator


def _is_transient_error(exc: Exception) -> bool:
    status_code = getattr(exc, 'status_code', None)
    if isinstance(status_code, int) and (status_code >= 500 or status_code in {429, 529}):
        return True

    error_text = str(exc).lower()
    return any(
        marker in error_text
        for marker in (
            'overloaded',
            'overloaded_error',
            'error code: 529',
            'rate limit',
            'temporarily unavailable',
            'timeout',
        )
    )


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

        self._client = Anthropic(
            api_key=self._api_key,
            max_retries=3,
            timeout=180.0,  # 3 minutes for long VPR generation requests with large context
        )

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
        """Calculate cost based on provider-reported tokens."""
        return calculate_cost(model_id, input_tokens, output_tokens)

    @_capture_method_typed(capture_response=False)
    @retry_on_transient_error(max_retries=3)
    def invoke(
        self,
        mode: TaskMode,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        use_system_cache: bool = False,
    ) -> Result[dict[str, Any]]:
        """
        Invoke the LLM with automatic model routing.

        Args:
            mode: TaskMode.STRATEGIC for Sonnet, TaskMode.TEMPLATE for Haiku
            system_prompt: System context and instructions
            user_prompt: User message/input
            max_tokens: Maximum output tokens
            temperature: Creativity parameter (lower = more consistent)
            use_system_cache: When True, wraps system_prompt with Anthropic prompt
                caching (cache_control ephemeral). Reduces cost on repeated calls.

        Returns:
            Result with response text, token usage, and cost
        """
        model_id = self._resolve_model(mode)

        logger.info('Invoking LLM', mode=mode.value, model=model_id, max_tokens=max_tokens)

        system: str | list[TextBlockParam] = system_prompt
        if use_system_cache:
            system = [TextBlockParam(type='text', text=system_prompt, cache_control={'type': 'ephemeral'})]

        try:
            response = self._client.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{'role': 'user', 'content': user_prompt}],
            )

            usage = getattr(response, 'usage', None)
            input_tokens = int(getattr(usage, 'input_tokens', 0) or 0)
            output_tokens = int(getattr(usage, 'output_tokens', 0) or 0)
            cache_read_input_tokens = int(getattr(usage, 'cache_read_input_tokens', 0) or 0)
            cache_creation_input_tokens = int(getattr(usage, 'cache_creation_input_tokens', 0) or 0)
            prompt_cache_hit = cache_read_input_tokens > 0
            cost = self._calculate_cost(model_id, input_tokens, output_tokens)

            self._log_metrics(
                mode=mode,
                model_id=model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                prompt_cache_hit=prompt_cache_hit,
                prompt_cache_lookup=use_system_cache,
                cache_read_input_tokens=cache_read_input_tokens,
                cache_creation_input_tokens=cache_creation_input_tokens,
            )

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
                    'prompt_cache_hit': prompt_cache_hit,
                    'cache_read_input_tokens': cache_read_input_tokens,
                    'cache_creation_input_tokens': cache_creation_input_tokens,
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

    def _log_metrics(
        self,
        *,
        mode: TaskMode,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        prompt_cache_hit: bool,
        prompt_cache_lookup: bool,
        cache_read_input_tokens: int,
        cache_creation_input_tokens: int,
    ) -> None:
        """Emit shared Q-10 usage metrics."""
        record_llm_usage(
            model_id=model_id,
            task_mode=mode.value,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            prompt_cache_hit=prompt_cache_hit,
            prompt_cache_lookup=prompt_cache_lookup,
            cache_read_input_tokens=cache_read_input_tokens,
            cache_creation_input_tokens=cache_creation_input_tokens,
        )


# Singleton instance for Lambda warm starts
_llm_router: LLMRouter | None = None


def get_llm_router() -> LLMRouter:
    """Get or create singleton LLM router instance."""
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router

# CareerVP Circuit Breaker & Fallback Strategy

**Document Version:** 1.0
**Date:** 2026-02-10
**Purpose:** Document Circuit Breaker patterns and equivalent LLM services for fallback

---

## Table of Contents

1. [Circuit Breaker Pattern Overview](#1-circuit-breaker-pattern-overview)
2. [LLM Provider Alternatives](#2-llm-provider-alternatives)
3. [Fallback Strategy Implementation](#3-fallback-strategy-implementation)
4. [Cost Comparison](#4-cost-comparison)
5. [Implementation Code](#5-implementation-code)
6. [Configuration Matrix](#6-configuration-matrix)

---

## 1. Circuit Breaker Pattern Overview

### 1.1 What is Circuit Breaker?

The Circuit Breaker pattern prevents cascading failures when a dependent service (like an LLM API) is experiencing issues. It has three states:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CIRCUIT BREAKER STATES                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│     ┌──────────────┐              ┌──────────────┐                    │
│     │    OPEN      │              │   HALF-OPEN  │                    │
│     │   (Block)    │              │  (Testing)   │                    │
│     │              │              │              │                    │
│     │  Requests    │────Fail─────▶│  Limited     │────Success───────▶│
│     │  REJECTED    │              │  Requests    │                   │
│     │              │              │  Allowed     │                   │
│     └──────┬───────┘              └──────┬───────┘                   │
│            │                             │                            │
│            │ Timeout                     │ Timeout                    │
│            │ (30s-60s)                   │ (10s)                      │
│            ▼                             ▼                            │
│     ┌──────────────┐              ┌──────────────┐                    │
│     │              │              │              │                    │
│     │  After N     │              │  After N     │────Fail───────────▶│
│     │  Failures    │              │  Successes   │                   │
│     │              │              │              │                   │
│     │              │              │              │                   │
│     └──────────────┘              └──────────────┘                    │
│                                                                         │
│     ┌──────────────────────────────────────────────────────────────┐  │
│     │                     CLOSED (Normal)                          │  │
│     │                                                               │  │
│     │  Requests flow through normally                               │  │
│     │  Failure count increments on errors                           │  │
│     │  Opens when failure threshold reached                         │  │
│     └──────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Why Circuit Breaker for LLMs?

| Scenario | Without CB | With CB |
|----------|-----------|---------|
| **Rate Limit** | Retry loop → Cost spike | Immediate fallback |
| **Latency Spike** | Timeout after 30s | Fast-fail to fallback |
| **API Outage** | All requests fail | Fallback provider |
| **Token Limit** | 500 error | Graceful degradation |

### 1.3 Circuit Breaker Configuration

```python
CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 5,          # Open after 5 failures
    "success_threshold": 3,          # Close after 3 successes
    "timeout_seconds": 60,           # Wait 60s before trying again
    "half_open_requests": 3,         # Allow 3 requests in half-open
    "volume_threshold": 10,          # Minimum requests before evaluating
}
```

---

## 2. LLM Provider Alternatives

### 2.1 Claude 4.5 Equivalents

| Provider | Model | Strength | Weakness | Best For |
|----------|-------|----------|----------|----------|
| **Anthropic** | Claude 4.5 Sonnet | Current default | N/A | CareerVP primary |
| **OpenAI** | GPT-4o | Reasoning, structured output | Expensive | Complex VPR analysis |
| **OpenAI** | GPT-4.1 | Longer context | More expensive | Gap analysis with long context |
| **Google** | Gemini 1.5 Pro | 2M context window | Lower reasoning | Document analysis |
| **AI21** | Jamba Large | 256K context | Less mature | Long CV processing |

### 2.2 Claude 4.5 Haiku Equivalents

| Provider | Model | Strength | Weakness | Best For |
|----------|-------|----------|----------|----------|
| **Anthropic** | Claude 4.5 Haiku | Fast, cheap | Shorter context | CV tailoring, cover letters |
| **OpenAI** | GPT-3.5-turbo | Very cheap | Weak reasoning | Simple validations |
| **OpenAI** | GPT-5 nano | Fast, structured | Limited reasoning | Formatted output |
| **OpenAI** | GPT-5 mini | Balanced | Medium cost | Fallback for all tasks |
| **Google** | Gemini 2.5 Flash | Fast, multimodal | Lower quality | Quick generations |
| **Google** | Gemini 2.5 Flash-Lite | Cheapest | Basic quality | PII detection, basic tasks |
| **AI21** | Jamba Mini | Efficient | Less capable | Simple transformations |

### 2.3 Detailed Model Comparison

#### Strategic Tasks (VPR, Gap Analysis - Need Reasoning)

| Model | Input | Output | Context | Price/M | Use Case |
|-------|-------|--------|---------|---------|----------|
| Claude 4.5 Sonnet | $3.00 | $15.00 | 200K | CareerVP default | VPR, Gap Analysis |
| GPT-4o | $2.50 | $10.00 | 128K | Slightly cheaper | VPR fallback |
| GPT-4.1 | $2.00 | $8.00 | 1M | Long context | Complex Gap Analysis |
| Gemini 1.5 Pro | $1.25 | $5.00 | 2M | Cheapest for volume | Document processing |
| Jamba Large | ~$1.00 | ~$4.00 | 256K | Good value | Long CV analysis |

#### Template Tasks (CV Tailoring, Cover Letter - Speed Priority)

| Model | Input | Output | Speed | Price/M | Use Case |
|-------|-------|--------|-------|---------|----------|
| Claude 4.5 Haiku | $0.25 | $1.25 | Fast | Default template | CV tailoring |
| GPT-3.5-turbo | $0.50 | $1.50 | Very fast | Cheap | Simple cover letters |
| GPT-5 nano | $0.05 | $0.40 | Ultra fast | Cheapest | Formatted output |
| Gemini 2.5 Flash | $0.075 | $0.30 | Very fast | Budget option | Template filling |
| Jamba Mini | ~$0.10 | ~$0.40 | Fast | Good value | Basic transformations |

---

## 3. Fallback Strategy Implementation

### 3.1 Fallback Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FALLBACK STRATEGY HIERARCHY                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TIER 1: Same Provider, Different Model                                 │
│  ────────────────────────────────────────                              │
│  Claude Sonnet → Claude Haiku (50% cheaper, faster)                    │
│                                                                         │
│  TIER 2: Different Provider, Same Capability                           │
│  ─────────────────────────────────────────────────                      │
│  Claude Sonnet → GPT-4o (similar reasoning)                            │
│  Claude Haiku → GPT-5 nano (fast, cheap)                                │
│                                                                         │
│  TIER 3: Different Provider, Budget Option                             │
│  ─────────────────────────────────────                                  │
│  Claude any → Gemini 2.5 Flash (cheapest viable)                       │
│                                                                         │
│  TIER 4: Graceful Degradation                                           │
│  ──────────────────────────────                                        │
│  Any LLM → Cached response (if available)                              │
│  Any LLM → Simplified prompt (fewer tokens)                             │
│  Any LLM → Static template (no LLM)                                      │
│                                                                         │
│  TIER 5: Ultimate Fallback                                             │
│  ─────────────────────────                                             │
│  All LLMs failed → Return "Service temporarily unavailable"            │
│  └─ User sees friendly message, request queued for retry               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Feature-Specific Fallbacks

| Feature | Primary | Fallback 1 | Fallback 2 | Fallback 3 |
|---------|---------|------------|------------|------------|
| **VPR Generation** | Claude Sonnet | GPT-4o | Gemini 1.5 Pro | Cached VPR |
| **Gap Analysis** | Claude Sonnet | GPT-4.1 | Gemini 1.5 Pro | 5-question limit |
| **CV Tailoring** | Claude Haiku | GPT-5 nano | Gemini 2.5 Flash | Static template |
| **Cover Letter** | Claude Haiku | GPT-3.5-turbo | Gemini 2.5 Flash | Template only |
| **Interview Prep** | Claude Sonnet | GPT-4o | Gemini 2.5 Flash | Cached responses |
| **Company Research** | Claude Haiku | GPT-5 nano | Gemini 2.5 Flash-Lite | Search only |
| **PII Detection** | Claude Haiku | GPT-5 nano | Regex rules | Static patterns |
| **FVS Validation** | Claude Sonnet | GPT-4o | Heuristic rules | Allow all, flag |

---

## 4. Cost Comparison

### 4.1 Per-Request Cost Estimation

Assuming average prompt: 2000 input tokens, 1000 output tokens

| Feature | Primary | Cost | Fallback | Cost | Savings |
|---------|---------|------|----------|------|---------|
| **VPR** | Claude Sonnet | $21.00 | GPT-4o | $14.00 | 33% |
| **Gap** | Claude Sonnet | $21.00 | GPT-4o | $14.00 | 33% |
| **CV Tailoring** | Claude Haiku | $1.75 | GPT-5 nano | $0.50 | 71% |
| **Cover Letter** | Claude Haiku | $1.75 | GPT-5 nano | $0.50 | 71% |
| **Interview Prep** | Claude Sonnet | $21.00 | GPT-4o | $14.00 | 33% |

### 4.2 Monthly Cost Projection

| Scenario | Requests/Month | Avg Cost/Req | Monthly Cost |
|----------|----------------|--------------|--------------|
| **All Claude** | 10,000 | $5.00 | $50,000 |
| **50% Fallback** | 10,000 | $3.50 | $35,000 |
| **Aggressive Fallback** | 10,000 | $2.00 | $20,000 |
| **Budget Mode** | 10,000 | $0.50 | $5,000 |

---

## 5. Implementation Code

### 5.1 Circuit Breaker Implementation

```python
# src/backend/careervp/infrastructure/circuit_breaker.py

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Callable, TypeVar
from functools import wraps
import asyncio
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 3           # Successes before closing
    timeout_seconds: int = 60            # Time in open state
    half_open_limit: int = 3             # Requests allowed in half-open
    volume_threshold: int = 10          # Min requests before evaluating


class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls.

    Prevents cascading failures by stopping requests to failing services
    and allowing gradual recovery.
    """

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_requests = 0
        self._callbacks: list[Callable] = []

    def register_callback(self, callback: Callable):
        """Register callback when circuit state changes."""
        self._callbacks.append(callback)

    def _notify_state_change(self, old_state: CircuitState, new_state: CircuitState):
        """Notify all registered callbacks of state change."""
        for callback in self._callbacks:
            try:
                callback(self.name, old_state, new_state)
            except Exception as e:
                logger.error(f"Circuit breaker callback failed: {e}")

    def record_success(self):
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self._success_count += 1
            self._half_open_requests += 1
            if self._success_count >= self.config.success_threshold:
                old_state = self.state
                self.state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                self._half_open_requests = 0
                self._notify_state_change(old_state, CircuitState.CLOSED)
                logger.info(f"Circuit {self.name}: Recovered, closed")

        elif self.state == CircuitState.CLOSED:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self):
        """Record a failed call."""
        if self.state == CircuitState.HALF_OPEN:
            old_state = self.state
            self.state = CircuitState.OPEN
            self._last_failure_time = datetime.utcnow()
            self._notify_state_change(old_state, CircuitState.OPEN)
            logger.warning(f"Circuit {self.name}: Opened due to failure in half-open")
            return

        self._failure_count += 1
        if self._failure_count >= self.config.failure_threshold:
            old_state = self.state
            self.state = CircuitState.OPEN
            self._last_failure_time = datetime.utcnow()
            self._notify_state_change(old_state, CircuitState.OPEN)
            logger.warning(f"Circuit {self.name}: Opened after {self._failure_count} failures")

    def allow_request(self) -> bool:
        """Check if a request should be allowed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self._last_failure_time:
                elapsed = datetime.utcnow() - self._last_failure_time
                if elapsed.total_seconds() >= self.config.timeout_seconds:
                    old_state = self.state
                    self.state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    self._half_open_requests = 0
                    self._notify_state_change(old_state, CircuitState.HALF_OPEN)
                    logger.info(f"Circuit {self.name}: Half-open, testing recovery")
                    return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            if self._half_open_requests < self.config.half_open_limit:
                self._half_open_requests += 1
                return True
            return False

        return False

    def get_state(self) -> dict:
        """Get current state for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure": self._last_failure_time.isoformat() if self._last_failure_time else None,
        }


class LLMCircuitBreaker:
    """
    Specialized circuit breaker for LLM API calls.

    Includes LLM-specific failure detection:
    - Rate limit errors (429)
    - Token limit errors (400)
    - API errors (500s)
    - Timeout detection
    """

    # Map LLM errors to circuit breaker actions
    TRANSIENT_ERRORS = {
        "rate_limit",           # 429 - Retry after delay
        "timeout",              # Request timeout
        "service_unavailable",  # 503 - Service temporarily unavailable
        "internal_error",       # 500 - Server error
    }

    PERMANENT_ERRORS = {
        "invalid_request",     # 400 - Bad request, won't fix by retry
        "authentication_error", # 401 - Auth issue
        "permission_denied",    # 403 - Permission issue
    }

    def __init__(self, model_name: str, config: CircuitBreakerConfig = None):
        self.model_name = model_name
        self.breaker = CircuitBreaker(f"llm:{model_name}", config)
        self._error_counts: dict[str, int] = {}

    def classify_error(self, error: Exception) -> str:
        """Classify LLM error type."""
        error_str = str(error).lower()

        if "429" in error_str or "rate limit" in error_str:
            return "rate_limit"
        if "400" in error_str or "bad request" in error_str:
            return "invalid_request"
        if "401" in error_str or "authentication" in error_str:
            return "authentication_error"
        if "403" in error_str or "permission" in error_str:
            return "permission_denied"
        if "500" in error_str or "internal" in error_str:
            return "internal_error"
        if "timeout" in error_str:
            return "timeout"

        return "unknown"

    def record_error(self, error: Exception):
        """Record an error and update circuit state."""
        error_type = self.classify_error(error)
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1

        if error_type in self.TRANSIENT_ERRORS:
            self.breaker.record_failure()
        elif error_type in self.PERMANENT_ERRORS:
            # Don't open circuit for permanent errors
            # These won't be fixed by retry
            logger.warning(f"Permanent error for {self.model_name}: {error_type}")

    def get_stats(self) -> dict:
        """Get error statistics."""
        return {
            "model": self.model_name,
            "circuit_state": self.breaker.get_state(),
            "error_counts": self._error_counts,
        }
```

### 5.2 Fallback Router Implementation

```python
# src/backend/careervp/infrastructure/llm_router.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, AsyncGenerator
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels for LLM routing."""
    STRATEGIC = 1   # VPR, Gap Analysis - Need reasoning
    TEMPLATE = 2     # CV Tailoring, Cover Letter - Speed priority
    VALIDATION = 3   # PII, FVS - Can use cheapest


@dataclass
class LLMProvider:
    """LLM provider configuration."""
    name: str
    model: str
    api_endpoint: str
    priority: int
    max_tokens: int
    cost_per_1m_input: float
    cost_per_1m_output: float
    circuit_breaker: LLMCircuitBreaker


@dataclass
class RoutingConfig:
    """Configuration for LLM routing."""
    providers: list[LLMProvider]
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout_seconds: float = 60.0


class LLMRouter:
    """
    Intelligent LLM router with circuit breaker and fallback.

    Routes requests to appropriate providers based on:
    - Task type (strategic vs template)
    - Current circuit breaker state
    - Cost optimization
    """

    def __init__(self, config: RoutingConfig):
        self.config = config
        self._provider_map: dict[str, LLMProvider] = {}
        self._provider_lookup: dict[TaskPriority, list[LLMProvider]] = {}

        for provider in config.providers:
            self._provider_map[provider.model] = provider
            if provider.priority not in self._provider_lookup:
                self._provider_lookup[provider.priority] = []
            self._provider_lookup[provider.priority].append(provider)

    async def generate(
        self,
        prompt: str,
        task_priority: TaskPriority,
        max_tokens: int = 2000,
    ) -> str:
        """
        Generate text using best available provider.

        Args:
            prompt: Input prompt
            task_priority: Priority level for routing
            max_tokens: Maximum output tokens

        Returns:
            Generated text from best provider

        Raises:
            AllProvidersFailed: If all providers fail
        """
        providers = self._get_ordered_providers(task_priority, max_tokens)

        last_error = None
        for attempt in range(self.config.max_retries):
            for provider in providers:
                if not provider.circuit_breaker.breaker.allow_request():
                    logger.debug(f"Circuit open for {provider.model}, skipping")
                    continue

                try:
                    result = await self._call_provider(provider, prompt, max_tokens)
                    provider.circuit_breaker.breaker.record_success()
                    logger.info(f"Success with {provider.model}")
                    return result

                except Exception as e:
                    provider.circuit_breaker.record_error(e)
                    last_error = e
                    logger.warning(f"Provider {provider.model} failed: {e}")
                    continue

            # All providers failed this attempt, wait before retry
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))

        raise AllProvidersFailed(f"All providers failed after {self.config.max_retries} attempts") from last_error

    def _get_ordered_providers(
        self,
        priority: TaskPriority,
        max_tokens: int,
    ) -> list[LLMProvider]:
        """Get providers ordered by preference for this task."""
        providers = self._provider_lookup.get(priority, [])

        # Filter by token limit and circuit state
        available = [
            p for p in providers
            if p.max_tokens >= max_tokens
            and p.circuit_breaker.breaker.state != CircuitState.OPEN
        ]

        # Sort by cost (cheapest first for template, best quality first for strategic)
        if priority == TaskPriority.TEMPLATE:
            available.sort(key=lambda p: p.cost_per_1m_input)
        else:
            # Strategic tasks prefer reasoning models
            available.sort(key=lambda p: p.cost_per_1m_input, reverse=True)

        return available

    async def _call_provider(
        self,
        provider: LLMProvider,
        prompt: str,
        max_tokens: int,
    ) -> str:
        """Call actual LLM provider."""
        # Import here to avoid circular dependencies
        from careervp.infrastructure.llm_clients import get_client

        client = get_client(provider.name)
        return await client.generate(
            model=provider.model,
            prompt=prompt,
            max_tokens=max_tokens,
            timeout=self.config.timeout_seconds,
        )


class AllProvidersFailed(Exception):
    """Raised when all providers fail."""
    pass
```

### 5.3 LLM Client Interface

```python
# src/backend/careervp/infrastructure/llm_clients.py

from abc import ABC, abstractmethod
from typing import Protocol


class LLMClientProtocol(Protocol):
    """Protocol for LLM clients."""

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float = 0.7,
        timeout: float = 60.0,
    ) -> str:
        """Generate text from model."""
        ...


class AnthropicClient:
    """Client for Anthropic Claude API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com"

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float = 0.7,
        timeout: float = 60.0,
    ) -> str:
        import httpx

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                }
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]


class OpenAIClient:
    """Client for OpenAI API."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float = 0.7,
        timeout: float = 60.0,
    ) -> str:
        import httpx

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "authorization": f"Bearer {self.api_key}",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_completion_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                }
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]


class GoogleClient:
    """Client for Google Gemini API."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float = 0.7,
        timeout: float = 60.0,
    ) -> str:
        import httpx

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": max_tokens,
                        "temperature": temperature,
                    }
                }
            )
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]


# Factory function
def get_client(provider: str) -> LLMClientProtocol:
    """Get LLM client for provider."""
    import os

    clients = {
        "anthropic": AnthropicClient(api_key=os.getenv("ANTHROPIC_API_KEY")),
        "openai": OpenAIClient(api_key=os.getenv("OPENAI_API_KEY")),
        "google": GoogleClient(api_key=os.getenv("GOOGLE_API_KEY")),
    }

    return clients[provider]
```

### 5.4 Usage Example

```python
# src/backend/careervp/handlers/vpr_handler.py

from careervp.infrastructure.llm_router import LLMRouter, TaskPriority
from careervp.infrastructure.circuit_breaker import CircuitBreakerConfig


# Configure providers
ROUTING_CONFIG = RoutingConfig(
    providers=[
        # Strategic: Claude Sonnet as primary
        LLMProvider(
            name="anthropic",
            model="claude-sonnet-4-20250514",
            api_endpoint="anthropic.com",
            priority=TaskPriority.STRATEGIC.value,
            max_tokens=4096,
            cost_per_1m_input=3.00,
            cost_per_1m_output=15.00,
            circuit_breaker=LLMCircuitBreaker("claude-sonnet-4"),
        ),
        # Fallback: GPT-4o
        LLMProvider(
            name="openai",
            model="gpt-4o-2024-08-06",
            api_endpoint="openai.com",
            priority=TaskPriority.STRATEGIC.value,
            max_tokens=4096,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
            circuit_breaker=LLMCircuitBreaker("gpt-4o"),
        ),
        # Template: Claude Haiku as primary
        LLMProvider(
            name="anthropic",
            model="claude-haiku-4-20250514",
            api_endpoint="anthropic.com",
            priority=TaskPriority.TEMPLATE.value,
            max_tokens=4096,
            cost_per_1m_input=0.25,
            cost_per_1m_output=1.25,
            circuit_breaker=LLMCircuitBreaker("claude-haiku-4"),
        ),
        # Fallback: GPT-5 nano
        LLMProvider(
            name="openai",
            model="gpt-5-nano-2025-08-07",
            api_endpoint="openai.com",
            priority=TaskPriority.TEMPLATE.value,
            max_tokens=4096,
            cost_per_1m_input=0.05,
            cost_per_1m_output=0.40,
            circuit_breaker=LLMCircuitBreaker("gpt-5-nano"),
        ),
    ]
)

router = LLMRouter(ROUTING_CONFIG)


class VPRHandler:
    """VPR Generator Handler with circuit breaker and fallback."""

    def __init__(self, router: LLMRouter):
        self.router = router

    async def generate_vpr(self, cv: CV, job: JobDescription) -> VPRResponse:
        """Generate VPR with automatic fallback."""
        prompt = self._build_vpr_prompt(cv, job)

        result = await self.router.generate(
            prompt=prompt,
            task_priority=TaskPriority.STRATEGIC,
            max_tokens=3000,
        )

        return VPRResponse.parse_raw(result)
```

---

## 6. Configuration Matrix

### 6.1 Feature to Provider Mapping

```python
FEATURE_CONFIG = {
    "vpr_generator": {
        "priority": TaskPriority.STRATEGIC,
        "primary": "anthropic/claude-sonnet-4",
        "fallbacks": [
            ("openai/gpt-4o", "Strategic fallback - similar reasoning"),
            ("google/gemini-1.5-pro", "Long context option"),
        ],
        "timeout": 60.0,
        "max_tokens": 4096,
    },
    "gap_analysis": {
        "priority": TaskPriority.STRATEGIC,
        "primary": "anthropic/claude-sonnet-4",
        "fallbacks": [
            ("openai/gpt-4.1", "Long context for complex analysis"),
            ("google/gemini-1.5-pro", "Document processing"),
        ],
        "timeout": 90.0,
        "max_tokens": 8192,
    },
    "cv_tailoring": {
        "priority": TaskPriority.TEMPLATE,
        "primary": "anthropic/claude-haiku-4",
        "fallbacks": [
            ("openai/gpt-5-nano", "Fast, cheap fallback"),
            ("google/gemini-2.5-flash", "Budget option"),
        ],
        "timeout": 30.0,
        "max_tokens": 2048,
    },
    "cover_letter": {
        "priority": TaskPriority.TEMPLATE,
        "primary": "anthropic/claude-haiku-4",
        "fallbacks": [
            ("openai/gpt-3.5-turbo", "Proven template model"),
            ("google/gemini-2.5-flash", "Fast generation"),
        ],
        "timeout": 30.0,
        "max_tokens": 2048,
    },
    "interview_prep": {
        "priority": TaskPriority.STRATEGIC,
        "primary": "anthropic/claude-sonnet-4",
        "fallbacks": [
            ("openai/gpt-4o", "Similar reasoning capability"),
            ("google/gemini-2.5-flash-thinking", "Reasoning focus"),
        ],
        "timeout": 60.0,
        "max_tokens": 4096,
    },
    "company_research": {
        "priority": TaskPriority.TEMPLATE,
        "primary": "anthropic/claude-haiku-4",
        "fallbacks": [
            ("openai/gpt-5-nano", "Quick research extraction"),
            ("google/gemini-2.5-flash-lite", "Lightweight option"),
        ],
        "timeout": 20.0,
        "max_tokens": 1024,
    },
    "pii_detection": {
        "priority": TaskPriority.VALIDATION,
        "primary": "anthropic/claude-haiku-4",
        "fallbacks": [
            ("openai/gpt-5-nano", "Pattern matching"),
            ("google/gemini-2.5-flash-lite", "Basic detection"),
        ],
        "timeout": 15.0,
        "max_tokens": 512,
    },
    "fvs_validation": {
        "priority": TaskPriority.STRATEGIC,
        "primary": "anthropic/claude-sonnet-4",
        "fallbacks": [
            ("openai/gpt-4o", "Fact verification"),
            # No fallback for FVS - quality is critical
        ],
        "timeout": 45.0,
        "max_tokens": 2048,
    },
}
```

### 6.2 Circuit Breaker Thresholds by Provider

```python
CIRCUIT_BREAKER_CONFIGS = {
    "anthropic/claude-sonnet-4": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        timeout_seconds=60,
        half_open_limit=3,
    ),
    "anthropic/claude-haiku-4": CircuitBreakerConfig(
        failure_threshold=3,  # Haiku more prone to rate limits
        success_threshold=2,
        timeout_seconds=30,
        half_open_limit=5,
    ),
    "openai/gpt-4o": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        timeout_seconds=60,
        half_open_limit=3,
    ),
    "openai/gpt-5-nano": CircuitBreakerConfig(
        failure_threshold=10,  # High rate limits, allow more failures
        success_threshold=2,
        timeout_seconds=30,
        half_open_limit=10,
    ),
    "google/gemini-1.5-pro": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        timeout_seconds=90,  # Longer timeouts for Gemini
        half_open_limit=2,
    ),
    "google/gemini-2.5-flash": CircuitBreakerConfig(
        failure_threshold=8,
        success_threshold=2,
        timeout_seconds=20,  # Flash is fast, quick recovery
        half_open_limit=5,
    ),
}
```

---

## 7. Monitoring & Alerting

### 7.1 Metrics to Track

| Metric | Threshold | Alert |
|--------|-----------|-------|
| Circuit Open Rate | > 5% | Warning |
| Fallback Activation | > 20% | Warning |
| Latency P95 | > 30s | Warning |
| Error Rate | > 1% | Critical |
| Cost/Day | > $2000 | Warning |

### 7.2 Health Check Endpoint

```python
# /health/llm-services

{
    "status": "healthy",
    "providers": {
        "anthropic/claude-sonnet-4": {"state": "closed", "failures": 0},
        "anthropic/claude-haiku-4": {"state": "closed", "failures": 2},
        "openai/gpt-4o": {"state": "closed", "fallback_count": 5},
        "google/gemini-2.5-flash": {"state": "half_open", "fallback_count": 10},
    },
    "routing": {
        "total_requests": 10000,
        "fallback_rate": 0.05,
        "avg_latency_ms": 2500,
    }
}
```

---

**Document Version:** 1.0
**Last Updated:** 2026-02-10

---

**END OF CIRCUIT BREAKER & FALLBACK DOCUMENT**

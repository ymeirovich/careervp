"""Minimal circuit breaker primitives used by Phase 0 checks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import monotonic


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = 'CLOSED'
    OPEN = 'OPEN'
    HALF_OPEN = 'HALF_OPEN'


@dataclass
class CircuitBreaker:
    """Simple circuit breaker with failure and recovery thresholds."""

    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    half_open_success_threshold: int = 1
    name: str = 'default'

    def __post_init__(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_success_count = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def can_proceed(self) -> bool:
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.HALF_OPEN:
            return True
        if self._opened_at is None:
            return False
        if monotonic() - self._opened_at >= self.recovery_timeout_seconds:
            self._state = CircuitState.HALF_OPEN
            self._half_open_success_count = 0
            return True
        return False

    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_success_count += 1
            if self._half_open_success_count >= self.half_open_success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._half_open_success_count = 0
                self._opened_at = None
            return

        if self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        self._failure_count += 1
        self._half_open_success_count = 0
        if self._state == CircuitState.HALF_OPEN or self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = monotonic()

    def get_state(self) -> dict[str, str | int | float | None]:
        return {
            'name': self.name,
            'state': self._state.value,
            'failure_count': self._failure_count,
            'failure_threshold': self.failure_threshold,
            'recovery_timeout_seconds': self.recovery_timeout_seconds,
            'half_open_success_threshold': self.half_open_success_threshold,
            'opened_at': self._opened_at,
        }

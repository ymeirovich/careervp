"""Minimal circuit breaker primitives used by Phase 0 checks."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from time import monotonic
from typing import Deque, Literal


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = 'CLOSED'
    OPEN = 'OPEN'
    HALF_OPEN = 'HALF_OPEN'


class CircuitBreakerBlockedError(RuntimeError):
    """Raised when an OPEN circuit blocks execution."""

    def __init__(self, retry_after: float) -> None:
        self.retry_after = max(0.0, retry_after)
        super().__init__(f'Circuit breaker is open. Retry after {self.retry_after:.2f} seconds.')


@dataclass
class CircuitBreaker:
    """Simple circuit breaker with failure and recovery thresholds."""

    failure_threshold: int = 5
    failure_window_seconds: float | None = None
    recovery_timeout_seconds: float = 30.0
    half_open_success_threshold: int = 1
    expected_exception: type[BaseException] | tuple[type[BaseException], ...] = Exception
    name: str = 'default'

    def __post_init__(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_success_count = 0
        self._opened_at: float | None = None
        self._failure_timestamps: Deque[float] = deque()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def __enter__(self) -> CircuitBreaker:
        if not self.can_proceed():
            raise CircuitBreakerBlockedError(self.retry_after_seconds())
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, _tb: object) -> Literal[False]:
        if exc is None:
            self.record_success()
            return False
        if isinstance(exc, self.expected_exception):
            self.record_failure()
        return False

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

    def retry_after_seconds(self) -> float:
        if self._state != CircuitState.OPEN or self._opened_at is None:
            return 0.0
        elapsed = monotonic() - self._opened_at
        return max(0.0, self.recovery_timeout_seconds - elapsed)

    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_success_count += 1
            if self._half_open_success_count >= self.half_open_success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._half_open_success_count = 0
                self._opened_at = None
                self._failure_timestamps.clear()
            return

        if self._state == CircuitState.CLOSED:
            self._failure_count = 0
            self._failure_timestamps.clear()

    def record_failure(self) -> None:
        now = monotonic()
        if self.failure_window_seconds is None:
            self._failure_count += 1
        else:
            self._failure_timestamps.append(now)
            window_start = now - self.failure_window_seconds
            while self._failure_timestamps and self._failure_timestamps[0] < window_start:
                self._failure_timestamps.popleft()
            self._failure_count = len(self._failure_timestamps)

        self._half_open_success_count = 0
        if self._state == CircuitState.HALF_OPEN or self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = now

    def get_state(self) -> dict[str, str | int | float | None]:
        return {
            'name': self.name,
            'state': self._state.value,
            'failure_count': self._failure_count,
            'failure_threshold': self.failure_threshold,
            'failure_window_seconds': self.failure_window_seconds,
            'recovery_timeout_seconds': self.recovery_timeout_seconds,
            'half_open_success_threshold': self.half_open_success_threshold,
            'opened_at': self._opened_at,
            'retry_after_seconds': self.retry_after_seconds(),
        }

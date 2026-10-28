"""A thread-safe circuit breaker.

The breaker tracks failures of a protected operation and short-circuits calls
once failures pass a threshold, giving a struggling dependency time to recover
instead of hammering it. It follows the usual three-state model:

* ``CLOSED``    -- calls flow through; consecutive failures are counted.
* ``OPEN``      -- calls are rejected immediately until the recovery timeout
                   elapses.
* ``HALF_OPEN`` -- a limited number of trial calls are allowed; a success
                   closes the breaker, a failure opens it again.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from src.utils.resilience.errors import CircuitOpenError


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True)
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 1

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout < 0:
            raise ValueError("recovery_timeout must be non-negative")
        if self.half_open_max_calls < 1:
            raise ValueError("half_open_max_calls must be >= 1")


class CircuitBreaker:
    """Guards a dependency and fails fast while it is unhealthy.

    A monotonic ``clock`` is injectable so the recovery window can be tested
    deterministically without real sleeping.
    """

    def __init__(
        self,
        name: str = "default",
        config: Optional[CircuitBreakerConfig] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.name = name
        self._config = config or CircuitBreakerConfig()
        self._clock = clock
        self._lock = threading.RLock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: Optional[float] = None
        self._half_open_calls = 0

    @property
    def config(self) -> CircuitBreakerConfig:
        return self._config

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._refresh()
            return self._state

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failure_count

    def _refresh(self) -> None:
        """Promote OPEN -> HALF_OPEN once the recovery timeout has elapsed."""
        if self._state is CircuitState.OPEN and self._opened_at is not None:
            if self._clock() - self._opened_at >= self._config.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0

    def _retry_after(self) -> Optional[float]:
        if self._state is not CircuitState.OPEN or self._opened_at is None:
            return None
        remaining = self._config.recovery_timeout - (self._clock() - self._opened_at)
        return max(0.0, remaining)

    def acquire(self) -> None:
        """Check out permission to make a call.

        Raises :class:`CircuitOpenError` if the call should not proceed. When
        the breaker is half-open this reserves one of the limited trial slots,
        so every successful ``acquire`` must be paired with a later
        :meth:`record_success` or :meth:`record_failure`.
        """
        with self._lock:
            self._refresh()
            if self._state is CircuitState.OPEN:
                raise CircuitOpenError(self.name, self._retry_after())
            if self._state is CircuitState.HALF_OPEN:
                if self._half_open_calls >= self._config.half_open_max_calls:
                    raise CircuitOpenError(self.name, self._retry_after())
                self._half_open_calls += 1

    def record_success(self) -> None:
        with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                self._close()
            else:
                self._failure_count = 0

    def record_failure(self) -> None:
        with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                # A probe failed; the dependency is still unhealthy.
                self._open()
                return
            self._failure_count += 1
            if self._failure_count >= self._config.failure_threshold:
                self._open()

    def reset(self) -> None:
        """Force the breaker back to the healthy CLOSED state."""
        with self._lock:
            self._close()

    def _open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()
        self._half_open_calls = 0

    def _close(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = None
        self._half_open_calls = 0

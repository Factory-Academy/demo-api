import threading
import time
from enum import Enum
from typing import Callable, Optional


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """A thread-safe circuit breaker.

    States:
      * ``CLOSED``   - calls flow through; consecutive failures are counted.
      * ``OPEN``     - calls are rejected until ``recovery_timeout`` elapses.
      * ``HALF_OPEN``- a limited number of probe calls are allowed to test
                       whether the dependency has recovered.

    The breaker only tracks *consecutive* failures. A single success while
    closed resets the counter, matching the common "trip on a burst" behaviour.
    ``time_func`` is injectable so tests can advance time without sleeping.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
        success_threshold: int = 1,
        time_func: Callable[[], float] = time.monotonic,
    ):
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if recovery_timeout < 0:
            raise ValueError("recovery_timeout must be non-negative")
        if half_open_max_calls < 1:
            raise ValueError("half_open_max_calls must be at least 1")
        if success_threshold < 1:
            raise ValueError("success_threshold must be at least 1")

        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.success_threshold = success_threshold
        self._time = time_func

        self._lock = threading.RLock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._opened_at: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._maybe_transition_to_half_open()
            return self._state

    def allow(self) -> bool:
        """Return ``True`` if a call may proceed, updating state as needed.

        A ``True`` result in the half-open state reserves one probe slot, so
        every ``allow()`` that returns ``True`` must be paired with exactly one
        ``record_success()`` or ``record_failure()``.
        """
        with self._lock:
            self._maybe_transition_to_half_open()

            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                return False

            # HALF_OPEN: admit only a bounded number of concurrent probes.
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

    def record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls = max(0, self._half_open_calls - 1)
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._reset()
            else:
                self._failure_count = 0

    def record_failure(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                # A failed probe sends the breaker straight back to open.
                self._trip()
                return

            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._trip()

    def retry_after(self) -> Optional[float]:
        """Seconds remaining before an open breaker will admit a probe."""
        with self._lock:
            if self._state != CircuitState.OPEN or self._opened_at is None:
                return None
            remaining = self.recovery_timeout - (self._time() - self._opened_at)
            return max(0.0, remaining)

    def _maybe_transition_to_half_open(self) -> None:
        if self._state != CircuitState.OPEN or self._opened_at is None:
            return
        if (self._time() - self._opened_at) >= self.recovery_timeout:
            self._state = CircuitState.HALF_OPEN
            self._half_open_calls = 0
            self._success_count = 0

    def _trip(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._time()
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0

    def _reset(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._opened_at = None

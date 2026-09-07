"""
Resilience primitives for calls that can fail transiently.

This module provides three composable building blocks for making outbound
calls (HTTP clients, database drivers, message queues) more robust:

- ``BackoffPolicy``: computes exponential backoff delays with optional jitter.
- ``CircuitBreaker``: trips open after repeated failures so a struggling
  dependency is given time to recover instead of being hammered.
- ``retry_with_backoff`` / ``resilient``: retry a callable, optionally under a
  per-attempt timeout and behind a circuit breaker.

All timing and randomness is injectable (``sleep``, ``clock``, ``random_fn``)
so the behavior can be exercised deterministically in tests without real
delays.
"""
from __future__ import annotations

import functools
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional, Tuple, Type


class ResilienceError(Exception):
    """Base class for errors raised by this module."""


class CircuitBreakerOpenError(ResilienceError):
    """Raised when a call is rejected because the circuit is open."""


class ResilienceTimeoutError(ResilienceError):
    """Raised when a single attempt exceeds its allotted timeout."""


class RetryError(ResilienceError):
    """Raised when all retry attempts are exhausted.

    The exception that caused the final attempt to fail is preserved on
    ``last_exception`` (and chained via ``__cause__``) so callers can inspect
    or re-raise the underlying error.
    """

    def __init__(self, message: str, last_exception: Optional[BaseException] = None):
        super().__init__(message)
        self.last_exception = last_exception


@dataclass
class BackoffPolicy:
    """Exponential backoff schedule.

    The delay before retry number ``attempt`` (0-indexed) is::

        min(base_delay * multiplier ** attempt, max_delay)

    When ``jitter`` is enabled the delay is drawn uniformly from
    ``[0, computed_delay]`` (full jitter), which spreads retries from many
    callers out in time and avoids a synchronized "thundering herd".
    """

    base_delay: float = 0.1
    max_delay: float = 10.0
    multiplier: float = 2.0
    jitter: bool = True

    def compute_delay(
        self, attempt: int, random_fn: Callable[[float, float], float] = random.uniform
    ) -> float:
        if attempt < 0:
            raise ValueError("attempt must be non-negative")
        raw = self.base_delay * (self.multiplier ** attempt)
        capped = min(raw, self.max_delay)
        if capped <= 0:
            return 0.0
        if self.jitter:
            return random_fn(0.0, capped)
        return capped


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """A thread-safe circuit breaker.

    States:

    - ``CLOSED``: calls flow through. Consecutive failures are counted; when
      they reach ``failure_threshold`` the breaker trips to ``OPEN``.
    - ``OPEN``: calls are rejected immediately with ``CircuitBreakerOpenError``
      until ``recovery_timeout`` seconds have elapsed, after which the breaker
      moves to ``HALF_OPEN``.
    - ``HALF_OPEN``: a limited number of trial calls are allowed. Enough
      successes (``success_threshold``) close the breaker; any failure reopens
      it.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 1,
        half_open_max_calls: int = 1,
        clock: Callable[[], float] = time.monotonic,
    ):
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if success_threshold < 1:
            raise ValueError("success_threshold must be >= 1")
        if half_open_max_calls < 1:
            raise ValueError("half_open_max_calls must be >= 1")
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.half_open_max_calls = half_open_max_calls
        self._clock = clock
        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._opened_at: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        """Current state, accounting for a possible OPEN -> HALF_OPEN move."""
        with self._lock:
            self._maybe_half_open()
            return self._state

    def _maybe_half_open(self) -> None:
        # Caller must hold the lock.
        if self._state is CircuitState.OPEN and self._opened_at is not None:
            if self._clock() - self._opened_at >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                self._half_open_calls = 0

    def before_call(self) -> None:
        """Reserve permission to make a call, or reject it.

        Raises ``CircuitBreakerOpenError`` when the circuit is open, or when it
        is half-open and the trial-call budget is already exhausted.
        """
        with self._lock:
            self._maybe_half_open()
            if self._state is CircuitState.OPEN:
                raise CircuitBreakerOpenError("circuit is open")
            if self._state is CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpenError(
                        "circuit is half-open and trial calls are exhausted"
                    )
                self._half_open_calls += 1

    def record_success(self) -> None:
        with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._reset_locked()
            else:
                self._failure_count = 0

    def record_failure(self) -> None:
        with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                # A failure during recovery immediately reopens the circuit.
                self._trip_locked()
                return
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._trip_locked()

    def reset(self) -> None:
        """Force the breaker back to a clean CLOSED state."""
        with self._lock:
            self._reset_locked()

    def _reset_locked(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._opened_at = None

    def _trip_locked(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0


def _call_with_timeout(func: Callable[[], Any], timeout: Optional[float]) -> Any:
    """Run ``func`` and enforce ``timeout`` seconds if given.

    A worker thread runs the call so a blocking function can be abandoned.
    Note: Python cannot forcibly kill the thread, so the underlying call keeps
    running in the background until it returns on its own; the timeout only
    stops the caller from waiting. Use ``timeout=None`` to disable enforcement.
    """
    if timeout is None:
        return func()
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError as exc:
            raise ResilienceTimeoutError(
                f"call exceeded timeout of {timeout}s"
            ) from exc


def retry_with_backoff(
    func: Callable[[], Any],
    *,
    retries: int = 2,
    policy: Optional[BackoffPolicy] = None,
    retry_on: Tuple[Type[BaseException], ...] = (Exception,),
    timeout: Optional[float] = None,
    breaker: Optional[CircuitBreaker] = None,
    on_retry: Optional[Callable[[int, BaseException, float], None]] = None,
    sleep: Callable[[float], None] = time.sleep,
    random_fn: Callable[[float, float], float] = random.uniform,
) -> Any:
    """Call ``func`` with retries, backoff, optional timeout and circuit breaker.

    Args:
        func: Zero-argument callable to invoke.
        retries: Number of *additional* attempts after the first, so the call
            is attempted up to ``retries + 1`` times.
        policy: Backoff schedule. Defaults to ``BackoffPolicy()``.
        retry_on: Exception types that count as transient failures and trigger
            a retry. Anything else propagates immediately.
        timeout: Per-attempt timeout in seconds, or ``None`` to disable.
        breaker: Optional shared ``CircuitBreaker`` guarding the dependency.
        on_retry: Callback invoked as ``on_retry(attempt, exception, delay)``
            before sleeping between attempts.
        sleep: Sleep function (injectable for tests).
        random_fn: Jitter source (injectable for tests).

    Returns:
        Whatever ``func`` returns on the first successful attempt.

    Raises:
        CircuitBreakerOpenError: If the breaker rejects the call.
        RetryError: If every attempt fails with a ``retry_on`` exception.
        Exception: Any non-retryable exception raised by ``func``.
    """
    if retries < 0:
        raise ValueError("retries must be non-negative")
    policy = policy or BackoffPolicy()
    total_attempts = retries + 1
    last_exception: Optional[BaseException] = None

    for attempt in range(total_attempts):
        if breaker is not None:
            # A rejected call is not a transient failure of func itself, so it
            # is never retried here; it propagates to the caller.
            breaker.before_call()
        try:
            result = _call_with_timeout(func, timeout)
        except retry_on as exc:
            last_exception = exc
            if breaker is not None:
                breaker.record_failure()
            is_last = attempt == total_attempts - 1
            if is_last:
                break
            delay = policy.compute_delay(attempt, random_fn=random_fn)
            if on_retry is not None:
                on_retry(attempt + 1, exc, delay)
            if delay > 0:
                sleep(delay)
            continue
        else:
            if breaker is not None:
                breaker.record_success()
            return result

    raise RetryError(
        f"call failed after {total_attempts} attempt(s)",
        last_exception=last_exception,
    ) from last_exception


def resilient(
    *,
    retries: int = 2,
    policy: Optional[BackoffPolicy] = None,
    retry_on: Tuple[Type[BaseException], ...] = (Exception,),
    timeout: Optional[float] = None,
    breaker: Optional[CircuitBreaker] = None,
    on_retry: Optional[Callable[[int, BaseException, float], None]] = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator form of :func:`retry_with_backoff`.

    The same ``breaker`` instance is shared across every call to the decorated
    function, so failures accumulate across calls as expected.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return retry_with_backoff(
                lambda: func(*args, **kwargs),
                retries=retries,
                policy=policy,
                retry_on=retry_on,
                timeout=timeout,
                breaker=breaker,
                on_retry=on_retry,
                sleep=sleep,
            )

        return wrapper

    return decorator

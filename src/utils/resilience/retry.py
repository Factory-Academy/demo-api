"""Retry runner that combines backoff with an optional circuit breaker."""

from __future__ import annotations

import functools
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Tuple, Type, TypeVar

from src.utils.resilience.backoff import BackoffPolicy
from src.utils.resilience.circuit_breaker import CircuitBreaker
from src.utils.resilience.errors import RetryError

logger = logging.getLogger(__name__)

T = TypeVar("T")

#: Exceptions that are retried unless a policy overrides the choice. These are
#: the transient faults that are usually worth re-attempting.
DEFAULT_RETRYABLE: Tuple[Type[BaseException], ...] = (TimeoutError, ConnectionError)


@dataclass
class RetryPolicy:
    """Describes how a call should be retried.

    ``retry_on`` lists the exception types that trigger another attempt.
    ``give_up_on`` takes precedence: a matching exception is never retried even
    if it also matches ``retry_on`` (useful for, say, retrying ``HTTPError`` in
    general but never a ``NotFound`` subclass).

    ``deadline`` is an optional wall-clock budget, in seconds, covering all
    attempts together. Once it is exhausted no further attempts are made even
    if ``max_attempts`` remains.
    """

    max_attempts: int = 3
    backoff: BackoffPolicy = field(default_factory=BackoffPolicy)
    retry_on: Tuple[Type[BaseException], ...] = DEFAULT_RETRYABLE
    give_up_on: Tuple[Type[BaseException], ...] = ()
    deadline: Optional[float] = None

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.deadline is not None and self.deadline <= 0:
            raise ValueError("deadline must be positive when set")

    def is_retryable(self, exc: BaseException) -> bool:
        if self.give_up_on and isinstance(exc, self.give_up_on):
            return False
        return isinstance(exc, self.retry_on)


def retry_call(
    func: Callable[..., T],
    *args: Any,
    policy: Optional[RetryPolicy] = None,
    breaker: Optional[CircuitBreaker] = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    rng: Optional[random.Random] = None,
    **kwargs: Any,
) -> T:
    """Call ``func`` with retries, backoff and an optional circuit breaker.

    Behaviour:

    * A successful call returns its result and records a breaker success.
    * A retryable failure (per ``policy``) records a breaker failure, waits for
      the backoff delay and tries again until attempts or the deadline run out,
      at which point :class:`RetryError` is raised with the last exception
      attached.
    * A non-retryable exception propagates immediately and does **not** count
      against the breaker, which is reserved for availability failures. If it
      was raised during a half-open probe, the reserved trial slot is released
      so a genuine probe can still run.
    * If the breaker is open, the attempt is rejected before ``func`` runs and
      :class:`CircuitOpenError` propagates to the caller.

    ``sleep``, ``clock`` and ``rng`` are injectable to keep retry logic
    testable without real delays.
    """
    policy = policy or RetryPolicy()
    start = clock()
    last_exc: Optional[BaseException] = None
    attempt = 0

    for attempt in range(1, policy.max_attempts + 1):
        if breaker is not None:
            # May raise CircuitOpenError, which intentionally propagates.
            breaker.acquire()
        try:
            result = func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - we classify below
            if not policy.is_retryable(exc):
                # Not an availability failure: return any reserved half-open
                # trial slot so a genuine probe can still run.
                if breaker is not None:
                    breaker.release()
                raise
            last_exc = exc
            if breaker is not None:
                breaker.record_failure()
            if attempt >= policy.max_attempts:
                break

            delay = policy.backoff.compute(attempt, rng=rng)
            if policy.deadline is not None:
                remaining = policy.deadline - (clock() - start)
                if remaining <= 0:
                    break
                delay = min(delay, remaining)

            logger.warning(
                "attempt %d/%d failed (%r); retrying in %.3fs",
                attempt,
                policy.max_attempts,
                exc,
                delay,
            )
            sleep(delay)

            if policy.deadline is not None and (clock() - start) >= policy.deadline:
                break
        else:
            if breaker is not None:
                breaker.record_success()
            return result

    raise RetryError(attempt, last_exc)


def resilient(
    *,
    policy: Optional[RetryPolicy] = None,
    breaker: Optional[CircuitBreaker] = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator form of :func:`retry_call`.

    The same ``policy`` and ``breaker`` instances are shared across every call
    to the wrapped function, so a breaker accumulates state across calls as
    intended.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return retry_call(
                func,
                *args,
                policy=policy,
                breaker=breaker,
                sleep=sleep,
                clock=clock,
                **kwargs,
            )

        return wrapper

    return decorator

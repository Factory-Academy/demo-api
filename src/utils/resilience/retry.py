import functools
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Tuple, Type, TypeVar

from .backoff import BackoffPolicy
from .circuit_breaker import CircuitBreaker
from .errors import CallTimeoutError, CircuitBreakerOpenError, RetryError

T = TypeVar("T")

# Called after a failed-but-retryable attempt as (attempt, error, delay).
OnRetry = Callable[[int, BaseException, float], None]


@dataclass
class RetryPolicy:
    """Declarative configuration for :func:`retry_call`.

    ``retryable_exceptions`` decides which errors trigger another attempt;
    anything else propagates immediately without consuming attempts or tripping
    an attached circuit breaker. A ``timeout`` (seconds) bounds each individual
    attempt and is enforced regardless of whether the callable cooperates.
    """

    max_attempts: int = 3
    backoff: BackoffPolicy = field(default_factory=BackoffPolicy)
    retryable_exceptions: Tuple[Type[BaseException], ...] = (Exception,)
    timeout: Optional[float] = None

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("timeout must be positive when set")
        if not self.retryable_exceptions:
            raise ValueError("retryable_exceptions must not be empty")


def retry_call(
    func: Callable[..., T],
    *args: Any,
    policy: Optional[RetryPolicy] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
    sleep: Callable[[float], None] = time.sleep,
    on_retry: Optional[OnRetry] = None,
    **kwargs: Any,
) -> T:
    """Invoke ``func(*args, **kwargs)`` with retries, backoff and an optional
    circuit breaker.

    Raises:
        CircuitBreakerOpenError: if an attached breaker rejects the call.
        RetryError: if every attempt fails with a retryable error. The final
            underlying error is available on ``RetryError.last_error``.
        Exception: any non-retryable error is re-raised unchanged.
    """
    policy = policy or RetryPolicy()

    # A CallTimeoutError should always be eligible for a retry even if the
    # caller narrowed retryable_exceptions to a domain-specific set.
    retryable = policy.retryable_exceptions
    if CallTimeoutError not in retryable and not _covers(retryable, CallTimeoutError):
        retryable = retryable + (CallTimeoutError,)

    last_error: Optional[BaseException] = None

    for attempt in range(1, policy.max_attempts + 1):
        if circuit_breaker is not None and not circuit_breaker.allow():
            raise CircuitBreakerOpenError(retry_after=circuit_breaker.retry_after())

        try:
            result = _call_with_timeout(func, args, kwargs, policy.timeout)
        except retryable as error:
            last_error = error
            if circuit_breaker is not None:
                circuit_breaker.record_failure()

            if attempt >= policy.max_attempts:
                break

            delay = policy.backoff.compute_delay(attempt)
            if on_retry is not None:
                on_retry(attempt, error, delay)
            if delay > 0:
                sleep(delay)
        else:
            if circuit_breaker is not None:
                circuit_breaker.record_success()
            return result

    raise RetryError(policy.max_attempts, last_error) from last_error


def resilient(
    policy: Optional[RetryPolicy] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
    sleep: Callable[[float], None] = time.sleep,
    on_retry: Optional[OnRetry] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator form of :func:`retry_call`.

    The same ``circuit_breaker`` instance is shared across every invocation of
    the wrapped function, so failures accumulate as expected.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return retry_call(
                func,
                *args,
                policy=policy,
                circuit_breaker=circuit_breaker,
                sleep=sleep,
                on_retry=on_retry,
                **kwargs,
            )

        return wrapper

    return decorator


def _call_with_timeout(
    func: Callable[..., T],
    args: tuple,
    kwargs: dict,
    timeout: Optional[float],
) -> T:
    if timeout is None:
        return func(*args, **kwargs)

    # A worker thread lets us stop *waiting* after the deadline. The call itself
    # cannot be forcibly killed, so a timed-out thread keeps running in the
    # background; callers should treat CallTimeoutError as "result unknown".
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            raise CallTimeoutError(timeout) from None


def _covers(exc_types: Tuple[Type[BaseException], ...], candidate: Type[BaseException]) -> bool:
    return any(issubclass(candidate, exc_type) for exc_type in exc_types)

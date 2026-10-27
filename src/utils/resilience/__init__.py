"""Retry-with-backoff and circuit-breaker utilities.

Typical usage::

    from src.utils.resilience import RetryPolicy, BackoffPolicy, CircuitBreaker, retry_call

    policy = RetryPolicy(max_attempts=3, backoff=BackoffPolicy(base_delay=0.1))
    breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)

    result = retry_call(client.fetch, "/status", policy=policy, circuit_breaker=breaker)
"""

from src.utils.resilience.backoff import BackoffPolicy
from src.utils.resilience.circuit_breaker import CircuitBreaker, CircuitState
from src.utils.resilience.errors import (
    CallTimeoutError,
    CircuitBreakerOpenError,
    ResilienceError,
    RetryError,
)
from src.utils.resilience.retry import RetryPolicy, resilient, retry_call

__all__ = [
    "BackoffPolicy",
    "CircuitBreaker",
    "CircuitState",
    "ResilienceError",
    "RetryError",
    "CircuitBreakerOpenError",
    "CallTimeoutError",
    "RetryPolicy",
    "retry_call",
    "resilient",
]

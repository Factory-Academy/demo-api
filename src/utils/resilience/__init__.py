"""Resilience utilities: retry-with-backoff and a circuit breaker.

Typical usage::

    from src.utils.resilience import (
        BackoffPolicy,
        CircuitBreaker,
        CircuitBreakerConfig,
        RetryPolicy,
        retry_call,
    )

    breaker = CircuitBreaker("payments", CircuitBreakerConfig(failure_threshold=3))
    policy = RetryPolicy(max_attempts=4, backoff=BackoffPolicy(base_delay=0.05))

    result = retry_call(charge_card, amount, policy=policy, breaker=breaker)

See ``docs/NOTES.md`` for the design rationale and edge-case handling.
"""

from src.utils.resilience.backoff import BackoffPolicy
from src.utils.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)
from src.utils.resilience.errors import (
    CircuitOpenError,
    ResilienceError,
    RetryError,
)
from src.utils.resilience.retry import (
    DEFAULT_RETRYABLE,
    RetryPolicy,
    resilient,
    retry_call,
)

__all__ = [
    "BackoffPolicy",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "CircuitOpenError",
    "ResilienceError",
    "RetryError",
    "DEFAULT_RETRYABLE",
    "RetryPolicy",
    "resilient",
    "retry_call",
]

import time
from typing import Any, Callable, Dict, Optional

from src.utils.resilience import (
    BackoffPolicy,
    CircuitBreaker,
    RetryPolicy,
    retry_call,
)


class UpstreamError(Exception):
    """Raised by a transport when the upstream status service misbehaves."""


# A transport is any callable that performs a single outbound request and
# returns the decoded payload, e.g. a thin wrapper around httpx or requests.
Transport = Callable[[str, Optional[dict]], Dict[str, Any]]


def _default_policy() -> RetryPolicy:
    return RetryPolicy(
        max_attempts=3,
        backoff=BackoffPolicy(base_delay=0.05, factor=2.0, max_delay=1.0),
        # Only transient transport failures are retried; a bad payload
        # (ValueError, KeyError, ...) fails fast instead of being repeated.
        retryable_exceptions=(UpstreamError,),
        timeout=2.0,
    )


class StatusNotifier:
    """Posts item status changes to an external notification service.

    The single outbound call (:meth:`notify`) is wrapped with retry-with-backoff
    and guarded by a circuit breaker, so a flaky or down dependency degrades
    gracefully instead of blocking the request path indefinitely.
    """

    def __init__(
        self,
        transport: Transport,
        policy: Optional[RetryPolicy] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._transport = transport
        self._policy = policy or _default_policy()
        self._breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5.0,
            half_open_max_calls=1,
        )
        self._sleep = sleep

    def notify(self, item_id: int, status: str) -> Dict[str, Any]:
        """Send a status update, retrying transient failures.

        Raises:
            CircuitBreakerOpenError: if the breaker is open after repeated
                upstream failures.
            RetryError: if every attempt fails.
        """
        payload = {"item_id": item_id, "status": status}
        return retry_call(
            self._transport,
            "/notifications",
            payload,
            policy=self._policy,
            circuit_breaker=self._breaker,
            sleep=self._sleep,
        )

    @property
    def circuit_state(self):
        return self._breaker.state

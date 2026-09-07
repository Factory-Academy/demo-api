"""
Client for notifying an external system when a record's status changes.

Status updates are pushed to a downstream webhook. That call crosses the
network, so it is wrapped with retry-with-backoff, a per-attempt timeout, and a
circuit breaker (see ``src.utils.resilience``). Transient problems (timeouts,
connection resets, 5xx responses) are retried and can trip the breaker;
permanent problems (4xx responses) fail fast without retrying.

The transport is injectable via ``sender`` so the client can be exercised in
tests without real network access.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from src.utils.resilience import (
    BackoffPolicy,
    CircuitBreaker,
    ResilienceTimeoutError,
    retry_with_backoff,
)


class NotifierError(Exception):
    """Base class for status-notifier failures."""


class NotifierUnavailableError(NotifierError):
    """Transient failure that is worth retrying (timeout, 5xx, connection)."""


class NotifierClientError(NotifierError):
    """Permanent failure caused by a bad request (4xx); not retried."""


# Exceptions that should trigger a retry / count against the circuit breaker.
RETRYABLE = (NotifierUnavailableError, ResilienceTimeoutError)


class StatusNotifier:
    def __init__(
        self,
        url: str,
        *,
        sender: Optional[Callable[[Dict[str, Any]], Any]] = None,
        breaker: Optional[CircuitBreaker] = None,
        policy: Optional[BackoffPolicy] = None,
        retries: int = 3,
        timeout: float = 2.0,
    ):
        self.url = url
        self._sender = sender or self._default_sender
        self._breaker = breaker or CircuitBreaker(
            failure_threshold=3, recovery_timeout=15.0
        )
        self._policy = policy or BackoffPolicy(base_delay=0.05, max_delay=1.0)
        self._retries = retries
        self._timeout = timeout

    def _default_sender(self, payload: Dict[str, Any]) -> int:
        # Imported lazily so tests that inject ``sender`` never require httpx
        # to be importable and never open a real client.
        import httpx

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(self.url, json=payload)
        except httpx.TimeoutException as exc:
            raise NotifierUnavailableError(f"timeout contacting {self.url}") from exc
        except httpx.TransportError as exc:
            raise NotifierUnavailableError(f"transport error: {exc}") from exc

        if response.status_code >= 500:
            raise NotifierUnavailableError(
                f"server error {response.status_code} from {self.url}"
            )
        if response.status_code >= 400:
            raise NotifierClientError(
                f"client error {response.status_code} from {self.url}"
            )
        return response.status_code

    def notify_status_change(
        self,
        entity_id: Any,
        status: str,
        *,
        updated_by: Optional[str] = None,
    ) -> Any:
        """Push a single status change downstream.

        Raises:
            CircuitBreakerOpenError: If the downstream is currently shut off.
            RetryError: If every retry attempt failed transiently.
            NotifierClientError: If the request was rejected as invalid (4xx).
        """
        payload = {
            "entity_id": entity_id,
            "status": status,
            "updated_by": updated_by,
        }
        return retry_with_backoff(
            lambda: self._sender(payload),
            retries=self._retries,
            policy=self._policy,
            retry_on=RETRYABLE,
            breaker=self._breaker,
        )

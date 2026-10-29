"""HTTP client that pushes item status changes to an external notifier.

The outbound POST is wrapped with the resilience utilities so transient
failures of the notifier service (timeouts, connection errors, 5xx responses)
are retried with backoff, while a circuit breaker stops us from hammering the
service once it is clearly down. Permanent failures (4xx) are not retried.

The notifier is treated as best-effort: callers get a boolean telling them
whether the notification was delivered, and a failure never propagates to break
the surrounding business operation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from src.utils.resilience import (
    BackoffPolicy,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    RetryError,
    RetryPolicy,
    retry_call,
)

logger = logging.getLogger(__name__)


class NotifierError(Exception):
    """Base error for the status notifier client."""


class NotifierUnavailableError(NotifierError):
    """Transient failure (timeout, connection error, or 5xx). Retryable."""


class NotifierRejectedError(NotifierError):
    """Permanent failure (the service rejected the request, e.g. 4xx)."""

    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"notifier rejected request with status {status_code}")


@dataclass(frozen=True)
class NotifierConfig:
    base_url: str
    timeout: float = 2.0
    max_attempts: int = 3
    endpoint: str = "/notifications"

    def __post_init__(self) -> None:
        if not self.base_url:
            raise ValueError("base_url is required")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")


def _default_breaker() -> CircuitBreaker:
    return CircuitBreaker(
        "status-notifier",
        CircuitBreakerConfig(failure_threshold=3, recovery_timeout=10.0),
    )


def _default_policy(max_attempts: int) -> RetryPolicy:
    return RetryPolicy(
        max_attempts=max_attempts,
        backoff=BackoffPolicy(base_delay=0.05, max_delay=1.0),
        retry_on=(NotifierUnavailableError,),
        give_up_on=(NotifierRejectedError,),
    )


class StatusNotifierClient:
    """Sends item status-change notifications to an external service."""

    def __init__(
        self,
        config: NotifierConfig,
        *,
        client: Optional[httpx.Client] = None,
        transport: Optional[httpx.BaseTransport] = None,
        breaker: Optional[CircuitBreaker] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> None:
        self._config = config
        self._client = client or httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            transport=transport,
        )
        self._breaker = breaker or _default_breaker()
        self._retry_policy = retry_policy or _default_policy(config.max_attempts)

    @property
    def breaker(self) -> CircuitBreaker:
        return self._breaker

    def notify_status_change(
        self,
        *,
        item_id: int,
        old_status: Optional[str],
        new_status: str,
        updated_by: str,
    ) -> bool:
        """Notify the external service of a status change.

        Returns ``True`` if the notification was accepted, ``False`` if it was
        dropped (retries exhausted, circuit open, or a permanent rejection).
        Never raises for an expected notifier failure, since delivery is
        best-effort relative to the local update that triggered it.
        """
        payload = {
            "item_id": item_id,
            "old_status": old_status,
            "new_status": new_status,
            "updated_by": updated_by,
        }
        try:
            retry_call(
                self._send,
                payload,
                policy=self._retry_policy,
                breaker=self._breaker,
            )
            return True
        except CircuitOpenError:
            logger.warning(
                "notifier circuit open; dropping notification for item %s",
                item_id,
            )
            return False
        except RetryError as exc:
            logger.error(
                "notifier failed after %d attempt(s) for item %s: %r",
                exc.attempts,
                item_id,
                exc.last_exception,
            )
            return False
        except NotifierRejectedError as exc:
            logger.error(
                "notifier rejected notification for item %s (status %d)",
                item_id,
                exc.status_code,
            )
            return False

    def _send(self, payload: Dict[str, Any]) -> httpx.Response:
        """Perform one POST, translating transport/HTTP errors into our types."""
        try:
            response = self._client.post(self._config.endpoint, json=payload)
        except httpx.TimeoutException as exc:
            raise NotifierUnavailableError("notifier request timed out") from exc
        except httpx.TransportError as exc:
            raise NotifierUnavailableError("notifier connection error") from exc

        if response.status_code >= 500:
            raise NotifierUnavailableError(
                f"notifier returned server error {response.status_code}"
            )
        if response.status_code >= 400:
            raise NotifierRejectedError(response.status_code)
        return response

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "StatusNotifierClient":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

"""Exceptions raised by the resilience utilities."""

from __future__ import annotations

from typing import Optional


class ResilienceError(Exception):
    """Base class for every error raised by this package."""


class RetryError(ResilienceError):
    """Raised when a call still fails after every retry attempt is used up.

    The exception that caused the final failure is preserved on
    :attr:`last_exception` so callers can inspect or re-raise it.
    """

    def __init__(self, attempts: int, last_exception: Optional[BaseException]):
        self.attempts = attempts
        self.last_exception = last_exception
        message = f"Call failed after {attempts} attempt(s)"
        if last_exception is not None:
            message += f": {last_exception!r}"
        super().__init__(message)


class CircuitOpenError(ResilienceError):
    """Raised when a call is rejected because the circuit breaker is open.

    :attr:`retry_after` is the estimated number of seconds until the breaker
    will next allow a trial call, when that estimate is available.
    """

    def __init__(self, name: str, retry_after: Optional[float] = None):
        self.name = name
        self.retry_after = retry_after
        message = f"Circuit '{name}' is open"
        if retry_after is not None:
            message += f"; retry after {retry_after:.2f}s"
        super().__init__(message)

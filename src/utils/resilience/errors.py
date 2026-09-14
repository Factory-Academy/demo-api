from typing import Optional


class ResilienceError(Exception):
    """Base class for all resilience-related failures."""


class RetryError(ResilienceError):
    """Raised when a call still fails after every retry attempt is used.

    The exception raised by the final attempt is preserved on ``last_error``
    and also chained via ``raise ... from`` so the original traceback survives.
    """

    def __init__(self, attempts: int, last_error: Optional[BaseException]):
        self.attempts = attempts
        self.last_error = last_error
        message = f"call failed after {attempts} attempt(s)"
        if last_error is not None:
            message += f": {last_error!r}"
        super().__init__(message)


class CircuitBreakerOpenError(ResilienceError):
    """Raised when a call is rejected because the circuit breaker is open."""

    def __init__(self, retry_after: Optional[float] = None):
        self.retry_after = retry_after
        message = "circuit breaker is open"
        if retry_after is not None:
            message += f"; retry after {retry_after:.3f}s"
        super().__init__(message)


class CallTimeoutError(ResilienceError):
    """Raised when a single call exceeds its allotted per-attempt timeout."""

    def __init__(self, timeout: float):
        self.timeout = timeout
        super().__init__(f"call exceeded timeout of {timeout:.3f}s")

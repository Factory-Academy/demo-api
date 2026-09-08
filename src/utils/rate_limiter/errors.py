"""Exceptions raised by the rate limiter."""
from typing import Optional


class RateLimitExceeded(Exception):
    """
    Raised when a request cannot be satisfied by the available tokens.

    Attributes:
        retry_after: Estimated seconds until enough tokens are available.
            ``None`` when the request can never be satisfied (for example,
            requesting more tokens than the bucket's capacity, or a drained
            fixed-quota bucket that never refills).
        key: The bucket key that rejected the request, when raised by a
            :class:`~src.utils.rate_limiter.limiter.RateLimiter`. ``None`` for a
            bare :class:`~src.utils.rate_limiter.bucket.TokenBucket`.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None,
        key: Optional[str] = None,
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.key = key

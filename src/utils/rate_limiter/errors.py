"""Exceptions raised by the rate limiter."""

from typing import Optional


class RateLimitExceeded(Exception):
    """Raised when a request cannot be satisfied within the configured rate.

    Attributes:
        retry_after: Seconds until the request could succeed, or ``None`` when
            it can never be satisfied (the demand exceeds the bucket capacity,
            or the bucket is drained and does not refill).
        key: The caller key that was limited, set when raised through a
            :class:`~src.utils.rate_limiter.limiter.RateLimiter`. ``None`` for a
            bare :class:`~src.utils.rate_limiter.bucket.TokenBucket`.
    """

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        key: Optional[object] = None,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after
        self.key = key

    def __repr__(self) -> str:
        # The default Exception repr drops retry_after and key, the two fields a
        # caller actually logs or acts on; spell them out explicitly.
        return (
            f"{type(self).__name__}({str(self)!r}, "
            f"retry_after={self.retry_after!r}, key={self.key!r})"
        )

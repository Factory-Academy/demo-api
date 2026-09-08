"""A keyed registry of token buckets for per-caller rate limiting."""
import threading
import time as _time
from typing import Callable, Dict, Optional

from .bucket import TokenBucket
from .errors import RateLimitExceeded
from .validation import validate_capacity, validate_refill_rate


class RateLimiter:
    """
    A registry of token buckets keyed by an arbitrary string.

    Each distinct key gets its own :class:`TokenBucket` created lazily on first
    use, all sharing the same ``capacity`` and ``refill_rate``. This is the
    typical way to rate-limit per user, per API key, or per IP address.

    Args:
        capacity: Bucket capacity applied to every key. Must be a finite
            number > 0.
        refill_rate: Refill rate (tokens/second) applied to every key. Must be
            finite and >= 0.
        time_func: Timestamp source shared by all buckets. Injectable for
            deterministic testing. Defaults to :func:`time.monotonic`.

    Raises:
        ValueError: If ``capacity`` <= 0, ``refill_rate`` < 0, or either is not
            a finite number.

    Examples:
        >>> limiter = RateLimiter(capacity=1, refill_rate=1)
        >>> limiter.allow("user-a")
        True
        >>> limiter.allow("user-a")
        False
        >>> limiter.allow("user-b")
        True
    """

    def __init__(
        self,
        capacity: float,
        refill_rate: float,
        time_func: Callable[[], float] = _time.monotonic,
    ):
        self.capacity = validate_capacity(capacity)
        self.refill_rate = validate_refill_rate(refill_rate)
        self._time_func = time_func
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def _bucket_for(self, key: str) -> TokenBucket:
        """Return the bucket for ``key``, creating it on first use."""
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = TokenBucket(
                    capacity=self.capacity,
                    refill_rate=self.refill_rate,
                    time_func=self._time_func,
                )
                self._buckets[key] = bucket
            return bucket

    def allow(self, key: str, tokens: float = 1) -> bool:
        """
        Return whether ``tokens`` are available for ``key``, consuming them.

        Args:
            key: Identifier for the caller (user id, API key, IP, ...).
            tokens: Tokens to consume. Must be a finite number > 0.

        Returns:
            True if consumed, False if the key is currently limited.

        Raises:
            ValueError: If ``tokens`` <= 0 or is not finite.
        """
        return self._bucket_for(key).try_consume(tokens)

    def check(self, key: str, tokens: float = 1) -> None:
        """
        Consume ``tokens`` for ``key`` or raise :class:`RateLimitExceeded`.

        Args:
            key: Identifier for the caller.
            tokens: Tokens to consume. Must be a finite number > 0.

        Raises:
            ValueError: If ``tokens`` <= 0 or is not finite.
            RateLimitExceeded: If the key is limited. The exception's ``key``
                attribute is set to ``key``.
        """
        try:
            self._bucket_for(key).consume(tokens)
        except RateLimitExceeded as error:
            error.key = key
            raise

    def tokens_remaining(self, key: str) -> float:
        """Current tokens available for ``key`` (creates the bucket if new)."""
        return self._bucket_for(key).available_tokens

    def reset(self, key: Optional[str] = None) -> None:
        """
        Reset one key's bucket or clear every bucket.

        Args:
            key: The key to refill. When ``None``, all buckets are dropped so
                every key starts fresh (full) on next use.
        """
        with self._lock:
            if key is None:
                self._buckets.clear()
                return
            bucket = self._buckets.get(key)
        if bucket is not None:
            bucket.reset()

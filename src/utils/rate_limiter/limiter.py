"""A keyed registry of token buckets for per-caller rate limiting."""

from __future__ import annotations

import threading
from typing import Callable, Dict, Optional

from src.utils.rate_limiter.bucket import TokenBucket
from src.utils.rate_limiter.errors import RateLimitExceeded
from src.utils.rate_limiter.validation import (
    Number,
    validate_capacity,
    validate_refill_rate,
)


class RateLimiter:
    """Per-key token-bucket rate limiter.

    Lazily creates one :class:`TokenBucket` per key, all sharing the same
    ``capacity`` and ``refill_rate``. This limits many independent callers
    (user ids, API keys, IP addresses) through a single object: each key gets
    its own independent allowance.

    Args:
        capacity: Burst size allowed per key. Must be > 0.
        refill_rate: Tokens restored per second per key. Must be >= 0.
        time_func: Clock shared by every bucket. Defaults to
            :func:`time.monotonic`; inject a fake for deterministic tests.
    """

    def __init__(
        self,
        capacity: Number,
        refill_rate: Number,
        time_func: Optional[Callable[[], float]] = None,
    ) -> None:
        self.capacity = validate_capacity(capacity)
        self.refill_rate = validate_refill_rate(refill_rate)
        self._time_func = time_func
        self._buckets: Dict[object, TokenBucket] = {}
        self._lock = threading.Lock()

    def _bucket_for(self, key: object) -> TokenBucket:
        """Return the bucket for ``key``, creating it on first use."""
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = TokenBucket(
                    self.capacity,
                    self.refill_rate,
                    time_func=self._time_func,
                )
                self._buckets[key] = bucket
            return bucket

    def allow(self, key: object, tokens: Number = 1) -> bool:
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

    def check(self, key: object, tokens: Number = 1) -> None:
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
        except RateLimitExceeded as exc:
            exc.key = key
            raise

    def tokens_remaining(self, key: object) -> float:
        """Current tokens available for ``key`` (creates the bucket if new)."""
        return self._bucket_for(key).available_tokens()

    def reset(self, key: object = None) -> None:
        """
        Reset one key's bucket or clear every bucket.

        Args:
            key: The key to refill. When ``None``, all buckets are dropped so
                every key starts fresh (full) on next use.
        """
        with self._lock:
            if key is None:
                self._buckets.clear()
            else:
                self._buckets.pop(key, None)

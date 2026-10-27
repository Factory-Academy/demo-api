"""A keyed registry of token buckets for per-caller rate limiting."""

from __future__ import annotations

import threading
from typing import Callable, Dict, FrozenSet, Optional

from src.utils.rate_limiter.bucket import TokenBucket
from src.utils.rate_limiter.errors import RateLimitExceeded
from src.utils.rate_limiter.validation import (
    Number,
    validate_capacity,
    validate_key,
    validate_refill_rate,
)

# Distinct sentinel for "reset every bucket". ``None`` cannot double as this
# marker because ``None`` is itself a legal key, so a caller that keys by
# ``None`` must still be able to reset just that one bucket.
_ALL_KEYS = object()


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
        validate_key(key)
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

    def retry_after(self, key: object, tokens: Number = 1) -> Optional[float]:
        """
        Seconds until ``tokens`` are available for ``key`` without consuming.

        Args:
            key: Identifier for the caller.
            tokens: Tokens to wait for. Must be a finite number > 0.

        Returns:
            0.0 if ``tokens`` are available now, a positive number of seconds
            otherwise, or ``None`` if the request can never be satisfied
            (exceeds capacity, or a drained non-refilling bucket).

        Raises:
            ValueError: If ``tokens`` <= 0 or is not finite.
        """
        return self._bucket_for(key).time_until_available(tokens)

    def active_keys(self) -> FrozenSet[object]:
        """Snapshot of keys that currently hold a live bucket.

        Returned as an immutable copy so iterating it never races with
        concurrent ``allow``/``reset`` calls mutating the registry.
        """
        with self._lock:
            return frozenset(self._buckets)

    def reset(self, key: object = _ALL_KEYS) -> None:
        """
        Reset one key's bucket, or every bucket when called with no argument.

        Args:
            key: The key to drop so it starts fresh (full) on next use. Omit the
                argument to drop every bucket. ``None`` is treated as an ordinary
                key, not a "reset everything" signal, so a caller keyed by
                ``None`` resets only that bucket.
        """
        if key is _ALL_KEYS:
            with self._lock:
                self._buckets.clear()
            return
        validate_key(key)
        with self._lock:
            self._buckets.pop(key, None)

    def reset_all(self) -> None:
        """Drop every bucket so all keys start fresh (full) on next use."""
        with self._lock:
            self._buckets.clear()

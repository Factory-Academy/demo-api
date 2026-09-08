"""
Token-bucket rate limiting utilities.

This module provides a small, dependency-free implementation of the
token-bucket algorithm along with a keyed registry for limiting many
independent callers (users, API keys, IP addresses) with a single object.

The token bucket holds up to ``capacity`` tokens and refills continuously at
``refill_rate`` tokens per second. Each request consumes one or more tokens;
when the bucket does not hold enough tokens the request is rejected. This
allows short bursts up to ``capacity`` while enforcing a steady long-run rate.
"""
import threading
import time as _time
from typing import Callable, Dict, Optional


class RateLimitExceeded(Exception):
    """
    Raised when a request cannot be satisfied by the available tokens.

    Attributes:
        retry_after: Estimated seconds until enough tokens are available.
            ``None`` when the request can never be satisfied (for example,
            requesting more tokens than the bucket's capacity).
        key: The bucket key that rejected the request, when raised by a
            :class:`RateLimiter`. ``None`` for a bare :class:`TokenBucket`.
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


class TokenBucket:
    """
    A single token bucket.

    Tokens accrue continuously up to ``capacity`` at a rate of ``refill_rate``
    tokens per second. Consuming tokens is thread-safe.

    Args:
        capacity: Maximum number of tokens the bucket can hold. Must be > 0.
            Also the largest request that can ever succeed.
        refill_rate: Tokens added per second. Must be >= 0. A rate of 0 creates
            a bucket that never refills (useful for a fixed quota).
        initial_tokens: Tokens present when the bucket is created. Defaults to
            ``capacity`` (a full bucket). Clamped to ``[0, capacity]``.
        time_func: Callable returning a monotonically increasing timestamp in
            seconds. Injectable for deterministic testing. Defaults to
            :func:`time.monotonic`.

    Raises:
        ValueError: If ``capacity`` <= 0 or ``refill_rate`` < 0.

    Examples:
        >>> bucket = TokenBucket(capacity=2, refill_rate=1)
        >>> bucket.try_consume()
        True
        >>> bucket.try_consume()
        True
        >>> bucket.try_consume()
        False
    """

    def __init__(
        self,
        capacity: float,
        refill_rate: float,
        initial_tokens: Optional[float] = None,
        time_func: Callable[[], float] = _time.monotonic,
    ):
        if capacity <= 0:
            raise ValueError("capacity must be greater than 0")
        if refill_rate < 0:
            raise ValueError("refill_rate cannot be negative")

        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self._time_func = time_func
        self._lock = threading.Lock()

        if initial_tokens is None:
            initial_tokens = capacity
        # Clamp so callers cannot start above capacity or below empty.
        self._tokens = max(0.0, min(float(initial_tokens), self.capacity))
        self._last_refill = self._time_func()

    def _refill(self) -> None:
        """Add tokens accrued since the last refill. Caller must hold the lock."""
        now = self._time_func()
        elapsed = now - self._last_refill
        # A non-monotonic clock could move backwards; never remove tokens.
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
            self._last_refill = now

    @property
    def available_tokens(self) -> float:
        """Current number of tokens, after accounting for refill."""
        with self._lock:
            self._refill()
            return self._tokens

    def try_consume(self, tokens: float = 1) -> bool:
        """
        Attempt to consume ``tokens`` without raising.

        Args:
            tokens: Number of tokens to consume. Must be > 0.

        Returns:
            True if the tokens were consumed, False if not enough were
            available.

        Raises:
            ValueError: If ``tokens`` <= 0.
        """
        if tokens <= 0:
            raise ValueError("tokens must be greater than 0")

        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def consume(self, tokens: float = 1) -> None:
        """
        Consume ``tokens`` or raise :class:`RateLimitExceeded`.

        Args:
            tokens: Number of tokens to consume. Must be > 0.

        Raises:
            ValueError: If ``tokens`` <= 0.
            RateLimitExceeded: If not enough tokens are available. Its
                ``retry_after`` reports the wait in seconds, or ``None`` when
                ``tokens`` exceeds the bucket capacity.
        """
        if tokens <= 0:
            raise ValueError("tokens must be greater than 0")

        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return
            retry_after = self._time_until_locked(tokens)

        raise RateLimitExceeded(
            "Rate limit exceeded",
            retry_after=retry_after,
        )

    def time_until_available(self, tokens: float = 1) -> Optional[float]:
        """
        Seconds until ``tokens`` can be consumed.

        Args:
            tokens: Number of tokens to wait for. Must be > 0.

        Returns:
            0.0 if the tokens are already available, a positive number of
            seconds otherwise, or ``None`` if the request exceeds capacity and
            can never be satisfied.

        Raises:
            ValueError: If ``tokens`` <= 0.
        """
        if tokens <= 0:
            raise ValueError("tokens must be greater than 0")
        with self._lock:
            self._refill()
            return self._time_until_locked(tokens)

    def _time_until_locked(self, tokens: float) -> Optional[float]:
        """Compute wait time for ``tokens``. Caller must hold the lock."""
        if self._tokens >= tokens:
            return 0.0
        if tokens > self.capacity:
            return None
        if self.refill_rate == 0:
            # Never refills and not currently satisfiable.
            return None
        deficit = tokens - self._tokens
        return deficit / self.refill_rate

    def reset(self) -> None:
        """Refill the bucket to capacity and restart its refill clock."""
        with self._lock:
            self._tokens = self.capacity
            self._last_refill = self._time_func()


class RateLimiter:
    """
    A registry of token buckets keyed by an arbitrary string.

    Each distinct key gets its own :class:`TokenBucket` created lazily on first
    use, all sharing the same ``capacity`` and ``refill_rate``. This is the
    typical way to rate-limit per user, per API key, or per IP address.

    Args:
        capacity: Bucket capacity applied to every key. Must be > 0.
        refill_rate: Refill rate (tokens/second) applied to every key.
            Must be >= 0.
        time_func: Timestamp source shared by all buckets. Injectable for
            deterministic testing. Defaults to :func:`time.monotonic`.

    Raises:
        ValueError: If ``capacity`` <= 0 or ``refill_rate`` < 0.

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
        if capacity <= 0:
            raise ValueError("capacity must be greater than 0")
        if refill_rate < 0:
            raise ValueError("refill_rate cannot be negative")

        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
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
            tokens: Tokens to consume. Must be > 0.

        Returns:
            True if consumed, False if the key is currently limited.

        Raises:
            ValueError: If ``tokens`` <= 0.
        """
        return self._bucket_for(key).try_consume(tokens)

    def check(self, key: str, tokens: float = 1) -> None:
        """
        Consume ``tokens`` for ``key`` or raise :class:`RateLimitExceeded`.

        Args:
            key: Identifier for the caller.
            tokens: Tokens to consume. Must be > 0.

        Raises:
            ValueError: If ``tokens`` <= 0.
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
        if key is not None and bucket is not None:
            bucket.reset()

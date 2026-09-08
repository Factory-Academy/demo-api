"""The single-bucket core of the token-bucket algorithm."""
import threading
import time as _time
from typing import Callable, Optional

from .errors import RateLimitExceeded
from .validation import (
    TOKEN_EPSILON,
    clamp_initial_tokens,
    validate_capacity,
    validate_refill_rate,
    validate_token_request,
)


class TokenBucket:
    """
    A single token bucket.

    Tokens accrue continuously up to ``capacity`` at a rate of ``refill_rate``
    tokens per second. Consuming tokens is thread-safe.

    Args:
        capacity: Maximum number of tokens the bucket can hold. Must be a finite
            number > 0. Also the largest request that can ever succeed.
        refill_rate: Tokens added per second. Must be finite and >= 0. A rate of
            0 creates a bucket that never refills (a fixed quota).
        initial_tokens: Tokens present when the bucket is created. Defaults to
            ``capacity`` (a full bucket). Clamped to ``[0, capacity]``.
        time_func: Callable returning a monotonically increasing timestamp in
            seconds. Injectable for deterministic testing. Defaults to
            :func:`time.monotonic`.

    Raises:
        ValueError: If ``capacity`` <= 0, ``refill_rate`` < 0, or either is not
            a finite number.

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
        self.capacity = validate_capacity(capacity)
        self.refill_rate = validate_refill_rate(refill_rate)
        self._time_func = time_func
        self._lock = threading.Lock()

        if initial_tokens is None:
            initial_tokens = self.capacity
        self._tokens = clamp_initial_tokens(initial_tokens, self.capacity)
        self._last_refill = self._time_func()

    def _refill(self) -> None:
        """Add tokens accrued since the last refill. Caller must hold the lock."""
        now = self._time_func()
        elapsed = now - self._last_refill
        # A non-monotonic clock could move backwards; never remove tokens.
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
            self._last_refill = now

    def _spend_locked(self, tokens: float) -> None:
        """Deduct ``tokens``, guarding against float dust below zero."""
        self._tokens = max(0.0, self._tokens - tokens)

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
            tokens: Number of tokens to consume. Must be a finite number > 0.

        Returns:
            True if the tokens were consumed, False if not enough were
            available.

        Raises:
            ValueError: If ``tokens`` <= 0 or is not finite.
        """
        tokens = validate_token_request(tokens)

        with self._lock:
            self._refill()
            # Allow a hair of tolerance so float dust never blocks an exact
            # request the caller is entitled to.
            if self._tokens + TOKEN_EPSILON >= tokens:
                self._spend_locked(tokens)
                return True
            return False

    def consume(self, tokens: float = 1) -> None:
        """
        Consume ``tokens`` or raise :class:`RateLimitExceeded`.

        Args:
            tokens: Number of tokens to consume. Must be a finite number > 0.

        Raises:
            ValueError: If ``tokens`` <= 0 or is not finite.
            RateLimitExceeded: If not enough tokens are available. Its
                ``retry_after`` reports the wait in seconds, or ``None`` when
                the request can never be satisfied.
        """
        tokens = validate_token_request(tokens)

        with self._lock:
            self._refill()
            if self._tokens + TOKEN_EPSILON >= tokens:
                self._spend_locked(tokens)
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
            tokens: Number of tokens to wait for. Must be a finite number > 0.

        Returns:
            0.0 if the tokens are already available, a positive number of
            seconds otherwise, or ``None`` if the request can never be
            satisfied (exceeds capacity, or a drained non-refilling bucket).

        Raises:
            ValueError: If ``tokens`` <= 0 or is not finite.
        """
        tokens = validate_token_request(tokens)
        with self._lock:
            self._refill()
            return self._time_until_locked(tokens)

    def _time_until_locked(self, tokens: float) -> Optional[float]:
        """Compute wait time for ``tokens``. Caller must hold the lock."""
        if self._tokens + TOKEN_EPSILON >= tokens:
            return 0.0
        if tokens > self.capacity + TOKEN_EPSILON:
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

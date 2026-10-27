"""The single-bucket core of the token-bucket algorithm."""

from __future__ import annotations

import threading
import time as _time
from typing import Callable, Optional

from src.utils.rate_limiter.errors import RateLimitExceeded
from src.utils.rate_limiter.validation import (
    TOKEN_EPSILON,
    Number,
    clamp_initial_tokens,
    validate_capacity,
    validate_refill_rate,
    validate_token_request,
)


class TokenBucket:
    """A thread-safe token bucket.

    The bucket holds up to ``capacity`` tokens and refills continuously at
    ``refill_rate`` tokens per second. Each call to :meth:`try_consume` or
    :meth:`consume` removes tokens; a request is rejected when the bucket does
    not hold enough. This permits short bursts up to ``capacity`` while
    enforcing ``refill_rate`` as the steady long-run throughput.

    Args:
        capacity: Maximum number of tokens the bucket can hold. Must be > 0.
        refill_rate: Tokens added per second. Must be >= 0; ``0`` yields a
            bucket that never refills (useful for a fixed one-time allowance).
        initial_tokens: Starting balance, clamped to ``[0, capacity]``.
            Defaults to a full bucket.
        time_func: Clock used to measure elapsed time. Defaults to
            :func:`time.monotonic`; inject a fake for deterministic tests.
    """

    def __init__(
        self,
        capacity: Number,
        refill_rate: Number,
        initial_tokens: Optional[Number] = None,
        time_func: Optional[Callable[[], float]] = None,
    ) -> None:
        self.capacity = validate_capacity(capacity)
        self.refill_rate = validate_refill_rate(refill_rate)
        self._time: Callable[[], float] = time_func or _time.monotonic
        if initial_tokens is None:
            self._tokens = self.capacity
        else:
            self._tokens = clamp_initial_tokens(initial_tokens, self.capacity)
        self._updated_at = self._time()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Add tokens accrued since the last refill. Caller must hold the lock."""
        now = self._time()
        elapsed = now - self._updated_at
        # A non-monotonic clock can step backwards; never remove tokens, just
        # advance the reference point so no future credit is lost.
        if elapsed > 0 and self.refill_rate > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        self._updated_at = now

    def _spend_locked(self, tokens: float) -> None:
        """Deduct ``tokens``, guarding against float dust below zero."""
        self._tokens -= tokens
        if self._tokens < 0:
            self._tokens = 0.0

    def available_tokens(self) -> float:
        """Current number of tokens, after accounting for refill."""
        with self._lock:
            self._refill()
            return self._tokens

    def try_consume(self, tokens: Number = 1) -> bool:
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
            if self._tokens + TOKEN_EPSILON >= tokens:
                self._spend_locked(tokens)
                return True
            return False

    def consume(self, tokens: Number = 1) -> None:
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
            available = self._tokens
            retry_after = self._time_until_locked(tokens)
        raise RateLimitExceeded(
            f"insufficient tokens: requested {tokens:g}, available {available:.6g}",
            retry_after=retry_after,
        )

    def time_until_available(self, tokens: Number = 1) -> Optional[float]:
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
            return None  # more than the bucket can ever hold
        if self.refill_rate <= 0:
            return None  # drained and never refills
        deficit = tokens - self._tokens
        return deficit / self.refill_rate

    def reset(self) -> None:
        """Refill the bucket to capacity and restart its refill clock."""
        with self._lock:
            self._tokens = self.capacity
            self._updated_at = self._time()

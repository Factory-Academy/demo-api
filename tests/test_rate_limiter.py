"""
Unit tests for the token-bucket rate limiter.

A ``FakeClock`` is used throughout so refill behavior is deterministic and the
tests never sleep on the wall clock.
"""
import pytest

from src.utils.rate_limiter import RateLimitExceeded, RateLimiter, TokenBucket


class FakeClock:
    """A manually advanced monotonic clock for deterministic tests."""

    def __init__(self, start: float = 0.0):
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestTokenBucketConstruction:
    """Validation and initial state of TokenBucket."""

    def test_starts_full_by_default(self):
        """Bucket should begin at capacity when no initial_tokens given."""
        bucket = TokenBucket(capacity=5, refill_rate=1)
        assert bucket.available_tokens == 5

    def test_respects_initial_tokens(self):
        """Explicit initial_tokens should set the starting balance."""
        # Inject a frozen clock so no wall-clock time refills the bucket
        # between construction and the read, keeping the assertion exact.
        clock = FakeClock()
        bucket = TokenBucket(capacity=5, refill_rate=1, initial_tokens=2, time_func=clock)
        assert bucket.available_tokens == 2

    def test_initial_tokens_clamped_to_capacity(self):
        """initial_tokens above capacity should clamp down to capacity."""
        bucket = TokenBucket(capacity=5, refill_rate=1, initial_tokens=100)
        assert bucket.available_tokens == 5

    def test_initial_tokens_clamped_to_zero(self):
        """Negative initial_tokens should clamp up to zero."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=5, refill_rate=1, initial_tokens=-3, time_func=clock)
        assert bucket.available_tokens == 0

    def test_zero_capacity_rejected(self):
        """Capacity of zero is invalid."""
        with pytest.raises(ValueError):
            TokenBucket(capacity=0, refill_rate=1)

    def test_negative_capacity_rejected(self):
        """Negative capacity is invalid."""
        with pytest.raises(ValueError):
            TokenBucket(capacity=-1, refill_rate=1)

    def test_negative_refill_rate_rejected(self):
        """Negative refill rate is invalid."""
        with pytest.raises(ValueError):
            TokenBucket(capacity=1, refill_rate=-1)

    def test_zero_refill_rate_allowed(self):
        """A zero refill rate is a valid fixed quota."""
        bucket = TokenBucket(capacity=3, refill_rate=0)
        assert bucket.available_tokens == 3

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_capacity_rejected(self, bad):
        """NaN/inf capacity must be rejected instead of poisoning the bucket."""
        with pytest.raises(ValueError):
            TokenBucket(capacity=bad, refill_rate=1)

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_refill_rate_rejected(self, bad):
        """NaN/inf refill rate must be rejected."""
        with pytest.raises(ValueError):
            TokenBucket(capacity=1, refill_rate=bad)

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_initial_tokens_rejected(self, bad):
        """NaN/inf initial_tokens must be rejected rather than silently clamped."""
        with pytest.raises(ValueError):
            TokenBucket(capacity=5, refill_rate=1, initial_tokens=bad)


class TestTokenBucketConsume:
    """Consuming tokens via try_consume and consume."""

    def test_try_consume_reduces_tokens(self):
        """A successful try_consume should decrement the balance."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=3, refill_rate=0, time_func=clock)
        assert bucket.try_consume() is True
        assert bucket.available_tokens == 2

    def test_try_consume_multiple_tokens(self):
        """Consuming several tokens at once should be supported."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=5, refill_rate=0, time_func=clock)
        assert bucket.try_consume(3) is True
        assert bucket.available_tokens == 2

    def test_try_consume_fails_when_empty(self):
        """try_consume should return False and not go negative."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=1, refill_rate=0, time_func=clock)
        assert bucket.try_consume() is True
        assert bucket.try_consume() is False
        assert bucket.available_tokens == 0

    def test_try_consume_exact_balance(self):
        """Consuming exactly the remaining tokens should succeed."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=2, refill_rate=0, time_func=clock)
        assert bucket.try_consume(2) is True
        assert bucket.available_tokens == 0

    def test_try_consume_more_than_available_leaves_balance(self):
        """A rejected request must not consume any tokens."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=5, refill_rate=0, time_func=clock)
        assert bucket.try_consume(6) is False
        assert bucket.available_tokens == 5

    def test_try_consume_zero_rejected(self):
        """Requesting zero tokens is invalid."""
        bucket = TokenBucket(capacity=5, refill_rate=0)
        with pytest.raises(ValueError):
            bucket.try_consume(0)

    def test_try_consume_negative_rejected(self):
        """Requesting negative tokens is invalid."""
        bucket = TokenBucket(capacity=5, refill_rate=0)
        with pytest.raises(ValueError):
            bucket.try_consume(-1)

    def test_consume_succeeds_silently(self):
        """consume should return None when tokens are available."""
        bucket = TokenBucket(capacity=2, refill_rate=0)
        assert bucket.consume(1) is None

    def test_consume_raises_when_empty(self):
        """consume should raise RateLimitExceeded when short on tokens."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=1, refill_rate=1, time_func=clock)
        bucket.consume(1)
        with pytest.raises(RateLimitExceeded):
            bucket.consume(1)

    def test_consume_zero_rejected(self):
        """consume with zero tokens is invalid."""
        bucket = TokenBucket(capacity=1, refill_rate=0)
        with pytest.raises(ValueError):
            bucket.consume(0)

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_try_consume_non_finite_rejected(self, bad):
        """A non-finite token request is invalid."""
        bucket = TokenBucket(capacity=5, refill_rate=0)
        with pytest.raises(ValueError):
            bucket.try_consume(bad)

    def test_consume_does_not_leave_negative_residue(self):
        """Float arithmetic must never drive the balance below zero."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=1, refill_rate=1, initial_tokens=0.3, time_func=clock)
        # Refill to a value that is not exactly representable, then drain it.
        clock.advance(0.7)
        assert bucket.try_consume(1) is True
        assert bucket.available_tokens >= 0.0
        assert bucket.available_tokens < TokenBucket(1, 1).capacity


class TestTokenBucketRefill:
    """Time-based refill behavior."""

    def test_refills_over_time(self):
        """Tokens should accrue at refill_rate per second."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=10, refill_rate=2, initial_tokens=0, time_func=clock)
        clock.advance(3)  # 3s * 2 tokens/s = 6 tokens
        assert bucket.available_tokens == 6

    def test_refill_does_not_exceed_capacity(self):
        """Accrued tokens should be capped at capacity."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=5, refill_rate=10, initial_tokens=0, time_func=clock)
        clock.advance(100)
        assert bucket.available_tokens == 5

    def test_partial_refill_after_consume(self):
        """After draining, the bucket should refill fractionally with time."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=4, refill_rate=1, time_func=clock)
        assert bucket.try_consume(4) is True
        assert bucket.available_tokens == 0
        clock.advance(2)
        assert bucket.available_tokens == 2

    def test_consume_succeeds_after_waiting(self):
        """A previously rejected request should succeed once refilled."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=1, refill_rate=1, time_func=clock)
        bucket.consume(1)
        with pytest.raises(RateLimitExceeded):
            bucket.consume(1)
        clock.advance(1)
        assert bucket.consume(1) is None

    def test_zero_rate_never_refills(self):
        """A zero refill rate should never restore tokens over time."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=2, refill_rate=0, time_func=clock)
        bucket.try_consume(2)
        clock.advance(1000)
        assert bucket.available_tokens == 0

    def test_clock_moving_backwards_does_not_remove_tokens(self):
        """A non-monotonic clock stepping back must not reduce the balance."""
        clock = FakeClock(start=100)
        bucket = TokenBucket(capacity=5, refill_rate=1, initial_tokens=3, time_func=clock)
        clock.now = 50  # simulate a backwards clock step
        assert bucket.available_tokens == 3

    def test_burst_then_steady_rate(self):
        """Full capacity should be spendable at once, then paced by refill."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=3, refill_rate=1, time_func=clock)
        # Burst: spend all three immediately.
        assert bucket.try_consume(3) is True
        assert bucket.try_consume(1) is False
        # Steady: one token per second thereafter.
        clock.advance(1)
        assert bucket.try_consume(1) is True
        assert bucket.try_consume(1) is False


class TestTimeUntilAvailable:
    """Wait-time estimation and retry_after reporting."""

    def test_zero_when_available(self):
        """Should report no wait when tokens are on hand."""
        bucket = TokenBucket(capacity=5, refill_rate=1)
        assert bucket.time_until_available(1) == 0.0

    def test_positive_wait_when_short(self):
        """Should report the deficit divided by the refill rate."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=4, refill_rate=2, initial_tokens=0, time_func=clock)
        # Need 3 tokens, have 0, at 2 tokens/s -> 1.5s.
        assert bucket.time_until_available(3) == pytest.approx(1.5)

    def test_none_when_exceeds_capacity(self):
        """Requesting more than capacity can never be satisfied."""
        bucket = TokenBucket(capacity=4, refill_rate=2)
        assert bucket.time_until_available(5) is None

    def test_none_when_zero_rate_and_short(self):
        """A drained fixed-quota bucket can never refill."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=2, refill_rate=0, time_func=clock)
        bucket.try_consume(2)
        assert bucket.time_until_available(1) is None

    def test_retry_after_on_exceeded(self):
        """RateLimitExceeded should carry a positive retry_after."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=2, refill_rate=2, time_func=clock)
        bucket.consume(2)
        with pytest.raises(RateLimitExceeded) as exc_info:
            bucket.consume(2)
        assert exc_info.value.retry_after == pytest.approx(1.0)

    def test_retry_after_none_when_over_capacity(self):
        """retry_after should be None when the request exceeds capacity."""
        bucket = TokenBucket(capacity=2, refill_rate=1)
        with pytest.raises(RateLimitExceeded) as exc_info:
            bucket.consume(3)
        assert exc_info.value.retry_after is None


class TestTokenBucketReset:
    """Resetting a bucket to full."""

    def test_reset_refills_to_capacity(self):
        """reset should restore the bucket to full immediately."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=5, refill_rate=0, time_func=clock)
        bucket.try_consume(5)
        assert bucket.available_tokens == 0
        bucket.reset()
        assert bucket.available_tokens == 5


class TestRateLimiter:
    """Keyed registry of buckets."""

    def test_construction_validates_capacity(self):
        """Invalid capacity should be rejected."""
        with pytest.raises(ValueError):
            RateLimiter(capacity=0, refill_rate=1)

    def test_construction_validates_refill_rate(self):
        """Negative refill rate should be rejected."""
        with pytest.raises(ValueError):
            RateLimiter(capacity=1, refill_rate=-1)

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_construction_rejects_non_finite(self, bad):
        """Non-finite capacity or refill rate should be rejected."""
        with pytest.raises(ValueError):
            RateLimiter(capacity=bad, refill_rate=1)
        with pytest.raises(ValueError):
            RateLimiter(capacity=1, refill_rate=bad)

    def test_allow_non_finite_tokens_rejected(self):
        """A non-finite token request through the registry is invalid."""
        limiter = RateLimiter(capacity=5, refill_rate=0)
        with pytest.raises(ValueError):
            limiter.allow("user-a", tokens=float("inf"))

    def test_allow_consumes_per_key(self):
        """allow should return True until a key's bucket is drained."""
        clock = FakeClock()
        limiter = RateLimiter(capacity=2, refill_rate=0, time_func=clock)
        assert limiter.allow("user-a") is True
        assert limiter.allow("user-a") is True
        assert limiter.allow("user-a") is False

    def test_keys_are_independent(self):
        """One key's usage should not affect another key."""
        clock = FakeClock()
        limiter = RateLimiter(capacity=1, refill_rate=0, time_func=clock)
        assert limiter.allow("user-a") is True
        assert limiter.allow("user-a") is False
        # A different key still has a full, independent bucket.
        assert limiter.allow("user-b") is True

    def test_same_bucket_reused_for_key(self):
        """Repeated access to a key should reuse the same bucket instance."""
        limiter = RateLimiter(capacity=1, refill_rate=1)
        first = limiter._bucket_for("k")
        second = limiter._bucket_for("k")
        assert first is second

    def test_check_raises_with_key(self):
        """check should raise RateLimitExceeded tagged with the key."""
        clock = FakeClock()
        limiter = RateLimiter(capacity=1, refill_rate=1, time_func=clock)
        limiter.check("user-a")
        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.check("user-a")
        assert exc_info.value.key == "user-a"
        assert exc_info.value.retry_after == pytest.approx(1.0)

    def test_allow_multiple_tokens(self):
        """allow should support consuming several tokens at once."""
        clock = FakeClock()
        limiter = RateLimiter(capacity=5, refill_rate=0, time_func=clock)
        assert limiter.allow("user-a", tokens=5) is True
        assert limiter.allow("user-a", tokens=1) is False

    def test_tokens_remaining(self):
        """tokens_remaining should reflect consumption for a key."""
        clock = FakeClock()
        limiter = RateLimiter(capacity=3, refill_rate=0, time_func=clock)
        limiter.allow("user-a", tokens=2)
        assert limiter.tokens_remaining("user-a") == 1

    def test_tokens_remaining_for_new_key_is_full(self):
        """A never-seen key should report a full bucket."""
        limiter = RateLimiter(capacity=3, refill_rate=0)
        assert limiter.tokens_remaining("fresh") == 3

    def test_reset_single_key(self):
        """Resetting one key should refill only that key."""
        clock = FakeClock()
        limiter = RateLimiter(capacity=2, refill_rate=0, time_func=clock)
        limiter.allow("user-a", tokens=2)
        limiter.allow("user-b", tokens=1)
        limiter.reset("user-a")
        assert limiter.tokens_remaining("user-a") == 2
        assert limiter.tokens_remaining("user-b") == 1

    def test_reset_all_keys(self):
        """Resetting with no key should clear every bucket."""
        clock = FakeClock()
        limiter = RateLimiter(capacity=2, refill_rate=0, time_func=clock)
        limiter.allow("user-a", tokens=2)
        limiter.allow("user-b", tokens=2)
        limiter.reset()
        assert limiter.tokens_remaining("user-a") == 2
        assert limiter.tokens_remaining("user-b") == 2

    def test_reset_unknown_key_is_noop(self):
        """Resetting a key that was never used should not error."""
        limiter = RateLimiter(capacity=2, refill_rate=0)
        limiter.reset("never-seen")  # should not raise

    def test_refill_shared_across_keys(self):
        """The shared clock should refill each key's bucket over time."""
        clock = FakeClock()
        limiter = RateLimiter(capacity=1, refill_rate=1, time_func=clock)
        assert limiter.allow("user-a") is True
        assert limiter.allow("user-a") is False
        clock.advance(1)
        assert limiter.allow("user-a") is True

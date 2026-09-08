"""
Focused tests for the rate limiter's tightened edge-case handling.

Two properties are exercised here that the broader behavior suite in
``test_rate_limiter.py`` does not target directly:

1. Non-finite numbers (``NaN``, ``+/-inf``) are rejected everywhere a rate or a
   token count is accepted, so a bad value can never silently poison a bucket.
2. Floating-point accumulation never wrongly rejects an exact request nor
   drives a balance below zero, thanks to the shared ``TOKEN_EPSILON`` slack.
"""
import pytest

from src.utils.rate_limiter import RateLimiter, RateLimitExceeded, TokenBucket
from src.utils.rate_limiter.validation import (
    TOKEN_EPSILON,
    clamp_initial_tokens,
    validate_capacity,
    validate_refill_rate,
    validate_token_request,
)

NON_FINITE = [float("nan"), float("inf"), float("-inf")]


class FakeClock:
    """A manually advanced monotonic clock for deterministic tests."""

    def __init__(self, start: float = 0.0):
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestValidationHelpers:
    """The shared numeric guardrails used by both classes."""

    def test_validate_capacity_returns_float(self):
        """A valid capacity is coerced to float and returned."""
        assert validate_capacity(5) == 5.0
        assert isinstance(validate_capacity(5), float)

    @pytest.mark.parametrize("value", [0, -1, -0.5])
    def test_validate_capacity_rejects_non_positive(self, value):
        """Capacity must be strictly positive."""
        with pytest.raises(ValueError):
            validate_capacity(value)

    @pytest.mark.parametrize("bad", NON_FINITE)
    def test_validate_capacity_rejects_non_finite(self, bad):
        """NaN/inf capacity is rejected with a clear message."""
        with pytest.raises(ValueError, match="finite"):
            validate_capacity(bad)

    def test_validate_refill_rate_allows_zero(self):
        """A zero refill rate is a valid fixed quota."""
        assert validate_refill_rate(0) == 0.0

    def test_validate_refill_rate_rejects_negative(self):
        """A negative refill rate is invalid."""
        with pytest.raises(ValueError):
            validate_refill_rate(-0.1)

    @pytest.mark.parametrize("bad", NON_FINITE)
    def test_validate_refill_rate_rejects_non_finite(self, bad):
        """NaN/inf refill rate is rejected."""
        with pytest.raises(ValueError, match="finite"):
            validate_refill_rate(bad)

    @pytest.mark.parametrize("value", [0, -1])
    def test_validate_token_request_rejects_non_positive(self, value):
        """A token request must be strictly positive."""
        with pytest.raises(ValueError):
            validate_token_request(value)

    @pytest.mark.parametrize("bad", NON_FINITE)
    def test_validate_token_request_rejects_non_finite(self, bad):
        """NaN/inf token request is rejected."""
        with pytest.raises(ValueError, match="finite"):
            validate_token_request(bad)

    def test_clamp_initial_tokens_within_range(self):
        """A value inside [0, capacity] is returned unchanged."""
        assert clamp_initial_tokens(3, 5) == 3.0

    def test_clamp_initial_tokens_above_capacity(self):
        """A value above capacity clamps down to capacity."""
        assert clamp_initial_tokens(100, 5) == 5.0

    def test_clamp_initial_tokens_below_zero(self):
        """A negative value clamps up to zero."""
        assert clamp_initial_tokens(-3, 5) == 0.0

    @pytest.mark.parametrize("bad", NON_FINITE)
    def test_clamp_initial_tokens_rejects_non_finite(self, bad):
        """A non-finite starting balance is rejected outright, not clamped."""
        with pytest.raises(ValueError, match="finite"):
            clamp_initial_tokens(bad, 5)


class TestTokenBucketNonFinite:
    """Non-finite inputs are rejected across the TokenBucket surface."""

    @pytest.mark.parametrize("bad", NON_FINITE)
    def test_time_until_available_rejects_non_finite(self, bad):
        """time_until_available validates its token argument."""
        bucket = TokenBucket(capacity=5, refill_rate=1)
        with pytest.raises(ValueError):
            bucket.time_until_available(bad)

    @pytest.mark.parametrize("bad", NON_FINITE)
    def test_consume_rejects_non_finite(self, bad):
        """consume validates its token argument."""
        bucket = TokenBucket(capacity=5, refill_rate=1)
        with pytest.raises(ValueError):
            bucket.consume(bad)


class TestFloatingPointTolerance:
    """Rounding dust must not change accept/reject decisions."""

    def test_exact_request_succeeds_despite_float_dust(self):
        """A balance a hair under the request should still be spendable."""
        clock = FakeClock()
        # 0.1/s for 9.9999999999s lands just short of 1.0 token.
        bucket = TokenBucket(capacity=10, refill_rate=0.1, initial_tokens=0, time_func=clock)
        clock.advance(9.9999999999)
        assert bucket.available_tokens < 1.0
        assert bucket.try_consume(1) is True

    def test_time_until_available_treats_near_capacity_as_feasible(self):
        """A request a hair over capacity from float dust stays feasible."""
        bucket = TokenBucket(capacity=3, refill_rate=1)
        assert bucket.time_until_available(3 + TOKEN_EPSILON / 2) == 0.0

    def test_request_clearly_over_capacity_is_infeasible(self):
        """A request meaningfully above capacity can never be satisfied."""
        bucket = TokenBucket(capacity=3, refill_rate=1)
        assert bucket.time_until_available(3.5) is None

    def test_repeated_fractional_consume_never_goes_negative(self):
        """Draining in fractional steps must not underflow the balance."""
        clock = FakeClock()
        bucket = TokenBucket(capacity=1, refill_rate=0, initial_tokens=0.9, time_func=clock)
        assert bucket.try_consume(0.3) is True
        assert bucket.try_consume(0.3) is True
        assert bucket.try_consume(0.3) is True
        assert bucket.available_tokens >= 0.0
        # The tiny remainder is not enough for another 0.3.
        assert bucket.try_consume(0.3) is False


class TestRateLimiterNonFinite:
    """The keyed registry rejects non-finite requests too."""

    @pytest.mark.parametrize("bad", NON_FINITE)
    def test_check_rejects_non_finite(self, bad):
        """check validates its token argument before touching a bucket."""
        limiter = RateLimiter(capacity=5, refill_rate=1)
        with pytest.raises(ValueError):
            limiter.check("user-a", tokens=bad)

    def test_rejected_check_does_not_consume(self):
        """A validation error must not have spent any tokens."""
        limiter = RateLimiter(capacity=5, refill_rate=0)
        with pytest.raises(ValueError):
            limiter.check("user-a", tokens=float("nan"))
        assert limiter.tokens_remaining("user-a") == 5

    def test_reset_after_clear_all_is_safe(self):
        """Resetting a single key after clearing every bucket is a no-op."""
        limiter = RateLimiter(capacity=2, refill_rate=0)
        limiter.allow("user-a")
        limiter.reset()  # drop all buckets
        limiter.reset("user-a")  # bucket no longer tracked; must not raise
        assert limiter.tokens_remaining("user-a") == 2

    def test_over_capacity_check_reports_no_retry(self):
        """A per-key request above capacity carries retry_after=None."""
        limiter = RateLimiter(capacity=2, refill_rate=1)
        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.check("user-a", tokens=3)
        assert exc_info.value.key == "user-a"
        assert exc_info.value.retry_after is None

import math
import threading

import pytest

from src.utils.rate_limiter import (
    TOKEN_EPSILON,
    RateLimiter,
    RateLimitExceeded,
    TokenBucket,
)
from src.utils.rate_limiter.validation import (
    clamp_initial_tokens,
    validate_capacity,
    validate_refill_rate,
    validate_token_request,
)


class FakeClock:
    """A manually advanced monotonic clock for deterministic time control."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = float(start)

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


# ---------------------------------------------------------------------------
# TokenBucket: construction and validation
# ---------------------------------------------------------------------------


def test_bucket_starts_full_by_default():
    bucket = TokenBucket(capacity=10, refill_rate=1)
    assert bucket.available_tokens() == 10


def test_bucket_respects_initial_tokens():
    bucket = TokenBucket(capacity=10, refill_rate=1, initial_tokens=3)
    assert bucket.available_tokens() == 3


def test_bucket_clamps_initial_tokens_into_range():
    assert TokenBucket(10, 1, initial_tokens=-5).available_tokens() == 0
    assert TokenBucket(10, 1, initial_tokens=99).available_tokens() == 10


@pytest.mark.parametrize("bad_capacity", [0, -1, -0.5])
def test_bucket_rejects_non_positive_capacity(bad_capacity):
    with pytest.raises(ValueError, match="capacity must be greater than 0"):
        TokenBucket(capacity=bad_capacity, refill_rate=1)


def test_bucket_rejects_negative_refill_rate():
    with pytest.raises(ValueError, match="refill_rate must not be negative"):
        TokenBucket(capacity=1, refill_rate=-1)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_bucket_rejects_non_finite_capacity(bad):
    with pytest.raises(ValueError, match="finite"):
        TokenBucket(capacity=bad, refill_rate=1)


def test_nan_capacity_is_rejected_not_silently_accepted():
    # NaN compares False against every threshold; the finite guard must catch it
    # before it poisons the bucket's balance.
    with pytest.raises(ValueError):
        TokenBucket(capacity=math.nan, refill_rate=1)


# ---------------------------------------------------------------------------
# TokenBucket: consuming
# ---------------------------------------------------------------------------


def test_try_consume_succeeds_until_drained():
    bucket = TokenBucket(capacity=3, refill_rate=0)
    assert bucket.try_consume() is True
    assert bucket.try_consume() is True
    assert bucket.try_consume() is True
    assert bucket.try_consume() is False


def test_try_consume_multiple_tokens():
    bucket = TokenBucket(capacity=10, refill_rate=0)
    assert bucket.try_consume(4) is True
    assert bucket.available_tokens() == 6
    assert bucket.try_consume(7) is False  # not enough, balance unchanged
    assert bucket.available_tokens() == 6


def test_consume_exact_capacity_in_one_shot():
    bucket = TokenBucket(capacity=5, refill_rate=0)
    bucket.consume(5)
    assert bucket.available_tokens() == 0


@pytest.mark.parametrize("bad", [0, -1, math.nan, math.inf])
def test_consume_rejects_invalid_token_counts(bad):
    bucket = TokenBucket(capacity=5, refill_rate=1)
    with pytest.raises(ValueError):
        bucket.try_consume(bad)
    with pytest.raises(ValueError):
        bucket.consume(bad)


def test_consume_raises_when_empty_with_retry_after():
    clock = FakeClock()
    bucket = TokenBucket(capacity=2, refill_rate=2, time_func=clock)
    bucket.consume(2)
    with pytest.raises(RateLimitExceeded) as excinfo:
        bucket.consume(1)
    # Need 1 token at 2 tokens/sec -> 0.5s.
    assert excinfo.value.retry_after == pytest.approx(0.5)
    assert excinfo.value.key is None


def test_consume_request_above_capacity_can_never_succeed():
    bucket = TokenBucket(capacity=5, refill_rate=1)
    with pytest.raises(RateLimitExceeded) as excinfo:
        bucket.consume(6)
    assert excinfo.value.retry_after is None


def test_drained_non_refilling_bucket_reports_no_retry():
    bucket = TokenBucket(capacity=2, refill_rate=0)
    bucket.consume(2)
    assert bucket.time_until_available(1) is None
    with pytest.raises(RateLimitExceeded) as excinfo:
        bucket.consume(1)
    assert excinfo.value.retry_after is None


# ---------------------------------------------------------------------------
# TokenBucket: refill behavior over time
# ---------------------------------------------------------------------------


def test_tokens_refill_over_time():
    clock = FakeClock()
    bucket = TokenBucket(capacity=10, refill_rate=5, initial_tokens=0, time_func=clock)
    assert bucket.available_tokens() == 0
    clock.advance(1)
    assert bucket.available_tokens() == pytest.approx(5)
    clock.advance(0.5)
    assert bucket.available_tokens() == pytest.approx(7.5)


def test_refill_never_exceeds_capacity():
    clock = FakeClock()
    bucket = TokenBucket(capacity=10, refill_rate=5, initial_tokens=0, time_func=clock)
    clock.advance(1000)
    assert bucket.available_tokens() == 10


def test_sustained_rate_matches_refill_rate():
    clock = FakeClock()
    bucket = TokenBucket(capacity=1, refill_rate=1, initial_tokens=1, time_func=clock)
    allowed = 0
    for _ in range(10):
        if bucket.try_consume(1):
            allowed += 1
        clock.advance(1)  # one token restored each tick
    # Started full (1), then 1/sec for 10 ticks.
    assert allowed == 11


def test_burst_then_steady_rate():
    clock = FakeClock()
    bucket = TokenBucket(capacity=5, refill_rate=1, time_func=clock)
    # Burst: capacity-sized spike allowed immediately.
    assert all(bucket.try_consume(1) for _ in range(5))
    assert bucket.try_consume(1) is False
    # Steady: one token per second thereafter.
    clock.advance(3)
    assert sum(bucket.try_consume(1) for _ in range(5)) == 3


def test_clock_moving_backwards_never_adds_tokens():
    clock = FakeClock(start=100)
    bucket = TokenBucket(capacity=5, refill_rate=1, initial_tokens=2, time_func=clock)
    clock.advance(-50)  # misbehaving clock steps back
    assert bucket.available_tokens() == 2


def test_time_until_available_zero_when_ready():
    bucket = TokenBucket(capacity=5, refill_rate=1)
    assert bucket.time_until_available(3) == 0.0


def test_time_until_available_positive_when_short():
    clock = FakeClock()
    bucket = TokenBucket(capacity=5, refill_rate=2, initial_tokens=0, time_func=clock)
    assert bucket.time_until_available(3) == pytest.approx(1.5)


def test_reset_refills_to_capacity():
    clock = FakeClock()
    bucket = TokenBucket(capacity=5, refill_rate=0, time_func=clock)
    bucket.consume(5)
    assert bucket.available_tokens() == 0
    bucket.reset()
    assert bucket.available_tokens() == 5


def test_fractional_tokens_and_epsilon_boundary():
    clock = FakeClock()
    bucket = TokenBucket(capacity=1, refill_rate=1, initial_tokens=0, time_func=clock)
    clock.advance(1)  # exactly one token, modulo float dust
    # A request for exactly the available balance must not be rejected by
    # floating-point error.
    assert bucket.try_consume(1) is True


def test_epsilon_is_small_and_positive():
    assert 0 < TOKEN_EPSILON < 1e-6


# ---------------------------------------------------------------------------
# TokenBucket: thread safety
# ---------------------------------------------------------------------------


def test_concurrent_consume_never_oversells():
    bucket = TokenBucket(capacity=1000, refill_rate=0)
    successes = []
    lock = threading.Lock()

    def worker():
        count = 0
        for _ in range(500):
            if bucket.try_consume(1):
                count += 1
        with lock:
            successes.append(count)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 8 threads * 500 attempts = 4000 attempts against 1000 tokens.
    assert sum(successes) == 1000
    assert bucket.available_tokens() == 0


# ---------------------------------------------------------------------------
# RateLimiter: per-key behavior
# ---------------------------------------------------------------------------


def test_limiter_isolates_keys():
    limiter = RateLimiter(capacity=2, refill_rate=0)
    assert limiter.allow("alice") is True
    assert limiter.allow("alice") is True
    assert limiter.allow("alice") is False
    # bob has his own untouched bucket.
    assert limiter.allow("bob") is True


def test_limiter_check_raises_with_key_attached():
    limiter = RateLimiter(capacity=1, refill_rate=0)
    limiter.check("acct-7")
    with pytest.raises(RateLimitExceeded) as excinfo:
        limiter.check("acct-7")
    assert excinfo.value.key == "acct-7"


def test_limiter_tokens_remaining_creates_full_bucket():
    limiter = RateLimiter(capacity=4, refill_rate=0)
    assert limiter.tokens_remaining("new-key") == 4


def test_limiter_refills_per_key_over_time():
    clock = FakeClock()
    limiter = RateLimiter(capacity=2, refill_rate=1, time_func=clock)
    assert limiter.allow("u1") is True
    assert limiter.allow("u1") is True
    assert limiter.allow("u1") is False
    clock.advance(1)
    assert limiter.allow("u1") is True


def test_limiter_reset_single_key():
    limiter = RateLimiter(capacity=1, refill_rate=0)
    assert limiter.allow("k") is True
    assert limiter.allow("k") is False
    limiter.reset("k")
    assert limiter.allow("k") is True


def test_limiter_reset_all_keys():
    limiter = RateLimiter(capacity=1, refill_rate=0)
    limiter.allow("a")
    limiter.allow("b")
    limiter.reset()
    assert limiter.tokens_remaining("a") == 1
    assert limiter.tokens_remaining("b") == 1


def test_limiter_reset_unknown_key_is_noop():
    limiter = RateLimiter(capacity=1, refill_rate=0)
    limiter.reset("never-seen")  # must not raise


def test_limiter_validates_config():
    with pytest.raises(ValueError):
        RateLimiter(capacity=0, refill_rate=1)
    with pytest.raises(ValueError):
        RateLimiter(capacity=1, refill_rate=-1)


def test_limiter_allow_validates_token_count():
    limiter = RateLimiter(capacity=5, refill_rate=1)
    with pytest.raises(ValueError):
        limiter.allow("k", 0)


# ---------------------------------------------------------------------------
# validation helpers (direct unit coverage)
# ---------------------------------------------------------------------------


def test_validate_capacity_returns_float():
    assert validate_capacity(5) == 5.0
    assert isinstance(validate_capacity(5), float)


def test_validate_refill_rate_allows_zero():
    assert validate_refill_rate(0) == 0.0


def test_validate_token_request_rejects_zero():
    with pytest.raises(ValueError):
        validate_token_request(0)


def test_clamp_initial_tokens_bounds():
    assert clamp_initial_tokens(-1, 10) == 0.0
    assert clamp_initial_tokens(5, 10) == 5.0
    assert clamp_initial_tokens(50, 10) == 10.0

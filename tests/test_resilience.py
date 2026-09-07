"""
Unit tests for the resilience primitives.

Timing and randomness are injected everywhere so these tests run instantly and
deterministically, with the single exception of the thread-based timeout test,
which uses a very short real delay.
"""
import pytest

from src.utils.resilience import (
    BackoffPolicy,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    ResilienceTimeoutError,
    RetryError,
    resilient,
    retry_with_backoff,
)


def no_sleep(_delay):
    """Sleep replacement that records nothing and returns immediately."""


class FakeClock:
    """Manually advanceable monotonic clock."""

    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestBackoffPolicy:
    def test_exponential_growth_without_jitter(self):
        policy = BackoffPolicy(base_delay=1.0, multiplier=2.0, max_delay=100.0, jitter=False)
        assert policy.compute_delay(0) == 1.0
        assert policy.compute_delay(1) == 2.0
        assert policy.compute_delay(2) == 4.0
        assert policy.compute_delay(3) == 8.0

    def test_delay_is_capped_at_max(self):
        policy = BackoffPolicy(base_delay=1.0, multiplier=10.0, max_delay=5.0, jitter=False)
        assert policy.compute_delay(5) == 5.0

    def test_zero_base_delay_returns_zero(self):
        policy = BackoffPolicy(base_delay=0.0, max_delay=0.0, jitter=True)
        assert policy.compute_delay(3) == 0.0

    def test_jitter_stays_within_bounds(self):
        policy = BackoffPolicy(base_delay=1.0, multiplier=2.0, max_delay=100.0, jitter=True)
        # Full-jitter draws from [0, capped]; force the extremes.
        assert policy.compute_delay(2, random_fn=lambda lo, hi: lo) == 0.0
        assert policy.compute_delay(2, random_fn=lambda lo, hi: hi) == 4.0

    def test_negative_attempt_rejected(self):
        with pytest.raises(ValueError):
            BackoffPolicy().compute_delay(-1)


class TestRetryWithBackoff:
    def test_returns_immediately_on_success(self):
        calls = {"n": 0}

        def op():
            calls["n"] += 1
            return "ok"

        assert retry_with_backoff(op, sleep=no_sleep) == "ok"
        assert calls["n"] == 1

    def test_succeeds_after_transient_failures(self):
        calls = {"n": 0}

        def op():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ValueError("flaky")
            return "ok"

        result = retry_with_backoff(
            op, retries=3, retry_on=(ValueError,), sleep=no_sleep
        )
        assert result == "ok"
        assert calls["n"] == 3

    def test_raises_retry_error_when_exhausted(self):
        original = ValueError("still broken")

        def op():
            raise original

        with pytest.raises(RetryError) as exc_info:
            retry_with_backoff(op, retries=2, retry_on=(ValueError,), sleep=no_sleep)
        assert exc_info.value.last_exception is original
        assert exc_info.value.__cause__ is original

    def test_attempt_count_matches_retries_plus_one(self):
        calls = {"n": 0}

        def op():
            calls["n"] += 1
            raise RuntimeError("boom")

        with pytest.raises(RetryError):
            retry_with_backoff(op, retries=4, retry_on=(RuntimeError,), sleep=no_sleep)
        assert calls["n"] == 5

    def test_non_retryable_exception_propagates_without_retry(self):
        calls = {"n": 0}

        def op():
            calls["n"] += 1
            raise KeyError("unexpected")

        with pytest.raises(KeyError):
            retry_with_backoff(op, retries=3, retry_on=(ValueError,), sleep=no_sleep)
        assert calls["n"] == 1

    def test_on_retry_callback_receives_attempt_and_delay(self):
        events = []

        def op():
            raise ValueError("x")

        policy = BackoffPolicy(base_delay=1.0, multiplier=2.0, jitter=False)
        with pytest.raises(RetryError):
            retry_with_backoff(
                op,
                retries=2,
                retry_on=(ValueError,),
                policy=policy,
                on_retry=lambda attempt, exc, delay: events.append((attempt, delay)),
                sleep=no_sleep,
            )
        assert events == [(1, 1.0), (2, 2.0)]

    def test_sleep_called_with_backoff_delays(self):
        slept = []

        def op():
            raise ValueError("x")

        policy = BackoffPolicy(base_delay=1.0, multiplier=3.0, jitter=False)
        with pytest.raises(RetryError):
            retry_with_backoff(
                op,
                retries=2,
                retry_on=(ValueError,),
                policy=policy,
                sleep=slept.append,
            )
        assert slept == [1.0, 3.0]

    def test_negative_retries_rejected(self):
        with pytest.raises(ValueError):
            retry_with_backoff(lambda: None, retries=-1)


class TestTimeout:
    def test_timeout_raises_and_is_retryable(self):
        import time

        calls = {"n": 0}

        def slow_then_fast():
            calls["n"] += 1
            if calls["n"] == 1:
                time.sleep(0.2)  # exceeds the timeout on the first attempt
            return "done"

        result = retry_with_backoff(
            slow_then_fast,
            retries=1,
            timeout=0.05,
            retry_on=(ResilienceTimeoutError,),
            sleep=no_sleep,
        )
        assert result == "done"
        assert calls["n"] == 2

    def test_timeout_disabled_when_none(self):
        assert retry_with_backoff(lambda: 42, timeout=None, sleep=no_sleep) == 42


class TestCircuitBreaker:
    def test_starts_closed(self):
        assert CircuitBreaker().state is CircuitState.CLOSED

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.before_call()
            cb.record_failure()
        assert cb.state is CircuitState.OPEN

    def test_open_circuit_rejects_calls(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.before_call()
        cb.record_failure()
        with pytest.raises(CircuitBreakerOpenError):
            cb.before_call()

    def test_success_resets_failure_count_while_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.before_call()
        cb.record_failure()
        cb.before_call()
        cb.record_failure()
        cb.before_call()
        cb.record_success()  # resets the streak
        cb.before_call()
        cb.record_failure()
        assert cb.state is CircuitState.CLOSED

    def test_transitions_to_half_open_after_recovery_timeout(self):
        clock = FakeClock()
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0, clock=clock)
        cb.before_call()
        cb.record_failure()
        assert cb.state is CircuitState.OPEN
        clock.advance(10.0)
        assert cb.state is CircuitState.HALF_OPEN

    def test_half_open_success_closes_circuit(self):
        clock = FakeClock()
        cb = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=5.0,
            success_threshold=1,
            clock=clock,
        )
        cb.before_call()
        cb.record_failure()
        clock.advance(5.0)
        cb.before_call()  # trial call in half-open
        cb.record_success()
        assert cb.state is CircuitState.CLOSED

    def test_half_open_failure_reopens_circuit(self):
        clock = FakeClock()
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0, clock=clock)
        cb.before_call()
        cb.record_failure()
        clock.advance(5.0)
        cb.before_call()
        cb.record_failure()
        assert cb.state is CircuitState.OPEN

    def test_half_open_limits_trial_calls(self):
        clock = FakeClock()
        cb = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=5.0,
            half_open_max_calls=1,
            clock=clock,
        )
        cb.before_call()
        cb.record_failure()
        clock.advance(5.0)
        cb.before_call()  # consumes the single trial slot
        with pytest.raises(CircuitBreakerOpenError):
            cb.before_call()

    def test_reset_returns_to_closed(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.before_call()
        cb.record_failure()
        assert cb.state is CircuitState.OPEN
        cb.reset()
        assert cb.state is CircuitState.CLOSED

    def test_invalid_thresholds_rejected(self):
        with pytest.raises(ValueError):
            CircuitBreaker(failure_threshold=0)
        with pytest.raises(ValueError):
            CircuitBreaker(success_threshold=0)
        with pytest.raises(ValueError):
            CircuitBreaker(half_open_max_calls=0)


class TestRetryWithBreaker:
    def test_open_breaker_short_circuits_without_retrying(self):
        cb = CircuitBreaker(failure_threshold=2)
        calls = {"n": 0}

        def op():
            calls["n"] += 1
            raise ValueError("dependency down")

        # First call: 3 attempts trip the breaker at the 2nd failure... breaker
        # opens mid-run and the next attempt is rejected.
        with pytest.raises((RetryError, CircuitBreakerOpenError)):
            retry_with_backoff(
                op, retries=5, retry_on=(ValueError,), breaker=cb, sleep=no_sleep
            )
        assert cb.state is CircuitState.OPEN

        calls_before = calls["n"]
        # Subsequent call is rejected immediately, func is never invoked.
        with pytest.raises(CircuitBreakerOpenError):
            retry_with_backoff(
                op, retries=5, retry_on=(ValueError,), breaker=cb, sleep=no_sleep
            )
        assert calls["n"] == calls_before

    def test_breaker_open_error_is_not_retried(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.before_call()
        cb.record_failure()  # breaker now open

        def op():
            raise AssertionError("should never be called")

        with pytest.raises(CircuitBreakerOpenError):
            retry_with_backoff(
                op, retries=5, retry_on=(Exception,), breaker=cb, sleep=no_sleep
            )


class TestResilientDecorator:
    def test_decorator_retries_and_returns(self):
        calls = {"n": 0}

        @resilient(retries=3, retry_on=(ValueError,), sleep=no_sleep)
        def flaky(x):
            calls["n"] += 1
            if calls["n"] < 2:
                raise ValueError("later")
            return x * 2

        assert flaky(21) == 42
        assert calls["n"] == 2

    def test_decorator_shares_breaker_across_calls(self):
        cb = CircuitBreaker(failure_threshold=2)

        @resilient(retries=0, retry_on=(ValueError,), breaker=cb, sleep=no_sleep)
        def always_fails():
            raise ValueError("nope")

        with pytest.raises(RetryError):
            always_fails()
        with pytest.raises(RetryError):
            always_fails()
        assert cb.state is CircuitState.OPEN
        with pytest.raises(CircuitBreakerOpenError):
            always_fails()

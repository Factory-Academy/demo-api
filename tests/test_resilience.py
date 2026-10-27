import pytest

from src.utils.resilience import (
    BackoffPolicy,
    CallTimeoutError,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    RetryError,
    RetryPolicy,
    resilient,
    retry_call,
)


class FakeClock:
    """A monotonic clock whose value only advances when told to."""

    def __init__(self) -> None:
        self._now = 0.0

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


class RecordingSleep:
    """A drop-in for time.sleep that records delays instead of waiting."""

    def __init__(self) -> None:
        self.delays: list = []

    def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


def _no_jitter(base_delay=0.1, factor=2.0, max_delay=30.0):
    return BackoffPolicy(base_delay=base_delay, factor=factor, max_delay=max_delay, jitter=False)


# --- Backoff -----------------------------------------------------------------


def test_backoff_grows_exponentially_without_jitter():
    backoff = _no_jitter(base_delay=0.1, factor=2.0)

    assert backoff.compute_delay(1) == pytest.approx(0.1)
    assert backoff.compute_delay(2) == pytest.approx(0.2)
    assert backoff.compute_delay(3) == pytest.approx(0.4)
    assert backoff.compute_delay(4) == pytest.approx(0.8)


def test_backoff_is_capped_at_max_delay():
    backoff = _no_jitter(base_delay=1.0, factor=10.0, max_delay=5.0)

    assert backoff.compute_delay(1) == pytest.approx(1.0)
    assert backoff.compute_delay(2) == pytest.approx(5.0)
    assert backoff.compute_delay(10) == pytest.approx(5.0)


def test_backoff_jitter_stays_within_equal_jitter_bounds():
    backoff = BackoffPolicy(base_delay=1.0, factor=1.0, max_delay=10.0, jitter=True)

    low = backoff.compute_delay(1, rng=lambda: 0.0)
    high = backoff.compute_delay(1, rng=lambda: 1.0)

    # Equal jitter: half the delay plus up to the other half.
    assert low == pytest.approx(0.5)
    assert high == pytest.approx(1.0)


def test_backoff_rejects_invalid_config():
    with pytest.raises(ValueError, match="base_delay must be non-negative"):
        BackoffPolicy(base_delay=-1.0)
    with pytest.raises(ValueError, match="factor must be at least 1"):
        BackoffPolicy(factor=0.5)
    with pytest.raises(ValueError, match="max_delay must be non-negative"):
        BackoffPolicy(max_delay=-1.0)


def test_backoff_rejects_bad_attempt():
    with pytest.raises(ValueError, match="attempt must be at least 1"):
        BackoffPolicy().compute_delay(0)


# --- Retry -------------------------------------------------------------------


def test_retry_returns_immediately_on_success():
    calls = {"n": 0}

    def ok() -> str:
        calls["n"] += 1
        return "value"

    assert retry_call(ok) == "value"
    assert calls["n"] == 1


def test_retry_succeeds_after_transient_failures():
    calls = {"n": 0}
    sleep = RecordingSleep()

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("boom")
        return "ok"

    policy = RetryPolicy(max_attempts=5, backoff=_no_jitter(), retryable_exceptions=(ValueError,))
    assert retry_call(flaky, policy=policy, sleep=sleep) == "ok"
    assert calls["n"] == 3
    assert len(sleep.delays) == 2


def test_retry_raises_retry_error_after_exhaustion():
    calls = {"n": 0}

    def always_fails() -> None:
        calls["n"] += 1
        raise ValueError("nope")

    policy = RetryPolicy(max_attempts=3, backoff=_no_jitter(), retryable_exceptions=(ValueError,))
    with pytest.raises(RetryError) as exc_info:
        retry_call(always_fails, policy=policy, sleep=lambda _: None)

    assert calls["n"] == 3
    assert exc_info.value.attempts == 3
    assert isinstance(exc_info.value.last_error, ValueError)
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_retry_does_not_retry_non_retryable_exception():
    calls = {"n": 0}

    def boom() -> None:
        calls["n"] += 1
        raise KeyError("fatal")

    policy = RetryPolicy(max_attempts=5, backoff=_no_jitter(), retryable_exceptions=(ValueError,))
    with pytest.raises(KeyError):
        retry_call(boom, policy=policy, sleep=lambda _: None)

    assert calls["n"] == 1


def test_retry_passes_through_args_and_kwargs():
    def add(a, b, c=0):
        return a + b + c

    assert retry_call(add, 1, 2, c=3) == 6


def test_retry_invokes_on_retry_callback():
    calls = {"n": 0}
    observed: list = []

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("x")
        return "ok"

    def on_retry(attempt, error, delay):
        observed.append((attempt, type(error).__name__, delay))

    policy = RetryPolicy(max_attempts=5, backoff=_no_jitter(), retryable_exceptions=(RuntimeError,))
    retry_call(flaky, policy=policy, sleep=lambda _: None, on_retry=on_retry)

    assert [a for a, _, _ in observed] == [1, 2]
    assert all(name == "RuntimeError" for _, name, _ in observed)


def test_retry_rejects_invalid_policy():
    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        RetryPolicy(max_attempts=0)
    with pytest.raises(ValueError, match="timeout must be positive when set"):
        RetryPolicy(timeout=0)
    with pytest.raises(ValueError, match="retryable_exceptions must not be empty"):
        RetryPolicy(retryable_exceptions=())


# --- Timeout -----------------------------------------------------------------


def test_timeout_raises_and_is_retried():
    import threading

    calls = {"n": 0}

    def slow_then_fast() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            threading.Event().wait(1.0)
        return "done"

    policy = RetryPolicy(max_attempts=3, backoff=_no_jitter(), timeout=0.05)
    assert retry_call(slow_then_fast, policy=policy, sleep=lambda _: None) == "done"
    assert calls["n"] == 2


def test_timeout_exhaustion_wraps_call_timeout_error():
    import threading

    def always_slow() -> None:
        threading.Event().wait(1.0)

    policy = RetryPolicy(max_attempts=2, backoff=_no_jitter(), timeout=0.05)
    with pytest.raises(RetryError) as exc_info:
        retry_call(always_slow, policy=policy, sleep=lambda _: None)

    assert isinstance(exc_info.value.last_error, CallTimeoutError)


def test_timeout_retried_even_with_narrow_retryable_set():
    import threading

    calls = {"n": 0}

    def slow_then_fast() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            threading.Event().wait(1.0)
        return "ok"

    # A timeout is retried even though the policy only lists ValueError.
    policy = RetryPolicy(
        max_attempts=3, backoff=_no_jitter(), retryable_exceptions=(ValueError,), timeout=0.05
    )
    assert retry_call(slow_then_fast, policy=policy, sleep=lambda _: None) == "ok"
    assert calls["n"] == 2


# --- Circuit breaker ---------------------------------------------------------


def test_breaker_opens_after_threshold():
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0, time_func=FakeClock())

    for _ in range(2):
        assert breaker.allow() is True
        breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED

    assert breaker.allow() is True
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow() is False


def test_breaker_success_resets_failure_count():
    breaker = CircuitBreaker(failure_threshold=3, time_func=FakeClock())

    breaker.record_failure()
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()
    breaker.record_failure()

    # Only two consecutive failures since the reset, so still closed.
    assert breaker.state == CircuitState.CLOSED


def test_breaker_transitions_to_half_open_after_recovery():
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0, time_func=clock)

    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN

    clock.advance(5.0)
    assert breaker.state == CircuitState.HALF_OPEN


def test_breaker_closes_after_successful_probe():
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0, time_func=clock)

    breaker.record_failure()
    clock.advance(5.0)

    assert breaker.allow() is True  # probe slot
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED


def test_breaker_reopens_after_failed_probe():
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0, time_func=clock)

    breaker.record_failure()
    clock.advance(5.0)

    assert breaker.allow() is True  # probe slot
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN


def test_breaker_retry_after_counts_down():
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0, time_func=clock)

    breaker.record_failure()
    assert breaker.retry_after() == pytest.approx(10.0)

    clock.advance(4.0)
    assert breaker.retry_after() == pytest.approx(6.0)


def test_breaker_rejects_invalid_config():
    with pytest.raises(ValueError, match="failure_threshold must be at least 1"):
        CircuitBreaker(failure_threshold=0)
    with pytest.raises(ValueError, match="recovery_timeout must be non-negative"):
        CircuitBreaker(recovery_timeout=-1.0)
    with pytest.raises(ValueError, match="half_open_max_calls must be at least 1"):
        CircuitBreaker(half_open_max_calls=0)
    with pytest.raises(ValueError, match="success_threshold must be at least 1"):
        CircuitBreaker(success_threshold=0)


# --- Breaker + retry_call integration ----------------------------------------


def test_open_breaker_rejects_without_calling_func():
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0, time_func=FakeClock())
    breaker.record_failure()  # trip it

    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        return "x"

    with pytest.raises(CircuitBreakerOpenError) as exc_info:
        retry_call(fn, circuit_breaker=breaker, sleep=lambda _: None)

    assert calls["n"] == 0
    assert exc_info.value.retry_after == pytest.approx(10.0)


def test_breaker_opens_through_retry_call():
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0, time_func=FakeClock())
    policy = RetryPolicy(max_attempts=3, backoff=_no_jitter(), retryable_exceptions=(ValueError,))

    def always_fails() -> None:
        raise ValueError("down")

    with pytest.raises(RetryError):
        retry_call(always_fails, policy=policy, circuit_breaker=breaker, sleep=lambda _: None)

    assert breaker.state == CircuitState.OPEN


def test_breaker_recovers_via_retry_call():
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0, time_func=clock)
    breaker.record_failure()  # open
    clock.advance(5.0)

    result = retry_call(lambda: "recovered", circuit_breaker=breaker, sleep=lambda _: None)

    assert result == "recovered"
    assert breaker.state == CircuitState.CLOSED


# --- Decorator ---------------------------------------------------------------


def test_resilient_decorator_retries_and_preserves_metadata():
    calls = {"n": 0}
    policy = RetryPolicy(max_attempts=5, backoff=_no_jitter(), retryable_exceptions=(ValueError,))

    @resilient(policy=policy, sleep=lambda _: None)
    def flaky(x):
        """docstring stays put"""
        calls["n"] += 1
        if calls["n"] < 2:
            raise ValueError("retry me")
        return x * 2

    assert flaky(21) == 42
    assert flaky.__name__ == "flaky"
    assert flaky.__doc__ == "docstring stays put"


def test_resilient_decorator_shares_breaker_across_calls():
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=10.0, time_func=FakeClock())
    policy = RetryPolicy(max_attempts=1, backoff=_no_jitter(), retryable_exceptions=(ValueError,))

    @resilient(policy=policy, circuit_breaker=breaker, sleep=lambda _: None)
    def fail():
        raise ValueError("x")

    with pytest.raises(RetryError):
        fail()
    with pytest.raises(RetryError):
        fail()

    assert breaker.state == CircuitState.OPEN

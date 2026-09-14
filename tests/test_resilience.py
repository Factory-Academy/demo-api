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
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class RecordingSleep:
    """A drop-in for time.sleep that records delays instead of waiting."""

    def __init__(self) -> None:
        self.delays = []

    def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


# --------------------------------------------------------------------------- #
# BackoffPolicy
# --------------------------------------------------------------------------- #

def test_backoff_grows_exponentially_without_jitter():
    policy = BackoffPolicy(base_delay=0.1, factor=2.0, max_delay=100.0, jitter=False)
    assert policy.compute_delay(1) == pytest.approx(0.1)
    assert policy.compute_delay(2) == pytest.approx(0.2)
    assert policy.compute_delay(3) == pytest.approx(0.4)


def test_backoff_is_capped_at_max_delay():
    policy = BackoffPolicy(base_delay=1.0, factor=10.0, max_delay=5.0, jitter=False)
    assert policy.compute_delay(5) == 5.0


def test_backoff_jitter_stays_within_equal_jitter_bounds():
    policy = BackoffPolicy(base_delay=1.0, factor=2.0, max_delay=100.0, jitter=True)
    base = 1.0 * 2.0 ** (3 - 1)  # 4.0
    lo = base / 2
    hi = base
    for rng_value in (0.0, 0.5, 0.999999):
        delay = policy.compute_delay(3, rng=lambda: rng_value)
        assert lo <= delay <= hi


def test_backoff_rejects_invalid_config():
    with pytest.raises(ValueError):
        BackoffPolicy(base_delay=-1)
    with pytest.raises(ValueError):
        BackoffPolicy(factor=0.5)
    with pytest.raises(ValueError):
        BackoffPolicy(max_delay=-0.1)


def test_backoff_rejects_bad_attempt():
    with pytest.raises(ValueError):
        BackoffPolicy().compute_delay(0)


# --------------------------------------------------------------------------- #
# retry_call
# --------------------------------------------------------------------------- #

def test_retry_returns_immediately_on_success():
    calls = {"n": 0}

    def ok():
        calls["n"] += 1
        return "value"

    assert retry_call(ok) == "value"
    assert calls["n"] == 1


def test_retry_succeeds_after_transient_failures():
    calls = {"n": 0}
    sleep = RecordingSleep()

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("boom")
        return "ok"

    policy = RetryPolicy(
        max_attempts=3,
        backoff=BackoffPolicy(base_delay=0.1, factor=2.0, jitter=False),
    )
    assert retry_call(flaky, policy=policy, sleep=sleep) == "ok"
    assert calls["n"] == 3
    # Two failures -> two backoff sleeps of 0.1 and 0.2.
    assert sleep.delays == [pytest.approx(0.1), pytest.approx(0.2)]


def test_retry_raises_retry_error_after_exhaustion():
    calls = {"n": 0}

    def always_fails():
        calls["n"] += 1
        raise ValueError("nope")

    policy = RetryPolicy(max_attempts=2, backoff=BackoffPolicy(jitter=False))
    with pytest.raises(RetryError) as exc_info:
        retry_call(always_fails, policy=policy, sleep=lambda _: None)

    assert calls["n"] == 2
    assert exc_info.value.attempts == 2
    assert isinstance(exc_info.value.last_error, ValueError)
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_retry_does_not_retry_non_retryable_exception():
    calls = {"n": 0}

    def boom():
        calls["n"] += 1
        raise KeyError("fatal")

    policy = RetryPolicy(max_attempts=5, retryable_exceptions=(RuntimeError,))
    with pytest.raises(KeyError):
        retry_call(boom, policy=policy, sleep=lambda _: None)
    assert calls["n"] == 1


def test_retry_passes_through_args_and_kwargs():
    def add(a, b, c=0):
        return a + b + c

    assert retry_call(add, 1, 2, c=3) == 6


def test_retry_invokes_on_retry_callback():
    events = []

    def flaky():
        raise RuntimeError("x")

    def on_retry(attempt, error, delay):
        events.append((attempt, type(error).__name__, delay))

    policy = RetryPolicy(
        max_attempts=3,
        backoff=BackoffPolicy(base_delay=0.1, factor=2.0, jitter=False),
    )
    with pytest.raises(RetryError):
        retry_call(flaky, policy=policy, sleep=lambda _: None, on_retry=on_retry)

    # Callback fires only between attempts, so max_attempts - 1 times.
    assert events == [
        (1, "RuntimeError", pytest.approx(0.1)),
        (2, "RuntimeError", pytest.approx(0.2)),
    ]


def test_retry_rejects_invalid_policy():
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)
    with pytest.raises(ValueError):
        RetryPolicy(timeout=0)
    with pytest.raises(ValueError):
        RetryPolicy(retryable_exceptions=())


# --------------------------------------------------------------------------- #
# timeout handling
# --------------------------------------------------------------------------- #

def test_timeout_raises_and_is_retried():
    import time as real_time

    calls = {"n": 0}

    def slow_then_fast():
        calls["n"] += 1
        if calls["n"] == 1:
            real_time.sleep(0.3)  # exceeds the 0.05s timeout
        return "done"

    policy = RetryPolicy(
        max_attempts=2,
        timeout=0.05,
        backoff=BackoffPolicy(base_delay=0, jitter=False),
    )
    assert retry_call(slow_then_fast, policy=policy, sleep=lambda _: None) == "done"
    assert calls["n"] == 2


def test_timeout_exhaustion_wraps_call_timeout_error():
    import time as real_time

    def always_slow():
        real_time.sleep(0.2)

    policy = RetryPolicy(
        max_attempts=2,
        timeout=0.02,
        backoff=BackoffPolicy(base_delay=0, jitter=False),
    )
    with pytest.raises(RetryError) as exc_info:
        retry_call(always_slow, policy=policy, sleep=lambda _: None)
    assert isinstance(exc_info.value.last_error, CallTimeoutError)


def test_timeout_retried_even_with_narrow_retryable_set():
    import time as real_time

    calls = {"n": 0}

    def slow_then_fast():
        calls["n"] += 1
        if calls["n"] == 1:
            real_time.sleep(0.2)
        return "ok"

    # retryable_exceptions deliberately excludes timeouts; the helper must still
    # treat CallTimeoutError as retryable.
    policy = RetryPolicy(
        max_attempts=2,
        timeout=0.02,
        retryable_exceptions=(RuntimeError,),
        backoff=BackoffPolicy(base_delay=0, jitter=False),
    )
    assert retry_call(slow_then_fast, policy=policy, sleep=lambda _: None) == "ok"
    assert calls["n"] == 2


# --------------------------------------------------------------------------- #
# CircuitBreaker
# --------------------------------------------------------------------------- #

def test_breaker_opens_after_threshold():
    breaker = CircuitBreaker(failure_threshold=3)
    assert breaker.state == CircuitState.CLOSED
    for _ in range(3):
        assert breaker.allow()
        breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow() is False


def test_breaker_success_resets_failure_count():
    breaker = CircuitBreaker(failure_threshold=3)
    breaker.allow(); breaker.record_failure()
    breaker.allow(); breaker.record_failure()
    breaker.allow(); breaker.record_success()  # resets the streak
    breaker.allow(); breaker.record_failure()
    breaker.allow(); breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED


def test_breaker_transitions_to_half_open_after_recovery():
    clock = FakeClock()
    breaker = CircuitBreaker(
        failure_threshold=1, recovery_timeout=5.0, time_func=clock
    )
    breaker.allow(); breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow() is False

    clock.advance(5.0)
    assert breaker.state == CircuitState.HALF_OPEN
    assert breaker.allow() is True  # first probe admitted
    assert breaker.allow() is False  # only one probe at a time


def test_breaker_closes_after_successful_probe():
    clock = FakeClock()
    breaker = CircuitBreaker(
        failure_threshold=1, recovery_timeout=1.0, time_func=clock
    )
    breaker.allow(); breaker.record_failure()
    clock.advance(1.0)
    assert breaker.allow() is True
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED


def test_breaker_reopens_after_failed_probe():
    clock = FakeClock()
    breaker = CircuitBreaker(
        failure_threshold=1, recovery_timeout=1.0, time_func=clock
    )
    breaker.allow(); breaker.record_failure()
    clock.advance(1.0)
    assert breaker.allow() is True
    breaker.record_failure()  # probe fails
    assert breaker.state == CircuitState.OPEN


def test_breaker_retry_after_counts_down():
    clock = FakeClock()
    breaker = CircuitBreaker(
        failure_threshold=1, recovery_timeout=10.0, time_func=clock
    )
    breaker.allow(); breaker.record_failure()
    assert breaker.retry_after() == pytest.approx(10.0)
    clock.advance(4.0)
    assert breaker.retry_after() == pytest.approx(6.0)


def test_breaker_rejects_invalid_config():
    with pytest.raises(ValueError):
        CircuitBreaker(failure_threshold=0)
    with pytest.raises(ValueError):
        CircuitBreaker(recovery_timeout=-1)
    with pytest.raises(ValueError):
        CircuitBreaker(half_open_max_calls=0)
    with pytest.raises(ValueError):
        CircuitBreaker(success_threshold=0)


# --------------------------------------------------------------------------- #
# retry_call + CircuitBreaker integration
# --------------------------------------------------------------------------- #

def test_open_breaker_rejects_without_calling_func():
    breaker = CircuitBreaker(failure_threshold=1)
    breaker.allow(); breaker.record_failure()  # open it

    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        return "x"

    with pytest.raises(CircuitBreakerOpenError):
        retry_call(fn, circuit_breaker=breaker, sleep=lambda _: None)
    assert calls["n"] == 0


def test_breaker_opens_through_retry_call():
    breaker = CircuitBreaker(failure_threshold=2)

    def always_fails():
        raise RuntimeError("down")

    policy = RetryPolicy(max_attempts=3, backoff=BackoffPolicy(jitter=False))
    # Attempts 1 and 2 fail and trip the breaker; attempt 3 is then rejected
    # up front, so the call ends as a circuit-open error rather than a retry
    # exhaustion.
    with pytest.raises(CircuitBreakerOpenError):
        retry_call(always_fails, policy=policy, circuit_breaker=breaker, sleep=lambda _: None)
    assert breaker.state == CircuitState.OPEN


def test_breaker_recovers_via_retry_call():
    clock = FakeClock()
    breaker = CircuitBreaker(
        failure_threshold=1, recovery_timeout=1.0, time_func=clock
    )
    breaker.allow(); breaker.record_failure()  # open

    clock.advance(1.0)  # now half-open on next check
    assert retry_call(lambda: "recovered", circuit_breaker=breaker, sleep=lambda _: None) == "recovered"
    assert breaker.state == CircuitState.CLOSED


# --------------------------------------------------------------------------- #
# resilient decorator
# --------------------------------------------------------------------------- #

def test_resilient_decorator_retries_and_preserves_metadata():
    calls = {"n": 0}

    @resilient(
        policy=RetryPolicy(max_attempts=3, backoff=BackoffPolicy(jitter=False)),
        sleep=lambda _: None,
    )
    def flaky(x):
        """docstring stays put"""
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("retry me")
        return x * 2

    assert flaky(21) == 42
    assert calls["n"] == 2
    assert flaky.__name__ == "flaky"
    assert flaky.__doc__ == "docstring stays put"


def test_resilient_decorator_shares_breaker_across_calls():
    breaker = CircuitBreaker(failure_threshold=2)

    @resilient(
        policy=RetryPolicy(max_attempts=1),
        circuit_breaker=breaker,
        sleep=lambda _: None,
    )
    def fail():
        raise RuntimeError("x")

    with pytest.raises(RetryError):
        fail()
    with pytest.raises(RetryError):
        fail()
    # Two separate invocations each recorded a failure -> breaker now open.
    assert breaker.state == CircuitState.OPEN
    with pytest.raises(CircuitBreakerOpenError):
        fail()

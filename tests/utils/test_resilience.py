"""Tests for the retry-with-backoff + circuit-breaker utilities.

These tests avoid real time: a fake monotonic clock drives the circuit
breaker's recovery window and a recording ``sleep`` captures backoff delays
without actually waiting.
"""

import random

import pytest

from src.utils.resilience import (
    BackoffPolicy,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    CircuitState,
    RetryError,
    RetryPolicy,
    resilient,
    retry_call,
)


class FakeClock:
    """A deterministic monotonic clock."""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


class RecordingSleep:
    """A ``sleep`` replacement that records the delays it was asked for."""

    def __init__(self, clock: FakeClock = None) -> None:
        self.delays = []
        self._clock = clock

    def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)
        if self._clock is not None:
            self._clock.advance(seconds)


# --------------------------------------------------------------------------- #
# BackoffPolicy
# --------------------------------------------------------------------------- #

def test_backoff_exponential_growth_and_cap():
    policy = BackoffPolicy(base_delay=1.0, max_delay=10.0, multiplier=2.0, jitter=False)
    delays = [policy.compute(attempt) for attempt in range(1, 6)]
    assert delays == [1.0, 2.0, 4.0, 8.0, 10.0]


def test_backoff_full_jitter_stays_within_bounds():
    policy = BackoffPolicy(base_delay=1.0, max_delay=100.0, multiplier=2.0, jitter=True)
    rng = random.Random(1234)
    for attempt in range(1, 8):
        ceiling = min(1.0 * 2 ** (attempt - 1), 100.0)
        delay = policy.compute(attempt, rng=rng)
        assert 0.0 <= delay <= ceiling


def test_backoff_requires_positive_attempt():
    policy = BackoffPolicy(jitter=False)
    with pytest.raises(ValueError):
        policy.compute(0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"base_delay": -1.0},
        {"base_delay": 5.0, "max_delay": 1.0},
        {"multiplier": 0.5},
    ],
)
def test_backoff_validates_configuration(kwargs):
    with pytest.raises(ValueError):
        BackoffPolicy(**kwargs)


# --------------------------------------------------------------------------- #
# CircuitBreaker
# --------------------------------------------------------------------------- #

def make_breaker(clock, **cfg):
    defaults = dict(failure_threshold=2, recovery_timeout=5.0, half_open_max_calls=1)
    defaults.update(cfg)
    return CircuitBreaker("test", CircuitBreakerConfig(**defaults), clock=clock)


def test_breaker_opens_after_threshold():
    clock = FakeClock()
    breaker = make_breaker(clock, failure_threshold=2)

    breaker.acquire()
    breaker.record_failure()
    assert breaker.state is CircuitState.CLOSED

    breaker.acquire()
    breaker.record_failure()
    assert breaker.state is CircuitState.OPEN


def test_breaker_rejects_calls_while_open():
    clock = FakeClock()
    breaker = make_breaker(clock, failure_threshold=1)
    breaker.acquire()
    breaker.record_failure()

    with pytest.raises(CircuitOpenError) as excinfo:
        breaker.acquire()
    assert excinfo.value.name == "test"
    assert 0 < excinfo.value.retry_after <= 5.0


def test_breaker_success_resets_failure_count_while_closed():
    clock = FakeClock()
    breaker = make_breaker(clock, failure_threshold=3)
    breaker.acquire()
    breaker.record_failure()
    assert breaker.failure_count == 1
    breaker.acquire()
    breaker.record_success()
    assert breaker.failure_count == 0
    assert breaker.state is CircuitState.CLOSED


def test_breaker_half_opens_after_recovery_timeout():
    clock = FakeClock()
    breaker = make_breaker(clock, failure_threshold=1, recovery_timeout=5.0)
    breaker.acquire()
    breaker.record_failure()
    assert breaker.state is CircuitState.OPEN

    clock.advance(4.9)
    assert breaker.state is CircuitState.OPEN
    clock.advance(0.1)
    assert breaker.state is CircuitState.HALF_OPEN


def test_breaker_half_open_limits_trial_calls():
    clock = FakeClock()
    breaker = make_breaker(clock, failure_threshold=1, half_open_max_calls=1)
    breaker.acquire()
    breaker.record_failure()
    clock.advance(5.0)
    assert breaker.state is CircuitState.HALF_OPEN

    breaker.acquire()  # reserve the single trial slot
    with pytest.raises(CircuitOpenError):
        breaker.acquire()


def test_breaker_half_open_success_closes():
    clock = FakeClock()
    breaker = make_breaker(clock, failure_threshold=1)
    breaker.acquire()
    breaker.record_failure()
    clock.advance(5.0)
    breaker.acquire()
    breaker.record_success()
    assert breaker.state is CircuitState.CLOSED
    assert breaker.failure_count == 0


def test_breaker_half_open_failure_reopens():
    clock = FakeClock()
    breaker = make_breaker(clock, failure_threshold=1)
    breaker.acquire()
    breaker.record_failure()
    clock.advance(5.0)
    breaker.acquire()
    breaker.record_failure()
    assert breaker.state is CircuitState.OPEN


def test_breaker_reset_forces_closed():
    clock = FakeClock()
    breaker = make_breaker(clock, failure_threshold=1)
    breaker.acquire()
    breaker.record_failure()
    assert breaker.state is CircuitState.OPEN
    breaker.reset()
    assert breaker.state is CircuitState.CLOSED
    assert breaker.failure_count == 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"failure_threshold": 0},
        {"recovery_timeout": -1.0},
        {"half_open_max_calls": 0},
    ],
)
def test_breaker_config_validation(kwargs):
    with pytest.raises(ValueError):
        CircuitBreakerConfig(**kwargs)


# --------------------------------------------------------------------------- #
# retry_call
# --------------------------------------------------------------------------- #

def test_retry_returns_on_first_success():
    calls = {"n": 0}

    def ok():
        calls["n"] += 1
        return "done"

    sleep = RecordingSleep()
    assert retry_call(ok, sleep=sleep) == "done"
    assert calls["n"] == 1
    assert sleep.delays == []


def test_retry_recovers_after_transient_failures():
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise TimeoutError("transient")
        return "ok"

    sleep = RecordingSleep()
    policy = RetryPolicy(max_attempts=5, backoff=BackoffPolicy(base_delay=1.0, jitter=False))
    assert retry_call(flaky, policy=policy, sleep=sleep) == "ok"
    assert attempts["n"] == 3
    assert sleep.delays == [1.0, 2.0]


def test_retry_exhausts_and_raises_retry_error():
    def always_fail():
        raise ConnectionError("down")

    sleep = RecordingSleep()
    policy = RetryPolicy(max_attempts=3, backoff=BackoffPolicy(jitter=False))
    with pytest.raises(RetryError) as excinfo:
        retry_call(always_fail, policy=policy, sleep=sleep)
    assert excinfo.value.attempts == 3
    assert isinstance(excinfo.value.last_exception, ConnectionError)
    # Delay only happens between attempts, so two sleeps for three attempts.
    assert len(sleep.delays) == 2


def test_retry_does_not_retry_unexpected_exception():
    calls = {"n": 0}

    def boom():
        calls["n"] += 1
        raise ValueError("programmer error")

    policy = RetryPolicy(max_attempts=5, retry_on=(TimeoutError,))
    with pytest.raises(ValueError):
        retry_call(boom, policy=policy, sleep=RecordingSleep())
    assert calls["n"] == 1


def test_retry_give_up_on_takes_precedence():
    class SpecificError(Exception):
        pass

    def raise_specific():
        raise SpecificError()

    policy = RetryPolicy(
        max_attempts=5,
        retry_on=(SpecificError,),
        give_up_on=(SpecificError,),
    )
    with pytest.raises(SpecificError):
        retry_call(raise_specific, policy=policy, sleep=RecordingSleep())


def test_retry_honours_deadline_budget():
    clock = FakeClock()
    sleep = RecordingSleep(clock)
    calls = {"n": 0}

    def slow_fail():
        calls["n"] += 1
        raise TimeoutError()

    policy = RetryPolicy(
        max_attempts=100,
        deadline=3.0,
        backoff=BackoffPolicy(base_delay=1.0, jitter=False),
    )
    with pytest.raises(RetryError):
        retry_call(slow_fail, policy=policy, sleep=sleep, clock=clock)

    assert calls["n"] < 100
    assert clock.t <= 3.0 + 1.0  # last partial wait is clamped to the budget


def test_retry_records_breaker_success_on_recovery():
    clock = FakeClock()
    breaker = CircuitBreaker(
        "svc", CircuitBreakerConfig(failure_threshold=5, recovery_timeout=100.0), clock=clock
    )
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise TimeoutError()
        return "ok"

    policy = RetryPolicy(max_attempts=3, backoff=BackoffPolicy(base_delay=0, jitter=False))
    assert retry_call(flaky, policy=policy, breaker=breaker, sleep=RecordingSleep()) == "ok"
    # One failure then a success resets the count back to zero.
    assert breaker.failure_count == 0
    assert breaker.state is CircuitState.CLOSED


def test_retry_fails_fast_when_breaker_trips_mid_retry():
    clock = FakeClock()
    breaker = CircuitBreaker(
        "svc", CircuitBreakerConfig(failure_threshold=1, recovery_timeout=100.0), clock=clock
    )

    def always_down():
        raise TimeoutError()

    policy = RetryPolicy(max_attempts=5, backoff=BackoffPolicy(base_delay=0, jitter=False))
    # First attempt fails and trips the breaker; the second acquire is rejected.
    with pytest.raises(CircuitOpenError):
        retry_call(always_down, policy=policy, breaker=breaker, sleep=RecordingSleep())
    assert breaker.state is CircuitState.OPEN


def test_retry_does_not_count_non_retryable_against_breaker():
    clock = FakeClock()
    breaker = CircuitBreaker(
        "svc", CircuitBreakerConfig(failure_threshold=1, recovery_timeout=100.0), clock=clock
    )

    def client_error():
        raise ValueError("bad request")

    policy = RetryPolicy(max_attempts=3, retry_on=(TimeoutError,))
    with pytest.raises(ValueError):
        retry_call(client_error, policy=policy, breaker=breaker, sleep=RecordingSleep())
    assert breaker.state is CircuitState.CLOSED
    assert breaker.failure_count == 0


# --------------------------------------------------------------------------- #
# resilient decorator
# --------------------------------------------------------------------------- #

def test_resilient_decorator_retries_and_preserves_metadata():
    attempts = {"n": 0}

    @resilient(
        policy=RetryPolicy(max_attempts=3, backoff=BackoffPolicy(base_delay=0, jitter=False)),
        sleep=lambda _: None,
    )
    def fetch(value):
        """Docstring kept by functools.wraps."""
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise TimeoutError()
        return value * 2

    assert fetch(21) == 42
    assert attempts["n"] == 2
    assert fetch.__name__ == "fetch"
    assert fetch.__doc__ == "Docstring kept by functools.wraps."


def test_resilient_decorator_shares_breaker_state_across_calls():
    breaker = CircuitBreaker(
        "svc", CircuitBreakerConfig(failure_threshold=2, recovery_timeout=100.0)
    )

    @resilient(
        policy=RetryPolicy(max_attempts=1, retry_on=(TimeoutError,)),
        breaker=breaker,
        sleep=lambda _: None,
    )
    def unstable():
        raise TimeoutError()

    with pytest.raises(RetryError):
        unstable()
    assert breaker.state is CircuitState.CLOSED  # one failure, threshold is two
    with pytest.raises(RetryError):
        unstable()
    assert breaker.state is CircuitState.OPEN  # second failure trips it

import pytest

from src.clients.status_notifier import StatusNotifier, UpstreamError
from src.utils.resilience import (
    BackoffPolicy,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    RetryError,
    RetryPolicy,
)


def _fast_policy(max_attempts=3):
    # No real waiting: tiny backoff and no per-attempt timeout.
    return RetryPolicy(
        max_attempts=max_attempts,
        backoff=BackoffPolicy(base_delay=0.0, factor=1.0, max_delay=0.0, jitter=False),
        retryable_exceptions=(UpstreamError,),
    )


class ScriptedTransport:
    """A transport that yields queued outcomes; exceptions are raised."""

    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.calls = []

    def __call__(self, path, payload):
        self.calls.append((path, payload))
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_notify_returns_payload_on_success():
    transport = ScriptedTransport([{"status": "ok"}])
    notifier = StatusNotifier(transport, policy=_fast_policy(), sleep=lambda _: None)

    result = notifier.notify(1, "active")

    assert result == {"status": "ok"}
    assert transport.calls == [("/notifications", {"item_id": 1, "status": "active"})]


def test_notify_retries_transient_failures_then_succeeds():
    transport = ScriptedTransport([UpstreamError("503"), UpstreamError("503"), {"status": "ok"}])
    notifier = StatusNotifier(transport, policy=_fast_policy(), sleep=lambda _: None)

    result = notifier.notify(7, "archived")

    assert result == {"status": "ok"}
    assert len(transport.calls) == 3
    assert notifier.circuit_state == CircuitState.CLOSED


def test_notify_raises_retry_error_when_all_attempts_fail():
    transport = ScriptedTransport([UpstreamError("a"), UpstreamError("b"), UpstreamError("c")])
    notifier = StatusNotifier(transport, policy=_fast_policy(), sleep=lambda _: None)

    with pytest.raises(RetryError) as exc_info:
        notifier.notify(2, "active")

    assert isinstance(exc_info.value.last_error, UpstreamError)
    assert len(transport.calls) == 3


def test_notify_does_not_retry_unexpected_errors():
    transport = ScriptedTransport([ValueError("bad payload")])
    notifier = StatusNotifier(transport, policy=_fast_policy(), sleep=lambda _: None)

    with pytest.raises(ValueError):
        notifier.notify(3, "active")

    assert len(transport.calls) == 1


def test_breaker_opens_after_sustained_upstream_failure():
    transport = ScriptedTransport([UpstreamError("down")] * 10)
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=30.0)
    notifier = StatusNotifier(
        transport, policy=_fast_policy(max_attempts=1), circuit_breaker=breaker, sleep=lambda _: None
    )

    with pytest.raises(RetryError):
        notifier.notify(1, "active")
    with pytest.raises(RetryError):
        notifier.notify(1, "active")

    # Breaker is now open: the next call is rejected without hitting the transport.
    call_count = len(transport.calls)
    with pytest.raises(CircuitBreakerOpenError):
        notifier.notify(1, "active")

    assert notifier.circuit_state == CircuitState.OPEN
    assert len(transport.calls) == call_count


def test_default_configuration_is_usable():
    transport = ScriptedTransport([{"status": "ok"}])
    notifier = StatusNotifier(transport, sleep=lambda _: None)

    assert notifier.notify(1, "active") == {"status": "ok"}
    assert notifier.circuit_state == CircuitState.CLOSED

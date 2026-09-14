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
    return RetryPolicy(
        max_attempts=max_attempts,
        backoff=BackoffPolicy(base_delay=0, jitter=False),
        retryable_exceptions=(UpstreamError,),
    )


class ScriptedTransport:
    """A transport that yields queued outcomes; exceptions are raised."""

    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.calls = []

    def __call__(self, path, payload=None):
        self.calls.append((path, payload))
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_notify_returns_payload_on_success():
    transport = ScriptedTransport([{"ok": True}])
    notifier = StatusNotifier(
        transport, policy=_fast_policy(), sleep=lambda _: None
    )
    result = notifier.notify(1, "active")
    assert result == {"ok": True}
    assert transport.calls == [("/notifications", {"item_id": 1, "status": "active"})]


def test_notify_retries_transient_failures_then_succeeds():
    transport = ScriptedTransport([UpstreamError("503"), UpstreamError("503"), {"ok": True}])
    notifier = StatusNotifier(
        transport, policy=_fast_policy(), sleep=lambda _: None
    )
    assert notifier.notify(7, "closed") == {"ok": True}
    assert len(transport.calls) == 3


def test_notify_raises_retry_error_when_all_attempts_fail():
    transport = ScriptedTransport([UpstreamError("a"), UpstreamError("b")])
    notifier = StatusNotifier(
        transport, policy=_fast_policy(max_attempts=2), sleep=lambda _: None
    )
    with pytest.raises(RetryError) as exc_info:
        notifier.notify(1, "active")
    assert isinstance(exc_info.value.last_error, UpstreamError)


def test_notify_does_not_retry_unexpected_errors():
    transport = ScriptedTransport([ValueError("bad payload")])
    notifier = StatusNotifier(
        transport, policy=_fast_policy(max_attempts=3), sleep=lambda _: None
    )
    with pytest.raises(ValueError):
        notifier.notify(1, "active")
    assert len(transport.calls) == 1


def test_breaker_opens_after_sustained_upstream_failure():
    transport = ScriptedTransport([UpstreamError("down")] * 10)
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    notifier = StatusNotifier(
        transport,
        policy=_fast_policy(max_attempts=1),
        circuit_breaker=breaker,
        sleep=lambda _: None,
    )

    # Each notify makes a single attempt and records one failure.
    with pytest.raises(RetryError):
        notifier.notify(1, "active")
    with pytest.raises(RetryError):
        notifier.notify(1, "active")
    with pytest.raises(RetryError):
        notifier.notify(1, "active")

    assert notifier.circuit_state == CircuitState.OPEN

    # Further calls short-circuit without touching the transport.
    calls_before = len(transport.calls)
    with pytest.raises(CircuitBreakerOpenError):
        notifier.notify(1, "active")
    assert len(transport.calls) == calls_before


def test_default_configuration_is_usable():
    transport = ScriptedTransport([{"ok": True}])
    notifier = StatusNotifier(transport, sleep=lambda _: None)
    assert notifier.notify(1, "active") == {"ok": True}
    assert notifier.circuit_state == CircuitState.CLOSED

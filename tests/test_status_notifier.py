"""
Tests for StatusNotifier, exercising the resilience wiring with an injected
in-memory transport (no real network calls).
"""
import pytest

from src.clients.status_notifier import (
    NotifierClientError,
    NotifierUnavailableError,
    StatusNotifier,
)
from src.utils.resilience import (
    BackoffPolicy,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    RetryError,
)

# No-delay backoff so retries do not sleep during tests.
NO_DELAY = BackoffPolicy(base_delay=0.0, max_delay=0.0, jitter=False)


def make_notifier(sender, **kwargs):
    kwargs.setdefault("policy", NO_DELAY)
    return StatusNotifier("https://downstream.example/hooks", sender=sender, **kwargs)


def test_notify_success_returns_transport_result():
    sent = []

    def sender(payload):
        sent.append(payload)
        return 200

    notifier = make_notifier(sender)
    result = notifier.notify_status_change(7, "closed", updated_by="alice")

    assert result == 200
    assert sent == [{"entity_id": 7, "status": "closed", "updated_by": "alice"}]


def test_notify_retries_transient_failures_then_succeeds():
    calls = {"n": 0}

    def sender(payload):
        calls["n"] += 1
        if calls["n"] < 3:
            raise NotifierUnavailableError("503")
        return 200

    notifier = make_notifier(sender, retries=3)
    assert notifier.notify_status_change(1, "active") == 200
    assert calls["n"] == 3


def test_notify_client_error_is_not_retried():
    calls = {"n": 0}

    def sender(payload):
        calls["n"] += 1
        raise NotifierClientError("400 bad payload")

    notifier = make_notifier(sender, retries=3)
    with pytest.raises(NotifierClientError):
        notifier.notify_status_change(1, "active")
    assert calls["n"] == 1


def test_notify_raises_retry_error_when_transient_failures_persist():
    def sender(payload):
        raise NotifierUnavailableError("still down")

    # Use a large failure threshold so retries exhaust before the breaker trips.
    breaker = CircuitBreaker(failure_threshold=99)
    notifier = make_notifier(sender, retries=2, breaker=breaker)
    with pytest.raises(RetryError):
        notifier.notify_status_change(1, "active")


def test_circuit_opens_after_repeated_failures():
    def sender(payload):
        raise NotifierUnavailableError("down")

    breaker = CircuitBreaker(failure_threshold=2)
    notifier = make_notifier(sender, retries=0, breaker=breaker)

    with pytest.raises(RetryError):
        notifier.notify_status_change(1, "active")
    with pytest.raises(RetryError):
        notifier.notify_status_change(2, "active")

    assert breaker.state is CircuitState.OPEN
    # Once open, calls are rejected before the transport is touched.
    with pytest.raises(CircuitBreakerOpenError):
        notifier.notify_status_change(3, "active")

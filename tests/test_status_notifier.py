"""Tests for the StatusNotifierClient and its resilience wiring.

These use ``httpx.MockTransport`` so no real network calls happen. The retry
policy is overridden with a zero-delay, jitter-free backoff so the tests run
without sleeping.
"""

import httpx
import pytest

from src.clients.status_notifier import (
    NotifierConfig,
    NotifierRejectedError,
    NotifierUnavailableError,
    StatusNotifierClient,
)
from src.utils.resilience import (
    BackoffPolicy,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    RetryPolicy,
)


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


class ScriptedTransport:
    """An httpx handler driven by a queue of scripted actions.

    Each action is either an ``int`` status code to return or an ``Exception``
    instance to raise (to simulate a transport-level failure). The last action
    repeats once the queue is drained.
    """

    def __init__(self, actions):
        self._actions = list(actions)
        self.requests = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        action = self._actions.pop(0) if len(self._actions) > 1 else self._actions[0]
        if isinstance(action, Exception):
            raise action
        return httpx.Response(action, json={"received": True})

    @property
    def call_count(self) -> int:
        return len(self.requests)


def make_client(actions, *, breaker=None, max_attempts=3, retry_on=None, give_up_on=None):
    handler = ScriptedTransport(actions)
    policy = RetryPolicy(
        max_attempts=max_attempts,
        backoff=BackoffPolicy(base_delay=0.0, jitter=False),
        retry_on=retry_on or (NotifierUnavailableError,),
        give_up_on=give_up_on or (NotifierRejectedError,),
    )
    client = StatusNotifierClient(
        NotifierConfig(base_url="https://notifier.test"),
        transport=httpx.MockTransport(handler),
        breaker=breaker,
        retry_policy=policy,
    )
    return client, handler


def notify(client):
    return client.notify_status_change(
        item_id=7, old_status="open", new_status="closed", updated_by="alice"
    )


def test_successful_notification_returns_true():
    client, handler = make_client([200])
    assert notify(client) is True
    assert handler.call_count == 1
    sent = handler.requests[0]
    assert sent.url.path == "/notifications"


def test_retries_on_server_error_then_succeeds():
    client, handler = make_client([500, 500, 200])
    assert notify(client) is True
    assert handler.call_count == 3


def test_persistent_server_error_returns_false_after_retries():
    client, handler = make_client([503], max_attempts=3)
    assert notify(client) is False
    assert handler.call_count == 3


def test_client_error_is_not_retried():
    client, handler = make_client([404])
    assert notify(client) is False
    assert handler.call_count == 1  # 4xx is permanent, no retry


def test_timeout_is_retried_then_succeeds():
    timeout = httpx.ConnectTimeout("timed out", request=None)
    client, handler = make_client([timeout, 200])
    assert notify(client) is True
    assert handler.call_count == 2


def test_connection_error_is_retried():
    conn_err = httpx.ConnectError("refused", request=None)
    client, handler = make_client([conn_err], max_attempts=2)
    assert notify(client) is False
    assert handler.call_count == 2


def test_circuit_opens_and_drops_further_notifications():
    clock = FakeClock()
    breaker = CircuitBreaker(
        "status-notifier",
        CircuitBreakerConfig(failure_threshold=2, recovery_timeout=10.0),
        clock=clock,
    )
    client, handler = make_client([500], breaker=breaker, max_attempts=1)

    # Two failing calls (threshold = 2) trip the breaker.
    assert notify(client) is False
    assert notify(client) is False
    assert breaker.state is CircuitState.OPEN

    calls_before = handler.call_count
    # Now the breaker short-circuits: the transport is not touched.
    assert notify(client) is False
    assert handler.call_count == calls_before


def test_circuit_recovers_after_timeout():
    clock = FakeClock()
    breaker = CircuitBreaker(
        "status-notifier",
        CircuitBreakerConfig(failure_threshold=1, recovery_timeout=10.0),
        clock=clock,
    )
    client, handler = make_client([500, 200], breaker=breaker, max_attempts=1)

    assert notify(client) is False
    assert breaker.state is CircuitState.OPEN

    clock.advance(10.0)  # recovery window elapses -> half-open
    assert notify(client) is True
    assert breaker.state is CircuitState.CLOSED


def test_rejected_response_during_half_open_frees_the_probe_slot():
    clock = FakeClock()
    breaker = CircuitBreaker(
        "status-notifier",
        CircuitBreakerConfig(
            failure_threshold=1, recovery_timeout=10.0, half_open_max_calls=1
        ),
        clock=clock,
    )
    client, handler = make_client([500, 404, 200], breaker=breaker, max_attempts=1)

    # A 5xx trips the breaker.
    assert notify(client) is False
    assert breaker.state is CircuitState.OPEN

    clock.advance(10.0)  # recovery window elapses -> half-open
    assert breaker.state is CircuitState.HALF_OPEN

    # A 4xx is a permanent rejection, not an availability failure, so it must
    # not consume the single half-open trial slot.
    assert notify(client) is False
    assert breaker.state is CircuitState.HALF_OPEN

    # The next genuine probe succeeds and closes the breaker; it would have been
    # dropped if the rejection had leaked the trial slot.
    assert notify(client) is True
    assert breaker.state is CircuitState.CLOSED
    assert handler.call_count == 3


def test_config_validation():
    with pytest.raises(ValueError):
        NotifierConfig(base_url="")
    with pytest.raises(ValueError):
        NotifierConfig(base_url="https://x", timeout=0)

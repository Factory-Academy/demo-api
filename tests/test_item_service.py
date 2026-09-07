"""
Tests for ItemService, focused on how batch status updates interact with the
resilient status notifier.
"""
from datetime import datetime

import pytest

from src.clients.status_notifier import NotifierUnavailableError, StatusNotifier
from src.services.item_service import ItemService, retry
from src.utils.resilience import BackoffPolicy, CircuitBreaker

NO_DELAY = BackoffPolicy(base_delay=0.0, max_delay=0.0, jitter=False)


class FakeDB:
    """Minimal in-memory store matching the get/save contract ItemService uses."""

    def __init__(self, records):
        self.records = {r["id"]: dict(r) for r in records}
        self.saved = []

    def get(self, id):
        return self.records.get(id)

    def save(self, record):
        self.records[record["id"]] = record
        self.saved.append(record["id"])


def base_record(id, status="active"):
    return {"id": id, "status": status, "created_at": datetime.utcnow()}


def test_retry_wrapper_still_returns_after_transient_failure():
    state = {"attempts": 0}

    def flaky():
        state["attempts"] += 1
        if state["attempts"] < 3:
            raise ValueError("temporary")
        return "ok"

    assert retry(flaky, attempts=3, exceptions=(ValueError,)) == "ok"
    assert state["attempts"] == 3


def test_retry_wrapper_reraises_last_error_on_exhaustion():
    def always_fails():
        raise ValueError("permanent")

    with pytest.raises(ValueError, match="permanent"):
        retry(always_fails, attempts=2, exceptions=(ValueError,))


def test_batch_update_categorizes_records():
    db = FakeDB([base_record(1, "active"), base_record(2, "closed")])
    service = ItemService(db)

    results = service.batch_update_status([1, 2, 99], "closed", "alice")

    assert results["updated"] == [1]
    assert results["skipped"] == [{"id": 2, "reason": "already in state"}]
    assert results["failed"] == [{"id": 99, "reason": "not found"}]
    assert db.records[1]["status"] == "closed"
    assert db.records[1]["updated_by"] == "alice"


def test_batch_update_notifies_downstream_on_success():
    db = FakeDB([base_record(1, "active"), base_record(2, "active")])
    notifications = []
    notifier = StatusNotifier(
        "https://x.example", sender=lambda p: notifications.append(p), policy=NO_DELAY
    )
    service = ItemService(db, notifier=notifier)

    results = service.batch_update_status([1, 2], "closed", "bob")

    assert results["updated"] == [1, 2]
    assert results["notify_failed"] == []
    assert [n["entity_id"] for n in notifications] == [1, 2]


def test_batch_update_records_notify_failures_without_failing_update():
    db = FakeDB([base_record(1, "active")])

    def failing_sender(payload):
        raise NotifierUnavailableError("downstream unreachable")

    notifier = StatusNotifier(
        "https://x.example",
        sender=failing_sender,
        policy=NO_DELAY,
        retries=1,
        breaker=CircuitBreaker(failure_threshold=99),
    )
    service = ItemService(db, notifier=notifier)

    results = service.batch_update_status([1], "closed", "bob")

    # The local update still commits even though the notification failed.
    assert results["updated"] == [1]
    assert db.records[1]["status"] == "closed"
    assert len(results["notify_failed"]) == 1
    assert results["notify_failed"][0]["id"] == 1

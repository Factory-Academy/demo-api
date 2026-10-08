from datetime import datetime

import pytest

from src.services.items import priority, status
from src.services.items.service import ItemService
from src.services.items.validation import ValidationResult

NOW = datetime(2024, 6, 1, 0, 0, 0)


class FakeDB:
    """Minimal in-memory stand-in for the record store."""

    def __init__(self, records=None):
        self.records = {r["id"]: r for r in (records or [])}
        self.saved_ids = []

    def get(self, id):
        return self.records.get(id)

    def save(self, record):
        self.records[record["id"]] = record
        self.saved_ids.append(record["id"])


@pytest.fixture
def service():
    return ItemService(FakeDB())


def test_calculate_priority_delegates_to_core(service):
    item = {"created_at": NOW, "urgency": 8}
    assert service.calculate_priority(item, now=NOW) == priority.classify(
        item, now=NOW
    )
    assert service.calculate_priority(item, now=NOW) == priority.CRITICAL


def test_validate_item_delegates_and_returns_result_type(service):
    result = service.validate_item({"name": "ok"}, now=NOW)
    assert isinstance(result, ValidationResult)
    assert result == (True, [])


def test_batch_update_mixed_outcomes():
    db = FakeDB(
        [
            {"id": 1, "status": "open"},
            {"id": 2, "status": "closed"},
        ]
    )
    svc = ItemService(db)

    result = svc.batch_update_status(
        [1, 2, 3], new_status="closed", updated_by="alice", now=NOW
    )

    assert result["updated"] == [1]
    assert result["skipped"] == [{"id": 2, "reason": status.REASON_ALREADY_IN_STATE}]
    assert result["failed"] == [{"id": 3, "reason": status.REASON_NOT_FOUND}]


def test_batch_update_writes_fields_and_saves():
    record = {"id": 1, "status": "open"}
    db = FakeDB([record])
    svc = ItemService(db)

    svc.batch_update_status([1], "closed", "alice", now=NOW)

    assert record["status"] == "closed"
    assert record["updated_by"] == "alice"
    assert record["updated_at"] == NOW
    # The same object is persisted, not a copy.
    assert db.saved_ids == [1]
    assert db.records[1] is record


def test_batch_update_skips_do_not_touch_db():
    db = FakeDB([{"id": 1, "status": "closed"}])
    svc = ItemService(db)

    svc.batch_update_status([1], "closed", "alice", now=NOW)

    assert db.saved_ids == []


def test_batch_update_empty_ids():
    db = FakeDB()
    svc = ItemService(db)

    result = svc.batch_update_status([], "closed", "alice", now=NOW)

    assert result == {"updated": [], "failed": [], "skipped": []}
    assert db.saved_ids == []


def test_batch_update_defaults_now_to_a_datetime():
    db = FakeDB([{"id": 1, "status": "open"}])
    svc = ItemService(db)

    svc.batch_update_status([1], "closed", "alice")

    assert isinstance(db.records[1]["updated_at"], datetime)


def test_legacy_import_path_still_works():
    from src.services.item_service import ItemService as LegacyItemService

    assert LegacyItemService is ItemService

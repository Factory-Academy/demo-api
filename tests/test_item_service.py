from datetime import datetime, timedelta

from src.domain import InMemoryRepository, ItemRecord, Priority
from src.services.item_service import ItemService


FIXED_NOW = datetime(2026, 1, 1, 12, 0, 0)


def make_record(id, **overrides):
    payload = {"name": f"item-{id}"}
    payload.update(overrides)
    return ItemRecord.create(id, payload, now=FIXED_NOW)


def make_service(*records):
    return ItemService(InMemoryRepository(list(records)))


def test_calculate_priority_delegates_to_domain():
    service = make_service()
    record = make_record(1, urgency=8)
    assert service.calculate_priority(record, now=FIXED_NOW) is Priority.CRITICAL


def test_validate_item_accepts_valid_payload():
    service = make_service()
    result = service.validate_item(
        {"name": "ok", "quantity": 1}, now=FIXED_NOW
    )
    assert result.is_valid is True
    assert result.errors == []
    assert bool(result) is True


def test_validate_item_reports_each_problem():
    service = make_service()
    past = (FIXED_NOW - timedelta(days=1)).isoformat()
    result = service.validate_item(
        {"name": "  ", "quantity": -1, "due_date": past}, now=FIXED_NOW
    )
    assert result.is_valid is False
    assert "Name is required" in result.errors
    assert "Quantity cannot be negative" in result.errors
    assert "Due date cannot be in the past" in result.errors


def test_validate_item_rejects_bad_date_format():
    service = make_service()
    result = service.validate_item(
        {"name": "ok", "due_date": "not-a-date"}, now=FIXED_NOW
    )
    assert result.is_valid is False
    assert "Invalid date format" in result.errors


def test_validate_item_accepts_future_due_date():
    service = make_service()
    future = (FIXED_NOW + timedelta(days=5)).isoformat()
    result = service.validate_item(
        {"name": "ok", "due_date": future}, now=FIXED_NOW
    )
    assert result.is_valid is True


def test_validate_item_supports_unpacking_for_backward_compat():
    service = make_service()
    ok, errors = service.validate_item({"name": "ok"}, now=FIXED_NOW)
    assert ok is True
    assert errors == []


def test_batch_update_marks_updated_failed_and_skipped():
    active = make_record(1, status="active")
    already = make_record(2, status="archived")
    service = make_service(active, already)
    later = FIXED_NOW + timedelta(hours=1)

    result = service.batch_update_status(
        [1, 2, 99], "archived", "alice", now=later
    )

    assert result.updated == [1]
    assert [o.id for o in result.skipped] == [2]
    assert result.skipped[0].reason == "already in state"
    assert [o.id for o in result.failed] == [99]
    assert result.failed[0].reason == "not found"

    stored = service.db.get(1)
    assert stored.status == "archived"
    assert stored.updated_by == "alice"
    assert stored.updated_at == later


def test_batch_update_persists_through_repository():
    service = make_service(make_record(1, status="active"))
    service.batch_update_status([1], "closed", "bob", now=FIXED_NOW)
    assert service.db.get(1).status == "closed"

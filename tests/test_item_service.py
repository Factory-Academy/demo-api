from datetime import datetime, timedelta
from typing import Dict, Optional

import pytest

from src.domain import ItemRecord, Priority
from src.services.item_service import ItemService


class FakeDB:
    """In-memory stand-in storing :class:`ItemRecord` objects by id."""

    def __init__(self, records=None):
        self.records: Dict[int, ItemRecord] = {r.id: r for r in (records or [])}

    def get(self, item_id: int) -> Optional[ItemRecord]:
        return self.records.get(item_id)

    def save(self, record: ItemRecord) -> None:
        self.records[record.id] = record


def _item(**overrides) -> ItemRecord:
    now = datetime(2024, 1, 1, 12, 0, 0)
    base = dict(id=1, name="Item", created_at=now, updated_at=now)
    base.update(overrides)
    return ItemRecord(**base)


@pytest.fixture(autouse=True)
def _clear_priority_cache():
    # calculate_priority is memoized; isolate tests from each other.
    ItemService.calculate_priority.cache_clear()
    yield


class TestScore:
    def test_base_score_from_urgency(self):
        record = _item(urgency=3)
        assert ItemService.score(record, now=record.created_at) == 30

    def test_critical_adds_fifty(self):
        record = _item(urgency=1, is_critical=True)
        assert ItemService.score(record, now=record.created_at) == 60

    def test_age_adds_half_point_per_day_after_thirty(self):
        record = _item()
        later = record.created_at + timedelta(days=100)
        assert ItemService.score(record, now=later) == 100 * 0.5

    def test_young_items_get_no_age_bonus(self):
        record = _item()
        later = record.created_at + timedelta(days=30)
        assert ItemService.score(record, now=later) == 0


class TestCalculatePriority:
    # calculate_priority is cached and reads the wall clock for age, so use a
    # fresh created_at (age ~0, no age bonus) to isolate the urgency thresholds.
    @staticmethod
    def _fresh(**overrides) -> ItemRecord:
        return _item(created_at=datetime.utcnow(), **overrides)

    def test_low(self):
        assert ItemService.calculate_priority(self._fresh(id=10)) == Priority.LOW

    def test_medium(self):
        assert ItemService.calculate_priority(self._fresh(id=11, urgency=2)) == Priority.MEDIUM

    def test_high(self):
        assert ItemService.calculate_priority(self._fresh(id=12, urgency=5)) == Priority.HIGH

    def test_critical_via_flag(self):
        record = self._fresh(id=13, urgency=3, is_critical=True)
        assert ItemService.calculate_priority(record) == Priority.CRITICAL


class TestValidateItem:
    def test_valid_item(self):
        service = ItemService(FakeDB())
        result = service.validate_item(_item(quantity=1))
        assert result
        assert result.errors == []

    def test_blank_name_rejected(self):
        service = ItemService(FakeDB())
        result = service.validate_item(_item(name="   "))
        assert not result
        assert "Name is required" in result.errors

    def test_negative_quantity_rejected(self):
        service = ItemService(FakeDB())
        result = service.validate_item(_item(quantity=-1))
        assert "Quantity cannot be negative" in result.errors

    def test_past_due_date_rejected(self):
        service = ItemService(FakeDB())
        reference = datetime(2024, 6, 1)
        record = _item(due_date=datetime(2024, 1, 1))
        result = service.validate_item(record, now=reference)
        assert "Due date cannot be in the past" in result.errors

    def test_future_due_date_allowed(self):
        service = ItemService(FakeDB())
        reference = datetime(2024, 1, 1)
        record = _item(due_date=datetime(2024, 12, 31))
        assert service.validate_item(record, now=reference)

    def test_negative_urgency_rejected(self):
        service = ItemService(FakeDB())
        result = service.validate_item(_item(urgency=-1))
        assert not result
        assert "Urgency cannot be negative" in result.errors

    def test_multiple_errors_accumulate(self):
        service = ItemService(FakeDB())
        record = _item(name="", quantity=-5, urgency=-2)
        result = service.validate_item(record)
        assert len(result.errors) == 3


class TestBatchUpdateStatus:
    def test_updates_skips_and_fails(self):
        now = datetime(2024, 1, 1)
        db = FakeDB(
            [
                _item(id=1, status="open"),
                _item(id=2, status="closed"),
            ]
        )
        service = ItemService(db)

        result = service.batch_update_status(
            ids=[1, 2, 99],
            new_status="closed",
            updated_by="alice",
            now=now,
        )

        assert result.updated == [1]
        assert [o.id for o in result.skipped] == [2]
        assert [o.id for o in result.failed] == [99]
        assert result.total == 3

    def test_persists_new_record_without_mutating_original(self):
        original = _item(id=1, status="open")
        db = FakeDB([original])
        service = ItemService(db)
        stamp = datetime(2030, 1, 1)

        service.batch_update_status([1], "done", "bob", now=stamp)

        saved = db.get(1)
        assert saved.status == "done"
        assert saved.updated_by == "bob"
        assert saved.updated_at == stamp
        # Frozen original is unchanged.
        assert original.status == "open"
        assert original.updated_by is None

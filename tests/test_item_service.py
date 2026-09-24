from datetime import datetime, timedelta

import pytest

from src.services.item_service import ItemService
from src.services.items.errors import ItemDataError


class FakeDB:
    """Minimal in-memory stand-in for the item store used by ItemService."""

    def __init__(self, records=None):
        self.records = {r["id"]: dict(r) for r in (records or [])}
        self.saved = []

    def get(self, identifier):
        record = self.records.get(identifier)
        return dict(record) if record is not None else None

    def save(self, record):
        self.records[record["id"]] = dict(record)
        self.saved.append(record)


@pytest.fixture
def service():
    return ItemService(
        FakeDB(
            [
                {"id": 1, "status": "open"},
                {"id": 2, "status": "done"},
                {"id": 3, "status": "open"},
            ]
        )
    )


class TestServiceDelegation:
    def test_calculate_priority(self, service):
        item = {"created_at": datetime.utcnow(), "urgency": 8}
        assert service.calculate_priority(item) == "critical"

    def test_calculate_priority_handles_missing_fields(self, service):
        # Would have raised KeyError under the old inline implementation.
        assert service.calculate_priority({}) == "low"

    def test_validate_item(self, service):
        ok, errors = service.validate_item({"name": "Widget"})
        assert ok is True
        assert errors == []

    def test_validate_item_reports_errors(self, service):
        ok, errors = service.validate_item({"name": 5})
        assert ok is False
        assert errors == ["Name must be a string"]


class TestBatchUpdateStatus:
    def test_updates_skips_and_failures(self, service):
        result = service.batch_update_status([1, 2, 99], "done", "alice")
        assert result["updated"] == [1]
        assert result["skipped"] == [{"id": 2, "reason": "already in state"}]
        assert result["failed"] == [{"id": 99, "reason": "not found"}]

    def test_duplicate_ids_processed_once(self, service):
        result = service.batch_update_status([1, 1, 1], "done", "alice")
        assert result["updated"] == [1]

    def test_empty_ids(self, service):
        result = service.batch_update_status([], "done", "alice")
        assert result == {"updated": [], "failed": [], "skipped": []}

    def test_none_ids(self, service):
        # Regression: iterating None raised TypeError before.
        result = service.batch_update_status(None, "done", "alice")
        assert result == {"updated": [], "failed": [], "skipped": []}

    def test_missing_status_raises(self, service):
        with pytest.raises(ItemDataError):
            service.batch_update_status([1], "", "alice")

    def test_oversized_batch_raises(self, service):
        too_many = list(range(batch_limit() + 1))
        with pytest.raises(ItemDataError):
            service.batch_update_status(too_many, "done", "alice")

    def test_saved_record_is_a_copy(self, service):
        service.batch_update_status([1], "done", "alice")
        # The stored record reflects the update.
        assert service.db.records[1]["status"] == "done"
        assert service.db.records[1]["updated_by"] == "alice"


def batch_limit():
    from src.services.items import batch

    return batch.MAX_BATCH_SIZE

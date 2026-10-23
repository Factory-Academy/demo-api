from datetime import datetime, timedelta

from src.services.item_service import ItemService


class FakeDB:
    def __init__(self, records=None):
        self.records = {r["id"]: dict(r) for r in (records or [])}
        self.saved = []

    def get(self, identifier):
        record = self.records.get(identifier)
        return dict(record) if record is not None else None

    def save(self, record):
        self.records[record["id"]] = record
        self.saved.append(record)


class TestCalculatePriority:
    def test_critical_item(self):
        service = ItemService(FakeDB())
        label = service.calculate_priority(
            {"urgency": 4, "is_critical": True, "created_at": datetime.utcnow()}
        )
        assert label == "critical"

    def test_low_priority_default(self):
        service = ItemService(FakeDB())
        assert service.calculate_priority({"created_at": datetime.utcnow()}) == "low"

    def test_missing_created_at_does_not_raise(self):
        service = ItemService(FakeDB())
        assert service.calculate_priority({"urgency": 2}) == "medium"

    def test_malformed_item_is_low(self):
        service = ItemService(FakeDB())
        assert service.calculate_priority(None) == "low"


class TestValidateItem:
    def test_valid(self):
        service = ItemService(FakeDB())
        ok, errors = service.validate_item({"name": "Thing"})
        assert ok is True
        assert errors == []

    def test_invalid(self):
        service = ItemService(FakeDB())
        ok, errors = service.validate_item({"name": ""})
        assert ok is False
        assert errors


class TestBatchUpdateStatus:
    def test_delegates_to_pure_helper(self):
        db = FakeDB([{"id": 1, "status": "open"}])
        service = ItemService(db)
        result = service.batch_update_status([1], "done", "alice")
        assert result["updated"] == [1]
        assert db.records[1]["status"] == "done"

    def test_none_ids_safe(self):
        service = ItemService(FakeDB())
        result = service.batch_update_status(None, "done", "alice")
        assert result == {"updated": [], "failed": [], "skipped": []}

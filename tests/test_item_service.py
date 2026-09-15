from datetime import datetime, timedelta

from src.services.item_service import ItemService


class FakeDB:
    """In-memory stand-in for the persistence layer used by ItemService."""

    def __init__(self, records=None):
        self.records = {r["id"]: r for r in (records or [])}
        self.saved = []

    def get(self, id):
        return self.records.get(id)

    def save(self, record):
        self.records[record["id"]] = record
        self.saved.append(record["id"])


def _service(records=None):
    return ItemService(FakeDB(records))


class TestCalculatePriority:
    def test_delegates_to_pure_core(self):
        item = {
            "created_at": datetime.utcnow(),
            "urgency": 4,
            "is_critical": True,
        }
        assert _service().calculate_priority(item) == "critical"


class TestValidateItem:
    def test_returns_tuple_for_valid_item(self):
        ok, errors = _service().validate_item({"name": "Widget"})
        assert ok is True
        assert errors == []

    def test_returns_errors_for_invalid_item(self):
        ok, errors = _service().validate_item({"name": "", "quantity": -1})
        assert ok is False
        assert "Name is required" in errors
        assert "Quantity cannot be negative" in errors


class TestBatchUpdateStatus:
    def test_updates_records_in_a_different_state(self):
        db = FakeDB([{"id": 1, "status": "open"}, {"id": 2, "status": "open"}])
        service = ItemService(db)

        result = service.batch_update_status([1, 2], "done", "alice")

        assert result["updated"] == [1, 2]
        assert result["failed"] == []
        assert result["skipped"] == []
        assert db.saved == [1, 2]
        assert db.records[1]["status"] == "done"
        assert db.records[1]["updated_by"] == "alice"
        assert isinstance(db.records[1]["updated_at"], datetime)

    def test_skips_records_already_in_state(self):
        db = FakeDB([{"id": 1, "status": "done"}])
        result = ItemService(db).batch_update_status([1], "done", "alice")

        assert result["skipped"] == [{"id": 1, "reason": "already in state"}]
        assert result["updated"] == []
        assert db.saved == []

    def test_fails_missing_records(self):
        db = FakeDB([])
        result = ItemService(db).batch_update_status([99], "done", "alice")

        assert result["failed"] == [{"id": 99, "reason": "not found"}]
        assert result["updated"] == []
        assert db.saved == []

    def test_mixed_batch_is_partitioned_correctly(self):
        db = FakeDB(
            [
                {"id": 1, "status": "open"},
                {"id": 2, "status": "done"},
            ]
        )
        result = ItemService(db).batch_update_status([1, 2, 3], "done", "bob")

        assert result["updated"] == [1]
        assert result["skipped"] == [{"id": 2, "reason": "already in state"}]
        assert result["failed"] == [{"id": 3, "reason": "not found"}]
        assert db.saved == [1]

    def test_empty_id_list_returns_empty_buckets(self):
        result = _service().batch_update_status([], "done", "alice")
        assert result == {"updated": [], "failed": [], "skipped": []}

    def test_all_updated_records_share_one_timestamp(self):
        db = FakeDB([{"id": 1, "status": "open"}, {"id": 2, "status": "open"}])
        service = ItemService(db)

        service.batch_update_status([1, 2], "done", "alice")

        assert db.records[1]["updated_at"] == db.records[2]["updated_at"]

    def test_mutates_and_saves_the_same_record_object(self):
        original = {"id": 1, "status": "open"}
        db = FakeDB([original])
        ItemService(db).batch_update_status([1], "done", "alice")

        # The fetched record is updated in place, matching legacy behavior.
        assert original["status"] == "done"

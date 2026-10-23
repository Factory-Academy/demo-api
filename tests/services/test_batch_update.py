from datetime import datetime

import pytest

from src.services.items import batch


class FakeDB:
    """Minimal in-memory stand-in for the datastore used by batch updates."""

    def __init__(self, records):
        self.records = {r["id"]: dict(r) for r in records}
        self.saved = []

    def get(self, identifier):
        record = self.records.get(identifier)
        return dict(record) if record is not None else None

    def save(self, record):
        self.records[record["id"]] = record
        self.saved.append(record)


NOW = datetime(2026, 6, 1)


class TestNormalizeIds:
    def test_none_is_empty(self):
        assert batch.normalize_ids(None) == []

    def test_dedupes_preserving_order(self):
        assert batch.normalize_ids([3, 1, 3, 2, 1]) == [3, 1, 2]

    def test_drops_none_entries(self):
        assert batch.normalize_ids([1, None, 2]) == [1, 2]

    def test_bare_string_is_empty(self):
        assert batch.normalize_ids("123") == []

    def test_non_iterable_is_empty(self):
        assert batch.normalize_ids(42) == []


class TestChunk:
    def test_splits_into_sizes(self):
        chunks = list(batch.chunk([1, 2, 3, 4, 5], size=2))
        assert chunks == [[1, 2], [3, 4], [5]]

    def test_non_positive_size_falls_back(self):
        chunks = list(batch.chunk([1, 2], size=0))
        assert chunks == [[1, 2]]


class TestPlanRecordChange:
    def test_missing(self):
        assert batch.plan_record_change(None, "done") == batch.MISSING

    def test_skip_when_already_in_state(self):
        assert batch.plan_record_change({"status": "done"}, "done") == batch.SKIP

    def test_update_when_different(self):
        assert batch.plan_record_change({"status": "open"}, "done") == batch.UPDATE


class TestBatchUpdateStatus:
    def test_updates_skips_and_failures(self):
        db = FakeDB(
            [
                {"id": 1, "status": "open"},
                {"id": 2, "status": "done"},
            ]
        )
        result = batch.batch_update_status(
            db, [1, 2, 3], "done", "alice", now=NOW
        )
        assert result["updated"] == [1]
        assert result["skipped"] == [{"id": 2, "reason": "already in state"}]
        assert result["failed"] == [{"id": 3, "reason": "not found"}]

    def test_sets_audit_fields(self):
        db = FakeDB([{"id": 1, "status": "open"}])
        batch.batch_update_status(db, [1], "done", "alice", now=NOW)
        saved = db.records[1]
        assert saved["status"] == "done"
        assert saved["updated_by"] == "alice"
        assert saved["updated_at"] == NOW

    def test_empty_ids_returns_empty_report(self):
        db = FakeDB([{"id": 1, "status": "open"}])
        result = batch.batch_update_status(db, [], "done", "alice", now=NOW)
        assert result == {"updated": [], "failed": [], "skipped": []}
        assert db.saved == []

    def test_none_ids_does_not_raise(self):
        db = FakeDB([{"id": 1, "status": "open"}])
        result = batch.batch_update_status(db, None, "done", "alice", now=NOW)
        assert result == {"updated": [], "failed": [], "skipped": []}

    def test_duplicate_ids_processed_once(self):
        db = FakeDB([{"id": 1, "status": "open"}])
        result = batch.batch_update_status(
            db, [1, 1, 1], "done", "alice", now=NOW
        )
        assert result["updated"] == [1]
        assert len(db.saved) == 1

    @pytest.mark.parametrize("bad_status", [None, "", "   ", 5])
    def test_invalid_status_fails_all(self, bad_status):
        db = FakeDB([{"id": 1, "status": "open"}])
        result = batch.batch_update_status(db, [1], bad_status, "alice", now=NOW)
        assert result["failed"] == [{"id": 1, "reason": "invalid status"}]
        assert db.saved == []

    def test_large_input_is_chunked(self):
        records = [{"id": i, "status": "open"} for i in range(1200)]
        db = FakeDB(records)
        result = batch.batch_update_status(
            db, list(range(1200)), "done", "alice", now=NOW, chunk_size=500
        )
        assert len(result["updated"]) == 1200
        assert len(db.saved) == 1200

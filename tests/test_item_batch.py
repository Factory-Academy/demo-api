from datetime import datetime

from src.services.items.batch import (
    FAIL,
    SKIP,
    UPDATE,
    Decision,
    classify_record,
    status_fields,
)

NOW = datetime(2026, 1, 1, 12, 0, 0)


class TestClassifyRecord:
    def test_missing_record_fails(self):
        assert classify_record(None, "done") == Decision(FAIL, "not found")

    def test_record_already_in_state_is_skipped(self):
        record = {"id": 1, "status": "done"}
        assert classify_record(record, "done") == Decision(SKIP, "already in state")

    def test_record_in_other_state_is_updated(self):
        record = {"id": 1, "status": "open"}
        assert classify_record(record, "done") == Decision(UPDATE)

    def test_record_without_status_is_updated(self):
        assert classify_record({"id": 1}, "done") == Decision(UPDATE)

    def test_decision_is_immutable(self):
        decision = classify_record(None, "done")
        try:
            decision.action = UPDATE
        except Exception as error:
            assert isinstance(error, (AttributeError,))
        else:  # pragma: no cover - frozen dataclass must reject assignment
            raise AssertionError("Decision should be frozen")


class TestStatusFields:
    def test_builds_expected_fields(self):
        fields = status_fields("done", "alice", now=NOW)
        assert fields == {
            "status": "done",
            "updated_by": "alice",
            "updated_at": NOW,
        }

    def test_now_defaults_to_utcnow(self):
        before = datetime.utcnow()
        fields = status_fields("done", "alice")
        after = datetime.utcnow()
        assert before <= fields["updated_at"] <= after

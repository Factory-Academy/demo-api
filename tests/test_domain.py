import math
from datetime import datetime

import pytest

from src.domain import (
    BatchOutcome,
    BatchUpdateResult,
    ItemRecord,
    Priority,
    ValidationResult,
    WidgetRecord,
    WidgetStats,
)


def _item(**overrides) -> ItemRecord:
    now = datetime(2024, 1, 1, 12, 0, 0)
    base = dict(id=1, name="Widget", created_at=now, updated_at=now)
    base.update(overrides)
    return ItemRecord(**base)


class TestPriority:
    @pytest.mark.parametrize(
        "score, expected",
        [
            (0, Priority.LOW),
            (19.9, Priority.LOW),
            (20, Priority.MEDIUM),
            (49, Priority.MEDIUM),
            (50, Priority.HIGH),
            (79, Priority.HIGH),
            (80, Priority.CRITICAL),
            (1000, Priority.CRITICAL),
        ],
    )
    def test_from_score_thresholds(self, score, expected):
        assert Priority.from_score(score) is expected

    def test_accepts_numeric_strings(self):
        assert Priority.from_score("85") is Priority.CRITICAL

    @pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
    def test_rejects_non_finite_scores(self, bad):
        # NaN compares False against every threshold, so it must not silently
        # fall through to LOW.
        with pytest.raises(ValueError, match="finite"):
            Priority.from_score(bad)

    @pytest.mark.parametrize("bad", [None, "high", object()])
    def test_rejects_non_numeric_scores(self, bad):
        with pytest.raises(ValueError, match="numeric"):
            Priority.from_score(bad)

    def test_values_compare_equal_to_plain_strings(self):
        # Backwards compatibility with the old string return values.
        assert Priority.CRITICAL == "critical"
        assert Priority.LOW == "low"


class TestItemRecord:
    def test_is_hashable(self):
        # Frozen records can be used as dict keys / cache keys.
        assert hash(_item()) == hash(_item())

    def test_age_days(self):
        created = datetime(2024, 1, 1)
        record = _item(created_at=created)
        assert record.age_days(now=datetime(2024, 1, 11)) == 10

    def test_with_changes_is_immutable_and_restamps(self):
        record = _item()
        stamp = datetime(2025, 6, 1)
        updated = record.with_changes(status="archived", now=stamp)

        assert updated.status == "archived"
        assert updated.updated_at == stamp
        # Original is untouched.
        assert record.status == "active"
        assert record.updated_at != stamp

    def test_with_status(self):
        stamp = datetime(2025, 6, 1)
        updated = _item().with_status("closed", "alice", now=stamp)
        assert updated.status == "closed"
        assert updated.updated_by == "alice"
        assert updated.updated_at == stamp

    def test_to_dict_roundtrips(self):
        record = _item(description="hi", urgency=3)
        data = record.to_dict()
        assert data["name"] == "Widget"
        assert data["urgency"] == 3
        assert ItemRecord.from_mapping(data) == record

    def test_from_mapping_parses_iso_strings(self):
        record = ItemRecord.from_mapping(
            {
                "id": "7",
                "name": "Parsed",
                "created_at": "2024-01-01T00:00:00",
                "due_date": "2024-02-01T00:00:00",
                "urgency": "5",
                "is_critical": 1,
            }
        )
        assert record.id == 7
        assert record.urgency == 5
        assert record.is_critical is True
        assert record.due_date == datetime(2024, 2, 1)

    def test_from_mapping_defaults(self):
        record = ItemRecord.from_mapping({"id": 1, "name": "Minimal"})
        assert record.status == "active"
        assert record.urgency == 0
        assert record.due_date is None
        assert isinstance(record.created_at, datetime)

    def test_from_mapping_rejects_bad_date(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            ItemRecord.from_mapping(
                {"id": 1, "name": "Bad", "due_date": "not-a-date"}
            )

    @pytest.mark.parametrize("missing", ["id", "name"])
    def test_from_mapping_requires_id_and_name(self, missing):
        data = {"id": 1, "name": "Present"}
        del data[missing]
        with pytest.raises(ValueError, match=f"Missing required field '{missing}'"):
            ItemRecord.from_mapping(data)

    @pytest.mark.parametrize(
        "raw, expected",
        [("true", True), ("false", False), ("0", False), ("yes", True), (0, False)],
    )
    def test_from_mapping_coerces_boolean_strings(self, raw, expected):
        # The old bool(str) coercion made "false" truthy; this must not.
        record = ItemRecord.from_mapping(
            {"id": 1, "name": "Flag", "is_critical": raw}
        )
        assert record.is_critical is expected

    def test_from_mapping_rejects_unknown_boolean_string(self):
        with pytest.raises(ValueError, match="Invalid boolean"):
            ItemRecord.from_mapping(
                {"id": 1, "name": "Flag", "is_critical": "maybe"}
            )

    def test_from_mapping_rejects_bad_integer(self):
        with pytest.raises(ValueError, match="Invalid integer for 'id'"):
            ItemRecord.from_mapping({"id": "seven", "name": "Bad"})

    def test_from_mapping_blank_date_falls_back_to_default(self):
        record = ItemRecord.from_mapping(
            {"id": 1, "name": "Blank", "due_date": "   "}
        )
        assert record.due_date is None

    def test_with_changes_rejects_unknown_field(self):
        with pytest.raises(ValueError, match="Unknown field for ItemRecord"):
            _item().with_changes(nonexistent="x")


class TestValidationResult:
    def test_ok_is_truthy(self):
        result = ValidationResult.ok()
        assert result
        assert result.is_valid is True
        assert result.errors == []

    def test_failed_is_falsy(self):
        result = ValidationResult.failed(["boom"])
        assert not result
        assert result.errors == ["boom"]

    def test_raise_for_errors(self):
        with pytest.raises(ValueError, match="a; b"):
            ValidationResult.failed(["a", "b"]).raise_for_errors()

    def test_raise_for_errors_noop_when_valid(self):
        ValidationResult.ok().raise_for_errors()  # should not raise


class TestBatchUpdateResult:
    def test_marks_and_totals(self):
        result = BatchUpdateResult()
        result.mark_updated(1)
        result.mark_failed(2, "not found")
        result.mark_skipped(3, "already in state")

        assert result.updated == [1]
        assert result.failed == [BatchOutcome(id=2, reason="not found")]
        assert result.skipped == [BatchOutcome(id=3, reason="already in state")]
        assert result.total == 3

    def test_to_dict_legacy_shape(self):
        result = BatchUpdateResult()
        result.mark_updated(1)
        result.mark_failed(2, "not found")

        assert result.to_dict() == {
            "updated": [1],
            "failed": [{"id": 2, "reason": "not found"}],
            "skipped": [],
        }


class TestWidgetDomain:
    def test_widget_record_immutable_update(self):
        now = datetime(2024, 1, 1)
        record = WidgetRecord(
            id=1, name="W", item_id=2, created_at=now, updated_at=now
        )
        stamp = datetime(2024, 2, 1)
        updated = record.with_changes(priority=5, now=stamp)
        assert updated.priority == 5
        assert updated.updated_at == stamp
        assert record.priority == 0

    def test_widget_record_rejects_unknown_change(self):
        now = datetime(2024, 1, 1)
        record = WidgetRecord(
            id=1, name="W", item_id=2, created_at=now, updated_at=now
        )
        with pytest.raises(ValueError, match="Unknown field for WidgetRecord"):
            record.with_changes(bogus=1)

    def test_widget_from_mapping_coerces_and_defaults(self):
        record = WidgetRecord.from_mapping(
            {"id": "1", "name": "W", "item_id": "2", "priority": "5"}
        )
        assert record.id == 1
        assert record.item_id == 2
        assert record.priority == 5
        assert record.notes is None
        assert isinstance(record.created_at, datetime)

    def test_widget_from_mapping_requires_item_id(self):
        with pytest.raises(ValueError, match="Missing required field 'item_id'"):
            WidgetRecord.from_mapping({"id": 1, "name": "W"})

    def test_widget_stats_to_dict(self):
        stats = WidgetStats(id=3, complexity_score=4.5, last_analyzed="t")
        assert stats.to_dict() == {
            "id": 3,
            "complexity_score": 4.5,
            "last_analyzed": "t",
        }

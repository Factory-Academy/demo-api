from datetime import datetime, timedelta

import pytest

from src.domain import ItemRecord, Priority, WidgetRecord, compute_priority


FIXED_NOW = datetime(2026, 1, 1, 12, 0, 0)


def test_item_record_create_sets_timestamps_and_defaults():
    record = ItemRecord.create(
        1, {"name": "Widget", "description": "d"}, now=FIXED_NOW
    )
    assert record.id == 1
    assert record.name == "Widget"
    assert record.created_at == FIXED_NOW
    assert record.updated_at == FIXED_NOW
    assert record.status == "active"
    assert record.urgency == 0
    assert record.is_critical is False


def test_item_record_create_rejects_unknown_fields():
    with pytest.raises(ValueError):
        ItemRecord.create(1, {"name": "x", "bogus": 1}, now=FIXED_NOW)


def test_apply_update_changes_only_provided_fields_and_touches_updated_at():
    record = ItemRecord.create(1, {"name": "old"}, now=FIXED_NOW)
    later = FIXED_NOW + timedelta(days=1)
    record.apply_update({"name": "new", "status": "archived"}, now=later)
    assert record.name == "new"
    assert record.status == "archived"
    assert record.created_at == FIXED_NOW
    assert record.updated_at == later


def test_apply_update_cannot_touch_id_or_created_at():
    record = ItemRecord.create(1, {"name": "x"}, now=FIXED_NOW)
    with pytest.raises(ValueError):
        record.apply_update({"id": 99})
    with pytest.raises(ValueError):
        record.apply_update({"created_at": FIXED_NOW})


def test_item_record_copy_is_independent():
    record = ItemRecord.create(1, {"name": "x"}, now=FIXED_NOW)
    clone = record.copy(name="y")
    assert clone.name == "y"
    assert record.name == "x"


def test_widget_record_create():
    record = WidgetRecord.create(
        5, {"name": "w", "item_id": 1, "priority": 3}, now=FIXED_NOW
    )
    assert record.id == 5
    assert record.item_id == 1
    assert record.priority == 3
    assert record.notes is None


def test_widget_record_create_rejects_unknown_fields():
    with pytest.raises(ValueError):
        WidgetRecord.create(5, {"name": "w", "item_id": 1, "oops": 1}, now=FIXED_NOW)


@pytest.mark.parametrize(
    "urgency,is_critical,age_days,expected",
    [
        (0, False, 0, Priority.LOW),      # score 0
        (2, False, 0, Priority.MEDIUM),   # score 20
        (5, False, 0, Priority.HIGH),     # score 50
        (0, True, 0, Priority.HIGH),      # score 50 (critical bonus)
        (8, False, 0, Priority.CRITICAL), # score 80
        (3, True, 0, Priority.CRITICAL),  # score 30 + 50 = 80
    ],
)
def test_compute_priority_buckets(urgency, is_critical, age_days, expected):
    created = FIXED_NOW - timedelta(days=age_days)
    record = ItemRecord.create(
        1,
        {"name": "x", "urgency": urgency, "is_critical": is_critical},
        now=created,
    )
    assert compute_priority(record, now=FIXED_NOW) is expected


def test_compute_priority_ages_in_stale_items():
    created = FIXED_NOW - timedelta(days=120)
    # No urgency, but 120 days old: 120 * 0.5 = 60 -> high.
    record = ItemRecord.create(1, {"name": "x"}, now=created)
    assert compute_priority(record, now=FIXED_NOW) is Priority.HIGH


def test_priority_compares_as_string():
    assert Priority.CRITICAL == "critical"

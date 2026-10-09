from datetime import datetime

from src.routes.record_helpers import (
    build_timestamped_record,
    find_record_by_id,
    find_record_index_by_id,
)


def test_build_timestamped_record_sets_shared_timestamps():
    now = datetime(2026, 1, 15, 12, 30, 0)

    record = build_timestamped_record({"name": "Item A"}, 3, now=now)

    assert record["name"] == "Item A"
    assert record["id"] == 3
    assert record["created_at"] == now
    assert record["updated_at"] == now


def test_find_record_by_id_returns_match_or_none():
    records = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]

    assert find_record_by_id(records, 2) == {"id": 2, "name": "B"}
    assert find_record_by_id(records, 99) is None


def test_find_record_helpers_skip_malformed_records():
    records = [{"name": "missing-id"}, "not-a-record", {"id": 3, "name": "C"}]

    assert find_record_index_by_id(records, 3) == 2
    assert find_record_by_id(records, 3) == {"id": 3, "name": "C"}

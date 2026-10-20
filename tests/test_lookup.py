import pytest

from src.services.lookup import NotFoundError, find_record_by_id


def test_find_record_by_id_returns_record():
    records = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]

    result = find_record_by_id(records, 2, "Widget not found")

    assert result == {"id": 2, "name": "B"}


def test_find_record_by_id_raises_not_found_error():
    with pytest.raises(NotFoundError, match="Widget not found"):
        find_record_by_id([], 99, "Widget not found")

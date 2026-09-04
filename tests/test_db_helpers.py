"""
Unit tests for database helper functions.
"""
import pytest
from datetime import datetime
from fastapi import HTTPException
from src.utils.db_helpers import (
    create_with_timestamps,
    delete_by_id,
    find_by_id,
    update_by_id,
)


class TestFindById:
    """Tests for find_by_id helper."""

    def test_find_by_id_found(self):
        """Should return the item when found."""
        db = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"},
        ]
        result = find_by_id(db, 2)
        assert result == {"id": 2, "name": "Item 2"}

    def test_find_by_id_first_item(self):
        """Should find first item in list."""
        db = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
        ]
        result = find_by_id(db, 1)
        assert result["id"] == 1

    def test_find_by_id_last_item(self):
        """Should find last item in list."""
        db = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"},
        ]
        result = find_by_id(db, 3)
        assert result["id"] == 3

    def test_find_by_id_not_found(self):
        """Should raise 404 when item not found."""
        db = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
        ]
        with pytest.raises(HTTPException) as exc_info:
            find_by_id(db, 999)
        assert exc_info.value.status_code == 404
        assert "Item not found" in exc_info.value.detail

    def test_find_by_id_custom_entity_name(self):
        """Should use custom entity name in error message."""
        db = []
        with pytest.raises(HTTPException) as exc_info:
            find_by_id(db, 1, "Widget")
        assert "Widget not found" in exc_info.value.detail

    def test_find_by_id_empty_db(self):
        """Should raise 404 on empty database."""
        db = []
        with pytest.raises(HTTPException) as exc_info:
            find_by_id(db, 1)
        assert exc_info.value.status_code == 404


class TestCreateWithTimestamps:
    """Tests for create_with_timestamps helper."""

    def test_create_with_timestamps_basic(self):
        """Should create item with ID and timestamps."""
        db = []
        data = {"name": "New Item", "description": "Test"}
        before = datetime.utcnow()
        item, new_next_id = create_with_timestamps(db, data, 1)
        after = datetime.utcnow()

        assert item["id"] == 1
        assert item["name"] == "New Item"
        assert item["description"] == "Test"
        assert before <= item["created_at"] <= after
        assert before <= item["updated_at"] <= after
        assert item["created_at"] == item["updated_at"]
        assert new_next_id == 2
        assert len(db) == 1
        assert db[0] == item

    def test_create_with_timestamps_increments_id(self):
        """Should increment next_id correctly."""
        db = []
        item1, next_id = create_with_timestamps(db, {"name": "Item 1"}, 1)
        item2, next_id = create_with_timestamps(db, {"name": "Item 2"}, next_id)
        item3, next_id = create_with_timestamps(db, {"name": "Item 3"}, next_id)

        assert item1["id"] == 1
        assert item2["id"] == 2
        assert item3["id"] == 3
        assert next_id == 4
        assert len(db) == 3

    def test_create_with_timestamps_preserves_data(self):
        """Should preserve all input data fields."""
        db = []
        data = {
            "name": "Widget",
            "item_id": 42,
            "priority": 5,
            "notes": "Important widget",
        }
        item, _ = create_with_timestamps(db, data, 10)

        assert item["name"] == "Widget"
        assert item["item_id"] == 42
        assert item["priority"] == 5
        assert item["notes"] == "Important widget"

    def test_create_with_timestamps_large_id(self):
        """Should handle large ID values."""
        db = []
        item, new_next_id = create_with_timestamps(db, {"name": "Item"}, 9999)
        assert item["id"] == 9999
        assert new_next_id == 10000


class TestUpdateById:
    """Tests for update_by_id helper."""

    def test_update_by_id_single_field(self):
        """Should update a single field."""
        db = [{"id": 1, "name": "Original", "status": "active"}]
        before = datetime.utcnow()
        result = update_by_id(db, 1, {"name": "Updated"})
        after = datetime.utcnow()

        assert result["name"] == "Updated"
        assert result["status"] == "active"
        assert result["id"] == 1
        assert before <= result["updated_at"] <= after
        assert len(db) == 1
        assert db[0] == result

    def test_update_by_id_multiple_fields(self):
        """Should update multiple fields."""
        db = [{"id": 2, "name": "Item", "description": "Desc", "status": "active"}]
        result = update_by_id(db, 2, {"name": "New Name", "status": "inactive"})

        assert result["name"] == "New Name"
        assert result["description"] == "Desc"
        assert result["status"] == "inactive"
        assert result["id"] == 2

    def test_update_by_id_not_found(self):
        """Should raise 404 if item not found."""
        db = [{"id": 1, "name": "Item"}]
        with pytest.raises(HTTPException) as exc_info:
            update_by_id(db, 999, {"name": "New"})
        assert exc_info.value.status_code == 404

    def test_update_by_id_preserves_created_at(self):
        """Should preserve created_at timestamp."""
        original_time = datetime(2025, 1, 1, 12, 0, 0)
        db = [
            {
                "id": 1,
                "name": "Item",
                "created_at": original_time,
                "updated_at": original_time,
            }
        ]
        result = update_by_id(db, 1, {"name": "Updated"})

        assert result["created_at"] == original_time
        assert result["updated_at"] > original_time

    def test_update_by_id_custom_entity_name(self):
        """Should use custom entity name in error message."""
        db = []
        with pytest.raises(HTTPException) as exc_info:
            update_by_id(db, 1, {}, "Widget")
        assert "Widget not found" in exc_info.value.detail

    def test_update_by_id_empty_update(self):
        """Should handle empty update data."""
        db = [{"id": 1, "name": "Item", "status": "active"}]
        result = update_by_id(db, 1, {})

        assert result["name"] == "Item"
        assert result["status"] == "active"
        assert "updated_at" in result


class TestDeleteById:
    """Tests for delete_by_id helper."""

    def test_delete_by_id_success(self):
        """Should delete item and return True."""
        db = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"},
        ]
        result = delete_by_id(db, 2)

        assert result is True
        assert len(db) == 2
        assert all(item["id"] != 2 for item in db)

    def test_delete_by_id_first_item(self):
        """Should delete first item."""
        db = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
        ]
        delete_by_id(db, 1)
        assert len(db) == 1
        assert db[0]["id"] == 2

    def test_delete_by_id_last_item(self):
        """Should delete last item."""
        db = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
        ]
        delete_by_id(db, 2)
        assert len(db) == 1
        assert db[0]["id"] == 1

    def test_delete_by_id_single_item(self):
        """Should delete single item in database."""
        db = [{"id": 1, "name": "Item"}]
        delete_by_id(db, 1)
        assert len(db) == 0

    def test_delete_by_id_not_found(self):
        """Should raise 404 if item not found."""
        db = [{"id": 1, "name": "Item"}]
        with pytest.raises(HTTPException) as exc_info:
            delete_by_id(db, 999)
        assert exc_info.value.status_code == 404
        assert "Item not found" in exc_info.value.detail
        assert len(db) == 1  # Should not modify db

    def test_delete_by_id_empty_db(self):
        """Should raise 404 on empty database."""
        db = []
        with pytest.raises(HTTPException) as exc_info:
            delete_by_id(db, 1)
        assert exc_info.value.status_code == 404

    def test_delete_by_id_custom_entity_name(self):
        """Should use custom entity name in error message."""
        db = []
        with pytest.raises(HTTPException) as exc_info:
            delete_by_id(db, 1, "Widget")
        assert "Widget not found" in exc_info.value.detail

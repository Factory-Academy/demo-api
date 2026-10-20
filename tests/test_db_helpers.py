from datetime import datetime
import pytest
from src.utils.db_helpers import find_by_id, create_record


class TestFindById:
    def test_find_existing_record(self):
        collection = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
        ]
        result = find_by_id(collection, 2)
        assert result == {"id": 2, "name": "Bob"}

    def test_find_first_record(self):
        collection = [
            {"id": 10, "name": "First"},
            {"id": 20, "name": "Second"},
        ]
        result = find_by_id(collection, 10)
        assert result == {"id": 10, "name": "First"}

    def test_find_last_record(self):
        collection = [
            {"id": 10, "name": "First"},
            {"id": 20, "name": "Last"},
        ]
        result = find_by_id(collection, 20)
        assert result == {"id": 20, "name": "Last"}

    def test_find_nonexistent_record(self):
        collection = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        result = find_by_id(collection, 99)
        assert result is None

    def test_find_in_empty_collection(self):
        collection = []
        result = find_by_id(collection, 1)
        assert result is None

    def test_find_with_missing_id_field(self):
        collection = [
            {"name": "No ID"},
            {"id": 2, "name": "Has ID"},
        ]
        result = find_by_id(collection, 2)
        assert result == {"id": 2, "name": "Has ID"}


class TestCreateRecord:
    def test_create_basic_record(self):
        data = {"name": "Test Item", "status": "active"}
        result = create_record(data, 1)
        
        assert result["id"] == 1
        assert result["name"] == "Test Item"
        assert result["status"] == "active"
        assert "created_at" in result
        assert "updated_at" in result
        assert isinstance(result["created_at"], datetime)
        assert isinstance(result["updated_at"], datetime)

    def test_create_record_timestamps_are_equal(self):
        data = {"name": "Test"}
        result = create_record(data, 5)
        
        assert result["created_at"] == result["updated_at"]

    def test_create_record_preserves_all_fields(self):
        data = {
            "name": "Complex Item",
            "description": "A detailed description",
            "priority": 10,
            "tags": ["urgent", "important"],
        }
        result = create_record(data, 42)
        
        assert result["id"] == 42
        assert result["name"] == "Complex Item"
        assert result["description"] == "A detailed description"
        assert result["priority"] == 10
        assert result["tags"] == ["urgent", "important"]

    def test_create_record_with_empty_data(self):
        data = {}
        result = create_record(data, 1)
        
        assert result["id"] == 1
        assert "created_at" in result
        assert "updated_at" in result

    def test_create_record_does_not_mutate_input(self):
        data = {"name": "Original"}
        original_keys = set(data.keys())
        
        result = create_record(data, 1)
        
        # Original data should not be modified
        assert set(data.keys()) == original_keys
        assert "id" not in data
        assert "created_at" not in data

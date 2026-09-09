"""Tests for the InMemoryStore CRUD helper."""

from datetime import datetime
from src.utils.crud_helpers import InMemoryStore


class TestInMemoryStore:
    """Test suite for InMemoryStore class."""

    def test_init_creates_empty_store(self):
        """Test that initialization creates an empty store."""
        db = []
        store = InMemoryStore(db)
        assert store.db is db
        assert len(store.db) == 0

    def test_next_id_increments(self):
        """Test that next_id increments correctly."""
        db = []
        store = InMemoryStore(db)
        assert store.next_id == 1
        assert store.next_id == 2
        assert store.next_id == 3

    def test_create_record_with_id_and_timestamps(self):
        """Test that create adds id and timestamps to records."""
        db = []
        store = InMemoryStore(db)

        data = {"name": "Test Item", "description": "A test"}
        record = store.create(data)

        assert record["id"] == 1
        assert record["name"] == "Test Item"
        assert record["description"] == "A test"
        assert isinstance(record["created_at"], datetime)
        assert isinstance(record["updated_at"], datetime)
        assert record["created_at"] == record["updated_at"]
        assert len(db) == 1
        assert db[0] is record

    def test_create_multiple_records_with_sequential_ids(self):
        """Test that multiple creates have sequential IDs."""
        db = []
        store = InMemoryStore(db)

        record1 = store.create({"name": "First"})
        record2 = store.create({"name": "Second"})

        assert record1["id"] == 1
        assert record2["id"] == 2
        assert len(db) == 2

    def test_get_by_id_finds_record(self):
        """Test that get_by_id finds existing records."""
        db = []
        store = InMemoryStore(db)

        record = store.create({"name": "Test"})
        found = store.get_by_id(record["id"])

        assert found is record
        assert found["name"] == "Test"

    def test_get_by_id_returns_none_for_missing_record(self):
        """Test that get_by_id returns None for missing records."""
        db = []
        store = InMemoryStore(db)

        found = store.get_by_id(999)
        assert found is None

    def test_delete_by_id_removes_record(self):
        """Test that delete_by_id removes records."""
        db = []
        store = InMemoryStore(db)

        record = store.create({"name": "Test"})
        assert len(db) == 1

        deleted = store.delete_by_id(record["id"])

        assert deleted is True
        assert len(db) == 0

    def test_delete_by_id_returns_false_for_missing_record(self):
        """Test that delete_by_id returns False for missing records."""
        db = []
        store = InMemoryStore(db)

        deleted = store.delete_by_id(999)
        assert deleted is False

    def test_update_by_id_updates_record(self):
        """Test that update_by_id updates records correctly."""
        db = []
        store = InMemoryStore(db)

        record = store.create({"name": "Original", "status": "active"})
        original_created_at = record["created_at"]

        updated = store.update_by_id(record["id"], {"name": "Updated"})

        assert updated is not None
        assert updated["id"] == record["id"]
        assert updated["name"] == "Updated"
        assert updated["status"] == "active"  # Unchanged
        assert updated["created_at"] == original_created_at
        assert updated["updated_at"] > original_created_at

    def test_update_by_id_returns_none_for_missing_record(self):
        """Test that update_by_id returns None for missing records."""
        db = []
        store = InMemoryStore(db)

        updated = store.update_by_id(999, {"name": "Updated"})
        assert updated is None

    def test_update_partial_fields(self):
        """Test that update preserves unspecified fields."""
        db = []
        store = InMemoryStore(db)

        record = store.create(
            {"name": "Test", "description": "Desc", "status": "active"}
        )

        updated = store.update_by_id(record["id"], {"status": "inactive"})

        assert updated["name"] == "Test"
        assert updated["description"] == "Desc"
        assert updated["status"] == "inactive"

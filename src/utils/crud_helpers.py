"""Generic CRUD helpers for in-memory list-based database operations."""

from datetime import datetime
from typing import Any, Callable, List, Optional, TypeVar

T = TypeVar("T")


class InMemoryStore:
    """Generic in-memory store for CRUD operations on list-based databases."""

    def __init__(self, db: List[dict]):
        """Initialize the store with a database list.

        Args:
            db: The in-memory database list to operate on.
        """
        self.db = db
        self._next_id = 1

    @property
    def next_id(self) -> int:
        """Get the next ID and increment the counter."""
        current = self._next_id
        self._next_id += 1
        return current

    def get_by_id(self, record_id: int) -> Optional[dict]:
        """Find a record by ID.

        Args:
            record_id: The ID to search for.

        Returns:
            The record if found, None otherwise.
        """
        for record in self.db:
            if record["id"] == record_id:
                return record
        return None

    def create(
        self,
        data: dict,
        exclude_fields: Optional[List[str]] = None,
    ) -> dict:
        """Create a record with ID and timestamps.

        Args:
            data: The data to create (typically from model_dump()).
            exclude_fields: Fields to exclude from the data (default: None).

        Returns:
            The created record with id, created_at, and updated_at.
        """
        now = datetime.utcnow()
        record = {
            **data,
            "id": self.next_id,
            "created_at": now,
            "updated_at": now,
        }
        self.db.append(record)
        return record

    def delete_by_id(self, record_id: int) -> bool:
        """Delete a record by ID.

        Args:
            record_id: The ID of the record to delete.

        Returns:
            True if a record was deleted, False if not found.
        """
        for i, record in enumerate(self.db):
            if record["id"] == record_id:
                self.db.pop(i)
                return True
        return False

    def update_by_id(self, record_id: int, update_data: dict) -> Optional[dict]:
        """Update a record by ID.

        Args:
            record_id: The ID of the record to update.
            update_data: The fields to update.

        Returns:
            The updated record, or None if not found.
        """
        for i, existing in enumerate(self.db):
            if existing["id"] == record_id:
                update_data["updated_at"] = datetime.utcnow()
                self.db[i] = {**existing, **update_data}
                return self.db[i]
        return None

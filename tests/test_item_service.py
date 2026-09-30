"""Tests for ItemService with focus on mutable default handling."""

import pytest
from datetime import datetime
from src.services.item_service import ItemService


class MockDB:
    """Mock database for testing."""

    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def save(self, record):
        self.data[record.get("id")] = record

    def values(self):
        return self.data.values()


class TestItemServiceStatusSummary:
    """Tests for get_status_summary method."""

    def test_summary_with_no_filters(self):
        """Test getting summary with no status filters."""
        db = MockDB()
        db.data = {
            1: {"id": 1, "status": "active", "urgency": 5, "quantity": 10},
            2: {"id": 2, "status": "active", "urgency": 3, "quantity": 5},
            3: {"id": 3, "status": "inactive", "urgency": 1, "quantity": 2},
        }
        service = ItemService(db)

        result = service.get_status_summary()

        assert result["total_items"] == 3
        assert "active" in result["status_breakdown"]
        assert "inactive" in result["status_breakdown"]
        assert result["filter_applied"]["include_status"] == []
        assert result["filter_applied"]["exclude_status"] == []

    def test_summary_with_include_status(self):
        """Test summary with include status filter."""
        db = MockDB()
        db.data = {
            1: {"id": 1, "status": "active", "urgency": 5, "quantity": 10},
            2: {"id": 2, "status": "pending", "urgency": 3, "quantity": 5},
            3: {"id": 3, "status": "inactive", "urgency": 1, "quantity": 2},
        }
        service = ItemService(db)

        result = service.get_status_summary(include_status=["active", "pending"])

        assert result["total_items"] == 2
        assert "inactive" not in result["status_breakdown"]
        assert result["filter_applied"]["include_status"] == ["active", "pending"]

    def test_summary_with_exclude_status(self):
        """Test summary with exclude status filter."""
        db = MockDB()
        db.data = {
            1: {"id": 1, "status": "active", "urgency": 5, "quantity": 10},
            2: {"id": 2, "status": "deleted", "urgency": 3, "quantity": 5},
            3: {"id": 3, "status": "inactive", "urgency": 1, "quantity": 2},
        }
        service = ItemService(db)

        result = service.get_status_summary(exclude_status=["deleted"])

        assert result["total_items"] == 2
        assert "deleted" not in result["status_breakdown"]

    def test_mutable_default_regression_include_status(self):
        """REGRESSION TEST: include_status default should not persist.

        This test ensures that the default empty list for include_status
        is not shared between multiple calls to get_status_summary.
        """
        db = MockDB()
        db.data = {
            1: {"id": 1, "status": "active", "urgency": 5, "quantity": 10},
        }
        service = ItemService(db)

        # First call with include_status
        result1 = service.get_status_summary(include_status=["active"])
        assert result1["filter_applied"]["include_status"] == ["active"]

        # Second call without include_status
        result2 = service.get_status_summary()
        assert result2["filter_applied"]["include_status"] == []

        # Third call with different include_status
        result3 = service.get_status_summary(include_status=["pending"])
        assert result3["filter_applied"]["include_status"] == ["pending"]

    def test_mutable_default_regression_exclude_status(self):
        """REGRESSION TEST: exclude_status default should not persist."""
        db = MockDB()
        db.data = {
            1: {"id": 1, "status": "active", "urgency": 5, "quantity": 10},
        }
        service = ItemService(db)

        # First call with exclude_status
        result1 = service.get_status_summary(exclude_status=["deleted"])
        assert result1["filter_applied"]["exclude_status"] == ["deleted"]

        # Second call without exclude_status
        result2 = service.get_status_summary()
        assert result2["filter_applied"]["exclude_status"] == []

    def test_aggregation_calculations(self):
        """Test that aggregations are calculated correctly."""
        db = MockDB()
        db.data = {
            1: {"id": 1, "status": "active", "urgency": 10, "quantity": 100},
            2: {"id": 2, "status": "active", "urgency": 20, "quantity": 200},
        }
        service = ItemService(db)

        result = service.get_status_summary()

        active_stats = result["status_breakdown"]["active"]
        assert active_stats["urgency"] == 15.0  # Average
        assert active_stats["quantity"] == 300  # Sum


class TestItemServiceBuildFilter:
    """Tests for build_item_filter method."""

    def test_build_filter_no_params(self):
        """Test building filter with no parameters."""
        db = MockDB()
        service = ItemService(db)

        result = service.build_item_filter()

        assert result["include_status"] == []
        assert result["exclude_status"] == []
        assert result["tags"] == []

    def test_build_filter_with_status(self):
        """Test building filter with status list."""
        db = MockDB()
        service = ItemService(db)

        result = service.build_item_filter(status_list=["active", "pending"])

        assert result["include_status"] == ["active", "pending"]

    def test_build_filter_with_tags(self):
        """Test building filter with tags."""
        db = MockDB()
        service = ItemService(db)

        result = service.build_item_filter(tags=["important", "urgent"])

        assert result["tags"] == ["important", "urgent"]

    def test_mutable_default_regression_status_list(self):
        """REGRESSION TEST: status_list default should not persist."""
        db = MockDB()
        service = ItemService(db)

        # First call with status_list
        result1 = service.build_item_filter(status_list=["active"])
        assert result1["include_status"] == ["active"]

        # Second call without status_list
        result2 = service.build_item_filter()
        assert result2["include_status"] == []

    def test_mutable_default_regression_tags(self):
        """REGRESSION TEST: tags default should not persist."""
        db = MockDB()
        service = ItemService(db)

        # First call with tags
        result1 = service.build_item_filter(tags=["urgent"])
        assert result1["tags"] == ["urgent"]

        # Second call without tags
        result2 = service.build_item_filter()
        assert result2["tags"] == []


class TestItemServiceBatchUpdate:
    """Tests for batch_update_status method."""

    def test_batch_update_success(self):
        """Test successful batch update."""
        db = MockDB()
        db.data = {
            1: {"id": 1, "status": "pending"},
            2: {"id": 2, "status": "pending"},
        }
        service = ItemService(db)

        result = service.batch_update_status(
            [1, 2], new_status="active", updated_by="test_user"
        )

        assert len(result["updated"]) == 2
        assert 1 in result["updated"]
        assert 2 in result["updated"]
        assert db.data[1]["status"] == "active"
        assert db.data[2]["status"] == "active"

    def test_batch_update_handles_not_found(self):
        """Test batch update with non-existent IDs."""
        db = MockDB()
        db.data = {1: {"id": 1, "status": "pending"}}
        service = ItemService(db)

        result = service.batch_update_status(
            [1, 999], new_status="active", updated_by="test_user"
        )

        assert len(result["updated"]) == 1
        assert len(result["failed"]) == 1
        assert result["failed"][0]["id"] == 999

    def test_batch_update_skips_same_status(self):
        """Test that items with same status are skipped."""
        db = MockDB()
        db.data = {
            1: {"id": 1, "status": "active"},
            2: {"id": 2, "status": "pending"},
        }
        service = ItemService(db)

        result = service.batch_update_status(
            [1, 2], new_status="active", updated_by="test_user"
        )

        assert len(result["updated"]) == 1
        assert len(result["skipped"]) == 1
        assert result["skipped"][0]["id"] == 1

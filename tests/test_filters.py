"""Tests for data filtering utilities.

This test suite includes regression tests for mutable default argument bugs.
"""

import pytest
from src.utils.filters import (
    filter_items_by_criteria,
    apply_transformations,
    aggregate_items,
    build_query_filter,
)


class TestFilterItemsByCriteria:
    """Tests for filter_items_by_criteria function."""

    def test_filter_with_no_criteria(self):
        """Test filtering with no criteria returns all items."""
        items = [
            {"id": 1, "name": "Item 1", "status": "active"},
            {"id": 2, "name": "Item 2", "status": "inactive"},
        ]
        result = filter_items_by_criteria(items)
        assert len(result) == 2
        assert result == items

    def test_filter_with_criteria(self):
        """Test filtering with criteria returns matching items."""
        items = [
            {"id": 1, "name": "Item 1", "status": "active"},
            {"id": 2, "name": "Item 2", "status": "inactive"},
            {"id": 3, "name": "Item 3", "status": "active"},
        ]
        result = filter_items_by_criteria(items, criteria={"status": "active"})
        assert len(result) == 2
        assert all(item["status"] == "active" for item in result)

    def test_exclude_fields(self):
        """Test excluding fields from results."""
        items = [
            {"id": 1, "name": "Item 1", "status": "active", "secret": "hidden"},
        ]
        result = filter_items_by_criteria(
            items, exclude_fields=["secret", "status"]
        )
        assert len(result) == 1
        assert "secret" not in result[0]
        assert "status" not in result[0]
        assert result[0]["name"] == "Item 1"

    def test_mutable_default_regression_criteria(self):
        """REGRESSION TEST: Ensure criteria default doesn't persist between calls.

        This test guards against the mutable default argument bug where
        using criteria={} as a default would cause the same dict to be
        shared across all function calls.
        """
        items = [{"id": 1, "status": "active"}]

        # First call with no criteria
        result1 = filter_items_by_criteria(items)
        assert len(result1) == 1

        # Second call with criteria
        result2 = filter_items_by_criteria(items, criteria={"status": "active"})
        assert len(result2) == 1

        # Third call with no criteria - should still work independently
        result3 = filter_items_by_criteria(items)
        assert len(result3) == 1

        # All calls should return the same results for the same inputs
        assert result1 == result3

    def test_mutable_default_regression_exclude_fields(self):
        """REGRESSION TEST: Ensure exclude_fields default doesn't persist.

        Guards against mutable default bug where using exclude_fields=[]
        as a default would cause the same list to be shared.
        """
        items = [{"id": 1, "name": "Test", "secret": "hidden"}]

        # First call with no exclusions
        result1 = filter_items_by_criteria(items)
        assert "secret" in result1[0]

        # Second call with exclusions
        result2 = filter_items_by_criteria(items, exclude_fields=["secret"])
        assert "secret" not in result2[0]

        # Third call with no exclusions - should include secret again
        result3 = filter_items_by_criteria(items)
        assert "secret" in result3[0]

    def test_multiple_criteria(self):
        """Test filtering with multiple criteria."""
        items = [
            {"id": 1, "status": "active", "priority": "high"},
            {"id": 2, "status": "active", "priority": "low"},
            {"id": 3, "status": "inactive", "priority": "high"},
        ]
        result = filter_items_by_criteria(
            items, criteria={"status": "active", "priority": "high"}
        )
        assert len(result) == 1
        assert result[0]["id"] == 1


class TestApplyTransformations:
    """Tests for apply_transformations function."""

    def test_apply_defaults(self):
        """Test applying default values to items."""
        item = {"name": "Test Item"}
        result = apply_transformations(
            item, defaults={"status": "active", "priority": "medium"}
        )
        assert result["name"] == "Test Item"
        assert result["status"] == "active"
        assert result["priority"] == "medium"

    def test_apply_transformations_function(self):
        """Test applying transformation functions."""
        item = {"name": "test", "count": 5}
        transformations = {
            "name": lambda x: x.upper(),
            "count": lambda x: x * 2,
        }
        result = apply_transformations(item, transformations=transformations)
        assert result["name"] == "TEST"
        assert result["count"] == 10

    def test_defaults_dont_override_existing(self):
        """Test that defaults don't override existing values."""
        item = {"name": "Test", "status": "custom"}
        result = apply_transformations(item, defaults={"status": "active"})
        assert result["status"] == "custom"

    def test_mutable_default_regression_transformations(self):
        """REGRESSION TEST: Ensure transformations default doesn't persist.

        Guards against using transformations={} as default.
        """
        item = {"name": "test"}

        # First call with no transformations
        result1 = apply_transformations(item)
        assert result1["name"] == "test"

        # Second call with transformation
        result2 = apply_transformations(
            item, transformations={"name": lambda x: x.upper()}
        )
        assert result2["name"] == "TEST"

        # Third call with no transformations - should not apply uppercase
        result3 = apply_transformations(item)
        assert result3["name"] == "test"

    def test_mutable_default_regression_defaults(self):
        """REGRESSION TEST: Ensure defaults dict doesn't persist.

        Guards against using defaults={} as default parameter.
        """
        item1 = {"name": "Item 1"}
        item2 = {"name": "Item 2"}

        # First call with defaults
        result1 = apply_transformations(item1, defaults={"status": "active"})
        assert result1["status"] == "active"

        # Second call without defaults
        result2 = apply_transformations(item2)
        assert "status" not in result2

        # Verify first item still has status
        assert result1["status"] == "active"

    def test_original_item_not_modified(self):
        """Test that the original item dict is not modified."""
        original = {"name": "test", "count": 5}
        original_copy = original.copy()

        apply_transformations(
            original,
            transformations={"name": lambda x: x.upper()},
            defaults={"status": "active"},
        )

        # Original should be unchanged
        assert original == original_copy


class TestAggregateItems:
    """Tests for aggregate_items function."""

    def test_aggregate_sum(self):
        """Test sum aggregation."""
        items = [
            {"status": "active", "count": 5},
            {"status": "active", "count": 3},
            {"status": "inactive", "count": 2},
        ]
        result = aggregate_items(items, "status", {"count": "sum"})
        assert result["active"]["count"] == 8
        assert result["inactive"]["count"] == 2

    def test_aggregate_avg(self):
        """Test average aggregation."""
        items = [
            {"status": "active", "score": 10},
            {"status": "active", "score": 20},
        ]
        result = aggregate_items(items, "status", {"score": "avg"})
        assert result["active"]["score"] == 15.0

    def test_aggregate_count(self):
        """Test count aggregation."""
        items = [
            {"status": "active", "value": 1},
            {"status": "active", "value": 2},
            {"status": "inactive", "value": 3},
        ]
        result = aggregate_items(items, "status", {"value": "count"})
        assert result["active"]["value"] == 2
        assert result["inactive"]["value"] == 1

    def test_aggregate_min_max(self):
        """Test min and max aggregations."""
        items = [
            {"status": "active", "score": 5},
            {"status": "active", "score": 15},
            {"status": "active", "score": 10},
        ]
        result = aggregate_items(
            items, "status", {"score": "min"}
        )
        assert result["active"]["score"] == 5

        result = aggregate_items(
            items, "status", {"score": "max"}
        )
        assert result["active"]["score"] == 15

    def test_mutable_default_regression_aggregations(self):
        """REGRESSION TEST: Ensure aggregations default doesn't persist.

        Guards against using aggregations={} as default.
        """
        items = [{"status": "active", "count": 5}]

        # First call with no aggregations
        result1 = aggregate_items(items, "status")
        assert result1["active"] == {}

        # Second call with aggregations
        result2 = aggregate_items(items, "status", {"count": "sum"})
        assert result2["active"]["count"] == 5

        # Third call with no aggregations - should be empty again
        result3 = aggregate_items(items, "status")
        assert result3["active"] == {}

    def test_handles_none_values(self):
        """Test that None values are handled correctly."""
        items = [
            {"status": "active", "count": 5},
            {"status": "active", "count": None},
            {"status": "active", "count": 3},
        ]
        result = aggregate_items(items, "status", {"count": "sum"})
        assert result["active"]["count"] == 8

    def test_empty_items_list(self):
        """Test aggregating an empty list."""
        result = aggregate_items([], "status", {"count": "sum"})
        assert result == {}


class TestBuildQueryFilter:
    """Tests for build_query_filter function."""

    def test_build_empty_filter(self):
        """Test building filter with no parameters."""
        result = build_query_filter()
        assert result["include_status"] == []
        assert result["exclude_status"] == []
        assert result["tags"] == []

    def test_build_filter_with_include_status(self):
        """Test building filter with include status."""
        result = build_query_filter(include_status=["active", "pending"])
        assert result["include_status"] == ["active", "pending"]
        assert result["exclude_status"] == []

    def test_build_filter_with_all_params(self):
        """Test building filter with all parameters."""
        result = build_query_filter(
            include_status=["active"],
            exclude_status=["deleted"],
            tags=["important", "urgent"],
        )
        assert result["include_status"] == ["active"]
        assert result["exclude_status"] == ["deleted"]
        assert result["tags"] == ["important", "urgent"]

    def test_mutable_default_regression_include_status(self):
        """REGRESSION TEST: Ensure include_status default doesn't persist."""
        # First call with include_status
        result1 = build_query_filter(include_status=["active"])
        assert result1["include_status"] == ["active"]

        # Second call without include_status
        result2 = build_query_filter()
        assert result2["include_status"] == []

        # First result should be unchanged
        assert result1["include_status"] == ["active"]

    def test_mutable_default_regression_exclude_status(self):
        """REGRESSION TEST: Ensure exclude_status default doesn't persist."""
        result1 = build_query_filter(exclude_status=["deleted"])
        assert result1["exclude_status"] == ["deleted"]

        result2 = build_query_filter()
        assert result2["exclude_status"] == []

    def test_mutable_default_regression_tags(self):
        """REGRESSION TEST: Ensure tags default doesn't persist."""
        result1 = build_query_filter(tags=["important"])
        assert result1["tags"] == ["important"]

        result2 = build_query_filter()
        assert result2["tags"] == []

    def test_returned_lists_are_independent(self):
        """Test that returned lists are independent between calls."""
        result1 = build_query_filter(include_status=["active"])
        result2 = build_query_filter(include_status=["pending"])

        # Modify result1 - should not affect result2
        result1["include_status"].append("extra")

        assert result1["include_status"] == ["active", "extra"]
        assert result2["include_status"] == ["pending"]

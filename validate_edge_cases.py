#!/usr/bin/env python3
"""Validation script for edge case handling in filters module."""

import sys
sys.path.insert(0, '.')

from src.utils.filters import (
    filter_items_by_criteria,
    apply_transformations,
    aggregate_items,
    build_query_filter,
    FilterError,
)


def test_filter_none_items():
    """Test that None items raises FilterError."""
    try:
        filter_items_by_criteria(None)
        return False, "Should have raised FilterError for None items"
    except FilterError as e:
        if "cannot be None" in str(e):
            return True, "Correctly raised FilterError for None items"
        return False, f"Wrong error message: {e}"


def test_filter_invalid_items():
    """Test that non-list items raises FilterError."""
    try:
        filter_items_by_criteria("not a list")
        return False, "Should have raised FilterError for non-list items"
    except FilterError as e:
        if "must be a list" in str(e):
            return True, "Correctly raised FilterError for non-list items"
        return False, f"Wrong error message: {e}"


def test_filter_non_dict_in_items():
    """Test that non-dict items in list raises FilterError."""
    try:
        filter_items_by_criteria([{"id": 1}, "not a dict"])
        return False, "Should have raised FilterError for non-dict item"
    except FilterError as e:
        if "must be dictionaries" in str(e):
            return True, "Correctly raised FilterError for non-dict item"
        return False, f"Wrong error message: {e}"


def test_transform_none_item():
    """Test that None item raises FilterError."""
    try:
        apply_transformations(None)
        return False, "Should have raised FilterError for None item"
    except FilterError as e:
        if "cannot be None" in str(e):
            return True, "Correctly raised FilterError for None item"
        return False, f"Wrong error message: {e}"


def test_transform_exception_handling():
    """Test that transformation exceptions are caught."""
    def bad_transform(x):
        raise ValueError("Intentional error")
    
    try:
        apply_transformations({"name": "test"}, transformations={"name": bad_transform})
        return False, "Should have raised FilterError for failing transformation"
    except FilterError as e:
        if "Transformation failed" in str(e):
            return True, "Correctly caught transformation exception"
        return False, f"Wrong error message: {e}"


def test_aggregate_invalid_type():
    """Test that invalid aggregation type raises FilterError."""
    try:
        aggregate_items([{"status": "active", "count": 5}], "status", {"count": "summ"})
        return False, "Should have raised FilterError for invalid aggregation type"
    except FilterError as e:
        if "Invalid aggregation type" in str(e):
            return True, "Correctly raised FilterError for invalid aggregation type"
        return False, f"Wrong error message: {e}"


def test_aggregate_empty_group_by():
    """Test that empty group_by raises FilterError."""
    try:
        aggregate_items([{"status": "active"}], "")
        return False, "Should have raised FilterError for empty group_by"
    except FilterError as e:
        if "must be a non-empty string" in str(e):
            return True, "Correctly raised FilterError for empty group_by"
        return False, f"Wrong error message: {e}"


def test_build_filter_invalid_types():
    """Test that invalid parameter types raise FilterError."""
    try:
        build_query_filter(include_status="active")
        return False, "Should have raised FilterError for non-list include_status"
    except FilterError as e:
        if "must be a list or None" in str(e):
            return True, "Correctly raised FilterError for non-list parameter"
        return False, f"Wrong error message: {e}"


def test_valid_operations():
    """Test that valid operations still work."""
    # Filter items
    items = [{"id": 1, "status": "active"}, {"id": 2, "status": "inactive"}]
    result = filter_items_by_criteria(items, criteria={"status": "active"})
    if len(result) != 1:
        return False, f"Filter failed: expected 1 item, got {len(result)}"
    
    # Apply transformations
    item = {"name": "test"}
    result = apply_transformations(item, defaults={"status": "active"})
    if result["status"] != "active":
        return False, "Transform failed: default not applied"
    
    # Aggregate items
    items = [{"status": "active", "count": 5}, {"status": "active", "count": 3}]
    result = aggregate_items(items, "status", {"count": "sum"})
    if result["active"]["count"] != 8:
        return False, f"Aggregate failed: expected 8, got {result['active']['count']}"
    
    # Build filter
    result = build_query_filter(include_status=["active"])
    if result["include_status"] != ["active"]:
        return False, "Build filter failed"
    
    return True, "All valid operations work correctly"


def main():
    """Run all validation tests."""
    tests = [
        ("Filter None items", test_filter_none_items),
        ("Filter invalid items type", test_filter_invalid_items),
        ("Filter non-dict in items", test_filter_non_dict_in_items),
        ("Transform None item", test_transform_none_item),
        ("Transform exception handling", test_transform_exception_handling),
        ("Aggregate invalid type", test_aggregate_invalid_type),
        ("Aggregate empty group_by", test_aggregate_empty_group_by),
        ("Build filter invalid types", test_build_filter_invalid_types),
        ("Valid operations", test_valid_operations),
    ]
    
    print("=" * 70)
    print("Edge Case Validation Tests")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            success, message = test_func()
            if success:
                print(f"✓ {name}: {message}")
                passed += 1
            else:
                print(f"✗ {name}: {message}")
                failed += 1
        except Exception as e:
            print(f"✗ {name}: Unexpected exception - {e}")
            failed += 1
    
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

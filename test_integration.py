#!/usr/bin/env python3
"""Integration test to verify edge case handling works across all layers."""

import sys
sys.path.insert(0, '.')

from src.utils.filters import FilterError
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


def test_service_integration():
    """Test that service layer properly handles FilterError."""
    print("Testing service layer integration...")
    
    db = MockDB()
    db.data = {
        1: {"id": 1, "status": "active", "urgency": 5, "quantity": 10},
        2: {"id": 2, "status": "pending", "urgency": 3, "quantity": 5},
    }
    service = ItemService(db)
    
    # Test valid operations work
    result = service.get_status_summary()
    assert result["total_items"] == 2
    print("  ✓ Valid summary works")
    
    result = service.get_status_summary(include_status=["active"])
    assert result["total_items"] == 1
    print("  ✓ Filtered summary works")
    
    # Test edge case: invalid status type
    try:
        service.build_item_filter(status_list="not-a-list")
        assert False, "Should have raised FilterError"
    except FilterError as e:
        assert "must be a list" in str(e)
        print("  ✓ Invalid status type caught")
    
    # Test edge case: invalid tags type
    try:
        service.build_item_filter(tags="not-a-list")
        assert False, "Should have raised FilterError"
    except FilterError as e:
        assert "must be a list" in str(e)
        print("  ✓ Invalid tags type caught")
    
    print("✓ Service integration tests passed\n")


def test_mutable_defaults_still_work():
    """Verify mutable default bug is still fixed."""
    print("Testing mutable defaults are still handled correctly...")
    
    from src.utils.filters import filter_items_by_criteria, build_query_filter
    
    items = [{"id": 1, "status": "active"}]
    
    # Call 1: no params
    result1 = filter_items_by_criteria(items)
    
    # Call 2: with params
    result2 = filter_items_by_criteria(items, criteria={"status": "active"})
    
    # Call 3: no params again
    result3 = filter_items_by_criteria(items)
    
    # Should be identical (no state leakage)
    assert result1 == result3
    print("  ✓ No state leakage in filter_items_by_criteria")
    
    # Test build_query_filter
    f1 = build_query_filter(include_status=["active"])
    f2 = build_query_filter()
    f3 = build_query_filter(include_status=["pending"])
    
    assert f1["include_status"] == ["active"]
    assert f2["include_status"] == []
    assert f3["include_status"] == ["pending"]
    print("  ✓ No state leakage in build_query_filter")
    
    print("✓ Mutable defaults still handled correctly\n")


def test_error_messages():
    """Verify error messages are clear and helpful."""
    print("Testing error message quality...")
    
    from src.utils.filters import aggregate_items, filter_items_by_criteria
    
    # Test aggregation error message
    try:
        aggregate_items([{"s": "a", "c": 5}], "s", {"c": "average"})
    except FilterError as e:
        msg = str(e)
        assert "Invalid aggregation type" in msg
        assert "Valid types:" in msg
        assert "avg, count, max, min, sum" in msg
        print(f"  ✓ Aggregation error: {msg}")
    
    # Test None items error
    try:
        filter_items_by_criteria(None)
    except FilterError as e:
        msg = str(e)
        assert "cannot be None" in msg
        print(f"  ✓ None error: {msg}")
    
    # Test type error
    try:
        filter_items_by_criteria("string")
    except FilterError as e:
        msg = str(e)
        assert "must be a list" in msg
        print(f"  ✓ Type error: {msg}")
    
    print("✓ Error messages are clear and helpful\n")


def main():
    """Run all integration tests."""
    print("=" * 70)
    print("Integration Test Suite")
    print("=" * 70 + "\n")
    
    try:
        test_service_integration()
        test_mutable_defaults_still_work()
        test_error_messages()
        
        print("=" * 70)
        print("✓ All integration tests passed!")
        print("=" * 70)
        return 0
    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

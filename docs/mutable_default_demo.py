#!/usr/bin/env python3
"""
Demonstration of the mutable default argument bug and the fix.

This script shows the difference between buggy code (using mutable defaults)
and the correct implementation (using None and initializing inside the function).
"""


def buggy_filter(items, criteria={}):
    """BUGGY VERSION - DO NOT USE!
    
    This demonstrates the mutable default argument bug.
    The criteria dict is shared across all function calls.
    """
    print(f"  criteria object id: {id(criteria)}")
    
    # If we modify criteria in any way, it persists!
    if 'call_count' not in criteria:
        criteria['call_count'] = 0
    criteria['call_count'] += 1
    
    return [
        item for item in items 
        if all(item.get(k) == v for k, v in criteria.items() if k != 'call_count')
    ]


def correct_filter(items, criteria=None):
    """CORRECT VERSION - USE THIS!
    
    This properly handles mutable defaults by using None
    and creating a new dict inside the function.
    """
    if criteria is None:
        criteria = {}
    
    print(f"  criteria object id: {id(criteria)}")
    
    return [
        item for item in items 
        if all(item.get(k) == v for k, v in criteria.items())
    ]


def main():
    print("=" * 70)
    print("MUTABLE DEFAULT ARGUMENT BUG DEMONSTRATION")
    print("=" * 70)
    
    test_items = [
        {"id": 1, "status": "active"},
        {"id": 2, "status": "inactive"},
    ]
    
    print("\n1. BUGGY VERSION (using criteria={} as default):")
    print("-" * 70)
    
    print("\nCall 1 - No criteria passed:")
    result1 = buggy_filter(test_items)
    print(f"  Returned {len(result1)} items")
    
    print("\nCall 2 - Still no criteria passed:")
    result2 = buggy_filter(test_items)
    print(f"  Returned {len(result2)} items")
    print(f"  ⚠️  Notice: Same dict object is reused! (same id)")
    
    print("\nCall 3 - Still no criteria passed:")
    result3 = buggy_filter(test_items)
    print(f"  Returned {len(result3)} items")
    print(f"  ⚠️  Call count keeps incrementing!")
    
    print("\n" + "=" * 70)
    print("2. CORRECT VERSION (using criteria=None):")
    print("-" * 70)
    
    print("\nCall 1 - No criteria passed:")
    result1 = correct_filter(test_items)
    print(f"  Returned {len(result1)} items")
    
    print("\nCall 2 - No criteria passed:")
    result2 = correct_filter(test_items)
    print(f"  Returned {len(result2)} items")
    print(f"  ✅ Different dict objects created (different ids)")
    
    print("\nCall 3 - With criteria:")
    result3 = correct_filter(test_items, criteria={"status": "active"})
    print(f"  Returned {len(result3)} items")
    print(f"  ✅ Different dict object created")
    
    print("\nCall 4 - No criteria again:")
    result4 = correct_filter(test_items)
    print(f"  Returned {len(result4)} items")
    print(f"  ✅ Fresh empty dict, not affected by previous calls")
    
    print("\n" + "=" * 70)
    print("3. REAL-WORLD IMPACT:")
    print("-" * 70)
    
    print("\nImagine this in a web API:")
    print("  - User A makes a request with filter {'status': 'active'}")
    print("  - User B makes a request with no filter")
    print("  - User B unexpectedly gets filtered results!")
    print("  - This is a SECURITY and CORRECTNESS bug")
    
    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print("✅ Always use None as default for mutable parameters")
    print("✅ Initialize mutable objects inside the function body")
    print("✅ Add regression tests to catch this bug")
    print("=" * 70)


if __name__ == "__main__":
    main()

# Mutable Default Argument Bugfix

## Overview

This document describes the fix for mutable default argument bugs in the codebase, specifically in the new data filtering utilities module.

## The Problem

In Python, using mutable objects (lists, dictionaries, sets) as default parameter values is a common bug that can lead to unexpected behavior. This happens because default parameter values are evaluated only once when the function is defined, not each time it's called.

### Example of the Bug

```python
# ❌ WRONG - Mutable default argument bug
def filter_items(items, criteria={}):
    # If caller doesn't pass criteria, they all share the same dict!
    criteria['last_call'] = True
    return [item for item in items if all(item.get(k) == v for k, v in criteria.items())]

# First call
result1 = filter_items([{'id': 1}])  # criteria = {'last_call': True}

# Second call - criteria dict is REUSED from first call!
result2 = filter_items([{'id': 2}])  # criteria = {'last_call': True} (same object!)
```

### Why This Is Dangerous

1. **State Leakage**: Data from one function call can "leak" into subsequent calls
2. **Hard to Debug**: The bug is subtle and may not appear in simple tests
3. **Race Conditions**: In concurrent code, this can cause unpredictable behavior
4. **Violation of Expectations**: Functions should be stateless unless explicitly designed otherwise

## The Solution

Always use `None` as the default value and initialize the mutable object inside the function:

```python
# ✅ CORRECT - Proper handling of mutable defaults
def filter_items(items, criteria=None):
    if criteria is None:
        criteria = {}
    # Now each call gets a fresh dict
    return [item for item in items if all(item.get(k) == v for k, v in criteria.items())]
```

## Implementation

This bugfix implements a new `src/utils/filters.py` module with several utility functions that properly handle mutable defaults:

### Functions Implemented

1. **`filter_items_by_criteria`**
   - Filters items based on criteria dictionary
   - Optionally excludes fields from results
   - Properly handles `criteria=None` and `exclude_fields=None`

2. **`apply_transformations`**
   - Applies transformation functions to item fields
   - Sets default values for missing fields
   - Properly handles `transformations=None` and `defaults=None`

3. **`aggregate_items`**
   - Aggregates items by a field with specified aggregation types
   - Supports sum, count, avg, min, max
   - Properly handles `aggregations=None`

4. **`build_query_filter`**
   - Builds filter configurations from parameters
   - Properly handles `include_status=None`, `exclude_status=None`, `tags=None`

### Integration Points

The utilities are integrated into:

1. **`src/routes/item_routes.py`**
   - Updated `list_items` endpoint to use filtering
   - Added `batch_transform_items` endpoint for bulk transformations

2. **`src/services/item_service.py`**
   - Added `get_status_summary` method with proper mutable default handling
   - Added `build_item_filter` method demonstrating utility usage

## Testing

Comprehensive regression tests are included in:

- `tests/test_filters.py`: Tests all filter utilities with specific mutable default regression tests
- `tests/test_item_service.py`: Tests service integration with mutable default regression tests

### Key Test Cases

Each function has dedicated regression tests that verify:

1. ✅ Basic functionality works correctly
2. ✅ First call with parameters works
3. ✅ Second call without parameters gets fresh defaults
4. ✅ Third call with different parameters is independent
5. ✅ Default values don't persist between calls

### Example Regression Test

```python
def test_mutable_default_regression_criteria(self):
    """REGRESSION TEST: Ensure criteria default doesn't persist between calls."""
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
```

## Best Practices

When writing Python functions, follow these guidelines:

### DO ✅

- Use `None` as default for mutable parameters
- Initialize mutable defaults inside the function body
- Document when a function returns a new object vs modifying in-place
- Add regression tests for mutable default handling

```python
def process_items(items, filters=None, options=None):
    if filters is None:
        filters = {}
    if options is None:
        options = []
    # ... rest of function
```

### DON'T ❌

- Use `[]`, `{}`, or `set()` as default parameter values
- Modify mutable parameters without documenting the behavior
- Assume "it's fine for my use case" - the bug can appear later

```python
# NEVER DO THIS
def process_items(items, filters={}, options=[]):
    # This will cause bugs!
```

## Files Changed

- **Created**: `src/utils/__init__.py`
- **Created**: `src/utils/filters.py` - Core filtering utilities
- **Modified**: `src/routes/item_routes.py` - Added filtering endpoints
- **Modified**: `src/services/item_service.py` - Added service methods
- **Created**: `tests/test_filters.py` - Comprehensive utility tests
- **Created**: `tests/test_item_service.py` - Service integration tests
- **Created**: `docs/BUGFIX_MUTABLE_DEFAULTS.md` - This documentation

## Verification

To verify the fix is working:

```bash
# Run the filter utility tests
pytest tests/test_filters.py -v

# Run the service integration tests
pytest tests/test_item_service.py -v

# Run all tests
pytest tests/ -v
```

All tests include specific regression tests for mutable default argument bugs, ensuring this issue doesn't reappear in future changes.

## References

- [Python Common Gotchas - Mutable Default Arguments](https://docs.python-guide.org/writing/gotchas/#mutable-default-arguments)
- [PEP 8 - Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/)
- [Effective Python: 90 Specific Ways to Write Better Python](https://effectivepython.com/)

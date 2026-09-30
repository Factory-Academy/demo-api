"""Data filtering utilities with proper handling of mutable defaults.

This module provides utilities for filtering and transforming item data.
All functions properly handle mutable default arguments using None-checks.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime


def filter_items_by_criteria(
    items: List[Dict[str, Any]],
    criteria: Optional[Dict[str, Any]] = None,
    exclude_fields: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Filter items based on criteria and optionally exclude fields.

    Args:
        items: List of item dictionaries to filter
        criteria: Dictionary of field-value pairs to match (default: None)
        exclude_fields: List of field names to exclude from results (default: None)

    Returns:
        Filtered list of items matching criteria with excluded fields removed

    Example:
        >>> items = [{"id": 1, "name": "test", "status": "active"}]
        >>> filter_items_by_criteria(items, {"status": "active"})
        [{"id": 1, "name": "test", "status": "active"}]
    """
    # Properly handle mutable defaults
    if criteria is None:
        criteria = {}
    if exclude_fields is None:
        exclude_fields = []

    filtered = []
    for item in items:
        # Check if item matches all criteria
        matches = all(
            item.get(key) == value for key, value in criteria.items()
        )
        if matches:
            # Create a copy and remove excluded fields
            filtered_item = {
                k: v for k, v in item.items() if k not in exclude_fields
            }
            filtered.append(filtered_item)

    return filtered


def apply_transformations(
    item: Dict[str, Any],
    transformations: Optional[Dict[str, callable]] = None,
    defaults: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Apply transformations to item fields and set defaults.

    Args:
        item: Item dictionary to transform
        transformations: Dict mapping field names to transformation functions
        defaults: Dict of default values for missing fields

    Returns:
        Transformed item dictionary

    Example:
        >>> item = {"name": "test"}
        >>> apply_transformations(item, defaults={"status": "active"})
        {"name": "test", "status": "active"}
    """
    # Properly handle mutable defaults
    if transformations is None:
        transformations = {}
    if defaults is None:
        defaults = {}

    # Create a new dict to avoid modifying the original
    result = item.copy()

    # Apply defaults for missing fields
    for key, value in defaults.items():
        if key not in result:
            result[key] = value

    # Apply transformations
    for field, transform_fn in transformations.items():
        if field in result:
            result[field] = transform_fn(result[field])

    return result


def aggregate_items(
    items: List[Dict[str, Any]],
    group_by: str,
    aggregations: Optional[Dict[str, str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Aggregate items by a field with specified aggregations.

    Args:
        items: List of items to aggregate
        group_by: Field name to group items by
        aggregations: Dict mapping field names to aggregation types
                     ('sum', 'count', 'avg', 'min', 'max')

    Returns:
        Dictionary mapping group values to aggregated results

    Example:
        >>> items = [
        ...     {"status": "active", "count": 5},
        ...     {"status": "active", "count": 3}
        ... ]
        >>> aggregate_items(items, "status", {"count": "sum"})
        {"active": {"count": 8}}
    """
    # Properly handle mutable defaults
    if aggregations is None:
        aggregations = {}

    groups: Dict[str, List[Dict[str, Any]]] = {}

    # Group items
    for item in items:
        key = item.get(group_by)
        if key is not None:
            if key not in groups:
                groups[key] = []
            groups[key].append(item)

    # Aggregate each group
    results = {}
    for group_key, group_items in groups.items():
        group_result = {}

        for field, agg_type in aggregations.items():
            values = [
                item.get(field)
                for item in group_items
                if item.get(field) is not None
            ]

            if not values:
                group_result[field] = None
                continue

            if agg_type == "sum":
                group_result[field] = sum(values)
            elif agg_type == "count":
                group_result[field] = len(values)
            elif agg_type == "avg":
                group_result[field] = sum(values) / len(values)
            elif agg_type == "min":
                group_result[field] = min(values)
            elif agg_type == "max":
                group_result[field] = max(values)

        results[group_key] = group_result

    return results


def build_query_filter(
    include_status: Optional[List[str]] = None,
    exclude_status: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a query filter from common parameters.

    Args:
        include_status: List of statuses to include
        exclude_status: List of statuses to exclude
        tags: List of tags that items must have

    Returns:
        Dictionary representing the filter configuration

    Example:
        >>> build_query_filter(include_status=["active", "pending"])
        {"include_status": ["active", "pending"], "exclude_status": [], "tags": []}
    """
    # Properly handle mutable defaults
    if include_status is None:
        include_status = []
    if exclude_status is None:
        exclude_status = []
    if tags is None:
        tags = []

    return {
        "include_status": include_status,
        "exclude_status": exclude_status,
        "tags": tags,
    }

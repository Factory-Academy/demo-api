"""
Shared database helper functions for CRUD operations with common patterns.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException


def find_by_id(
    db: List[Dict[str, Any]], item_id: int, entity_name: str = "Item"
) -> Dict[str, Any]:
    """
    Find an item in the database by ID.

    Args:
        db: The database list to search
        item_id: The ID to search for
        entity_name: The name of the entity for error messages

    Returns:
        The found item dictionary

    Raises:
        HTTPException: 404 if item not found
    """
    for item in db:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail=f"{entity_name} not found")


def create_with_timestamps(
    db: List[Dict[str, Any]],
    data: Dict[str, Any],
    next_id: int,
) -> Tuple[Dict[str, Any], int]:
    """
    Create a new item with ID, created_at, and updated_at timestamps.

    Args:
        db: The database list to append to
        data: The item data (should be dict from model_dump)
        next_id: The current next ID counter

    Returns:
        Tuple of (created_item, new_next_id)
    """
    now = datetime.utcnow()
    db_item = {
        **data,
        "id": next_id,
        "created_at": now,
        "updated_at": now,
    }
    db.append(db_item)
    return db_item, next_id + 1


def update_by_id(
    db: List[Dict[str, Any]],
    item_id: int,
    update_data: Dict[str, Any],
    entity_name: str = "Item",
) -> Dict[str, Any]:
    """
    Update an item in the database by ID.

    Args:
        db: The database list to search
        item_id: The ID to search for
        update_data: The fields to update (exclude_unset applied by caller)
        entity_name: The name of the entity for error messages

    Returns:
        The updated item dictionary

    Raises:
        HTTPException: 404 if item not found
    """
    for i, existing in enumerate(db):
        if existing["id"] == item_id:
            update_data["updated_at"] = datetime.utcnow()
            db[i] = {**existing, **update_data}
            return db[i]
    raise HTTPException(status_code=404, detail=f"{entity_name} not found")


def delete_by_id(
    db: List[Dict[str, Any]], item_id: int, entity_name: str = "Item"
) -> bool:
    """
    Delete an item from the database by ID.

    Args:
        db: The database list to search
        item_id: The ID to search for
        entity_name: The name of the entity for error messages

    Returns:
        True if deleted

    Raises:
        HTTPException: 404 if item not found
    """
    for i, item in enumerate(db):
        if item["id"] == item_id:
            db.pop(i)
            return True
    raise HTTPException(status_code=404, detail=f"{entity_name} not found")

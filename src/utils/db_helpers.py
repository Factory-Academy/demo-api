from datetime import datetime
from typing import Any, Optional, List


def find_by_id(collection: List[dict], record_id: int) -> Optional[dict]:
    """
    Find a record by ID in a collection.
    
    Args:
        collection: List of dictionaries to search through
        record_id: ID to search for
        
    Returns:
        The matching record or None if not found
    """
    for record in collection:
        if record.get("id") == record_id:
            return record
    return None


def create_record(data: dict, record_id: int) -> dict:
    """
    Create a new database record with standard metadata fields.
    
    Args:
        data: The base data for the record
        record_id: The ID to assign to the new record
        
    Returns:
        A new record with id, created_at, and updated_at fields
    """
    now = datetime.utcnow()
    return {
        **data,
        "id": record_id,
        "created_at": now,
        "updated_at": now,
    }

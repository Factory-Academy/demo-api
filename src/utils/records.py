from datetime import datetime
from typing import Any, Dict


def utcnow() -> datetime:
    """Return the current UTC time."""
    return datetime.utcnow()


def prepare_new_record(data: Dict[str, Any], next_id: int) -> Dict[str, Any]:
    """
    Initialize a new database record with standard fields.
    
    Args:
        data: The record data from the request model.
        next_id: The ID to assign to the new record.
        
    Returns:
        A dictionary containing the data plus id, created_at, and updated_at.
    """
    now = datetime.utcnow()
    return {
        **data,
        "id": next_id,
        "created_at": now,
        "updated_at": now,
    }


def mark_updated(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Set the updated_at timestamp on a record.
    
    Args:
        record: The record (or update dict) to timestamp.
        
    Returns:
        The modified record.
    """
    record["updated_at"] = datetime.utcnow()
    return record

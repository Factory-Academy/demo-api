from typing import List, Any, TypeVar, Optional
from src.utils.exceptions import ResourceNotFoundError

T = TypeVar("T", bound=dict)

def find_or_404(collection: List[T], entity_id: int, entity_name: str) -> T:
    """
    Find an entity in a collection by ID or raise ResourceNotFoundError.
    """
    for item in collection:
        if item.get("id") == entity_id:
            return item
    raise ResourceNotFoundError(entity_name, entity_id)

def find_index_or_404(collection: List[T], entity_id: int, entity_name: str) -> int:
    """
    Find the index of an entity in a collection by ID or raise ResourceNotFoundError.
    """
    for i, item in enumerate(collection):
        if item.get("id") == entity_id:
            return i
    raise ResourceNotFoundError(entity_name, entity_id)

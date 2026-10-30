from typing import List, Any, TypeVar, Optional, Union
from src.utils.exceptions import ResourceNotFoundError, ValidationError

T = TypeVar("T", bound=dict)

def find_or_404(collection: List[T], entity_id: Any, entity_name: str) -> T:
    """
    Find an entity in a collection by ID or raise ResourceNotFoundError.
    """
    if entity_id is None:
        raise ValidationError(f"{entity_name} ID cannot be None")

    for item in collection:
        if item.get("id") == entity_id:
            return item
    raise ResourceNotFoundError(entity_name, entity_id)

def find_index_or_404(collection: List[T], entity_id: Any, entity_name: str) -> int:
    """
    Find the index of an entity in a collection by ID or raise ResourceNotFoundError.
    """
    if entity_id is None:
        raise ValidationError(f"{entity_name} ID cannot be None")

    for i, item in enumerate(collection):
        if item.get("id") == entity_id:
            return i
    raise ResourceNotFoundError(entity_name, entity_id)

def find_by_or_404(collection: List[T], entity_name: str, **kwargs) -> T:
    """
    Find an entity in a collection by arbitrary criteria or raise ResourceNotFoundError.
    """
    if not kwargs:
        raise ValidationError("Search criteria cannot be empty")

    for item in collection:
        if all(item.get(k) == v for k, v in kwargs.items()):
            return item
    
    raise ResourceNotFoundError(entity_name, **kwargs)

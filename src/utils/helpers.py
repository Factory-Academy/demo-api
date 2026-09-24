from typing import Iterable, Any, Optional
from src.utils.exceptions import ResourceNotFoundError

def find_entity_or_404(collection: Iterable[dict], key: str, value: Any, entity_name: str) -> dict:
    """
    Finds an entity in a collection by key/value or raises ResourceNotFoundError.
    """
    for item in collection:
        if item.get(key) == value:
            return item
    raise ResourceNotFoundError(entity_name, value)

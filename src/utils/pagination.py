from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")

class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    offset: int
    limit: int

def paginate(items: List[T], offset: int = 0, limit: int = 10) -> Page[T]:
    total = len(items)
    paginated_items = items[offset : offset + limit]
    return Page(
        items=paginated_items,
        total=total,
        offset=offset,
        limit=limit
    )

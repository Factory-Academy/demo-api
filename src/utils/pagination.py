from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


def paginate(
    items: Sequence[T],
    offset: int = 0,
    limit: int = 100,
    max_limit: int = 1000,
) -> Sequence[T]:
    """Paginate a sequence of items using offset and limit."""
    if offset < 0:
        raise ValueError("Offset cannot be negative")
    if limit <= 0:
        raise ValueError("Limit must be a positive integer")
    if limit > max_limit:
        raise ValueError(f"Limit cannot exceed {max_limit}")

    return items[offset : offset + limit]

from typing import TypeVar, Sequence

T = TypeVar("T")


def paginate(
    items: Sequence[T], offset: int = 0, limit: int = 100, max_limit: int = 1000
) -> Sequence[T]:
    """
    Paginates a sequence of items using offset and limit.

    Args:
        items: The sequence of items to paginate.
        offset: The number of items to skip. Defaults to 0.
        limit: The maximum number of items to return. Defaults to 100.
        max_limit: The maximum allowed value for limit. Defaults to 1000.

    Returns:
        The paginated sequence of items.

    Raises:
        ValueError: If offset is negative or limit is non-positive or exceeds max_limit.
    """
    if offset < 0:
        raise ValueError("Offset cannot be negative")
    if limit <= 0:
        raise ValueError("Limit must be a positive integer")
    if limit > max_limit:
        raise ValueError(f"Limit cannot exceed {max_limit}")

    return items[offset : offset + limit]

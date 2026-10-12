from typing import TypeVar, Sequence

T = TypeVar("T")


def paginate(items: Sequence[T], offset: int = 0, limit: int = 100) -> Sequence[T]:
    """
    Paginates a sequence of items using offset and limit.

    Args:
        items: The sequence of items to paginate.
        offset: The number of items to skip. Defaults to 0.
        limit: The maximum number of items to return. Defaults to 100.

    Returns:
        The paginated sequence of items.
    """
    if offset < 0:
        offset = 0
    if limit < 0:
        limit = 0

    return items[offset : offset + limit]

"""Pure helpers for pagination math."""


def page_bounds(total_items: int, page: int, page_size: int) -> tuple[int, int]:
    """Return half-open slice bounds ``[start, end)`` for a 1-based page."""
    if total_items < 0:
        raise ValueError("total_items must be >= 0")
    if page < 1:
        raise ValueError("page must be >= 1")
    if page_size < 1:
        raise ValueError("page_size must be >= 1")

    start = min((page - 1) * page_size, total_items)
    end = min(start + page_size, total_items)
    return start, end

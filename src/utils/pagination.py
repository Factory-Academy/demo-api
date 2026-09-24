"""Pagination utilities for list slicing and page range calculation."""


def get_page_range(page: int, page_size: int, total_items: int) -> tuple[int, int]:
    """
    Calculate the start and end indices for a page of items.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        total_items: Total number of items in the collection

    Returns:
        Tuple of (start_index, end_index) for slicing
    """
    if page < 1:
        raise ValueError("Page must be >= 1")
    if page_size < 1:
        raise ValueError("Page size must be >= 1")
    if total_items < 0:
        raise ValueError("Total items must be >= 0")

    start = (page - 1) * page_size
    end = min(start + page_size, total_items)

    return start, end


def paginate_list(items: list, page: int, page_size: int) -> list:
    """
    Return a page of items from a list.

    Args:
        items: List of items to paginate
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        List containing the requested page of items
    """
    start, end = get_page_range(page, page_size, len(items))
    return items[start:end]

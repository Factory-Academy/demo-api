import sys
from typing import Tuple


def get_page_indices(page: int, page_size: int, total: int) -> Tuple[int, int]:
    """Return (start, end) indices for slicing a collection into pages.
    
    Pages are 1-indexed. Returns indices suitable for Python slicing, where
    the end index is exclusive. Returns (0, 0) when the page is out of bounds.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        total: Total number of items in the collection
    
    Returns:
        A tuple (start, end) where start is inclusive and end is exclusive,
        matching Python slice semantics: collection[start:end]
    
    Examples:
        >>> get_page_indices(1, 10, 25)  # First page of 25 items
        (0, 10)
        >>> get_page_indices(2, 10, 25)  # Second page
        (10, 20)
        >>> get_page_indices(3, 10, 25)  # Last page (partial)
        (20, 25)
    """
    if page < 1 or page_size < 1 or total < 0:
        return (0, 0)
    
    # Guard against integer overflow when computing start index
    if page > sys.maxsize // page_size:
        return (0, 0)
    
    start = (page - 1) * page_size
    if start >= total:
        return (0, 0)
    
    end = start + page_size
    if end > total:
        end = total
    
    return (start, end)

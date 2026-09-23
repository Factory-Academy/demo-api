import pytest
from src.utils.pagination import get_page_range, paginate_list


def test_get_page_range_first_page():
    """Test first page returns correct range."""
    start, end = get_page_range(page=1, page_size=10, total_items=25)
    assert start == 0
    assert end == 10


def test_get_page_range_middle_page():
    """Test middle page returns correct range."""
    start, end = get_page_range(page=2, page_size=10, total_items=25)
    assert start == 10
    assert end == 20


def test_get_page_range_last_page_partial():
    """Test last page with fewer items than page_size."""
    start, end = get_page_range(page=3, page_size=10, total_items=25)
    assert start == 20
    assert end == 25


def test_get_page_range_exact_fit():
    """Test when total items exactly divides by page_size."""
    start, end = get_page_range(page=3, page_size=10, total_items=30)
    assert start == 20
    assert end == 30


def test_get_page_range_invalid_page():
    """Test error handling for invalid page number."""
    with pytest.raises(ValueError, match="Page must be >= 1"):
        get_page_range(page=0, page_size=10, total_items=25)


def test_get_page_range_invalid_page_size():
    """Test error handling for invalid page size."""
    with pytest.raises(ValueError, match="Page size must be >= 1"):
        get_page_range(page=1, page_size=0, total_items=25)


def test_paginate_list_returns_correct_items():
    """Regression test: verify each page returns the correct items."""
    items = list(range(25))  # [0, 1, 2, ..., 24]

    # Page 1: should get items 0-9
    page1 = paginate_list(items, page=1, page_size=10)
    assert page1 == list(range(0, 10))
    assert len(page1) == 10

    # Page 2: should get items 10-19
    page2 = paginate_list(items, page=2, page_size=10)
    assert page2 == list(range(10, 20))
    assert len(page2) == 10

    # Page 3: should get items 20-24 (only 5 items)
    page3 = paginate_list(items, page=3, page_size=10)
    assert page3 == list(range(20, 25))
    assert len(page3) == 5


def test_paginate_list_empty():
    """Test pagination with empty list."""
    items = []
    page = paginate_list(items, page=1, page_size=10)
    assert page == []


def test_paginate_list_single_item():
    """Test pagination with single item."""
    items = [42]
    page = paginate_list(items, page=1, page_size=10)
    assert page == [42]

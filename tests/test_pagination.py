from src.utils.pagination import get_page_indices


def test_first_page_full():
    """First page of a collection with multiple full pages."""
    start, end = get_page_indices(1, 10, 25)
    assert start == 0
    assert end == 10


def test_second_page_full():
    """Second page returns correct indices."""
    start, end = get_page_indices(2, 10, 25)
    assert start == 10
    assert end == 20


def test_last_page_partial():
    """Last page with fewer items than page_size."""
    start, end = get_page_indices(3, 10, 25)
    assert start == 20
    assert end == 25


def test_single_full_page():
    """Collection fits exactly in one page."""
    start, end = get_page_indices(1, 10, 10)
    assert start == 0
    assert end == 10


def test_page_beyond_bounds():
    """Requesting a page beyond the collection returns (0, 0)."""
    start, end = get_page_indices(5, 10, 25)
    assert start == 0
    assert end == 0


def test_invalid_page_number():
    """Zero or negative page numbers return (0, 0)."""
    assert get_page_indices(0, 10, 25) == (0, 0)
    assert get_page_indices(-1, 10, 25) == (0, 0)


def test_invalid_page_size():
    """Zero or negative page size returns (0, 0)."""
    assert get_page_indices(1, 0, 25) == (0, 0)
    assert get_page_indices(1, -5, 25) == (0, 0)


def test_empty_collection():
    """Empty collection returns (0, 0)."""
    start, end = get_page_indices(1, 10, 0)
    assert start == 0
    assert end == 0


def test_regression_off_by_one():
    """Regression test: slicing with returned indices should give correct count.
    
    Before fix: get_page_indices(1, 10, 25) returned (0, 9) instead of (0, 10),
    causing items[0:9] to return only 9 items instead of 10.
    """
    items = list(range(25))
    start, end = get_page_indices(1, 10, 25)
    page = items[start:end]
    assert len(page) == 10
    assert page == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


def test_regression_second_page():
    """Regression test: second page should have correct items."""
    items = list(range(25))
    start, end = get_page_indices(2, 10, 25)
    page = items[start:end]
    assert len(page) == 10
    assert page == [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]


def test_regression_last_partial_page():
    """Regression test: partial last page should have correct count."""
    items = list(range(25))
    start, end = get_page_indices(3, 10, 25)
    page = items[start:end]
    assert len(page) == 5
    assert page == [20, 21, 22, 23, 24]

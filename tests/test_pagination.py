import pytest

from src.utils.pagination import page_bounds


def test_page_bounds_second_page_exact_boundary_regression():
    # Regression: page 2 of 10-sized pages in a 20-item set must end at 20.
    assert page_bounds(total_items=20, page=2, page_size=10) == (10, 20)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"total_items": -1, "page": 1, "page_size": 10},
        {"total_items": 10, "page": 0, "page_size": 10},
        {"total_items": 10, "page": 1, "page_size": 0},
    ],
)
def test_page_bounds_rejects_invalid_inputs(kwargs):
    with pytest.raises(ValueError):
        page_bounds(**kwargs)

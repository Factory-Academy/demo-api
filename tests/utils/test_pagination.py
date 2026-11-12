import pytest

from src.utils.pagination import MAX_PAGE_LIMIT, paginate_offset_limit


def test_paginate_offset_limit_returns_requested_slice():
    items = [1, 2, 3, 4, 5]

    result = paginate_offset_limit(items, offset=1, limit=3)

    assert result == [2, 3, 4]


def test_paginate_offset_limit_returns_empty_when_offset_is_past_end():
    items = [1, 2, 3]

    result = paginate_offset_limit(items, offset=5, limit=2)

    assert result == []


@pytest.mark.parametrize(
    "offset,limit,error_message",
    [
        (-1, 1, "offset must be >= 0"),
        (0, 0, "limit must be >= 1"),
        (0, MAX_PAGE_LIMIT + 1, f"limit must be <= {MAX_PAGE_LIMIT}"),
    ],
)
def test_paginate_offset_limit_validates_inputs(offset, limit, error_message):
    with pytest.raises(ValueError, match=error_message):
        paginate_offset_limit([1, 2, 3], offset=offset, limit=limit)

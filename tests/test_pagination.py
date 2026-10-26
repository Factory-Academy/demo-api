from src.utils.pagination import paginate


def test_paginate_returns_exactly_limit_items():
    items = list(range(10))

    result = paginate(items, offset=2, limit=3)

    assert result == [2, 3, 4]

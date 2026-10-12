from src.utils.pagination import paginate


def test_paginate_basic():
    items = [1, 2, 3, 4, 5]
    assert paginate(items, offset=0, limit=2) == [1, 2]
    assert paginate(items, offset=2, limit=2) == [3, 4]
    assert paginate(items, offset=4, limit=2) == [5]
    assert paginate(items, offset=5, limit=2) == []


def test_paginate_defaults():
    items = list(range(150))
    result = paginate(items)
    assert len(result) == 100
    assert result[0] == 0
    assert result[-1] == 99


def test_paginate_negative_values():
    items = [1, 2, 3]
    # Negative offset should be treated as 0
    assert paginate(items, offset=-1, limit=2) == [1, 2]
    # Negative limit should be treated as 0
    assert paginate(items, offset=0, limit=-1) == []


def test_paginate_out_of_bounds():
    items = [1, 2, 3]
    assert paginate(items, offset=10, limit=5) == []

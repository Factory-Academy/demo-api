import pytest
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


def test_paginate_negative_offset():
    items = [1, 2, 3]
    with pytest.raises(ValueError, match="Offset cannot be negative"):
        paginate(items, offset=-1, limit=2)


def test_paginate_invalid_limit():
    items = [1, 2, 3]
    with pytest.raises(ValueError, match="Limit must be a positive integer"):
        paginate(items, offset=0, limit=0)
    with pytest.raises(ValueError, match="Limit must be a positive integer"):
        paginate(items, offset=0, limit=-1)


def test_paginate_max_limit():
    items = list(range(2000))
    with pytest.raises(ValueError, match="Limit cannot exceed 1000"):
        paginate(items, offset=0, limit=1001)
    
    # Custom max_limit
    assert len(paginate(items, offset=0, limit=50, max_limit=50)) == 50
    with pytest.raises(ValueError, match="Limit cannot exceed 50"):
        paginate(items, offset=0, limit=51, max_limit=50)


def test_paginate_out_of_bounds():
    items = [1, 2, 3]
    assert paginate(items, offset=10, limit=5) == []

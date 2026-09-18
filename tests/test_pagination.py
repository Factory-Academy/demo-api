from src.utils.pagination import paginate

def test_paginate_basic():
    items = list(range(20))
    page = paginate(items, offset=0, limit=10)
    assert page.items == list(range(10))
    assert page.total == 20
    assert page.offset == 0
    assert page.limit == 10

def test_paginate_offset():
    items = list(range(20))
    page = paginate(items, offset=5, limit=5)
    assert page.items == [5, 6, 7, 8, 9]
    assert page.total == 20
    assert page.offset == 5
    assert page.limit == 5

def test_paginate_empty():
    items = []
    page = paginate(items, offset=0, limit=10)
    assert page.items == []
    assert page.total == 0

def test_paginate_beyond_total():
    items = list(range(5))
    page = paginate(items, offset=10, limit=10)
    assert page.items == []
    assert page.total == 5
    assert page.offset == 10
    assert page.limit == 10

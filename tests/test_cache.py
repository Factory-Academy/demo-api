from src.utils.cache import ttl_cache


def test_ttl_cache_reuses_value_before_expiration():
    attempts = {"count": 0}

    @ttl_cache(ttl_seconds=10, maxsize=4)
    def compute(value):
        attempts["count"] += 1
        return value * 2

    assert compute(3) == 6
    assert compute(3) == 6
    assert attempts["count"] == 1


def test_ttl_cache_expires_entries_after_ttl():
    now = {"value": 100.0}
    attempts = {"count": 0}

    def fake_time():
        return now["value"]

    @ttl_cache(ttl_seconds=5, maxsize=4, time_func=fake_time)
    def compute(value):
        attempts["count"] += 1
        return value * 3

    assert compute(2) == 6
    now["value"] += 3
    assert compute(2) == 6
    now["value"] += 3
    assert compute(2) == 6
    assert attempts["count"] == 2


def test_ttl_cache_evicts_least_recently_used_entry():
    calls = {}

    @ttl_cache(ttl_seconds=60, maxsize=2)
    def compute(value):
        calls[value] = calls.get(value, 0) + 1
        return value

    assert compute(1) == 1
    assert compute(2) == 2
    assert compute(1) == 1
    assert compute(3) == 3
    assert compute(2) == 2

    assert calls[1] == 1
    assert calls[2] == 2
    assert calls[3] == 1

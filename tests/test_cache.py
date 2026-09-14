import time

import pytest

from src.utils.cache import ttl_cache


def test_ttl_cache_returns_cached_value_within_ttl():
    attempts = {"count": 0}

    @ttl_cache(ttl_seconds=1, maxsize=10)
    def square(value: int) -> int:
        attempts["count"] += 1
        return value * value

    assert square(3) == 9
    assert square(3) == 9
    assert attempts["count"] == 1


def test_ttl_cache_expires_entries_after_ttl():
    attempts = {"count": 0}

    @ttl_cache(ttl_seconds=0.01, maxsize=10)
    def multiply_by_two(value: int) -> int:
        attempts["count"] += 1
        return value * 2

    assert multiply_by_two(4) == 8
    time.sleep(0.02)
    assert multiply_by_two(4) == 8
    assert attempts["count"] == 2


def test_ttl_cache_evicts_oldest_entry_when_maxsize_is_reached():
    attempts = {"count": 0}

    @ttl_cache(ttl_seconds=60, maxsize=2)
    def identity(value: int) -> int:
        attempts["count"] += 1
        return value

    assert identity(1) == 1
    assert identity(2) == 2
    assert identity(3) == 3
    assert identity(1) == 1
    assert attempts["count"] == 4


@pytest.mark.parametrize(
    "ttl_seconds,maxsize,error_message",
    [
        (0, 1, "ttl_seconds must be greater than 0"),
        (1, 0, "maxsize must be at least 1"),
    ],
)
def test_ttl_cache_rejects_invalid_configuration(
    ttl_seconds: float, maxsize: int, error_message: str
):
    with pytest.raises(ValueError, match=error_message):
        ttl_cache(ttl_seconds=ttl_seconds, maxsize=maxsize)

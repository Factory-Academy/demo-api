import asyncio

from fastapi.testclient import TestClient

from src.main import app
from src.routes import widget_routes
from src.utils.cache import retry, ttl_cache

client = TestClient(app)


def test_ttl_cache_reuses_value_until_expired(monkeypatch):
    clock = {"now": 100.0}
    call_count = {"value": 0}

    def fake_monotonic():
        return clock["now"]

    monkeypatch.setattr("src.utils.cache.time.monotonic", fake_monotonic)

    @ttl_cache(ttl_seconds=10, maxsize=10)
    def square(value):
        call_count["value"] += 1
        return value * value

    assert square(3) == 9
    assert square(3) == 9
    assert call_count["value"] == 1

    clock["now"] += 11
    assert square(3) == 9
    assert call_count["value"] == 2


def test_ttl_cache_enforces_maxsize_lru(monkeypatch):
    monkeypatch.setattr("src.utils.cache.time.monotonic", lambda: 10.0)
    calls = []

    @ttl_cache(ttl_seconds=60, maxsize=2)
    def compute(value):
        calls.append(value)
        return value

    assert compute(1) == 1
    assert compute(2) == 2
    assert compute(1) == 1
    assert compute(3) == 3
    assert compute(2) == 2

    assert calls == [1, 2, 3, 2]


def test_ttl_cache_supports_async_functions(monkeypatch):
    monkeypatch.setattr("src.utils.cache.time.monotonic", lambda: 50.0)
    call_count = {"value": 0}

    @ttl_cache(ttl_seconds=30, maxsize=4)
    async def compute(value):
        call_count["value"] += 1
        return value + 7

    assert asyncio.run(compute(5)) == 12
    assert asyncio.run(compute(5)) == 12
    assert call_count["value"] == 1


def test_get_widget_route_uses_cache():
    widget_routes.widgets_db.clear()
    widget_routes.next_id = 1
    widget_routes.get_widget.cache_clear()

    create_response = client.post(
        "/widgets/",
        json={"name": "Original", "item_id": 10, "priority": 1},
    )
    assert create_response.status_code == 201

    first = client.get("/widgets/1")
    assert first.status_code == 200
    assert first.json()["name"] == "Original"

    widget_routes.widgets_db[0] = {
        **widget_routes.widgets_db[0],
        "name": "Updated",
    }

    second = client.get("/widgets/1")
    assert second.status_code == 200
    assert second.json()["name"] == "Original"


def test_retry_retries_until_success():
    calls = {"count": 0}

    @retry(attempts=3)
    def sometimes_fails():
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError("temporary")
        return "ok"

    assert sometimes_fails() == "ok"
    assert calls["count"] == 3


def test_retry_raises_after_max_attempts():
    calls = {"count": 0}

    @retry(attempts=2, exceptions=(ValueError,))
    def always_fails():
        calls["count"] += 1
        raise ValueError("still failing")

    try:
        always_fails()
        assert False, "Expected ValueError"
    except ValueError:
        assert calls["count"] == 2

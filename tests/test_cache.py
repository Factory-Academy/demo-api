import time

from fastapi.testclient import TestClient

from src.main import app
from src.routes import item_routes
from src.utils.cache import ttl_cache

client = TestClient(app)


def setup_function():
    item_routes.items_db.clear()
    item_routes.next_id = 1
    item_routes.find_item_by_id.cache_clear()


def test_ttl_cache_reuses_value_before_expiration():
    calls = {"count": 0}

    @ttl_cache(ttl_seconds=1, maxsize=10)
    def compute(value: int):
        calls["count"] += 1
        return calls["count"] + value

    assert compute(2) == 3
    assert compute(2) == 3
    assert calls["count"] == 1


def test_ttl_cache_expires_entries():
    calls = {"count": 0}

    @ttl_cache(ttl_seconds=0.05, maxsize=10)
    def compute(value: int):
        calls["count"] += 1
        return calls["count"] + value

    first = compute(1)
    time.sleep(0.06)
    second = compute(1)

    assert second != first
    assert calls["count"] == 2


def test_ttl_cache_evicts_oldest_entry_when_maxsize_reached():
    calls = {"count": 0}

    @ttl_cache(ttl_seconds=1, maxsize=2)
    def compute(value: int):
        calls["count"] += 1
        return calls["count"] + value

    compute(1)
    compute(2)
    compute(3)
    compute(1)

    assert calls["count"] == 4


def test_item_lookup_cache_is_cleared_after_update():
    create_response = client.post("/items/", json={"name": "Original"})
    created = create_response.json()

    first_get = client.get(f"/items/{created['id']}")
    assert first_get.status_code == 200
    assert first_get.json()["name"] == "Original"

    update_response = client.put(f"/items/{created['id']}", json={"name": "Updated"})
    assert update_response.status_code == 200

    second_get = client.get(f"/items/{created['id']}")
    assert second_get.status_code == 200
    assert second_get.json()["name"] == "Updated"

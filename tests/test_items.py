import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.routes import item_routes

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_items_db():
    item_routes.items_db.clear()
    item_routes.next_id = 1
    yield
    item_routes.items_db.clear()
    item_routes.next_id = 1


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_items_empty():
    response = client.get("/items/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_item():
    response = client.post(
        "/items/",
        json={"name": "Test Item", "description": "A test item"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Item"


def test_list_items_supports_offset_limit_pagination():
    client.post("/items/", json={"name": "Item 1", "description": "A"})
    client.post("/items/", json={"name": "Item 2", "description": "B"})
    client.post("/items/", json={"name": "Item 3", "description": "C"})

    response = client.get("/items/?offset=1&limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["name"] == "Item 2"

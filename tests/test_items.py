from fastapi.testclient import TestClient
from src.main import app
from src.routes import item_routes

client = TestClient(app)


def setup_function():
    item_routes.items_db.clear()
    item_routes.next_id = 1


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_items_empty():
    response = client.get("/items/")
    assert response.status_code == 200


def test_create_item():
    response = client.post(
        "/items/",
        json={"name": "Test Item", "description": "A test item"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Item"


def test_get_item_ignores_malformed_records():
    item_routes.items_db.extend([None, {"name": "missing id"}])

    response = client.get("/items/1")

    assert response.status_code == 404
    assert response.json() == {"detail": "Item not found"}

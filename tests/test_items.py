from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


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


def test_update_item_touches_only_provided_fields():
    created = client.post("/items/", json={"name": "Before"}).json()
    updated = client.put(f"/items/{created['id']}", json={"status": "archived"})
    assert updated.status_code == 200
    body = updated.json()
    assert body["name"] == "Before"  # unchanged
    assert body["status"] == "archived"


def test_update_missing_item_returns_404():
    assert client.put("/items/999999", json={"name": "x"}).status_code == 404


def test_delete_item():
    created = client.post("/items/", json={"name": "Doomed"}).json()
    assert client.delete(f"/items/{created['id']}").status_code == 200
    assert client.get(f"/items/{created['id']}").status_code == 404


def test_delete_missing_item_returns_404():
    assert client.delete("/items/999999").status_code == 404

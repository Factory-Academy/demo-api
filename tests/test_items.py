from fastapi.testclient import TestClient
from src.main import app
from src.services.item_service import ItemService

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_items_empty():
    response = client.get("/items/")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_items_pagination():
    # Create 15 items
    for i in range(15):
        client.post(
            "/items/",
            json={"name": f"Item {i}", "description": "Test description"},
        )

    # Test first page
    response = client.get("/items/?offset=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] >= 15
    assert data["offset"] == 0
    assert data["limit"] == 10

    # Test second page
    response = client.get("/items/?offset=10&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 5
    assert data["offset"] == 10


def test_create_item():
    response = client.post(
        "/items/",
        json={"name": "Test Item", "description": "A test item"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Item"


def test_calculate_priority_missing_created_at_uses_default():
    service = ItemService(db=None)
    priority = service.calculate_priority({"urgency": 1})
    assert priority == "low"

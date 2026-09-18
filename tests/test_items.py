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

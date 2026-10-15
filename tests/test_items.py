from fastapi.testclient import TestClient
from datetime import datetime, timedelta

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


def test_calculate_priority_optional_age_bonus():
    service = ItemService(db=None)
    item = {"created_at": datetime.utcnow() - timedelta(days=100), "urgency": 2}

    assert service.calculate_priority(item) == "high"
    assert service.calculate_priority(item, include_age_bonus=False) == "medium"


def test_calculate_priority_without_created_at_when_age_bonus_disabled():
    service = ItemService(db=None)
    item = {"urgency": 2}

    assert service.calculate_priority(item, include_age_bonus=False) == "medium"

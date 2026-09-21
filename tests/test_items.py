import time
from datetime import datetime
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


def test_calculate_priority_caching():
    """Test that calculate_priority uses caching correctly."""
    service = ItemService(db=None)
    
    # Clear cache before test
    service.calculate_priority.cache.clear()
    
    item = {"urgency": 5, "is_critical": True, "created_at": datetime.utcnow()}
    
    # First call should compute
    initial_cache_size = len(service.calculate_priority.cache)
    priority1 = service.calculate_priority(item)
    new_cache_size = len(service.calculate_priority.cache)
    
    # Cache should have one more entry
    assert new_cache_size == initial_cache_size + 1
    
    # Second call with same item should use cache
    priority2 = service.calculate_priority(item)
    assert priority1 == priority2
    assert len(service.calculate_priority.cache) == new_cache_size


def test_calculate_priority_cache_different_items():
    """Test that different items create separate cache entries."""
    service = ItemService(db=None)
    service.calculate_priority.cache.clear()
    
    item1 = {"urgency": 5, "is_critical": False}
    item2 = {"urgency": 10, "is_critical": True}
    
    priority1 = service.calculate_priority(item1)
    priority2 = service.calculate_priority(item2)
    
    # Should have two cache entries
    assert len(service.calculate_priority.cache) == 2
    assert priority1 != priority2

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


def test_calculate_priority_with_multiplier():
    from src.services.item_service import ItemService
    from datetime import datetime, timedelta
    
    service = ItemService(db={})
    item = {
        "created_at": datetime.utcnow() - timedelta(days=1),
        "urgency": 5,
        "is_critical": False
    }
    
    # 5 * 10 * 1.0 = 50 -> high
    assert service.calculate_priority(item) == "high"
    
    # 5 * 10 * 0.2 = 10 -> low
    assert service.calculate_priority(item, multiplier=0.2) == "low"
    
    # 5 * 10 * 2.0 = 100 -> critical
    assert service.calculate_priority(item, multiplier=2.0) == "critical"

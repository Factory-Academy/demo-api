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


def test_list_items_pagination():
    # Add multiple items to test pagination
    # First, get current count
    current_count = len(client.get("/items/").json())
    
    for i in range(5):
        client.post("/items/", json={"name": f"Pagination Item {i}"})
    
    # Test offset and limit
    response = client.get(f"/items/?offset={current_count}&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Pagination Item 0"
    assert data[1]["name"] == "Pagination Item 1"

    # Test another offset
    response = client.get(f"/items/?offset={current_count + 2}&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Pagination Item 2"
    assert data[1]["name"] == "Pagination Item 3"

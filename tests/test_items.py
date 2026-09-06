from fastapi.testclient import TestClient
from src.main import app
from src.services.item_service import retry

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


def test_get_item_by_id():
    """Test that refactored find_by_id helper works in GET endpoint."""
    # Create an item first
    create_response = client.post(
        "/items/",
        json={"name": "Get Test Item", "description": "Test"},
    )
    item_id = create_response.json()["id"]

    # Retrieve it using the refactored find_by_id helper
    response = client.get(f"/items/{item_id}")
    assert response.status_code == 200
    assert response.json()["id"] == item_id
    assert response.json()["name"] == "Get Test Item"


def test_get_item_not_found():
    """Test that find_by_id helper returns 404 correctly."""
    response = client.get("/items/99999")
    assert response.status_code == 404


def test_update_item():
    """Test that refactored update_by_id helper works in PUT endpoint."""
    # Create an item first
    create_response = client.post(
        "/items/",
        json={"name": "Update Test", "description": "Original"},
    )
    item_id = create_response.json()["id"]

    # Update it using the refactored update_by_id helper
    update_response = client.put(
        f"/items/{item_id}",
        json={"name": "Updated Name", "description": "Updated"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Name"
    assert update_response.json()["id"] == item_id


def test_update_item_not_found():
    """Test that update_by_id helper returns 404 when item not found."""
    response = client.put(
        "/items/99999",
        json={"name": "Updated"},
    )
    assert response.status_code == 404


def test_delete_item():
    """Test that refactored delete_by_id helper works in DELETE endpoint."""
    # Create an item first
    create_response = client.post(
        "/items/",
        json={"name": "Delete Test", "description": "Test"},
    )
    item_id = create_response.json()["id"]

    # Delete it using the refactored delete_by_id helper
    delete_response = client.delete(f"/items/{item_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"

    # Verify it's gone by trying to get it
    get_response = client.get(f"/items/{item_id}")
    assert get_response.status_code == 404


def test_delete_item_not_found():
    """Test that delete_by_id helper returns 404 when item not found."""
    response = client.delete("/items/99999")
    assert response.status_code == 404


def test_retry_succeeds_after_transient_failure():
    state = {"attempts": 0}

    def flaky_operation():
        state["attempts"] += 1
        if state["attempts"] < 3:
            raise ValueError("temporary issue")
        return "ok"

    result = retry(flaky_operation, attempts=3, exceptions=(ValueError,))
    assert result == "ok"
    assert state["attempts"] == 3

from fastapi.testclient import TestClient
from src.main import app
import pytest

client = TestClient(app)

def test_get_item_not_found_custom_message():
    """Verify that ResourceNotFoundError is handled and returns a clear message."""
    response = client.get("/items/9999")
    assert response.status_code == 404
    # The message comes from ResourceNotFoundError
    assert response.json()["detail"] == "Item with ID 9999 not found"

def test_update_item_not_found_custom_message():
    response = client.put("/items/9999", json={"name": "New Name"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Item with ID 9999 not found"

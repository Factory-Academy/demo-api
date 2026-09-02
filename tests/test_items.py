import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.routes import item_routes

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_item_store():
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


def test_create_item_forces_inactive_status_when_flag_enabled(monkeypatch):
    monkeypatch.setenv("FEATURE_ITEMS_FORCE_INACTIVE_STATUS", "true")

    response = client.post(
        "/items/",
        json={
            "name": "Flagged Item",
            "description": "A flagged item",
            "status": "active",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "inactive"

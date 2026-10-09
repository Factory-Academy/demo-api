import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.routes import item_routes, widget_routes

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_in_memory_data():
    item_routes.items_db.clear()
    item_routes.next_id = 1
    widget_routes.widgets_db.clear()
    widget_routes.next_id = 1


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


def test_create_widget():
    response = client.post(
        "/widgets/",
        json={"name": "Test Widget", "item_id": 1, "priority": 2},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Test Widget"
    assert body["id"] == 1


def test_update_item_skips_malformed_records():
    item_routes.items_db.extend(
        [
            {"name": "invalid-record"},
            {
                "id": 2,
                "name": "Target Item",
                "description": "before",
                "status": "active",
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
            },
        ]
    )

    response = client.put("/items/2", json={"description": "after"})

    assert response.status_code == 200
    assert response.json()["description"] == "after"

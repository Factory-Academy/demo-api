import pytest
from fastapi.testclient import TestClient

from src.main import app, audit_log
from src.routes import item_routes

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    item_routes.items_db.clear()
    item_routes.next_id = 1
    audit_log.clear()
    yield
    audit_log.clear()


def test_create_item_publishes_item_created():
    response = client.post("/items/", json={"name": "Widget A"})

    assert response.status_code == 201
    assert audit_log.names() == ["ItemCreated"]
    entry = audit_log.entries[0]
    assert entry.payload["item_id"] == response.json()["id"]
    assert entry.payload["name"] == "Widget A"


def test_update_item_publishes_item_updated_with_changed_fields():
    created = client.post("/items/", json={"name": "Widget A"}).json()
    audit_log.clear()

    response = client.put(f"/items/{created['id']}", json={"status": "archived"})

    assert response.status_code == 200
    assert audit_log.names() == ["ItemUpdated"]
    payload = audit_log.entries[0].payload
    assert payload["item_id"] == created["id"]
    assert payload["changed_fields"] == ("status",)
    assert payload["status"] == "archived"


def test_delete_item_publishes_item_deleted():
    created = client.post("/items/", json={"name": "Widget A"}).json()
    audit_log.clear()

    response = client.delete(f"/items/{created['id']}")

    assert response.status_code == 200
    assert audit_log.names() == ["ItemDeleted"]
    assert audit_log.entries[0].payload["item_id"] == created["id"]


def test_failed_update_publishes_no_event():
    response = client.put("/items/999", json={"status": "archived"})

    assert response.status_code == 404
    assert audit_log.entries == []


def test_failed_delete_publishes_no_event():
    response = client.delete("/items/999")

    assert response.status_code == 404
    assert audit_log.entries == []


def test_full_lifecycle_records_each_event_once():
    created = client.post("/items/", json={"name": "Widget A"}).json()
    client.put(f"/items/{created['id']}", json={"status": "archived"})
    client.delete(f"/items/{created['id']}")

    assert audit_log.names() == ["ItemCreated", "ItemUpdated", "ItemDeleted"]

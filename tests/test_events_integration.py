import pytest
from fastapi.testclient import TestClient

from src.events import (
    AuditLog,
    EventBus,
    ItemCreated,
    ItemDeleted,
    ItemUpdated,
    get_audit_log,
    reset_event_bus,
)
from src.main import app
from src.routes import item_routes


@pytest.fixture
def client():
    # Each test gets a clean bus, audit trail, and item store so state does
    # not leak between tests.
    reset_event_bus()
    audit = get_audit_log()
    # Drop any subscription left pointing at a previous bus so that startup
    # cleanly re-attaches the singleton audit log to the fresh default bus.
    audit.detach()
    audit.clear()
    item_routes.items_db.clear()
    item_routes.next_id = 1
    with TestClient(app) as test_client:  # triggers startup -> audit attach
        yield test_client


def test_audit_log_records_item_lifecycle():
    bus = EventBus()
    audit = AuditLog()
    audit.attach(bus)

    bus.publish(ItemCreated(item_id=1, item={"id": 1, "name": "a"}))
    bus.publish(ItemUpdated(item_id=1, changes={"status": "done"}))
    bus.publish(ItemDeleted(item_id=1))

    entries = audit.entries()
    assert [e["event"] for e in entries] == [
        "ItemCreated",
        "ItemUpdated",
        "ItemDeleted",
    ]
    assert entries[1]["payload"] == {"changes": {"status": "done"}}
    assert all(e["item_id"] == 1 for e in entries)


def test_audit_attach_is_idempotent():
    bus = EventBus()
    audit = AuditLog()
    audit.attach(bus)
    audit.attach(bus)

    assert bus.subscriber_count() == 1


def test_audit_detach_stops_recording():
    bus = EventBus()
    audit = AuditLog()
    audit.attach(bus)
    audit.detach()

    bus.publish(ItemCreated(item_id=1))
    assert audit.entries() == []


def test_audit_log_is_bounded():
    audit = AuditLog(max_entries=3)
    bus = EventBus()
    audit.attach(bus)

    for i in range(5):
        bus.publish(ItemCreated(item_id=i))

    entries = audit.entries()
    assert len(entries) == 3
    assert [e["item_id"] for e in entries] == [2, 3, 4]


def test_audit_log_rejects_non_positive_capacity():
    with pytest.raises(ValueError):
        AuditLog(max_entries=0)


def test_create_item_route_emits_and_audits_event(client):
    response = client.post("/items/", json={"name": "Widget", "description": "d"})
    assert response.status_code == 201
    created_id = response.json()["id"]

    audit = client.get("/items/events/audit")
    assert audit.status_code == 200
    entries = audit.json()
    assert len(entries) == 1
    assert entries[0]["event"] == "ItemCreated"
    assert entries[0]["item_id"] == created_id


def test_update_item_route_emits_update_event(client):
    created = client.post("/items/", json={"name": "Widget"}).json()
    client.put(f"/items/{created['id']}", json={"status": "archived"})

    entries = client.get("/items/events/audit").json()
    assert [e["event"] for e in entries] == ["ItemCreated", "ItemUpdated"]
    assert entries[1]["payload"]["changes"]["status"] == "archived"


def test_delete_item_route_emits_delete_event(client):
    created = client.post("/items/", json={"name": "Widget"}).json()
    client.delete(f"/items/{created['id']}")

    entries = client.get("/items/events/audit").json()
    assert [e["event"] for e in entries] == ["ItemCreated", "ItemDeleted"]


def test_update_missing_item_emits_no_event(client):
    response = client.put("/items/999", json={"status": "x"})
    assert response.status_code == 404
    assert client.get("/items/events/audit").json() == []


def test_delete_missing_item_emits_no_event(client):
    response = client.delete("/items/999")
    assert response.status_code == 404
    assert client.get("/items/events/audit").json() == []

import pytest
from fastapi.testclient import TestClient

from src.error_handling import ResourceNotFoundError, get_resource_by_id
from src.main import app
from src.routes import item_routes, widget_routes

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_in_memory_data():
    item_routes.items_db.clear()
    item_routes.next_id = 1
    widget_routes.widgets_db.clear()
    widget_routes.next_id = 1


def test_get_resource_by_id_returns_matching_record():
    records = [{"id": 1, "name": "Sample"}]

    result = get_resource_by_id(records, resource="Item", resource_id=1)

    assert result == {"id": 1, "name": "Sample"}


def test_get_resource_by_id_raises_shared_not_found_error():
    with pytest.raises(ResourceNotFoundError) as exc_info:
        get_resource_by_id([], resource="Widget", resource_id=44)

    assert str(exc_info.value) == "Widget with id 44 was not found"


def test_get_item_not_found_returns_consistent_404_payload():
    response = client.get("/items/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Item with id 999 was not found"}


def test_get_widget_not_found_returns_consistent_404_payload():
    response = client.get("/widgets/321")

    assert response.status_code == 404
    assert response.json() == {"detail": "Widget with id 321 was not found"}

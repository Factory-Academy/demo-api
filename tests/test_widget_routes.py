from fastapi.testclient import TestClient

from src.main import app
from src.routes import widget_routes

client = TestClient(app)


def setup_function():
    widget_routes.widgets_db.clear()
    widget_routes.next_id = 1


def test_get_widget_returns_404_when_missing():
    response = client.get("/widgets/123")

    assert response.status_code == 404
    assert response.json() == {"detail": "Widget not found"}


def test_get_widget_stats_returns_404_when_missing():
    response = client.get("/widgets/123/stats")

    assert response.status_code == 404
    assert response.json() == {"detail": "Widget not found"}


def test_get_widget_stats_returns_stats_for_existing_widget():
    create_response = client.post(
        "/widgets/",
        json={"name": "W1", "item_id": 10, "priority": 1},
    )
    widget_id = create_response.json()["id"]

    response = client.get(f"/widgets/{widget_id}/stats")

    assert response.status_code == 200
    assert response.json()["id"] == widget_id

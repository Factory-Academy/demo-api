from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_create_and_get_widget():
    created = client.post(
        "/widgets/",
        json={"name": "Gadget", "item_id": 1, "priority": 2},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Gadget"
    assert body["item_id"] == 1
    assert body["priority"] == 2
    assert "created_at" in body

    fetched = client.get(f"/widgets/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


def test_get_missing_widget_returns_404():
    assert client.get("/widgets/999999").status_code == 404


def test_list_widgets_returns_200():
    assert client.get("/widgets/").status_code == 200

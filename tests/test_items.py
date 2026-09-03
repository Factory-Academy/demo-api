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

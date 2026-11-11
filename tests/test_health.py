from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_healthz_returns_ok():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.text == "ok"
    assert response.headers["content-type"].startswith("text/plain")

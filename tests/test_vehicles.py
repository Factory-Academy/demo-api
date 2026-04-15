from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_vehicles_empty():
    response = client.get("/vehicles/")
    assert response.status_code == 200


def test_create_vehicle():
    response = client.post(
        "/vehicles/",
        json={
            "vin": "1FVNY5Y90HP312345",
            "model_name": "R1T",
            "model_year": 2025,
        },
    )
    assert response.status_code == 201
    assert response.json()["model_name"] == "R1T"

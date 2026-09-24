import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.utils.exceptions import ResourceNotFoundError, ValidationError
from src.utils.helpers import find_entity_or_404

client = TestClient(app)

def test_resource_not_found_exception_handler():
    response = client.get("/items/999")
    assert response.status_code == 404
    assert "Item with identifier 999 not found" in response.json()["detail"]

def test_find_entity_or_404_success():
    collection = [{"id": 1, "name": "Test"}]
    result = find_entity_or_404(collection, "id", 1, "TestItem")
    assert result == {"id": 1, "name": "Test"}

def test_find_entity_or_404_failure():
    collection = [{"id": 1, "name": "Test"}]
    with pytest.raises(ResourceNotFoundError) as excinfo:
        find_entity_or_404(collection, "id", 2, "TestItem")
    assert excinfo.value.status_code == 404
    assert "TestItem with identifier 2 not found" in str(excinfo.value)

def test_validation_error():
    with pytest.raises(ValidationError) as excinfo:
        raise ValidationError("Invalid input")
    assert excinfo.value.status_code == 400
    assert excinfo.value.message == "Invalid input"

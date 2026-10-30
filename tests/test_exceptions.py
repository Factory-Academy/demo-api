import pytest
import json
from src.utils.exceptions import AppError, ResourceNotFoundError, ValidationError
from src.utils.shortcuts import find_or_404, find_index_or_404, find_by_or_404
from src.main import app_error_handler

@pytest.mark.asyncio
async def test_app_error_handler_resource_not_found():
    exc = ResourceNotFoundError("Widget", 42)
    request = None
    response = await app_error_handler(request, exc)
    
    assert response.status_code == 404
    content = json.loads(response.body)
    assert content["detail"] == "Widget with ID 42 not found"
    assert content["resource_type"] == "Widget"
    assert content["resource_id"] == 42

@pytest.mark.asyncio
async def test_app_error_handler_validation_error():
    exc = ValidationError(["Invalid name", "Invalid quantity"])
    request = None
    response = await app_error_handler(request, exc)
    
    assert response.status_code == 400
    content = json.loads(response.body)
    assert "Validation failed" in content["detail"]
    assert "Invalid name" in content["errors"]
    assert "Invalid quantity" in content["errors"]

def test_find_or_404_none_id():
    with pytest.raises(ValidationError) as excinfo:
        find_or_404([], None, "Item")
    assert "ID cannot be None" in str(excinfo.value)

def test_find_by_or_404_success():
    collection = [{"id": 1, "name": "One", "type": "A"}, {"id": 2, "name": "Two", "type": "B"}]
    result = find_by_or_404(collection, "Item", type="B")
    assert result == {"id": 2, "name": "Two", "type": "B"}

def test_find_by_or_404_raises():
    collection = [{"id": 1, "name": "One"}]
    with pytest.raises(ResourceNotFoundError) as excinfo:
        find_by_or_404(collection, "Item", name="Two")
    assert "Item with name=Two not found" in str(excinfo.value)

def test_find_or_404_success():
    collection = [{"id": 1, "name": "One"}, {"id": 2, "name": "Two"}]
    result = find_or_404(collection, 1, "Item")
    assert result == {"id": 1, "name": "One"}

def test_find_or_404_raises():
    collection = [{"id": 1, "name": "One"}]
    with pytest.raises(ResourceNotFoundError) as excinfo:
        find_or_404(collection, 2, "Item")
    assert str(excinfo.value) == "Item with ID 2 not found"

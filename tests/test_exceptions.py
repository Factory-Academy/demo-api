import pytest
from fastapi import Request
from fastapi.responses import JSONResponse
from src.utils.exceptions import ResourceNotFoundError, ValidationError
from src.utils.shortcuts import find_or_404, find_index_or_404
from src.main import resource_not_found_handler, validation_error_handler

@pytest.mark.asyncio
async def test_resource_not_found_handler():
    exc = ResourceNotFoundError("Widget", 42)
    request = None  # Not used in the handler
    response = await resource_not_found_handler(request, exc)
    
    assert response.status_code == 404
    assert response.body == b'{"detail":"Widget with ID 42 not found"}'

@pytest.mark.asyncio
async def test_validation_error_handler():
    exc = ValidationError(["Invalid name", "Invalid quantity"])
    request = None
    response = await validation_error_handler(request, exc)
    
    assert response.status_code == 400
    assert b"Validation failed" in response.body
    assert b"Invalid name" in response.body

def test_find_or_404_success():
    collection = [{"id": 1, "name": "One"}, {"id": 2, "name": "Two"}]
    result = find_or_404(collection, 1, "Item")
    assert result == {"id": 1, "name": "One"}

def test_find_or_404_raises():
    collection = [{"id": 1, "name": "One"}]
    with pytest.raises(ResourceNotFoundError) as excinfo:
        find_or_404(collection, 2, "Item")
    assert str(excinfo.value) == "Item with ID 2 not found"

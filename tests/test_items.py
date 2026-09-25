import os
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.utils.feature_flags import flags

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


def test_item_stats_disabled(monkeypatch):
    """Test that item stats endpoint is disabled by default."""
    monkeypatch.delenv("FEATURE_ITEM_STATS", raising=False)
    flags.clear_cache()
    
    response = client.get("/items/stats/summary")
    assert response.status_code == 403
    assert response.json()["detail"] == "Feature not enabled"


def test_item_stats_enabled(monkeypatch):
    """Test that item stats endpoint works when feature is enabled."""
    monkeypatch.setenv("FEATURE_ITEM_STATS", "true")
    flags.clear_cache()
    
    response = client.get("/items/stats/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_items" in data
    assert "active_items" in data

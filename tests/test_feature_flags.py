"""Tests for feature flag helper."""

import os
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from src.utils.feature_flags import FeatureFlags, flags


@pytest.fixture
def feature_flags():
    """Create a fresh FeatureFlags instance for each test."""
    ff = FeatureFlags(prefix="TEST_FLAG_")
    yield ff
    ff.clear_cache()


def test_is_enabled_true_values(feature_flags, monkeypatch):
    """Test that various truthy values enable flags."""
    for value in ["true", "True", "TRUE", "1", "yes", "Yes", "YES"]:
        monkeypatch.setenv("TEST_FLAG_MY_FLAG", value)
        feature_flags.clear_cache()
        assert feature_flags.is_enabled("my_flag") is True


def test_is_enabled_false_values(feature_flags, monkeypatch):
    """Test that missing or falsy values disable flags."""
    for value in ["false", "0", "no", "", "anything"]:
        monkeypatch.setenv("TEST_FLAG_MY_FLAG", value)
        feature_flags.clear_cache()
        assert feature_flags.is_enabled("my_flag") is False


def test_is_enabled_unset(feature_flags, monkeypatch):
    """Test that unset environment variables default to disabled."""
    monkeypatch.delenv("TEST_FLAG_MY_FLAG", raising=False)
    feature_flags.clear_cache()
    assert feature_flags.is_enabled("my_flag") is False


def test_is_enabled_case_insensitive(feature_flags, monkeypatch):
    """Test that flag names are case-insensitive."""
    monkeypatch.setenv("TEST_FLAG_MY_FLAG", "true")
    feature_flags.clear_cache()
    
    assert feature_flags.is_enabled("my_flag") is True
    assert feature_flags.is_enabled("MY_FLAG") is True
    assert feature_flags.is_enabled("My_Flag") is True


def test_cache_behavior(feature_flags, monkeypatch):
    """Test that flags are cached after first check."""
    monkeypatch.setenv("TEST_FLAG_CACHED", "true")
    feature_flags.clear_cache()
    
    # First call reads from env
    assert feature_flags.is_enabled("cached") is True
    
    # Change env var
    monkeypatch.setenv("TEST_FLAG_CACHED", "false")
    
    # Second call uses cache (should still be true)
    assert feature_flags.is_enabled("cached") is True
    
    # Clear cache and check again
    feature_flags.clear_cache()
    assert feature_flags.is_enabled("cached") is False


def test_custom_prefix(monkeypatch):
    """Test using a custom environment variable prefix."""
    monkeypatch.setenv("MY_FEATURE_CUSTOM", "true")
    ff = FeatureFlags(prefix="MY_FEATURE_")
    
    assert ff.is_enabled("custom") is True


def test_require_flag_decorator_enabled(monkeypatch):
    """Test require_flag decorator with enabled flag."""
    monkeypatch.setenv("FEATURE_TEST_ENDPOINT", "true")
    flags.clear_cache()
    
    app = FastAPI()
    
    @app.get("/test")
    @flags.require_flag("test_endpoint")
    async def test_endpoint():
        return {"status": "ok"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_require_flag_decorator_disabled(monkeypatch):
    """Test require_flag decorator with disabled flag."""
    monkeypatch.delenv("FEATURE_TEST_ENDPOINT", raising=False)
    flags.clear_cache()
    
    app = FastAPI()
    
    @app.get("/test")
    @flags.require_flag("test_endpoint")
    async def test_endpoint():
        return {"status": "ok"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Feature not enabled"


def test_require_flag_decorator_sync_function(monkeypatch):
    """Test require_flag decorator with sync function."""
    monkeypatch.setenv("FEATURE_SYNC_TEST", "true")
    flags.clear_cache()
    
    app = FastAPI()
    
    @app.get("/sync-test")
    @flags.require_flag("sync_test")
    def sync_endpoint():
        return {"sync": True}
    
    client = TestClient(app)
    response = client.get("/sync-test")
    
    assert response.status_code == 200
    assert response.json() == {"sync": True}


def test_multiple_flags_independent(feature_flags, monkeypatch):
    """Test that multiple flags work independently."""
    monkeypatch.setenv("TEST_FLAG_FLAG_A", "true")
    monkeypatch.setenv("TEST_FLAG_FLAG_B", "false")
    feature_flags.clear_cache()
    
    assert feature_flags.is_enabled("flag_a") is True
    assert feature_flags.is_enabled("flag_b") is False

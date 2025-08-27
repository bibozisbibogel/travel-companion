"""Pytest configuration and fixtures for Travel Companion API tests."""

import asyncio
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    # Set test environment variables to avoid pydantic parsing issues
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["SUPABASE_URL"] = "https://test.supabase.co"
    os.environ["SUPABASE_KEY"] = "test-key"
    os.environ["ALLOWED_ORIGINS"] = '["http://testserver"]'

    try:
        # Import app after setting environment
        from travel_companion.main import app

        with TestClient(app) as client:
            yield client
    finally:
        # Clean up environment variables
        for key in ["SECRET_KEY", "SUPABASE_URL", "SUPABASE_KEY", "ALLOWED_ORIGINS"]:
            os.environ.pop(key, None)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock application settings for testing."""
    from travel_companion.core.config import Settings

    return Settings(
        app_name="Travel Companion API Test",
        debug=True,
        database_url="sqlite:///test.db",
        redis_url="redis://localhost:6379/1",
        secret_key="test-secret-key",
    )

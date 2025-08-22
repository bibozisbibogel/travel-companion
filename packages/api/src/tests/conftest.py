"""Pytest configuration and fixtures for Travel Companion API tests."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from travel_companion.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    with TestClient(app) as client:
        yield client


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

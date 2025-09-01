"""Pytest configuration and fixtures for Travel Companion API tests."""

import asyncio
import os
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    # Store original environment
    original_env = {}
    env_keys = [
        "SECRET_KEY",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "ALLOWED_ORIGINS",
        "REDIS_URL",
        "ENVIRONMENT",
    ]

    for key in env_keys:
        original_env[key] = os.environ.get(key)

    # Set test environment variables
    os.environ["SECRET_KEY"] = "test-secret-key-12345678901234567890"
    os.environ["SUPABASE_URL"] = "https://test.supabase.co"
    os.environ["SUPABASE_KEY"] = "test-key"
    os.environ["ALLOWED_ORIGINS"] = '["http://testserver"]'  # JSON format to avoid parsing issues
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    os.environ["ENVIRONMENT"] = "test"

    app = None
    try:
        # Import app after setting environment
        from unittest.mock import AsyncMock

        from travel_companion.api.v1.users import get_user_service
        from travel_companion.main import app

        # Create a global mock for the user service to prevent database access
        mock_service = AsyncMock()
        mock_service.create_user = AsyncMock()
        mock_service.authenticate_user = AsyncMock()
        mock_service.get_user_by_id = AsyncMock()

        # Override the dependency globally for this test client
        app.dependency_overrides[get_user_service] = lambda: mock_service

        with TestClient(app) as client:
            yield client
    finally:
        # Restore original environment
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        # Clear all dependency overrides
        if app and hasattr(app, "dependency_overrides"):
            app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(sample_user):
    """Create a test client with authenticated user."""
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["SUPABASE_URL"] = "https://test.supabase.co"
    os.environ["SUPABASE_KEY"] = "test-key"
    os.environ["ALLOWED_ORIGINS"] = '["http://testserver"]'

    try:
        from unittest.mock import AsyncMock

        from travel_companion.api.deps import get_current_user, get_user_service
        from travel_companion.main import app

        # Create a global mock for the user service to prevent database access
        mock_service = AsyncMock()
        mock_service.create_user = AsyncMock()
        mock_service.authenticate_user = AsyncMock()
        mock_service.get_user_by_id = AsyncMock()

        # Override the dependencies with authenticated user
        app.dependency_overrides[get_user_service] = lambda: mock_service
        app.dependency_overrides[get_current_user] = lambda: sample_user

        with TestClient(app) as client:
            yield client
    finally:
        # Clean up environment variables and dependency overrides
        for key in ["SECRET_KEY", "SUPABASE_URL", "SUPABASE_KEY", "ALLOWED_ORIGINS"]:
            os.environ.pop(key, None)
        # Clear all dependency overrides
        if hasattr(app, "dependency_overrides"):
            app.dependency_overrides.clear()


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


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    from travel_companion.models.user import User

    return User(
        user_id=uuid4(),
        email="test@example.com",
        password_hash="$2b$12$test.hash.value",
        first_name="Test",
        last_name="User",
        travel_preferences={
            "budget_range": {"min": 100, "max": 1000},
            "accommodation_types": ["hotel"],
            "activity_interests": ["sightseeing"],
        },
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_user_service(monkeypatch):
    """Mock user service for testing."""
    mock_service = Mock()

    def mock_get_user_service():
        return mock_service

    # Patch the dependency
    monkeypatch.setattr("travel_companion.api.deps.get_user_service", mock_get_user_service)

    return mock_service

"""Tests for user API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import status

from travel_companion.models.user import User
from travel_companion.utils.errors import UserAlreadyExistsError


class TestUserRegistration:
    """Test cases for user registration endpoint."""

    @pytest.fixture
    def valid_user_data(self):
        """Valid user registration data."""
        return {
            "email": "test@example.com",
            "password": "SecurePassword123",
            "first_name": "Test",
            "last_name": "User",
        }

    @pytest.fixture
    def created_user(self):
        """Sample created user."""
        now = datetime.now(UTC)
        return User(
            user_id=uuid4(),
            email="test@example.com",
            password_hash="hashed_password",
            first_name="Test",
            last_name="User",
            travel_preferences={
                "budget_range": {"min": 0, "max": 5000},
                "accommodation_types": ["hotel", "apartment"],
                "activity_interests": [],
                "dietary_restrictions": [],
                "accessibility_needs": [],
                "travel_pace": "moderate",
                "group_size_preference": "small",
                "season_preferences": [],
            },
            created_at=now,
            updated_at=now,
        )

    def test_register_user_success(self, client, valid_user_data, created_user):
        """Test successful user registration."""
        from travel_companion.api.v1.users import get_user_service
        from travel_companion.main import app

        # Mock the user service dependency
        mock_service = AsyncMock()
        mock_service.create_user = AsyncMock(return_value=created_user)

        # Override the dependency
        app.dependency_overrides[get_user_service] = lambda: mock_service

        try:
            # Make request
            response = client.post("/api/v1/users/register", json=valid_user_data)

            # Assertions
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()

            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert "expires_in" in data
            assert "user" in data

            user_data = data["user"]
            assert user_data["email"] == "test@example.com"
            assert user_data["first_name"] == "Test"
            assert user_data["last_name"] == "User"
            assert "user_id" in user_data
            assert "password_hash" not in user_data  # Should not be exposed
        finally:
            # Clean up dependency override
            if get_user_service in app.dependency_overrides:
                del app.dependency_overrides[get_user_service]

    def test_register_user_duplicate_email(self, client, valid_user_data):
        """Test registration with duplicate email."""
        from travel_companion.api.v1.users import get_user_service
        from travel_companion.main import app

        # Setup mock to raise UserAlreadyExistsError
        mock_service = AsyncMock()
        mock_service.create_user = AsyncMock(
            side_effect=UserAlreadyExistsError("User with email test@example.com already exists")
        )

        # Override the dependency
        app.dependency_overrides[get_user_service] = lambda: mock_service

        try:
            # Make request
            response = client.post("/api/v1/users/register", json=valid_user_data)

            # Assertions
            assert response.status_code == status.HTTP_409_CONFLICT
            data = response.json()
            assert "USER_ALREADY_EXISTS" in data["detail"]["error_code"]
        finally:
            # Clean up dependency override
            if get_user_service in app.dependency_overrides:
                del app.dependency_overrides[get_user_service]

    @pytest.mark.parametrize(
        "invalid_email", ["invalid-email", "@example.com", "test@", "test.example.com", ""]
    )
    def test_register_user_invalid_email(self, client, invalid_email):
        """Test registration with invalid email formats."""
        user_data = {
            "email": invalid_email,
            "password": "SecurePassword123",
            "first_name": "Test",
            "last_name": "User",
        }

        response = client.post("/api/v1/users/register", json=user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize(
        "weak_password",
        [
            "short",  # Too short
            "nouppercase123",  # No uppercase
            "NOLOWERCASE123",  # No lowercase
            "NoNumbers",  # No digits
            "a" * 129,  # Too long
        ],
    )
    def test_register_user_weak_password(self, client, weak_password):
        """Test registration with weak passwords."""
        user_data = {
            "email": "test@example.com",
            "password": weak_password,
            "first_name": "Test",
            "last_name": "User",
        }

        response = client.post("/api/v1/users/register", json=user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_user_missing_required_fields(self, client):
        """Test registration with missing required fields."""
        # Missing email
        response = client.post(
            "/api/v1/users/register", json={"password": "SecurePassword123", "first_name": "Test"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing password
        response = client.post(
            "/api/v1/users/register", json={"email": "test@example.com", "first_name": "Test"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_user_optional_fields_none(self, client, created_user):
        """Test registration with optional fields as None."""
        user_data = {
            "email": "test@example.com",
            "password": "SecurePassword123",
            "first_name": None,
            "last_name": None,
        }

        from travel_companion.api.v1.users import get_user_service
        from travel_companion.main import app

        mock_service = AsyncMock()
        mock_service.create_user = AsyncMock(return_value=created_user)

        app.dependency_overrides[get_user_service] = lambda: mock_service

        try:
            response = client.post("/api/v1/users/register", json=user_data)
            assert response.status_code == status.HTTP_201_CREATED
        finally:
            if get_user_service in app.dependency_overrides:
                del app.dependency_overrides[get_user_service]

    def test_register_user_internal_error(self, client, valid_user_data):
        """Test registration with internal server error."""
        from travel_companion.api.v1.users import get_user_service
        from travel_companion.main import app

        # Setup mock to raise generic exception
        mock_service = AsyncMock()
        mock_service.create_user = AsyncMock(side_effect=Exception("Database error"))

        app.dependency_overrides[get_user_service] = lambda: mock_service

        try:
            response = client.post("/api/v1/users/register", json=valid_user_data)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert data["detail"]["error_code"] == "INTERNAL_ERROR"
        finally:
            if get_user_service in app.dependency_overrides:
                del app.dependency_overrides[get_user_service]


class TestUserLogin:
    """Test cases for user login endpoint."""

    @pytest.fixture
    def valid_login_data(self):
        """Valid login data."""
        return {"email": "test@example.com", "password": "SecurePassword123"}

    @pytest.fixture
    def authenticated_user(self):
        """Sample authenticated user."""
        now = datetime.now(UTC)
        return User(
            user_id=uuid4(),
            email="test@example.com",
            password_hash="hashed_password",
            first_name="Test",
            last_name="User",
            travel_preferences={},
            created_at=now,
            updated_at=now,
        )

    def test_login_user_success(self, client, valid_login_data, authenticated_user):
        """Test successful user login."""
        from travel_companion.api.v1.users import get_user_service
        from travel_companion.main import app

        # Setup mock
        mock_service = AsyncMock()
        mock_service.authenticate_user = AsyncMock(return_value=authenticated_user)

        app.dependency_overrides[get_user_service] = lambda: mock_service

        try:
            # Make request
            response = client.post("/api/v1/users/login", json=valid_login_data)

            # Assertions
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert "expires_in" in data
            assert "user" in data

            user_data = data["user"]
            assert user_data["email"] == "test@example.com"
        finally:
            if get_user_service in app.dependency_overrides:
                del app.dependency_overrides[get_user_service]

    def test_login_user_invalid_credentials(self, client, valid_login_data):
        """Test login with invalid credentials."""
        from travel_companion.api.v1.users import get_user_service
        from travel_companion.main import app

        # Setup mock to return None (authentication failed)
        mock_service = AsyncMock()
        mock_service.authenticate_user = AsyncMock(return_value=None)

        app.dependency_overrides[get_user_service] = lambda: mock_service

        try:
            # Make request
            response = client.post("/api/v1/users/login", json=valid_login_data)

            # Assertions
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            data = response.json()
            assert data["detail"]["error_code"] == "INVALID_CREDENTIALS"
        finally:
            if get_user_service in app.dependency_overrides:
                del app.dependency_overrides[get_user_service]

    def test_login_user_invalid_email_format(self, client):
        """Test login with invalid email format."""
        login_data = {"email": "invalid-email", "password": "SecurePassword123"}

        response = client.post("/api/v1/users/login", json=login_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_user_missing_fields(self, client):
        """Test login with missing fields."""
        # Missing password
        response = client.post("/api/v1/users/login", json={"email": "test@example.com"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing email
        response = client.post("/api/v1/users/login", json={"password": "SecurePassword123"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_user_internal_error(self, client, valid_login_data):
        """Test login with internal server error."""
        from travel_companion.api.v1.users import get_user_service
        from travel_companion.main import app

        # Setup mock to raise exception
        mock_service = AsyncMock()
        mock_service.authenticate_user = AsyncMock(side_effect=Exception("Database error"))

        app.dependency_overrides[get_user_service] = lambda: mock_service

        try:
            response = client.post("/api/v1/users/login", json=valid_login_data)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert data["detail"]["error_code"] == "INTERNAL_ERROR"
        finally:
            if get_user_service in app.dependency_overrides:
                del app.dependency_overrides[get_user_service]

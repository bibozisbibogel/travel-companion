"""Tests for user models."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from travel_companion.models.user import User, UserCreate, UserLogin, UserResponse


class TestUserCreate:
    """Test cases for UserCreate model."""

    def test_user_create_valid_data(self):
        """Test UserCreate with valid data."""
        user_data = UserCreate(
            email="test@example.com",
            password="SecurePassword123",
            first_name="Test",
            last_name="User",
        )

        assert user_data.email == "test@example.com"
        assert user_data.password == "SecurePassword123"
        assert user_data.first_name == "Test"
        assert user_data.last_name == "User"

    def test_user_create_optional_fields(self):
        """Test UserCreate with optional fields as None."""
        user_data = UserCreate(email="test@example.com", password="SecurePassword123")

        assert user_data.first_name is None
        assert user_data.last_name is None

    @pytest.mark.parametrize(
        "invalid_email", ["invalid-email", "@example.com", "test@", "test.example.com", ""]
    )
    def test_user_create_invalid_email(self, invalid_email):
        """Test UserCreate with invalid email formats."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(email=invalid_email, password="SecurePassword123")

        assert "email" in str(exc_info.value).lower()

    @pytest.mark.parametrize(
        "weak_password",
        [
            "short",  # Too short
            "nouppercase123",  # No uppercase
            "NOLOWERCASE123",  # No lowercase
            "NoNumbers",  # No digits
        ],
    )
    def test_user_create_weak_password(self, weak_password):
        """Test UserCreate with weak passwords."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(email="test@example.com", password=weak_password)

        assert "password" in str(exc_info.value).lower()

    def test_user_create_password_too_long(self):
        """Test UserCreate with password that's too long."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="a" * 129,  # Too long
            )

    def test_user_create_missing_required_fields(self):
        """Test UserCreate with missing required fields."""
        # Missing email
        with pytest.raises(ValidationError):
            UserCreate(password="SecurePassword123")

        # Missing password
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com")


class TestUserLogin:
    """Test cases for UserLogin model."""

    def test_user_login_valid_data(self):
        """Test UserLogin with valid data."""
        login_data = UserLogin(email="test@example.com", password="SecurePassword123")

        assert login_data.email == "test@example.com"
        assert login_data.password == "SecurePassword123"

    def test_user_login_invalid_email(self):
        """Test UserLogin with invalid email."""
        with pytest.raises(ValidationError):
            UserLogin(email="invalid-email", password="SecurePassword123")

    def test_user_login_missing_fields(self):
        """Test UserLogin with missing fields."""
        # Missing password
        with pytest.raises(ValidationError):
            UserLogin(email="test@example.com")

        # Missing email
        with pytest.raises(ValidationError):
            UserLogin(password="SecurePassword123")


class TestUserResponse:
    """Test cases for UserResponse model."""

    def test_user_response_creation(self):
        """Test UserResponse model creation."""
        now = datetime.now(UTC)
        user_id = uuid4()

        user_response = UserResponse(
            user_id=user_id,
            email="test@example.com",
            first_name="Test",
            last_name="User",
            travel_preferences={"budget_range": {"min": 0, "max": 5000}},
            created_at=now,
            updated_at=now,
        )

        assert user_response.user_id == user_id
        assert user_response.email == "test@example.com"
        assert user_response.first_name == "Test"
        assert user_response.last_name == "User"
        assert user_response.travel_preferences["budget_range"]["min"] == 0


class TestUser:
    """Test cases for User model."""

    def test_user_creation_with_defaults(self):
        """Test User model with default values."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password_123",
            first_name="Test",
            last_name="User",
        )

        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password_123"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert isinstance(user.user_id, type(uuid4()))
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
        assert user.travel_preferences == {}

    def test_user_creation_with_explicit_values(self):
        """Test User model with explicit values."""
        now = datetime.now(UTC)
        user_id = uuid4()
        preferences = {"budget_range": {"min": 100, "max": 1000}}

        user = User(
            user_id=user_id,
            email="test@example.com",
            password_hash="hashed_password_123",
            first_name="Test",
            last_name="User",
            travel_preferences=preferences,
            created_at=now,
            updated_at=now,
        )

        assert user.user_id == user_id
        assert user.created_at == now
        assert user.updated_at == now
        assert user.travel_preferences == preferences

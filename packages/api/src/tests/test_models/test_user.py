"""Tests for user models."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from travel_companion.models.user import (
    AuthToken,
    TravelPreferences,
    User,
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)


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

        travel_prefs = TravelPreferences(
            budget_min=0,
            budget_max=5000,
            preferred_currency="USD",
            accommodation_types=["hotel"],
            activity_interests=["museums"],
        )

        user_response = UserResponse(
            user_id=user_id,
            email="test@example.com",
            first_name="Test",
            last_name="User",
            travel_preferences=travel_prefs,
            created_at=now,
            updated_at=now,
        )

        assert user_response.user_id == user_id
        assert user_response.email == "test@example.com"
        assert user_response.first_name == "Test"
        assert user_response.last_name == "User"
        assert user_response.travel_preferences.budget_min == 0
        assert user_response.travel_preferences.budget_max == 5000
        assert user_response.travel_preferences.preferred_currency == "USD"


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
        assert isinstance(user.travel_preferences, TravelPreferences)
        assert user.travel_preferences.preferred_currency == "USD"  # Default value

    def test_user_creation_with_explicit_values(self):
        """Test User model with explicit values."""
        now = datetime.now(UTC)
        user_id = uuid4()
        preferences = TravelPreferences(
            budget_min=100,
            budget_max=1000,
            preferred_currency="EUR",
            accommodation_types=["apartment"],
            activity_interests=["beaches"],
        )

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
        assert user.travel_preferences.budget_min == 100
        assert user.travel_preferences.budget_max == 1000
        assert user.travel_preferences.preferred_currency == "EUR"


class TestTravelPreferences:
    """Test cases for TravelPreferences model."""

    def test_travel_preferences_defaults(self):
        """Test TravelPreferences with default values."""
        prefs = TravelPreferences()

        assert prefs.budget_min is None
        assert prefs.budget_max is None
        assert prefs.preferred_currency == "USD"
        assert prefs.accommodation_types == []
        assert prefs.activity_interests == []
        assert prefs.dietary_restrictions == []
        assert prefs.accessibility_needs == []
        assert prefs.travel_style is None

    def test_travel_preferences_full(self):
        """Test TravelPreferences with all fields."""
        prefs = TravelPreferences(
            budget_min=500,
            budget_max=2000,
            preferred_currency="EUR",
            accommodation_types=["hotel", "apartment"],
            activity_interests=["museums", "beaches"],
            dietary_restrictions=["vegetarian", "gluten-free"],
            accessibility_needs=["wheelchair"],
            travel_style="luxury"
        )

        assert prefs.budget_min == 500
        assert prefs.budget_max == 2000
        assert prefs.preferred_currency == "EUR"
        assert "hotel" in prefs.accommodation_types
        assert "museums" in prefs.activity_interests
        assert "vegetarian" in prefs.dietary_restrictions
        assert "wheelchair" in prefs.accessibility_needs
        assert prefs.travel_style == "luxury"

    def test_travel_preferences_budget_validation(self):
        """Test TravelPreferences budget validation."""
        # Valid budget range
        prefs = TravelPreferences(budget_min=100, budget_max=500)
        assert prefs.budget_min == 100
        assert prefs.budget_max == 500

        # Invalid: max less than min
        with pytest.raises(ValidationError) as exc_info:
            TravelPreferences(budget_min=500, budget_max=100)
        assert "Maximum budget must be greater than minimum budget" in str(exc_info.value)

        # Invalid: max equal to min
        with pytest.raises(ValidationError):
            TravelPreferences(budget_min=500, budget_max=500)

        # Invalid: negative budgets
        with pytest.raises(ValidationError):
            TravelPreferences(budget_min=-100)

        with pytest.raises(ValidationError):
            TravelPreferences(budget_max=-100)

    def test_travel_preferences_currency_validation(self):
        """Test TravelPreferences currency validation."""
        # Valid uppercase currency
        prefs = TravelPreferences(preferred_currency="GBP")
        assert prefs.preferred_currency == "GBP"

        # Invalid lowercase currency
        with pytest.raises(ValidationError) as exc_info:
            TravelPreferences(preferred_currency="gbp")
        assert "Currency code must be uppercase" in str(exc_info.value)

        # Invalid currency length
        with pytest.raises(ValidationError):
            TravelPreferences(preferred_currency="GB")  # Too short

        with pytest.raises(ValidationError):
            TravelPreferences(preferred_currency="GBPP")  # Too long


class TestUserUpdate:
    """Test cases for UserUpdate model."""

    def test_user_update_partial(self):
        """Test UserUpdate with partial data."""
        update_data = UserUpdate(first_name="UpdatedName")

        assert update_data.first_name == "UpdatedName"
        assert update_data.last_name is None
        assert update_data.travel_preferences is None

    def test_user_update_full(self):
        """Test UserUpdate with all optional fields."""
        prefs = TravelPreferences(preferred_currency="EUR")
        update_data = UserUpdate(
            first_name="Updated",
            last_name="Name",
            travel_preferences=prefs
        )

        assert update_data.first_name == "Updated"
        assert update_data.last_name == "Name"
        assert update_data.travel_preferences.preferred_currency == "EUR"

    def test_user_update_validation(self):
        """Test UserUpdate field validation."""
        # Empty names should fail
        with pytest.raises(ValidationError):
            UserUpdate(first_name="")

        with pytest.raises(ValidationError):
            UserUpdate(last_name="")

        # Too long names should fail
        with pytest.raises(ValidationError):
            UserUpdate(first_name="a" * 101)

        with pytest.raises(ValidationError):
            UserUpdate(last_name="a" * 101)


class TestUserBase:
    """Test cases for UserBase model."""

    def test_user_base_creation(self):
        """Test UserBase model creation."""
        prefs = TravelPreferences(preferred_currency="CAD")
        user_base = UserBase(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            travel_preferences=prefs
        )

        assert user_base.email == "test@example.com"
        assert user_base.first_name == "Test"
        assert user_base.last_name == "User"
        assert user_base.travel_preferences.preferred_currency == "CAD"

    def test_user_base_with_defaults(self):
        """Test UserBase with default travel preferences."""
        user_base = UserBase(email="test@example.com")

        assert user_base.email == "test@example.com"
        assert user_base.first_name is None
        assert user_base.last_name is None
        assert isinstance(user_base.travel_preferences, TravelPreferences)
        assert user_base.travel_preferences.preferred_currency == "USD"

    def test_user_base_name_validation(self):
        """Test UserBase name field validation."""
        # Empty names should fail
        with pytest.raises(ValidationError):
            UserBase(email="test@example.com", first_name="")

        with pytest.raises(ValidationError):
            UserBase(email="test@example.com", last_name="")

        # Too long names should fail
        with pytest.raises(ValidationError):
            UserBase(email="test@example.com", first_name="a" * 101)

        with pytest.raises(ValidationError):
            UserBase(email="test@example.com", last_name="a" * 101)


class TestAuthToken:
    """Test cases for AuthToken model."""

    def test_auth_token_creation(self):
        """Test AuthToken model creation."""
        user_response = UserResponse(
            user_id=uuid4(),
            email="test@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )

        token = AuthToken(
            access_token="jwt.token.here",
            expires_in=3600,
            user=user_response
        )

        assert token.access_token == "jwt.token.here"
        assert token.token_type == "bearer"  # Default value
        assert token.expires_in == 3600
        assert token.user.email == "test@example.com"

    def test_auth_token_custom_type(self):
        """Test AuthToken with custom token type."""
        user_response = UserResponse(
            user_id=uuid4(),
            email="test@example.com",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )

        token = AuthToken(
            access_token="custom.token",
            token_type="custom",
            expires_in=7200,
            user=user_response
        )

        assert token.token_type == "custom"
        assert token.expires_in == 7200

    def test_auth_token_required_fields(self):
        """Test AuthToken required fields."""
        # Missing access_token
        with pytest.raises(ValidationError):
            AuthToken(
                expires_in=3600,
                user=UserResponse(
                    user_id=uuid4(),
                    email="test@example.com",
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
            )

        # Missing expires_in
        with pytest.raises(ValidationError):
            AuthToken(
                access_token="token",
                user=UserResponse(
                    user_id=uuid4(),
                    email="test@example.com",
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
            )

        # Missing user
        with pytest.raises(ValidationError):
            AuthToken(
                access_token="token",
                expires_in=3600
            )

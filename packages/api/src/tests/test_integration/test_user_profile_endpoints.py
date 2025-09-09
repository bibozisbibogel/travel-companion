"""Integration tests for user profile endpoints."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from travel_companion.models.user import TravelPreferences, User


class TestUserProfileEndpoints:
    """Test user profile API endpoints integration."""

    @pytest.fixture
    def sample_user(self):
        """Create sample user for testing."""
        return User(
            user_id=uuid4(),
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            travel_preferences=TravelPreferences(
                budget_min=1000,
                budget_max=5000,
                preferred_currency="USD",
                accommodation_types=["hotel"],
                activity_interests=["museums"],
                travel_style="moderate",
            ),
        )

    async def test_get_current_user_profile_success(self, client, sample_user):
        """Test successful retrieval of current user profile."""

        # Mock get_current_user to return sample user
        async def mock_get_current_user():
            return sample_user

        from travel_companion.api.deps import get_current_user

        client.app.dependency_overrides[get_current_user] = mock_get_current_user

        response = client.get("/api/v1/users/me")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == str(sample_user.user_id)
        assert data["email"] == sample_user.email
        assert data["first_name"] == sample_user.first_name
        assert data["last_name"] == sample_user.last_name

        # Verify travel preferences structure
        prefs = data["travel_preferences"]
        assert prefs["budget_min"] == 1000
        assert prefs["budget_max"] == 5000
        assert prefs["preferred_currency"] == "USD"
        assert prefs["accommodation_types"] == ["hotel"]
        assert prefs["activity_interests"] == ["museums"]
        assert prefs["travel_style"] == "moderate"

    async def test_update_user_profile_success_partial_fields(self, client, sample_user):
        """Test successful user profile update with partial fields."""
        updated_user = User(
            user_id=sample_user.user_id,
            email=sample_user.email,
            password_hash=sample_user.password_hash,
            first_name="Alice",
            last_name=sample_user.last_name,  # Unchanged
            travel_preferences=sample_user.travel_preferences,  # Unchanged
        )

        # Mock dependencies
        async def mock_get_current_user():
            return sample_user

        async def mock_get_user_service():
            service = AsyncMock()
            service.update_user.return_value = updated_user
            return service

        from travel_companion.api.deps import get_current_user
        from travel_companion.api.v1.users import get_user_service

        client.app.dependency_overrides[get_current_user] = mock_get_current_user
        client.app.dependency_overrides[get_user_service] = mock_get_user_service

        update_data = {"first_name": "Alice"}

        response = client.put("/api/v1/users/me", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["first_name"] == "Alice"
        assert data["last_name"] == "Doe"  # Unchanged

    async def test_update_user_profile_invalid_preferences(self, client, sample_user):
        """Test user profile update with invalid travel preferences."""

        # Mock get_current_user
        async def mock_get_current_user():
            return sample_user

        from travel_companion.api.deps import get_current_user

        client.app.dependency_overrides[get_current_user] = mock_get_current_user

        # Invalid: budget_max < budget_min
        update_data = {
            "travel_preferences": {
                "budget_min": 5000,
                "budget_max": 1000,  # Invalid: max < min
                "preferred_currency": "USD",
            }
        }

        response = client.put("/api/v1/users/me", json=update_data)

        assert response.status_code == 422
        data = response.json()
        assert "Maximum budget must be greater than minimum budget" in str(data)

    async def test_update_user_profile_validation_error_empty_name(self, client, sample_user):
        """Test user profile update with validation error for empty name."""

        # Mock get_current_user
        async def mock_get_current_user():
            return sample_user

        from travel_companion.api.deps import get_current_user

        client.app.dependency_overrides[get_current_user] = mock_get_current_user

        # Invalid: empty first name
        update_data = {"first_name": ""}

        response = client.put("/api/v1/users/me", json=update_data)

        assert response.status_code == 422
        data = response.json()
        assert "Name cannot be empty" in str(data)

    async def test_update_user_profile_unauthorized(self, client):
        """Test user profile update without authentication."""
        # No authentication token provided
        update_data = {"first_name": "Unauthorized"}

        response = client.put("/api/v1/users/me", json=update_data)

        assert response.status_code == 403  # No authorization header

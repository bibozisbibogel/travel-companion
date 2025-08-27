"""Unit tests for user service profile update functionality."""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from travel_companion.models.user import TravelPreferences, UserUpdate
from travel_companion.services.user_service import UserService
from travel_companion.utils.errors import DatabaseError


class TestUserServiceProfileUpdate:
    """Test user service profile update methods."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Supabase client."""
        return Mock()

    @pytest.fixture
    def user_service(self, mock_client):
        """Create user service with mock client."""
        return UserService(mock_client)

    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID for tests."""
        return uuid4()

    @pytest.fixture
    def sample_user_data(self, sample_user_id):
        """Sample user data returned from database."""
        return {
            "user_id": str(sample_user_id),
            "email": "test@example.com",
            "password_hash": "hashed_password",
            "first_name": "John",
            "last_name": "Doe",
            "travel_preferences": {
                "budget_min": 1000,
                "budget_max": 5000,
                "preferred_currency": "USD",
                "accommodation_types": ["hotel"],
                "activity_interests": ["museums"],
                "dietary_restrictions": [],
                "accessibility_needs": [],
                "travel_style": "moderate"
            },
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }

    async def test_update_user_success_all_fields(self, user_service, mock_client, sample_user_id, sample_user_data):
        """Test successful user profile update with all fields."""
        # Arrange
        new_preferences = TravelPreferences(
            budget_min=2000,
            budget_max=8000,
            preferred_currency="EUR",
            accommodation_types=["apartment", "hotel"],
            activity_interests=["hiking", "museums"],
            dietary_restrictions=["vegetarian"],
            travel_style="luxury"
        )
        
        update_data = UserUpdate(
            first_name="Jane",
            last_name="Smith",
            travel_preferences=new_preferences
        )
        
        # Mock database response
        updated_data = sample_user_data.copy()
        updated_data.update({
            "first_name": "Jane",
            "last_name": "Smith",
            "travel_preferences": new_preferences.model_dump()
        })
        
        mock_result = Mock()
        mock_result.data = [updated_data]
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

        # Act
        result = await user_service.update_user(sample_user_id, update_data)

        # Assert
        assert result is not None
        assert result.first_name == "Jane"
        assert result.last_name == "Smith"
        assert result.travel_preferences.budget_min == 2000
        assert result.travel_preferences.budget_max == 8000
        assert result.travel_preferences.preferred_currency == "EUR"
        
        # Verify database call
        mock_client.table.assert_called_once_with("users")
        update_call = mock_client.table.return_value.update.call_args[0][0]
        assert update_call["first_name"] == "Jane"
        assert update_call["last_name"] == "Smith"
        assert update_call["travel_preferences"] == new_preferences.model_dump()
        assert "updated_at" in update_call

    async def test_update_user_success_partial_fields(self, user_service, mock_client, sample_user_id, sample_user_data):
        """Test successful user profile update with partial fields."""
        # Arrange
        update_data = UserUpdate(first_name="Alice")
        
        updated_data = sample_user_data.copy()
        updated_data["first_name"] = "Alice"
        
        mock_result = Mock()
        mock_result.data = [updated_data]
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

        # Act
        result = await user_service.update_user(sample_user_id, update_data)

        # Assert
        assert result is not None
        assert result.first_name == "Alice"
        assert result.last_name == "Doe"  # Unchanged
        
        # Verify database call
        update_call = mock_client.table.return_value.update.call_args[0][0]
        assert update_call["first_name"] == "Alice"
        assert "last_name" not in update_call  # Should not be in update
        assert "travel_preferences" not in update_call  # Should not be in update

    async def test_update_user_success_only_preferences(self, user_service, mock_client, sample_user_id, sample_user_data):
        """Test successful user profile update with only preferences."""
        # Arrange
        new_preferences = TravelPreferences(
            budget_min=3000,
            budget_max=10000,
            preferred_currency="GBP",
            accommodation_types=["resort"],
            activity_interests=["beaches", "nightlife"],
            travel_style="luxury"
        )
        
        update_data = UserUpdate(travel_preferences=new_preferences)
        
        updated_data = sample_user_data.copy()
        updated_data["travel_preferences"] = new_preferences.model_dump()
        
        mock_result = Mock()
        mock_result.data = [updated_data]
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

        # Act
        result = await user_service.update_user(sample_user_id, update_data)

        # Assert
        assert result is not None
        assert result.first_name == "John"  # Unchanged
        assert result.travel_preferences.budget_min == 3000
        assert result.travel_preferences.preferred_currency == "GBP"
        
        # Verify database call
        update_call = mock_client.table.return_value.update.call_args[0][0]
        assert "first_name" not in update_call
        assert "last_name" not in update_call
        assert update_call["travel_preferences"] == new_preferences.model_dump()

    async def test_update_user_not_found(self, user_service, mock_client, sample_user_id):
        """Test user update when user is not found."""
        # Arrange
        update_data = UserUpdate(first_name="NotFound")
        
        mock_result = Mock()
        mock_result.data = []  # Empty result indicates user not found
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

        # Act
        result = await user_service.update_user(sample_user_id, update_data)

        # Assert
        assert result is None

    async def test_update_user_database_error(self, user_service, mock_client, sample_user_id):
        """Test user update with database error."""
        # Arrange
        update_data = UserUpdate(first_name="Error")
        
        mock_client.table.return_value.update.return_value.eq.return_value.execute.side_effect = \
            Exception("Database connection failed")

        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            await user_service.update_user(sample_user_id, update_data)
        
        assert "Database error updating user profile" in str(exc_info.value)
        assert "Database connection failed" in str(exc_info.value)

    async def test_update_user_empty_update(self, user_service, mock_client, sample_user_id, sample_user_data):
        """Test user update with empty update data."""
        # Arrange
        update_data = UserUpdate()  # All fields None
        
        mock_result = Mock()
        mock_result.data = [sample_user_data]
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

        # Act
        result = await user_service.update_user(sample_user_id, update_data)

        # Assert
        assert result is not None
        
        # Verify database call only contains updated_at
        update_call = mock_client.table.return_value.update.call_args[0][0]
        assert len(update_call) == 1  # Only updated_at
        assert "updated_at" in update_call
        assert "first_name" not in update_call
        assert "last_name" not in update_call
        assert "travel_preferences" not in update_call

    async def test_update_user_preferences_validation(self, user_service, mock_client, sample_user_id, sample_user_data):
        """Test that travel preferences are properly validated during update."""
        # Arrange - Create valid preferences
        valid_preferences = TravelPreferences(
            budget_min=1000,
            budget_max=5000,
            preferred_currency="USD",
            accommodation_types=["hotel", "apartment"],
            activity_interests=["museums", "hiking"],
            dietary_restrictions=["vegetarian"],
            accessibility_needs=[],
            travel_style="moderate"
        )
        
        update_data = UserUpdate(travel_preferences=valid_preferences)
        
        updated_data = sample_user_data.copy()
        updated_data["travel_preferences"] = valid_preferences.model_dump()
        
        mock_result = Mock()
        mock_result.data = [updated_data]
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

        # Act
        result = await user_service.update_user(sample_user_id, update_data)

        # Assert
        assert result is not None
        assert result.travel_preferences.budget_min == 1000
        assert result.travel_preferences.budget_max == 5000
        assert result.travel_preferences.preferred_currency == "USD"
        assert result.travel_preferences.accommodation_types == ["hotel", "apartment"]
        assert result.travel_preferences.activity_interests == ["museums", "hiking"]
        
        # Verify the model_dump was called correctly
        update_call = mock_client.table.return_value.update.call_args[0][0]
        expected_prefs = {
            "budget_min": 1000,
            "budget_max": 5000,
            "preferred_currency": "USD",
            "accommodation_types": ["hotel", "apartment"],
            "activity_interests": ["museums", "hiking"],
            "dietary_restrictions": ["vegetarian"],
            "accessibility_needs": [],
            "travel_style": "moderate"
        }
        assert update_call["travel_preferences"] == expected_prefs
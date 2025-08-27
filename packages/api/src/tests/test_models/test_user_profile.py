"""Unit tests for user profile models and validation."""

import pytest
from pydantic import ValidationError

from travel_companion.models.user import TravelPreferences, UserUpdate


class TestTravelPreferences:
    """Test travel preferences model validation."""

    def test_travel_preferences_default_creation(self):
        """Test creating travel preferences with default values."""
        prefs = TravelPreferences()
        
        assert prefs.budget_min is None
        assert prefs.budget_max is None
        assert prefs.preferred_currency == "USD"
        assert prefs.accommodation_types == []
        assert prefs.activity_interests == []
        assert prefs.dietary_restrictions == []
        assert prefs.accessibility_needs == []
        assert prefs.travel_style is None

    def test_travel_preferences_valid_data(self):
        """Test creating travel preferences with valid data."""
        prefs = TravelPreferences(
            budget_min=1000,
            budget_max=5000,
            preferred_currency="EUR",
            accommodation_types=["hotel", "apartment"],
            activity_interests=["museums", "hiking"],
            dietary_restrictions=["vegetarian"],
            accessibility_needs=["wheelchair"],
            travel_style="luxury"
        )
        
        assert prefs.budget_min == 1000
        assert prefs.budget_max == 5000
        assert prefs.preferred_currency == "EUR"
        assert prefs.accommodation_types == ["hotel", "apartment"]
        assert prefs.activity_interests == ["museums", "hiking"]
        assert prefs.dietary_restrictions == ["vegetarian"]
        assert prefs.accessibility_needs == ["wheelchair"]
        assert prefs.travel_style == "luxury"

    def test_travel_preferences_budget_validation_success(self):
        """Test valid budget range validation."""
        # Valid: min < max
        prefs = TravelPreferences(budget_min=1000, budget_max=5000)
        assert prefs.budget_min == 1000
        assert prefs.budget_max == 5000
        
        # Valid: only min set
        prefs = TravelPreferences(budget_min=1000)
        assert prefs.budget_min == 1000
        assert prefs.budget_max is None
        
        # Valid: only max set
        prefs = TravelPreferences(budget_max=5000)
        assert prefs.budget_min is None
        assert prefs.budget_max == 5000

    def test_travel_preferences_budget_validation_failure(self):
        """Test invalid budget range validation."""
        # Invalid: max <= min
        with pytest.raises(ValidationError) as exc_info:
            TravelPreferences(budget_min=5000, budget_max=1000)
        assert "Maximum budget must be greater than minimum budget" in str(exc_info.value)
        
        # Invalid: max == min
        with pytest.raises(ValidationError) as exc_info:
            TravelPreferences(budget_min=1000, budget_max=1000)
        assert "Maximum budget must be greater than minimum budget" in str(exc_info.value)

    def test_travel_preferences_budget_negative_values(self):
        """Test that negative budget values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TravelPreferences(budget_min=-100)
        assert "Input should be greater than or equal to 0" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            TravelPreferences(budget_max=-500)
        assert "Input should be greater than or equal to 0" in str(exc_info.value)

    def test_travel_preferences_currency_validation_success(self):
        """Test valid currency code validation."""
        valid_currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"]
        
        for currency in valid_currencies:
            prefs = TravelPreferences(preferred_currency=currency)
            assert prefs.preferred_currency == currency

    def test_travel_preferences_currency_validation_failure(self):
        """Test invalid currency code validation."""
        # Invalid: lowercase
        with pytest.raises(ValidationError) as exc_info:
            TravelPreferences(preferred_currency="usd")
        assert "Currency code must be uppercase" in str(exc_info.value)
        
        # Invalid: mixed case
        with pytest.raises(ValidationError) as exc_info:
            TravelPreferences(preferred_currency="Eur")
        assert "Currency code must be uppercase" in str(exc_info.value)
        
        # Invalid: too short
        with pytest.raises(ValidationError) as exc_info:
            TravelPreferences(preferred_currency="US")
        assert "String should have at least 3 characters" in str(exc_info.value)
        
        # Invalid: too long
        with pytest.raises(ValidationError) as exc_info:
            TravelPreferences(preferred_currency="USDT")
        assert "String should have at most 3 characters" in str(exc_info.value)

    def test_travel_preferences_lists_validation(self):
        """Test list field validation."""
        prefs = TravelPreferences(
            accommodation_types=["hotel", "hostel", "apartment", "resort"],
            activity_interests=["museums", "hiking", "beaches", "nightlife"],
            dietary_restrictions=["vegetarian", "gluten-free", "halal"],
            accessibility_needs=["wheelchair", "hearing-impaired", "visual-impaired"]
        )
        
        assert len(prefs.accommodation_types) == 4
        assert len(prefs.activity_interests) == 4
        assert len(prefs.dietary_restrictions) == 3
        assert len(prefs.accessibility_needs) == 3


class TestUserUpdate:
    """Test user update model validation."""

    def test_user_update_empty(self):
        """Test creating empty user update (all fields None)."""
        update = UserUpdate()
        
        assert update.first_name is None
        assert update.last_name is None
        assert update.travel_preferences is None

    def test_user_update_partial_name(self):
        """Test updating only name fields."""
        update = UserUpdate(
            first_name="John",
            last_name="Doe"
        )
        
        assert update.first_name == "John"
        assert update.last_name == "Doe"
        assert update.travel_preferences is None

    def test_user_update_only_first_name(self):
        """Test updating only first name."""
        update = UserUpdate(first_name="Jane")
        
        assert update.first_name == "Jane"
        assert update.last_name is None
        assert update.travel_preferences is None

    def test_user_update_only_last_name(self):
        """Test updating only last name."""
        update = UserUpdate(last_name="Smith")
        
        assert update.first_name is None
        assert update.last_name == "Smith"
        assert update.travel_preferences is None

    def test_user_update_only_preferences(self):
        """Test updating only travel preferences."""
        prefs = TravelPreferences(
            budget_min=2000,
            budget_max=8000,
            preferred_currency="EUR",
            accommodation_types=["hotel"],
            activity_interests=["museums"]
        )
        
        update = UserUpdate(travel_preferences=prefs)
        
        assert update.first_name is None
        assert update.last_name is None
        assert update.travel_preferences == prefs

    def test_user_update_all_fields(self):
        """Test updating all available fields."""
        prefs = TravelPreferences(
            budget_min=1500,
            budget_max=6000,
            preferred_currency="GBP",
            accommodation_types=["apartment", "hotel"],
            activity_interests=["hiking", "museums", "food"],
            dietary_restrictions=["vegetarian"],
            travel_style="adventure"
        )
        
        update = UserUpdate(
            first_name="Alice",
            last_name="Johnson",
            travel_preferences=prefs
        )
        
        assert update.first_name == "Alice"
        assert update.last_name == "Johnson"
        assert update.travel_preferences == prefs

    def test_user_update_name_validation_failure(self):
        """Test name validation in user updates."""
        # Empty string not allowed
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(first_name="")
        assert "String should have at least 1 character" in str(exc_info.value)
        
        # Too long name not allowed
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(last_name="a" * 101)  # 101 characters
        assert "String should have at most 100 characters" in str(exc_info.value)

    def test_user_update_nested_preferences_validation(self):
        """Test that nested travel preferences validation works in updates."""
        # Invalid nested preferences should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(travel_preferences=TravelPreferences(
                budget_min=5000,
                budget_max=1000  # Invalid: max < min
            ))
        assert "Maximum budget must be greater than minimum budget" in str(exc_info.value)
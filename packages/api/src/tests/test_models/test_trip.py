"""Tests for trip data models."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from travel_companion.models.trip import (
    AccommodationType,
    ActivityOption,
    FlightOption,
    HotelOption,
    TravelClass,
    TripDestination,
    TripPlan,
    TripPlanRequest,
    TripRequirements,
    TripStatus,
)


class TestTripDestination:
    """Test TripDestination model."""

    def test_destination_creation(self):
        """Test creating a trip destination."""
        destination = TripDestination(
            city="Paris",
            country="France",
            country_code="FR",
            airport_code="CDG",
            latitude=48.8566,
            longitude=2.3522
        )

        assert destination.city == "Paris"
        assert destination.country == "France"
        assert destination.country_code == "FR"
        assert destination.airport_code == "CDG"
        assert destination.latitude == 48.8566
        assert destination.longitude == 2.3522

    def test_destination_without_optional_fields(self):
        """Test creating a destination with only required fields."""
        destination = TripDestination(
            city="London",
            country="United Kingdom",
            country_code="GB"
        )

        assert destination.city == "London"
        assert destination.airport_code is None
        assert destination.latitude is None
        assert destination.longitude is None

    def test_destination_validation(self):
        """Test destination field validation."""
        # Empty city should fail
        with pytest.raises(ValidationError):
            TripDestination(city="", country="France", country_code="FR")

        # Invalid latitude
        with pytest.raises(ValidationError):
            TripDestination(
                city="Paris",
                country="France",
                country_code="FR",
                latitude=91  # > 90
            )

        # Invalid longitude
        with pytest.raises(ValidationError):
            TripDestination(
                city="Paris",
                country="France",
                country_code="FR",
                longitude=181  # > 180
            )


class TestTripRequirements:
    """Test TripRequirements model."""

    def test_requirements_creation(self):
        """Test creating trip requirements."""
        requirements = TripRequirements(
            budget=Decimal("2000.00"),
            currency="EUR",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 7),
            travelers=2,
            travel_class=TravelClass.BUSINESS,
            accommodation_type=AccommodationType.HOTEL
        )

        assert requirements.budget == Decimal("2000.00")
        assert requirements.currency == "EUR"
        assert requirements.start_date == date(2024, 6, 1)
        assert requirements.end_date == date(2024, 6, 7)
        assert requirements.travelers == 2
        assert requirements.travel_class == TravelClass.BUSINESS
        assert requirements.accommodation_type == AccommodationType.HOTEL

    def test_requirements_defaults(self):
        """Test trip requirements default values."""
        requirements = TripRequirements(
            budget=Decimal("1500.00"),
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 7),
            travelers=1
        )

        assert requirements.currency == "USD"  # Default
        assert requirements.travel_class == TravelClass.ECONOMY  # Default
        assert requirements.accommodation_type is None  # Default

    def test_requirements_validation(self):
        """Test trip requirements validation."""
        # End date before start date
        with pytest.raises(ValidationError):
            TripRequirements(
                budget=Decimal("1000.00"),
                start_date=date(2024, 6, 7),
                end_date=date(2024, 6, 1),  # Before start
                travelers=1
            )

        # Zero budget
        with pytest.raises(ValidationError):
            TripRequirements(
                budget=Decimal("0.00"),  # Must be > 0
                start_date=date(2024, 6, 1),
                end_date=date(2024, 6, 7),
                travelers=1
            )

        # Invalid traveler count
        with pytest.raises(ValidationError):
            TripRequirements(
                budget=Decimal("1000.00"),
                start_date=date(2024, 6, 1),
                end_date=date(2024, 6, 7),
                travelers=0  # Must be >= 1
            )

        with pytest.raises(ValidationError):
            TripRequirements(
                budget=Decimal("1000.00"),
                start_date=date(2024, 6, 1),
                end_date=date(2024, 6, 7),
                travelers=11  # Must be <= 10
            )

        # Invalid currency format
        with pytest.raises(ValidationError):
            TripRequirements(
                budget=Decimal("1000.00"),
                currency="eur",  # Must be uppercase
                start_date=date(2024, 6, 1),
                end_date=date(2024, 6, 7),
                travelers=1
            )


class TestTripPlanRequest:
    """Test TripPlanRequest model."""

    def test_plan_request_creation(self):
        """Test creating a trip plan request."""
        destination = TripDestination(
            city="Tokyo",
            country="Japan",
            country_code="JP"
        )

        requirements = TripRequirements(
            budget=Decimal("3000.00"),
            start_date=date(2024, 8, 1),
            end_date=date(2024, 8, 10),
            travelers=2
        )

        preferences = {
            "dietary_restrictions": ["vegetarian"],
            "activity_interests": ["culture", "food"]
        }

        request = TripPlanRequest(
            destination=destination,
            requirements=requirements,
            preferences=preferences
        )

        assert request.destination.city == "Tokyo"
        assert request.requirements.budget == Decimal("3000.00")
        assert request.preferences["dietary_restrictions"] == ["vegetarian"]

    def test_plan_request_without_preferences(self):
        """Test creating a trip plan request without preferences."""
        destination = TripDestination(
            city="Sydney",
            country="Australia",
            country_code="AU"
        )

        requirements = TripRequirements(
            budget=Decimal("2500.00"),
            start_date=date(2024, 9, 1),
            end_date=date(2024, 9, 7),
            travelers=1
        )

        request = TripPlanRequest(
            destination=destination,
            requirements=requirements
        )

        assert request.preferences is None


class TestFlightOption:
    """Test FlightOption model."""

    def test_flight_option_creation(self):
        """Test creating a flight option."""
        flight = FlightOption(
            airline="Air France",
            flight_number="AF123",
            departure_airport="CDG",
            arrival_airport="JFK",
            departure_time=datetime(2024, 6, 1, 10, 30),
            arrival_time=datetime(2024, 6, 1, 16, 45),
            duration_minutes=495,
            price=Decimal("650.00"),
            currency="EUR",
            travel_class=TravelClass.ECONOMY,
            stops=0
        )

        assert flight.airline == "Air France"
        assert flight.flight_number == "AF123"
        assert flight.duration_minutes == 495
        assert flight.price == Decimal("650.00")
        assert flight.travel_class == TravelClass.ECONOMY
        assert flight.stops == 0

    def test_flight_option_validation(self):
        """Test flight option validation."""
        # Invalid duration
        with pytest.raises(ValidationError):
            FlightOption(
                airline="Test Airline",
                flight_number="TA123",
                departure_airport="AAA",
                arrival_airport="BBB",
                departure_time=datetime(2024, 6, 1, 10, 0),
                arrival_time=datetime(2024, 6, 1, 12, 0),
                duration_minutes=0,  # Must be > 0
                price=Decimal("100.00"),
                currency="USD",
                travel_class=TravelClass.ECONOMY,
                stops=0
            )

        # Invalid price
        with pytest.raises(ValidationError):
            FlightOption(
                airline="Test Airline",
                flight_number="TA123",
                departure_airport="AAA",
                arrival_airport="BBB",
                departure_time=datetime(2024, 6, 1, 10, 0),
                arrival_time=datetime(2024, 6, 1, 12, 0),
                duration_minutes=120,
                price=Decimal("0.00"),  # Must be > 0
                currency="USD",
                travel_class=TravelClass.ECONOMY,
                stops=0
            )


class TestHotelOption:
    """Test HotelOption model."""

    def test_hotel_option_creation(self):
        """Test creating a hotel option."""
        hotel = HotelOption(
            name="Hotel Paris",
            address="123 Rue de la Paix, Paris",
            star_rating=4,
            guest_rating=8.5,
            price_per_night=Decimal("150.00"),
            currency="EUR",
            accommodation_type=AccommodationType.HOTEL,
            amenities=["wifi", "breakfast", "gym"],
            distance_to_center=2.5
        )

        assert hotel.name == "Hotel Paris"
        assert hotel.star_rating == 4
        assert hotel.guest_rating == 8.5
        assert hotel.price_per_night == Decimal("150.00")
        assert hotel.accommodation_type == AccommodationType.HOTEL
        assert "wifi" in hotel.amenities

    def test_hotel_option_validation(self):
        """Test hotel option validation."""
        # Invalid star rating
        with pytest.raises(ValidationError):
            HotelOption(
                name="Test Hotel",
                address="Test Address",
                star_rating=6,  # Must be <= 5
                price_per_night=Decimal("100.00"),
                currency="USD",
                accommodation_type=AccommodationType.HOTEL
            )

        # Invalid guest rating
        with pytest.raises(ValidationError):
            HotelOption(
                name="Test Hotel",
                address="Test Address",
                guest_rating=11.0,  # Must be <= 10
                price_per_night=Decimal("100.00"),
                currency="USD",
                accommodation_type=AccommodationType.HOTEL
            )


class TestActivityOption:
    """Test ActivityOption model."""

    def test_activity_option_creation(self):
        """Test creating an activity option."""
        activity = ActivityOption(
            name="Eiffel Tower Tour",
            description="Guided tour of the iconic Eiffel Tower",
            category="Sightseeing",
            duration_hours=2.5,
            price=Decimal("35.00"),
            currency="EUR",
            location="Champ de Mars, Paris",
            rating=9.2,
            min_age=5
        )

        assert activity.name == "Eiffel Tower Tour"
        assert activity.category == "Sightseeing"
        assert activity.duration_hours == 2.5
        assert activity.price == Decimal("35.00")
        assert activity.rating == 9.2
        assert activity.min_age == 5

    def test_activity_option_minimal(self):
        """Test creating an activity with only required fields."""
        activity = ActivityOption(
            name="Walking Tour",
            description="Free walking tour of the city",
            category="Culture",
            location="City Center"
        )

        assert activity.name == "Walking Tour"
        assert activity.duration_hours is None
        assert activity.price is None
        assert activity.rating is None
        assert activity.min_age is None


class TestTripPlan:
    """Test TripPlan model."""

    def test_trip_plan_creation(self):
        """Test creating a complete trip plan."""
        flights = [
            FlightOption(
                airline="Test Airline",
                flight_number="TA123",
                departure_airport="JFK",
                arrival_airport="CDG",
                departure_time=datetime(2024, 6, 1, 10, 0),
                arrival_time=datetime(2024, 6, 1, 16, 0),
                duration_minutes=480,
                price=Decimal("600.00"),
                currency="USD",
                travel_class=TravelClass.ECONOMY,
                stops=0
            )
        ]

        hotels = [
            HotelOption(
                name="Test Hotel",
                address="Test Address",
                price_per_night=Decimal("120.00"),
                currency="EUR",
                accommodation_type=AccommodationType.HOTEL
            )
        ]

        plan = TripPlan(
            flights=flights,
            hotels=hotels,
            activities=[],
            total_estimated_cost=Decimal("1500.00"),
            currency="EUR"
        )

        assert len(plan.flights) == 1
        assert len(plan.hotels) == 1
        assert len(plan.activities) == 0
        assert plan.total_estimated_cost == Decimal("1500.00")
        assert isinstance(plan.generated_at, datetime)

    def test_trip_plan_empty(self):
        """Test creating an empty trip plan."""
        plan = TripPlan(
            total_estimated_cost=Decimal("1.00"),  # Must be > 0
            currency="USD"
        )

        assert len(plan.flights) == 0
        assert len(plan.hotels) == 0
        assert len(plan.activities) == 0


class TestEnums:
    """Test enumeration classes."""

    def test_trip_status_enum(self):
        """Test TripStatus enum values."""
        assert TripStatus.DRAFT == "draft"
        assert TripStatus.PLANNING == "planning"
        assert TripStatus.CONFIRMED == "confirmed"
        assert TripStatus.COMPLETED == "completed"
        assert TripStatus.CANCELLED == "cancelled"

    def test_travel_class_enum(self):
        """Test TravelClass enum values."""
        assert TravelClass.ECONOMY == "economy"
        assert TravelClass.PREMIUM_ECONOMY == "premium_economy"
        assert TravelClass.BUSINESS == "business"
        assert TravelClass.FIRST == "first"

    def test_accommodation_type_enum(self):
        """Test AccommodationType enum values."""
        assert AccommodationType.HOTEL == "hotel"
        assert AccommodationType.APARTMENT == "apartment"
        assert AccommodationType.HOSTEL == "hostel"
        assert AccommodationType.RESORT == "resort"
        assert AccommodationType.BED_AND_BREAKFAST == "bed_and_breakfast"
        assert AccommodationType.VACATION_RENTAL == "vacation_rental"

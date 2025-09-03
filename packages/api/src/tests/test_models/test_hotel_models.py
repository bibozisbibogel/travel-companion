"""Tests for hotel data models in external.py."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from travel_companion.models.external import (
    HotelComparisonResult,
    HotelLocation,
    HotelOption,
    HotelSearchRequest,
    HotelSearchResponse,
)


class TestHotelSearchRequest:
    """Test suite for HotelSearchRequest model."""

    def test_hotel_search_request_valid(self):
        """Test HotelSearchRequest creation with valid data."""
        check_in = datetime(2024, 6, 15, 15, 0)
        check_out = datetime(2024, 6, 17, 11, 0)

        request = HotelSearchRequest(
            location="New York",
            check_in_date=check_in,
            check_out_date=check_out,
            guest_count=2,
            room_count=1,
            budget_per_night=Decimal("200.00"),
            currency="USD",
            max_results=50,
        )

        assert request.location == "New York"
        assert request.check_in_date == check_in
        assert request.check_out_date == check_out
        assert request.guest_count == 2
        assert request.room_count == 1
        assert request.budget_per_night == Decimal("200.00")
        assert request.currency == "USD"
        assert request.max_results == 50

    def test_hotel_search_request_defaults(self):
        """Test HotelSearchRequest default values."""
        check_in = datetime(2024, 6, 15)
        check_out = datetime(2024, 6, 17)

        request = HotelSearchRequest(
            location="Paris",
            check_in_date=check_in,
            check_out_date=check_out,
            guest_count=4,
        )

        assert request.room_count == 1  # Default
        assert request.currency == "USD"  # Default
        assert request.max_results == 50  # Default
        assert request.budget_per_night is None  # Default

    def test_hotel_search_request_validation_guest_count_limits(self):
        """Test HotelSearchRequest validates guest count limits."""
        check_in = datetime(2024, 6, 15)
        check_out = datetime(2024, 6, 17)

        # Test minimum guest count
        with pytest.raises(ValidationError) as exc_info:
            HotelSearchRequest(
                location="Tokyo",
                check_in_date=check_in,
                check_out_date=check_out,
                guest_count=0,  # Below minimum
            )
        assert "greater than or equal to 1" in str(exc_info.value)

        # Test maximum guest count
        with pytest.raises(ValidationError) as exc_info:
            HotelSearchRequest(
                location="Tokyo",
                check_in_date=check_in,
                check_out_date=check_out,
                guest_count=25,  # Above maximum
            )
        assert "less than or equal to 20" in str(exc_info.value)

    def test_hotel_search_request_validation_room_count_limits(self):
        """Test HotelSearchRequest validates room count limits."""
        check_in = datetime(2024, 6, 15)
        check_out = datetime(2024, 6, 17)

        # Test maximum room count
        with pytest.raises(ValidationError) as exc_info:
            HotelSearchRequest(
                location="London",
                check_in_date=check_in,
                check_out_date=check_out,
                guest_count=2,
                room_count=15,  # Above maximum
            )
        assert "less than or equal to 10" in str(exc_info.value)

    def test_hotel_search_request_validation_budget_positive(self):
        """Test HotelSearchRequest validates budget is positive."""
        check_in = datetime(2024, 6, 15)
        check_out = datetime(2024, 6, 17)

        with pytest.raises(ValidationError) as exc_info:
            HotelSearchRequest(
                location="Berlin",
                check_in_date=check_in,
                check_out_date=check_out,
                guest_count=2,
                budget_per_night=Decimal("-50.00"),  # Negative budget
            )
        assert "greater than 0" in str(exc_info.value)

    def test_hotel_search_request_validation_max_results_limits(self):
        """Test HotelSearchRequest validates max results limits."""
        check_in = datetime(2024, 6, 15)
        check_out = datetime(2024, 6, 17)

        # Test maximum results
        with pytest.raises(ValidationError) as exc_info:
            HotelSearchRequest(
                location="Madrid",
                check_in_date=check_in,
                check_out_date=check_out,
                guest_count=2,
                max_results=500,  # Above maximum
            )
        assert "less than or equal to 250" in str(exc_info.value)

    def test_hotel_search_request_validation_currency_uppercase(self):
        """Test HotelSearchRequest validates currency is uppercase."""
        check_in = datetime(2024, 6, 15)
        check_out = datetime(2024, 6, 17)

        with pytest.raises(ValidationError) as exc_info:
            HotelSearchRequest(
                location="Rome",
                check_in_date=check_in,
                check_out_date=check_out,
                guest_count=2,
                currency="eur",  # Lowercase currency
            )
        assert "Currency code must be uppercase" in str(exc_info.value)

    def test_hotel_search_request_validation_location_not_empty(self):
        """Test HotelSearchRequest validates location is not empty."""
        check_in = datetime(2024, 6, 15)
        check_out = datetime(2024, 6, 17)

        with pytest.raises(ValidationError) as exc_info:
            HotelSearchRequest(
                location="",  # Empty location
                check_in_date=check_in,
                check_out_date=check_out,
                guest_count=2,
            )
        assert "at least 1 character" in str(exc_info.value)

    def test_hotel_search_request_checkout_after_checkin_validation(self):
        """Test HotelSearchRequest validates check-out after check-in."""
        check_in = datetime(2024, 6, 17)
        check_out = datetime(2024, 6, 15)  # Before check-in

        with pytest.raises(ValidationError) as exc_info:
            HotelSearchRequest(
                location="Amsterdam",
                check_in_date=check_in,
                check_out_date=check_out,  # Before check-in
                guest_count=2,
            )
        assert "Check-out date must be after check-in date" in str(exc_info.value)


class TestHotelLocation:
    """Test suite for HotelLocation model."""

    def test_hotel_location_valid(self):
        """Test HotelLocation creation with valid data."""
        location = HotelLocation(
            latitude=40.7128,
            longitude=-74.0060,
            address="123 Main St",
            city="New York",
            country="USA",
            postal_code="10001",
        )

        assert location.latitude == 40.7128
        assert location.longitude == -74.0060
        assert location.address == "123 Main St"
        assert location.city == "New York"
        assert location.country == "USA"
        assert location.postal_code == "10001"

    def test_hotel_location_minimal(self):
        """Test HotelLocation with only required fields."""
        location = HotelLocation(
            latitude=48.8566,
            longitude=2.3522,
        )

        assert location.latitude == 48.8566
        assert location.longitude == 2.3522
        assert location.address is None
        assert location.city is None
        assert location.country is None
        assert location.postal_code is None

    def test_hotel_location_validation_latitude_limits(self):
        """Test HotelLocation validates latitude limits."""
        # Test minimum latitude
        with pytest.raises(ValidationError) as exc_info:
            HotelLocation(latitude=-95.0, longitude=0.0)
        assert "greater than or equal to -90" in str(exc_info.value)

        # Test maximum latitude
        with pytest.raises(ValidationError) as exc_info:
            HotelLocation(latitude=95.0, longitude=0.0)
        assert "less than or equal to 90" in str(exc_info.value)

    def test_hotel_location_validation_longitude_limits(self):
        """Test HotelLocation validates longitude limits."""
        # Test minimum longitude
        with pytest.raises(ValidationError) as exc_info:
            HotelLocation(latitude=0.0, longitude=-185.0)
        assert "greater than or equal to -180" in str(exc_info.value)

        # Test maximum longitude
        with pytest.raises(ValidationError) as exc_info:
            HotelLocation(latitude=0.0, longitude=185.0)
        assert "less than or equal to 180" in str(exc_info.value)


class TestHotelOption:
    """Test suite for HotelOption model."""

    @pytest.fixture
    def sample_hotel_location(self) -> HotelLocation:
        """Create sample hotel location for testing."""
        return HotelLocation(
            latitude=40.7128,
            longitude=-74.0060,
            address="123 Test St",
            city="New York",
            country="USA",
        )

    def test_hotel_option_valid(self, sample_hotel_location):
        """Test HotelOption creation with valid data."""
        hotel_id = uuid4()
        trip_id = uuid4()

        hotel = HotelOption(
            hotel_id=hotel_id,
            trip_id=trip_id,
            external_id="booking_123",
            name="Test Hotel",
            location=sample_hotel_location,
            price_per_night=Decimal("150.00"),
            currency="USD",
            rating=4.5,
            amenities=["WiFi", "Pool", "Gym"],
            photos=["https://example.com/photo1.jpg"],
            booking_url="https://booking.com/hotel/123",
        )

        assert hotel.hotel_id == hotel_id
        assert hotel.trip_id == trip_id
        assert hotel.external_id == "booking_123"
        assert hotel.name == "Test Hotel"
        assert hotel.location == sample_hotel_location
        assert hotel.price_per_night == Decimal("150.00")
        assert hotel.currency == "USD"
        assert hotel.rating == 4.5
        assert hotel.amenities == ["WiFi", "Pool", "Gym"]
        assert hotel.photos == ["https://example.com/photo1.jpg"]
        assert hotel.booking_url == "https://booking.com/hotel/123"

    def test_hotel_option_defaults(self, sample_hotel_location):
        """Test HotelOption default values."""
        hotel = HotelOption(
            external_id="test_123",
            name="Minimal Hotel",
            location=sample_hotel_location,
            price_per_night=Decimal("100.00"),
        )

        assert hotel.trip_id is None  # Default
        assert hotel.currency == "USD"  # Default
        assert hotel.rating is None  # Default
        assert hotel.amenities == []  # Default
        assert hotel.photos == []  # Default
        assert hotel.booking_url is None  # Default
        assert hotel.created_at is not None  # Generated

    def test_hotel_option_auto_generated_fields(self, sample_hotel_location):
        """Test HotelOption auto-generated fields."""
        hotel = HotelOption(
            external_id="auto_test",
            name="Auto Hotel",
            location=sample_hotel_location,
            price_per_night=Decimal("200.00"),
        )

        # Hotel ID should be auto-generated UUID
        assert hotel.hotel_id is not None
        assert len(str(hotel.hotel_id)) == 36  # UUID length

        # Created_at should be auto-generated
        assert hotel.created_at is not None
        assert isinstance(hotel.created_at, datetime)

    def test_hotel_option_validation_price_positive(self, sample_hotel_location):
        """Test HotelOption validates price is positive."""
        with pytest.raises(ValidationError) as exc_info:
            HotelOption(
                external_id="negative_price",
                name="Bad Hotel",
                location=sample_hotel_location,
                price_per_night=Decimal("-50.00"),  # Negative price
            )
        assert "greater than 0" in str(exc_info.value)

    def test_hotel_option_validation_price_precision(self, sample_hotel_location):
        """Test HotelOption validates price precision (2 decimal places)."""
        hotel = HotelOption(
            external_id="precision_test",
            name="Precision Hotel",
            location=sample_hotel_location,
            price_per_night=Decimal("123.456789"),  # More than 2 decimal places
        )

        # Should be rounded to 2 decimal places
        assert hotel.price_per_night == Decimal("123.46")

    def test_hotel_option_validation_rating_limits(self, sample_hotel_location):
        """Test HotelOption validates rating limits."""
        # Test minimum rating
        with pytest.raises(ValidationError) as exc_info:
            HotelOption(
                external_id="rating_test",
                name="Bad Rating Hotel",
                location=sample_hotel_location,
                price_per_night=Decimal("100.00"),
                rating=0.5,  # Below minimum
            )
        assert "greater than or equal to 1" in str(exc_info.value)

        # Test maximum rating
        with pytest.raises(ValidationError) as exc_info:
            HotelOption(
                external_id="rating_test",
                name="High Rating Hotel",
                location=sample_hotel_location,
                price_per_night=Decimal("100.00"),
                rating=6.0,  # Above maximum
            )
        assert "less than or equal to 5" in str(exc_info.value)

    def test_hotel_option_validation_name_not_empty(self, sample_hotel_location):
        """Test HotelOption validates name is not empty."""
        with pytest.raises(ValidationError) as exc_info:
            HotelOption(
                external_id="empty_name",
                name="",  # Empty name
                location=sample_hotel_location,
                price_per_night=Decimal("100.00"),
            )
        assert "at least 1 character" in str(exc_info.value)

    def test_hotel_option_serialization(self, sample_hotel_location):
        """Test HotelOption serialization to dict."""
        hotel = HotelOption(
            external_id="serialization_test",
            name="Serialize Hotel",
            location=sample_hotel_location,
            price_per_night=Decimal("175.50"),
            rating=4.2,
            amenities=["WiFi", "Breakfast"],
        )

        data = hotel.model_dump()

        assert data["external_id"] == "serialization_test"
        assert data["name"] == "Serialize Hotel"
        assert data["price_per_night"] == Decimal("175.50")
        assert data["rating"] == 4.2
        assert data["amenities"] == ["WiFi", "Breakfast"]
        assert "hotel_id" in data
        assert "created_at" in data

    def test_hotel_option_from_dict(self, sample_hotel_location):
        """Test HotelOption creation from dict (from_attributes)."""
        data = {
            "external_id": "dict_test",
            "name": "Dict Hotel",
            "location": sample_hotel_location,
            "price_per_night": "89.99",  # String should be converted
            "currency": "EUR",
            "rating": 3.8,
        }

        hotel = HotelOption(**data)

        assert hotel.external_id == "dict_test"
        assert hotel.name == "Dict Hotel"
        assert hotel.price_per_night == Decimal("89.99")
        assert hotel.currency == "EUR"
        assert hotel.rating == 3.8


class TestHotelSearchResponse:
    """Test suite for HotelSearchResponse model."""

    @pytest.fixture
    def sample_hotels(self) -> list[HotelOption]:
        """Create sample hotel list for testing."""
        location = HotelLocation(latitude=40.7128, longitude=-74.0060)
        return [
            HotelOption(
                external_id="hotel_1",
                name="Hotel One",
                location=location,
                price_per_night=Decimal("120.00"),
            ),
            HotelOption(
                external_id="hotel_2",
                name="Hotel Two",
                location=location,
                price_per_night=Decimal("180.00"),
            ),
        ]

    def test_hotel_search_response_valid(self, sample_hotels):
        """Test HotelSearchResponse creation with valid data."""
        cache_expires = datetime(2024, 6, 15, 18, 0)

        response = HotelSearchResponse(
            hotels=sample_hotels,
            search_metadata={"location": "New York", "budget": 200},
            total_results=2,
            search_time_ms=150,
            cached=True,
            cache_expires_at=cache_expires,
        )

        assert len(response.hotels) == 2
        assert response.hotels[0].name == "Hotel One"
        assert response.search_metadata == {"location": "New York", "budget": 200}
        assert response.total_results == 2
        assert response.search_time_ms == 150
        assert response.cached is True
        assert response.cache_expires_at == cache_expires

    def test_hotel_search_response_defaults(self):
        """Test HotelSearchResponse default values."""
        response = HotelSearchResponse()

        assert response.hotels == []  # Default
        assert response.search_metadata == {}  # Default
        assert response.total_results == 0  # Default
        assert response.search_time_ms == 0  # Default
        assert response.cached is False  # Default
        assert response.cache_expires_at is None  # Default

    def test_hotel_search_response_validation_positive_values(self):
        """Test HotelSearchResponse validates positive values."""
        # Test negative total results
        with pytest.raises(ValidationError) as exc_info:
            HotelSearchResponse(total_results=-5)
        assert "greater than or equal to 0" in str(exc_info.value)

        # Test negative search time
        with pytest.raises(ValidationError) as exc_info:
            HotelSearchResponse(search_time_ms=-100)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_hotel_search_response_serialization(self, sample_hotels):
        """Test HotelSearchResponse serialization."""
        response = HotelSearchResponse(
            hotels=sample_hotels,
            total_results=2,
            search_time_ms=200,
        )

        data = response.model_dump()

        assert len(data["hotels"]) == 2
        assert data["total_results"] == 2
        assert data["search_time_ms"] == 200
        assert data["cached"] is False


class TestHotelComparisonResult:
    """Test suite for HotelComparisonResult model."""

    @pytest.fixture
    def sample_hotel(self) -> HotelOption:
        """Create sample hotel for testing."""
        location = HotelLocation(latitude=40.7128, longitude=-74.0060)
        return HotelOption(
            external_id="comparison_test",
            name="Comparison Hotel",
            location=location,
            price_per_night=Decimal("150.00"),
            rating=4.2,
        )

    def test_hotel_comparison_result_valid(self, sample_hotel):
        """Test HotelComparisonResult creation with valid data."""
        comparison = HotelComparisonResult(
            hotel=sample_hotel,
            score=85.5,
            price_rank=2,
            location_rank=1,
            rating_rank=3,
            value_score=0.75,
            reasons=["Great location", "Good price"],
        )

        assert comparison.hotel == sample_hotel
        assert comparison.score == 85.5
        assert comparison.price_rank == 2
        assert comparison.location_rank == 1
        assert comparison.rating_rank == 3
        assert comparison.value_score == 0.75
        assert comparison.reasons == ["Great location", "Good price"]

    def test_hotel_comparison_result_defaults(self, sample_hotel):
        """Test HotelComparisonResult default values."""
        comparison = HotelComparisonResult(
            hotel=sample_hotel,
            score=90.0,
            price_rank=1,
            location_rank=1,
            rating_rank=1,
            value_score=0.9,
        )

        assert comparison.reasons == []  # Default empty list

    def test_hotel_comparison_result_validation_score_limits(self, sample_hotel):
        """Test HotelComparisonResult validates score limits."""
        # Test minimum score
        with pytest.raises(ValidationError) as exc_info:
            HotelComparisonResult(
                hotel=sample_hotel,
                score=-5.0,  # Below minimum
                price_rank=1,
                location_rank=1,
                rating_rank=1,
                value_score=0.5,
            )
        assert "greater than or equal to 0" in str(exc_info.value)

        # Test maximum score
        with pytest.raises(ValidationError) as exc_info:
            HotelComparisonResult(
                hotel=sample_hotel,
                score=105.0,  # Above maximum
                price_rank=1,
                location_rank=1,
                rating_rank=1,
                value_score=0.5,
            )
        assert "less than or equal to 100" in str(exc_info.value)

    def test_hotel_comparison_result_validation_value_score_limits(self, sample_hotel):
        """Test HotelComparisonResult validates value score limits."""
        # Test minimum value score
        with pytest.raises(ValidationError) as exc_info:
            HotelComparisonResult(
                hotel=sample_hotel,
                score=80.0,
                price_rank=1,
                location_rank=1,
                rating_rank=1,
                value_score=-0.1,  # Below minimum
            )
        assert "greater than or equal to 0" in str(exc_info.value)

        # Test maximum value score
        with pytest.raises(ValidationError) as exc_info:
            HotelComparisonResult(
                hotel=sample_hotel,
                score=80.0,
                price_rank=1,
                location_rank=1,
                rating_rank=1,
                value_score=1.5,  # Above maximum
            )
        assert "less than or equal to 1" in str(exc_info.value)

    def test_hotel_comparison_result_validation_rank_minimum(self, sample_hotel):
        """Test HotelComparisonResult validates rank minimums."""
        # Test price rank minimum
        with pytest.raises(ValidationError) as exc_info:
            HotelComparisonResult(
                hotel=sample_hotel,
                score=80.0,
                price_rank=0,  # Below minimum
                location_rank=1,
                rating_rank=1,
                value_score=0.8,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_hotel_comparison_result_serialization(self, sample_hotel):
        """Test HotelComparisonResult serialization."""
        comparison = HotelComparisonResult(
            hotel=sample_hotel,
            score=88.0,
            price_rank=1,
            location_rank=2,
            rating_rank=1,
            value_score=0.92,
            reasons=["Best value", "Excellent rating"],
        )

        data = comparison.model_dump()

        assert "hotel" in data
        assert data["score"] == 88.0
        assert data["price_rank"] == 1
        assert data["location_rank"] == 2
        assert data["rating_rank"] == 1
        assert data["value_score"] == 0.92
        assert data["reasons"] == ["Best value", "Excellent rating"]

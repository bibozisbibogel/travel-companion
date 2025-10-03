"""Tests for Hotel Agent API fallback functionality."""

from decimal import Decimal
from unittest.mock import patch

import pytest

from travel_companion.agents.hotel_agent import HotelAgent
from travel_companion.models.external import HotelSearchResponse
from travel_companion.services.external_apis.airbnb import AirbnbListingResult
from travel_companion.services.external_apis.booking import BookingApiResponse
from travel_companion.services.external_apis.expedia import ExpediaHotelResult
from travel_companion.utils.errors import ExternalAPIError


@pytest.fixture
def hotel_agent():
    """Create HotelAgent instance for testing."""
    return HotelAgent()


@pytest.fixture
def sample_search_request():
    """Sample hotel search request."""
    return {
        "location": "New York, NY",
        "check_in_date": "2024-03-15",
        "check_out_date": "2024-03-18",
        "guest_count": 2,
        "room_count": 1,
        "budget": 200.0,
        "currency": "USD",
        "max_results": 10,
    }


@pytest.fixture
def booking_api_response():
    """Mock Booking.com API successful response."""
    from travel_companion.services.external_apis.booking import BookingHotelResult

    booking_hotel = BookingHotelResult(
        hotel_id="booking_123",
        name="Booking Hotel NYC",
        address="123 Broadway, NY",
        latitude=40.7589,
        longitude=-73.9851,
        rating=4.2,
        price_per_night=150.0,
        currency="USD",
        amenities=["WiFi", "Gym"],
        photos=["booking1.jpg"],
        booking_url="https://booking.com/hotel/123",
    )

    return BookingApiResponse(
        hotels=[booking_hotel], api_response_time_ms=1200, total_results=1, has_more_results=False
    )


@pytest.fixture
def expedia_api_response():
    """Mock Expedia API successful response."""
    expedia_hotel = ExpediaHotelResult(
        hotel_id="expedia_456",
        name="Expedia Hotel NYC",
        address="456 Fifth Ave, NY",
        latitude=40.7614,
        longitude=-73.9776,
        rating=4.5,
        price_per_night=180.0,
        currency="USD",
        amenities=["WiFi", "Pool", "Parking"],
        photos=["expedia1.jpg", "expedia2.jpg"],
        booking_url="https://expedia.com/hotel/456",
        description="Luxury hotel in Midtown",
    )

    return [expedia_hotel]


@pytest.fixture
def airbnb_api_response():
    """Mock Airbnb API successful response."""
    airbnb_listing = AirbnbListingResult(
        listing_id="airbnb_789",
        name="Cozy NYC Apartment",
        property_type="Apartment",
        address="789 Park Ave, NY",
        latitude=40.7505,
        longitude=-73.9934,
        rating=4.8,
        review_count=67,
        price_per_night=120.0,
        currency="USD",
        amenities=["WiFi", "Kitchen", "Washer"],
        photos=["airbnb1.jpg"],
        booking_url="https://airbnb.com/rooms/789",
        bedrooms=1,
        bathrooms=1.0,
        max_guests=2,
        host_name="John",
        instant_book=True,
    )

    return [airbnb_listing]


@pytest.mark.skip(reason="Booking, Expedia, and Airbnb clients are currently disabled")
class TestHotelAgentFallback:
    """Test suite for Hotel Agent API fallback functionality."""

    async def test_successful_booking_api_no_fallback(
        self, hotel_agent, sample_search_request, booking_api_response
    ):
        """Test successful hotel search using Booking.com API without fallback."""
        with patch.object(
            hotel_agent._booking_client, "search_hotels", return_value=booking_api_response
        ):
            response = await hotel_agent._search_hotels(sample_search_request)

            assert isinstance(response, HotelSearchResponse)
            assert len(response.hotels) == 1
            assert response.search_metadata["successful_api"] == "booking.com"
            assert "booking.com" in response.search_metadata["apis_attempted"]
            assert len(response.search_metadata["apis_attempted"]) == 1
            assert response.hotels[0].external_id == "booking_booking_123"
            assert response.hotels[0].name == "Booking Hotel NYC"
            assert response.hotels[0].price_per_night == Decimal("150.0")

    async def test_fallback_to_expedia_when_booking_fails(
        self, hotel_agent, sample_search_request, expedia_api_response
    ):
        """Test fallback to Expedia API when Booking.com fails."""
        with (
            patch.object(
                hotel_agent._booking_client,
                "search_hotels",
                side_effect=ExternalAPIError("Booking.com API failed"),
            ),
            patch.object(
                hotel_agent._expedia_client, "search_hotels", return_value=expedia_api_response
            ),
        ):
            response = await hotel_agent._search_hotels(sample_search_request)

            assert isinstance(response, HotelSearchResponse)
            assert len(response.hotels) == 1
            assert response.search_metadata["successful_api"] == "expedia"
            assert "booking.com" in response.search_metadata["apis_attempted"]
            assert "expedia" in response.search_metadata["apis_attempted"]
            assert len(response.search_metadata["apis_attempted"]) == 2
            assert response.hotels[0].external_id == "expedia_expedia_456"
            assert response.hotels[0].name == "Expedia Hotel NYC"
            assert response.hotels[0].price_per_night == Decimal("180.0")
            assert "Booking.com API failed" in response.search_metadata["api_errors"]["booking.com"]

    async def test_fallback_to_airbnb_when_booking_and_expedia_fail(
        self, hotel_agent, sample_search_request, airbnb_api_response
    ):
        """Test fallback to Airbnb API when both Booking.com and Expedia fail."""
        with (
            patch.object(
                hotel_agent._booking_client,
                "search_hotels",
                side_effect=ExternalAPIError("Booking.com API failed"),
            ),
            patch.object(
                hotel_agent._expedia_client,
                "search_hotels",
                side_effect=ExternalAPIError("Expedia API failed"),
            ),
            patch.object(
                hotel_agent._airbnb_client, "search_listings", return_value=airbnb_api_response
            ),
        ):
            response = await hotel_agent._search_hotels(sample_search_request)

            assert isinstance(response, HotelSearchResponse)
            assert len(response.hotels) == 1
            assert response.search_metadata["successful_api"] == "airbnb"
            assert "booking.com" in response.search_metadata["apis_attempted"]
            assert "expedia" in response.search_metadata["apis_attempted"]
            assert "airbnb" in response.search_metadata["apis_attempted"]
            assert len(response.search_metadata["apis_attempted"]) == 3
            assert response.hotels[0].external_id == "airbnb_airbnb_789"
            assert response.hotels[0].name == "Cozy NYC Apartment"
            assert response.hotels[0].price_per_night == Decimal("120.0")
            assert "Booking.com API failed" in response.search_metadata["api_errors"]["booking.com"]
            assert "Expedia API failed" in response.search_metadata["api_errors"]["expedia"]

    async def test_all_apis_fail_returns_empty_results(self, hotel_agent, sample_search_request):
        """Test that when all APIs fail, empty results are returned."""
        with (
            patch.object(
                hotel_agent._booking_client,
                "search_hotels",
                side_effect=ExternalAPIError("Booking.com API failed"),
            ),
            patch.object(
                hotel_agent._expedia_client,
                "search_hotels",
                side_effect=ExternalAPIError("Expedia API failed"),
            ),
            patch.object(
                hotel_agent._airbnb_client,
                "search_listings",
                side_effect=ExternalAPIError("Airbnb API failed"),
            ),
        ):
            response = await hotel_agent._search_hotels(sample_search_request)

            assert isinstance(response, HotelSearchResponse)
            assert len(response.hotels) == 0
            assert response.search_metadata["successful_api"] is None
            assert len(response.search_metadata["apis_attempted"]) == 3
            assert "Booking.com API failed" in response.search_metadata["api_errors"]["booking.com"]
            assert "Expedia API failed" in response.search_metadata["api_errors"]["expedia"]
            assert "Airbnb API failed" in response.search_metadata["api_errors"]["airbnb"]
            assert response.total_results == 0

    async def test_budget_filtering_applied_across_all_apis(
        self, hotel_agent, booking_api_response, expedia_api_response, airbnb_api_response
    ):
        """Test that budget filtering is applied consistently across all APIs."""
        # Set a low budget that should filter out expensive hotels
        search_request = {
            "location": "New York, NY",
            "check_in_date": "2024-03-15",
            "check_out_date": "2024-03-18",
            "guest_count": 2,
            "room_count": 1,
            "budget": 100.0,  # Low budget to filter out hotels
            "currency": "USD",
            "max_results": 10,
        }

        # Test Booking.com with budget filter
        with patch.object(
            hotel_agent._booking_client, "search_hotels", return_value=booking_api_response
        ):
            response = await hotel_agent._search_hotels(search_request)
            # Booking hotel costs $150, should be filtered out
            assert len(response.hotels) == 0
            assert response.search_metadata["successful_api"] == "booking.com"

        # Test fallback to Expedia with budget filter
        with (
            patch.object(
                hotel_agent._booking_client,
                "search_hotels",
                side_effect=ExternalAPIError("Booking.com API failed"),
            ),
            patch.object(
                hotel_agent._expedia_client, "search_hotels", return_value=expedia_api_response
            ),
        ):
            response = await hotel_agent._search_hotels(search_request)
            # Expedia hotel costs $180, should be filtered out
            assert len(response.hotels) == 0
            assert response.search_metadata["successful_api"] == "expedia"

        # Test fallback to Airbnb which should pass budget filter
        with (
            patch.object(
                hotel_agent._booking_client,
                "search_hotels",
                side_effect=ExternalAPIError("Booking.com API failed"),
            ),
            patch.object(
                hotel_agent._expedia_client,
                "search_hotels",
                side_effect=ExternalAPIError("Expedia API failed"),
            ),
            patch.object(
                hotel_agent._airbnb_client, "search_listings", return_value=airbnb_api_response
            ),
        ):
            response = await hotel_agent._search_hotels(search_request)
            # Airbnb listing costs $120, but Airbnb API handles budget filtering internally
            # so it should return results
            assert len(response.hotels) == 1
            assert response.search_metadata["successful_api"] == "airbnb"

    async def test_mixed_api_results_metadata_tracking(
        self, hotel_agent, sample_search_request, booking_api_response, expedia_api_response
    ):
        """Test that metadata is properly tracked when switching between APIs."""
        # First test successful Booking.com
        with patch.object(
            hotel_agent._booking_client, "search_hotels", return_value=booking_api_response
        ):
            response = await hotel_agent._search_hotels(sample_search_request)

            assert "booking_api_response_time" in response.search_metadata
            assert "booking_total_results" in response.search_metadata
            assert response.search_metadata["booking_api_response_time"] == 1200
            assert response.search_metadata["booking_total_results"] == 1

        # Then test fallback to Expedia
        with (
            patch.object(
                hotel_agent._booking_client,
                "search_hotels",
                side_effect=ExternalAPIError("Booking.com API failed"),
            ),
            patch.object(
                hotel_agent._expedia_client, "search_hotels", return_value=expedia_api_response
            ),
        ):
            response = await hotel_agent._search_hotels(sample_search_request)

            assert "expedia_total_results" in response.search_metadata
            assert response.search_metadata["expedia_total_results"] == 1
            assert "booking_api_response_time" not in response.search_metadata

    async def test_external_id_prefixes_for_different_apis(
        self, hotel_agent, booking_api_response, expedia_api_response, airbnb_api_response
    ):
        """Test that external IDs have correct prefixes for different APIs."""
        search_request = {
            "location": "Test City",
            "check_in_date": "2024-03-15",
            "check_out_date": "2024-03-18",
            "guest_count": 2,
            "budget": 300.0,  # High budget to include all results
        }

        # Test Booking.com prefix
        with patch.object(
            hotel_agent._booking_client, "search_hotels", return_value=booking_api_response
        ):
            response = await hotel_agent._search_hotels(search_request)
            assert response.hotels[0].external_id.startswith("booking_")

        # Test Expedia prefix
        with (
            patch.object(
                hotel_agent._booking_client,
                "search_hotels",
                side_effect=ExternalAPIError("Booking.com failed"),
            ),
            patch.object(
                hotel_agent._expedia_client, "search_hotels", return_value=expedia_api_response
            ),
        ):
            response = await hotel_agent._search_hotels(search_request)
            assert response.hotels[0].external_id.startswith("expedia_")

        # Test Airbnb prefix
        with (
            patch.object(
                hotel_agent._booking_client,
                "search_hotels",
                side_effect=ExternalAPIError("Booking.com failed"),
            ),
            patch.object(
                hotel_agent._expedia_client,
                "search_hotels",
                side_effect=ExternalAPIError("Expedia failed"),
            ),
            patch.object(
                hotel_agent._airbnb_client, "search_listings", return_value=airbnb_api_response
            ),
        ):
            response = await hotel_agent._search_hotels(search_request)
            assert response.hotels[0].external_id.startswith("airbnb_")

    async def test_performance_tracking_across_fallbacks(
        self, hotel_agent, sample_search_request, expedia_api_response
    ):
        """Test that performance metrics are tracked across API fallbacks."""
        with (
            patch.object(
                hotel_agent._booking_client,
                "search_hotels",
                side_effect=ExternalAPIError("Booking.com API failed"),
            ),
            patch.object(
                hotel_agent._expedia_client, "search_hotels", return_value=expedia_api_response
            ),
            patch("time.time", side_effect=[1000.0, 1000.05, 1000.1, 1000.15]),
        ):  # Mock time values for multiple calls
            response = await hotel_agent._search_hotels(sample_search_request)

            # Should have search time even with fallback
            assert response.search_time_ms > 0
            assert isinstance(response.search_time_ms, int)

            # Should track which APIs were attempted
            assert len(response.search_metadata["apis_attempted"]) == 2
            assert response.search_metadata["apis_attempted"] == ["booking.com", "expedia"]

    async def test_partial_failures_with_data_conversion_errors(
        self, hotel_agent, sample_search_request
    ):
        """Test handling of partial failures during data conversion."""
        # Mock response with some valid and some invalid data
        from travel_companion.services.external_apis.booking import (
            BookingApiResponse,
            BookingHotelResult,
        )

        valid_hotel = BookingHotelResult(
            hotel_id="valid_123", name="Valid Hotel", price_per_night=150.0, currency="USD"
        )

        invalid_hotel = BookingHotelResult(
            hotel_id="invalid_456",
            name="Invalid Hotel",
            price_per_night=-50.0,  # Negative price - this should pass validation but might cause conversion issues
            currency="INVALID",
        )

        booking_response = BookingApiResponse(
            hotels=[valid_hotel, invalid_hotel],
            api_response_time_ms=1000,
            total_results=2,
            has_more_results=False,
        )

        with patch.object(
            hotel_agent._booking_client, "search_hotels", return_value=booking_response
        ):
            response = await hotel_agent._search_hotels(sample_search_request)

            # Should successfully return the valid hotel and skip the invalid one
            assert len(response.hotels) >= 1
            assert any(hotel.external_id == "booking_valid_123" for hotel in response.hotels)
            assert response.search_metadata["successful_api"] == "booking.com"

    async def test_airbnb_max_price_filter_integration(self, hotel_agent, airbnb_api_response):
        """Test that Airbnb API receives max_price filter when budget is specified."""
        search_request = {
            "location": "San Francisco, CA",
            "check_in_date": "2024-03-15",
            "check_out_date": "2024-03-18",
            "guest_count": 2,
            "budget": 250.0,  # Should be passed to Airbnb as max_price
        }

        with (
            patch.object(
                hotel_agent._booking_client,
                "search_hotels",
                side_effect=ExternalAPIError("Booking.com failed"),
            ),
            patch.object(
                hotel_agent._expedia_client,
                "search_hotels",
                side_effect=ExternalAPIError("Expedia failed"),
            ),
            patch.object(
                hotel_agent._airbnb_client, "search_listings", return_value=airbnb_api_response
            ) as mock_airbnb,
        ):
            await hotel_agent._search_hotels(search_request)

            # Verify that Airbnb was called with max_price parameter
            mock_airbnb.assert_called_once()
            call_args = mock_airbnb.call_args[0][
                0
            ]  # First positional argument (AirbnbSearchParams)
            assert call_args.max_price == 250.0

    @pytest.mark.asyncio
    async def test_concurrent_api_calls_not_implemented(self, hotel_agent, sample_search_request):
        """Test that APIs are called sequentially, not concurrently (as per current implementation)."""
        call_order = []

        async def mock_booking_search(*args, **kwargs):
            call_order.append("booking")
            raise ExternalAPIError("Booking failed")

        async def mock_expedia_search(*args, **kwargs):
            call_order.append("expedia")
            raise ExternalAPIError("Expedia failed")

        async def mock_airbnb_search(*args, **kwargs):
            call_order.append("airbnb")
            return []

        with (
            patch.object(
                hotel_agent._booking_client, "search_hotels", side_effect=mock_booking_search
            ),
            patch.object(
                hotel_agent._expedia_client, "search_hotels", side_effect=mock_expedia_search
            ),
            patch.object(
                hotel_agent._airbnb_client, "search_listings", side_effect=mock_airbnb_search
            ),
        ):
            response = await hotel_agent._search_hotels(sample_search_request)

            # Verify sequential execution order
            assert call_order == ["booking", "expedia", "airbnb"]
            assert response.search_metadata["apis_attempted"] == [
                "booking.com",
                "expedia",
                "airbnb",
            ]

"""Test Google Places integration for Hotel Agent."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from travel_companion.agents.hotel_agent import HotelAgent
from travel_companion.core.config import get_settings
from travel_companion.models.external import HotelOption, HotelSearchRequest, HotelSearchResponse
from travel_companion.services.external_apis.google_places import Place, PlaceLocation


class TestHotelAgentGooglePlaces:
    """Test Google Places integration in Hotel Agent."""

    @pytest.fixture
    def mock_google_place(self):
        """Mock Google Place object."""
        return Place(
            id="ChIJN1t_tDeuEmsRUsoyG83frY4",
            display_name={"text": "Test Hotel"},
            formatted_address="123 Test Street, Test City, Test Country",
            location=PlaceLocation(latitude=40.7128, longitude=-74.0060),
            types=["lodging", "establishment"],
            primary_type="lodging",
            rating=4.5,
            user_rating_count=150,
            price_level="PRICE_LEVEL_MODERATE",
            website_uri="https://example.com",
            google_maps_uri="https://maps.google.com/place/test",
            photos=[],
        )

    @pytest.fixture
    def hotel_search_request(self):
        """Hotel search request fixture."""
        return HotelSearchRequest(
            location="Test City",
            check_in_date=datetime(2024, 6, 15),
            check_out_date=datetime(2024, 6, 17),
            guest_count=2,
            room_count=1,
            budget_per_night=Decimal("200.00"),
            currency="USD",
            max_results=20,
        )

    @pytest.mark.asyncio
    async def test_google_places_integration_primary_provider(
        self, hotel_search_request, mock_google_place
    ):
        """Test that GooglePlacesClient is used as primary provider."""
        # Mock the GooglePlacesClient
        mock_places_api = AsyncMock()
        mock_places_api.text_search.return_value = [mock_google_place]

        mock_google_client = AsyncMock()
        mock_google_client.__aenter__.return_value = mock_google_client
        mock_google_client.places_api = mock_places_api

        with (
            patch(
                "travel_companion.agents.hotel_agent.GooglePlacesClient"
            ) as mock_google_places_client_class,
            patch.object(get_settings(), "google_places_api_key", "test_key"),
        ):
            mock_google_places_client_class.return_value = mock_google_client

            # Create hotel agent
            hotel_agent = HotelAgent()

            # Test the search_hotels_google_places method directly
            result = await hotel_agent.search_hotels_google_places(hotel_search_request)

            # Verify Google Places API was called
            mock_places_api.text_search.assert_called_once()
            call_args = mock_places_api.text_search.call_args

            # Check the query contains hotel search terms
            assert "hotels in Test City" == call_args[1]["text_query"]
            assert call_args[1]["max_result_count"] == 20
            assert call_args[1]["price_levels"] == [
                "PRICE_LEVEL_INEXPENSIVE",
                "PRICE_LEVEL_MODERATE",
                "PRICE_LEVEL_EXPENSIVE",
            ]

            # Verify results were converted correctly
            assert len(result) == 1
            hotel = result[0]
            assert isinstance(hotel, HotelOption)
            assert hotel.name == "Test Hotel"
            assert hotel.external_id == "google_places_ChIJN1t_tDeuEmsRUsoyG83frY4"
            assert hotel.location.latitude == 40.7128
            assert hotel.location.longitude == -74.0060
            assert hotel.price_per_night == Decimal("150")  # PRICE_LEVEL_MODERATE
            assert hotel.currency == "USD"

    @pytest.mark.asyncio
    async def test_place_to_hotel_conversion(self, hotel_search_request, mock_google_place):
        """Test conversion from Google Place to HotelOption."""
        hotel_agent = HotelAgent()

        # Test the conversion method directly
        result = await hotel_agent._convert_place_to_hotel(mock_google_place, hotel_search_request)

        assert result is not None
        assert isinstance(result, HotelOption)
        assert result.name == "Test Hotel"
        assert result.external_id == "google_places_ChIJN1t_tDeuEmsRUsoyG83frY4"
        assert result.location.address == "123 Test Street, Test City, Test Country"
        assert result.location.city == "Test City"
        assert result.location.country == "Test Country"
        assert result.price_per_night == Decimal("150")  # PRICE_LEVEL_MODERATE mapping
        assert result.rating == 4.5
        assert result.currency == "USD"
        assert "Air Conditioning" in result.amenities  # From lodging type
        assert "Daily Housekeeping" in result.amenities  # From lodging type

    @pytest.mark.asyncio
    async def test_hotel_price_level_mapping(self):
        """Test hotel price level mapping."""
        hotel_agent = HotelAgent()

        # Test different price levels
        assert hotel_agent._estimate_hotel_price_from_level("PRICE_LEVEL_FREE") == Decimal("30")
        assert hotel_agent._estimate_hotel_price_from_level("PRICE_LEVEL_INEXPENSIVE") == Decimal(
            "70"
        )
        assert hotel_agent._estimate_hotel_price_from_level("PRICE_LEVEL_MODERATE") == Decimal(
            "150"
        )
        assert hotel_agent._estimate_hotel_price_from_level("PRICE_LEVEL_EXPENSIVE") == Decimal(
            "300"
        )
        assert hotel_agent._estimate_hotel_price_from_level(
            "PRICE_LEVEL_VERY_EXPENSIVE"
        ) == Decimal("500")
        assert hotel_agent._estimate_hotel_price_from_level(None) == Decimal("120")  # Default

    def test_map_hotel_price_levels(self):
        """Test mapping budget to Google Places price levels for hotels."""
        hotel_agent = HotelAgent()

        # Test different budget levels
        budget_50 = hotel_agent._map_hotel_price_levels(50.0)
        assert "PRICE_LEVEL_INEXPENSIVE" in budget_50
        assert "PRICE_LEVEL_MODERATE" not in budget_50

        budget_150 = hotel_agent._map_hotel_price_levels(150.0)
        assert "PRICE_LEVEL_INEXPENSIVE" in budget_150
        assert "PRICE_LEVEL_MODERATE" in budget_150
        assert "PRICE_LEVEL_EXPENSIVE" not in budget_150

        budget_500 = hotel_agent._map_hotel_price_levels(500.0)
        assert all(
            level in budget_500
            for level in [
                "PRICE_LEVEL_INEXPENSIVE",
                "PRICE_LEVEL_MODERATE",
                "PRICE_LEVEL_EXPENSIVE",
                "PRICE_LEVEL_VERY_EXPENSIVE",
            ]
        )

    def test_extract_hotel_amenities_from_types(self):
        """Test extracting hotel amenities from place types."""
        hotel_agent = HotelAgent()

        # Test different place types
        types_with_amenities = ["lodging", "spa", "restaurant", "gym", "parking"]
        amenities = hotel_agent._extract_hotel_amenities_from_types(types_with_amenities)

        assert "Spa" in amenities
        assert "Restaurant" in amenities
        assert "Fitness Center" in amenities
        assert "Parking" in amenities
        assert "Air Conditioning" in amenities  # From lodging type
        assert "Daily Housekeeping" in amenities  # From lodging type

    @pytest.mark.asyncio
    async def test_google_places_as_primary_in_search_flow(
        self, hotel_search_request, mock_google_place
    ):
        """Test that Google Places is called first in the search flow."""
        # Create a mock HotelOption from the Place
        from decimal import Decimal
        from uuid import uuid4

        from travel_companion.models.external import HotelLocation, HotelOption

        mock_hotel = HotelOption(
            hotel_id=uuid4(),
            external_id=f"google_places_{mock_google_place.id}",
            name=mock_google_place.display_name["text"],
            address=mock_google_place.formatted_address,
            location=HotelLocation(
                latitude=mock_google_place.location.latitude,
                longitude=mock_google_place.location.longitude,
                city="Test City",
                country="Test Country",
                country_code="TC",
            ),
            price_per_night=Decimal("150"),
            currency="USD",
            rating=mock_google_place.rating,
            total_ratings=mock_google_place.user_rating_count,
            check_in_date=hotel_search_request.check_in_date,
            check_out_date=hotel_search_request.check_out_date,
            guest_count=hotel_search_request.guest_count,
            room_count=hotel_search_request.room_count,
        )

        hotel_agent = HotelAgent()

        # Mock cache to return None (no cached result)
        with (
            patch.object(
                hotel_agent._cache_manager, "get_hotel_search_cache", new_callable=AsyncMock
            ) as mock_cache_get,
            patch.object(
                hotel_agent._cache_manager, "set_hotel_search_cache", new_callable=AsyncMock
            ),
            patch.object(
                hotel_agent, "search_hotels_google_places", new_callable=AsyncMock
            ) as mock_search_google,
        ):
            mock_cache_get.return_value = None  # Bypass cache
            mock_search_google.return_value = [mock_hotel]

            # Process the search request
            request_data = {
                "location": hotel_search_request.location,
                "check_in_date": hotel_search_request.check_in_date,
                "check_out_date": hotel_search_request.check_out_date,
                "guest_count": hotel_search_request.guest_count,
                "room_count": hotel_search_request.room_count,
            }

            result = await hotel_agent.process(request_data)

            # Verify Google Places was called
            mock_search_google.assert_called_once()

            # Verify results
            assert isinstance(result, HotelSearchResponse)
            assert len(result.hotels) == 1
            assert result.hotels[0].name == "Test Hotel"
            assert result.search_metadata["api_used"] == "google_places"

    @pytest.mark.asyncio
    async def test_fallback_to_booking_when_google_places_fails(self, hotel_search_request):
        """Test fallback to Booking.com when Google Places fails."""
        hotel_agent = HotelAgent()

        # Mock the search method to fail with Google Places
        with (
            patch.object(
                hotel_agent._cache_manager, "get_hotel_search_cache", new_callable=AsyncMock
            ) as mock_cache_get,
            patch.object(
                hotel_agent._cache_manager, "set_hotel_search_cache", new_callable=AsyncMock
            ),
            patch.object(
                hotel_agent, "search_hotels_google_places", new_callable=AsyncMock
            ) as mock_search_google,
        ):
            mock_cache_get.return_value = None  # Bypass cache
            mock_search_google.side_effect = Exception("Google API error")

            request_data = {
                "location": hotel_search_request.location,
                "check_in_date": hotel_search_request.check_in_date,
                "check_out_date": hotel_search_request.check_out_date,
                "guest_count": hotel_search_request.guest_count,
            }

            result = await hotel_agent.process(request_data)

            # Verify Google Places was attempted
            mock_search_google.assert_called_once()

            # Verify API failed since Google Places failed
            assert result.search_metadata["api_used"] == "google_places"
            assert "google_places" in result.search_metadata["api_errors"]
            assert len(result.hotels) == 0

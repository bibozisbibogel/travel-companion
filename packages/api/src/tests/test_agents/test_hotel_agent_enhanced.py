"""Tests for enhanced hotel agent with Geoapify + LiteAPI integration."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from travel_companion.agents.hotel_agent import HotelAgent
from travel_companion.models.external import HotelOption, HotelSearchResponse


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = Mock()
    settings.geoapify_api_key = "test_geoapify_key"
    settings.liteapi_key = "test_liteapi_key"
    settings.hotel_cache_ttl_seconds = 1800
    settings.hotel_max_results = 100
    settings.hotel_api_timeout_seconds = 30
    return settings


@pytest.fixture
def mock_database():
    """Mock database manager."""
    return Mock()


@pytest.fixture
def mock_redis():
    """Mock Redis manager."""
    return Mock()


@pytest.fixture
async def hotel_agent(mock_settings, mock_database, mock_redis):
    """Create hotel agent for testing."""
    with patch("travel_companion.agents.hotel_agent.GeoapifyClient"):
        with patch("travel_companion.agents.hotel_agent.LiteAPIClient"):
            agent = HotelAgent(mock_settings, mock_database, mock_redis)
            yield agent


@pytest.mark.asyncio
class TestHotelAgentEnhanced:
    """Test cases for enhanced hotel agent functionality."""

    async def test_search_hotels_with_rates_success(self, hotel_agent):
        """Test successful hotel search with rates integration."""
        # Mock Geoapify response
        mock_geoapify_hotels = [
            {
                "name": "Tokyo Grand Hotel",
                "latitude": 35.6762,
                "longitude": 139.6503,
                "place_id": "geo123",
                "address": "1-1-1 Marunouchi",
                "city": "Tokyo",
                "country": "Japan",
            },
            {
                "name": "Shibuya Business Hotel",
                "latitude": 35.6596,
                "longitude": 139.7016,
                "place_id": "geo456",
                "address": "2-2-2 Shibuya",
                "city": "Tokyo",
                "country": "Japan",
            },
        ]

        # Mock LiteAPI hotels response
        mock_liteapi_hotels = [
            {
                "id": "LITE123",
                "name": "Tokyo Grand Hotel",
                "latitude": 35.6762,
                "longitude": 139.6503,
            },
            {
                "id": "LITE456",
                "name": "Shibuya Business Hotel",
                "latitude": 35.6596,
                "longitude": 139.7016,
            },
        ]

        # Mock LiteAPI rates response
        mock_rates_data = {
            "data": [
                {
                    "hotel_id": "LITE123",
                    "rates": [
                        {"total_amount": 15000, "currency": "JPY"},
                        {"total_amount": 18000, "currency": "JPY"},
                    ],
                },
                {"hotel_id": "LITE456", "rates": [{"total_amount": 12000, "currency": "JPY"}]},
            ]
        }

        # Setup mocks
        hotel_agent._geoapify_client.search_hotels = AsyncMock(return_value=mock_geoapify_hotels)
        hotel_agent._liteapi_client.search_hotels_by_geo = AsyncMock(
            return_value=mock_liteapi_hotels
        )
        hotel_agent._liteapi_client.get_min_rates = AsyncMock(return_value=mock_rates_data)

        result = await hotel_agent.search_hotels_with_rates(
            location="Tokyo",
            check_in_date="2025-01-15",
            check_out_date="2025-01-17",
            guest_count=2,
            room_count=1,
            max_results=10,
        )

        assert isinstance(result, HotelSearchResponse)
        assert len(result.hotels) == 2
        assert result.search_metadata["provider"] == "geoapify_liteapi"
        assert result.search_metadata["location"] == "Tokyo"

        # Verify hotels have rates
        hotel_with_rates = [h for h in result.hotels if h.price_per_night > 0]
        assert len(hotel_with_rates) == 2

        # Verify API calls were made
        hotel_agent._geoapify_client.search_hotels.assert_called_once()
        hotel_agent._liteapi_client.search_hotels_by_geo.assert_called_once()
        hotel_agent._liteapi_client.get_min_rates.assert_called_once()

    async def test_search_hotels_with_rates_full_rates(self, hotel_agent):
        """Test hotel search with full rates instead of minimum rates."""
        mock_geoapify_hotels = [
            {
                "name": "Test Hotel",
                "latitude": 35.6762,
                "longitude": 139.6503,
                "place_id": "geo123",
                "address": "Test Address",
                "city": "Tokyo",
                "country": "Japan",
            }
        ]

        mock_liteapi_hotels = [
            {"id": "LITE123", "name": "Test Hotel", "latitude": 35.6762, "longitude": 139.6503}
        ]

        mock_full_rates_data = {
            "data": [
                {
                    "hotel_id": "LITE123",
                    "rates": [
                        {
                            "total_amount": 15000,
                            "currency": "JPY",
                            "room_type": "Standard Double",
                            "board_type": "BB",
                            "cancellation_policy": "Free cancellation",
                        }
                    ],
                }
            ]
        }

        hotel_agent._geoapify_client.search_hotels = AsyncMock(return_value=mock_geoapify_hotels)
        hotel_agent._liteapi_client.search_hotels_by_geo = AsyncMock(
            return_value=mock_liteapi_hotels
        )
        hotel_agent._liteapi_client.get_full_rates = AsyncMock(return_value=mock_full_rates_data)

        result = await hotel_agent.search_hotels_with_rates(
            location="Tokyo",
            check_in_date="2025-01-15",
            check_out_date="2025-01-17",
            guest_count=2,
            get_full_rates=True,  # Request full rates
        )

        assert result.search_metadata["rate_type"] == "full"
        hotel_agent._liteapi_client.get_full_rates.assert_called_once()
        hotel_agent._liteapi_client.get_min_rates.assert_not_called()

    async def test_search_hotels_with_rates_no_geoapify_results(self, hotel_agent):
        """Test handling when Geoapify returns no hotels."""
        hotel_agent._geoapify_client.search_hotels = AsyncMock(return_value=[])

        result = await hotel_agent.search_hotels_with_rates(
            location="NonexistentCity",
            check_in_date="2025-01-15",
            check_out_date="2025-01-17",
            guest_count=2,
        )

        assert len(result.hotels) == 0
        assert "error" in result.search_metadata
        assert "No hotels found in location" in result.search_metadata["error"]

    async def test_search_hotels_with_rates_no_liteapi_results(self, hotel_agent):
        """Test fallback when LiteAPI returns no hotels."""
        mock_geoapify_hotels = [
            {
                "name": "Fallback Hotel",
                "latitude": 35.6762,
                "longitude": 139.6503,
                "place_id": "geo123",
                "address": "Test Address",
                "city": "Tokyo",
                "country": "Japan",
            }
        ]

        hotel_agent._geoapify_client.search_hotels = AsyncMock(return_value=mock_geoapify_hotels)
        hotel_agent._liteapi_client.search_hotels_by_geo = AsyncMock(return_value=[])

        result = await hotel_agent.search_hotels_with_rates(
            location="Tokyo", check_in_date="2025-01-15", check_out_date="2025-01-17", guest_count=2
        )

        # Should return fallback response with Geoapify data only
        assert len(result.hotels) == 1
        assert result.search_metadata["provider"] == "geoapify_fallback"
        assert result.hotels[0].price_per_night == Decimal("0.01")  # Minimum valid price

    async def test_search_hotels_with_rates_budget_filter(self, hotel_agent):
        """Test budget filtering functionality."""
        mock_geoapify_hotels = [
            {
                "name": "Expensive Hotel",
                "latitude": 35.6762,
                "longitude": 139.6503,
                "place_id": "geo123",
                "address": "Expensive District",
                "city": "Tokyo",
                "country": "Japan",
            },
            {
                "name": "Budget Hotel",
                "latitude": 35.6596,
                "longitude": 139.7016,
                "place_id": "geo456",
                "address": "Budget District",
                "city": "Tokyo",
                "country": "Japan",
            },
        ]

        mock_liteapi_hotels = [
            {"id": "LITE123", "latitude": 35.6762, "longitude": 139.6503},
            {"id": "LITE456", "latitude": 35.6596, "longitude": 139.7016},
        ]

        mock_rates_data = {
            "data": [
                {
                    "hotel_id": "LITE123",
                    "rates": [{"total_amount": 300.00}],  # Above budget
                },
                {
                    "hotel_id": "LITE456",
                    "rates": [{"total_amount": 80.00}],  # Within budget
                },
            ]
        }

        hotel_agent._geoapify_client.search_hotels = AsyncMock(return_value=mock_geoapify_hotels)
        hotel_agent._liteapi_client.search_hotels_by_geo = AsyncMock(
            return_value=mock_liteapi_hotels
        )
        hotel_agent._liteapi_client.get_min_rates = AsyncMock(return_value=mock_rates_data)

        result = await hotel_agent.search_hotels_with_rates(
            location="Tokyo",
            check_in_date="2025-01-15",
            check_out_date="2025-01-17",
            guest_count=2,
            budget_per_night=100.0,  # Budget filter
        )

        # Only budget hotel should be returned
        assert len(result.hotels) == 1
        assert result.hotels[0].price_per_night <= Decimal("100")

    async def test_search_hotels_with_rates_exception_fallback(self, hotel_agent):
        """Test fallback to original search method on exception."""
        # Mock Geoapify to raise an exception
        hotel_agent._geoapify_client.search_hotels = AsyncMock(side_effect=Exception("API Error"))

        # Mock the fallback method
        with patch.object(hotel_agent, "search_hotels_by_location") as mock_fallback:
            mock_fallback_response = HotelSearchResponse(
                hotels=[],
                search_metadata={"provider": "fallback"},
                total_results=0,
                search_time_ms=100,
                cached=False,
            )
            mock_fallback.return_value = mock_fallback_response

            result = await hotel_agent.search_hotels_with_rates(
                location="Tokyo",
                check_in_date="2025-01-15",
                check_out_date="2025-01-17",
                guest_count=2,
            )

            # Should use fallback method
            mock_fallback.assert_called_once()
            assert result.search_metadata["provider"] == "fallback"

    async def test_combine_geoapify_liteapi_data(self, hotel_agent):
        """Test data combination from Geoapify and LiteAPI."""
        geoapify_hotels = [
            {
                "name": "Test Hotel",
                "latitude": 35.676,  # Rounded to 3 decimals: 35.676
                "longitude": 139.650,  # Rounded to 3 decimals: 139.650
                "place_id": "geo123",
                "address": "Test Address",
                "city": "Tokyo",
                "country": "Japan",
            }
        ]

        liteapi_hotels = [
            {
                "id": "LITE123",
                "latitude": 35.676,  # Matches rounded Geoapify coordinates
                "longitude": 139.650,
            }
        ]

        rates_data = {"data": [{"hotel_id": "LITE123", "rates": [{"total_amount": 150.0}]}]}

        result = await hotel_agent._combine_geoapify_liteapi_data(
            geoapify_hotels, liteapi_hotels, rates_data
        )

        assert len(result) == 1
        hotel = result[0]
        assert isinstance(hotel, HotelOption)
        assert hotel.name == "Test Hotel"
        assert hotel.price_per_night == Decimal("150.0")
        assert "liteapi_LITE123" in hotel.external_id

    async def test_create_fallback_response(self, hotel_agent):
        """Test creation of fallback response."""
        geoapify_hotels = [
            {
                "name": "Fallback Hotel",
                "latitude": 35.6762,
                "longitude": 139.6503,
                "place_id": "geo123",
                "address": "Test Address",
                "city": "Tokyo",
                "country": "Japan",
            }
        ]

        import time

        start_time = time.time()

        result = await hotel_agent._create_fallback_response(geoapify_hotels, "Tokyo", start_time)

        assert isinstance(result, HotelSearchResponse)
        assert len(result.hotels) == 1
        assert result.search_metadata["provider"] == "geoapify_fallback"
        assert result.hotels[0].price_per_night == Decimal("0.01")  # Minimum valid price
        assert "geoapify_geo123" in result.hotels[0].external_id

    @pytest.mark.parametrize(
        "guest_count,room_count,expected_adults", [(2, 1, 2), (4, 2, 4), (6, 3, 6)]
    )
    async def test_search_hotels_with_rates_occupancy_params(
        self, hotel_agent, guest_count, room_count, expected_adults
    ):
        """Test that occupancy parameters are correctly passed to LiteAPI."""
        mock_geoapify_hotels = [
            {"name": "Test", "latitude": 35.6762, "longitude": 139.6503, "place_id": "geo123"}
        ]
        mock_liteapi_hotels = [{"id": "LITE123", "latitude": 35.6762, "longitude": 139.6503}]
        mock_rates_data = {"data": [{"hotel_id": "LITE123", "rates": [{"total_amount": 100.0}]}]}

        hotel_agent._geoapify_client.search_hotels = AsyncMock(return_value=mock_geoapify_hotels)
        hotel_agent._liteapi_client.search_hotels_by_geo = AsyncMock(
            return_value=mock_liteapi_hotels
        )
        hotel_agent._liteapi_client.get_min_rates = AsyncMock(return_value=mock_rates_data)

        await hotel_agent.search_hotels_with_rates(
            location="Tokyo",
            check_in_date="2025-01-15",
            check_out_date="2025-01-17",
            guest_count=guest_count,
            room_count=room_count,
        )

        # Verify the occupancy parameters passed to LiteAPI
        call_args = hotel_agent._liteapi_client.get_min_rates.call_args
        rates_request = call_args[0][0]
        assert len(rates_request.occupancies) == 1
        assert rates_request.occupancies[0].rooms == room_count
        assert rates_request.occupancies[0].adults == expected_adults
        assert rates_request.occupancies[0].children == 0

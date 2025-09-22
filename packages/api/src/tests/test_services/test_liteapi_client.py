"""Tests for LiteAPI client."""

from unittest.mock import Mock, patch

import httpx
import pytest

from travel_companion.services.external_apis.liteapi import (
    LiteAPIClient,
    LiteAPIHotelSearchRequest,
    LiteAPIMinRatesRequest,
    LiteAPIOccupancy,
    LiteAPIRatesRequest,
    LiteAPIStay,
)
from travel_companion.utils.errors import ExternalAPIError


@pytest.fixture
def mock_settings():
    """Mock settings with LiteAPI key."""
    with patch("travel_companion.services.external_apis.liteapi.get_settings") as mock:
        mock.return_value.liteapi_key = "test_liteapi_key"
        yield mock


@pytest.fixture
async def liteapi_client(mock_settings):
    """Create LiteAPI client for testing."""
    async with LiteAPIClient() as client:
        yield client


@pytest.mark.asyncio
class TestLiteAPIClient:
    """Test cases for LiteAPI client."""

    async def test_client_initialization(self, mock_settings):
        """Test client initializes with proper configuration."""
        client = LiteAPIClient()
        assert client.api_key == "test_liteapi_key"
        assert client._rate_limit == 1000
        assert client._search_circuit.name == "liteapi_search"
        assert client._rates_circuit.name == "liteapi_rates"

    async def test_client_initialization_missing_key(self):
        """Test client raises error when API key is missing."""
        with patch("travel_companion.services.external_apis.liteapi.get_settings") as mock:
            mock.return_value.liteapi_key = ""
            with pytest.raises(ValueError, match="LITEAPI_KEY not configured"):
                LiteAPIClient()

    async def test_search_hotels_by_geo_success(self, liteapi_client):
        """Test successful hotel search by geo location."""
        # Mock response data
        mock_response_data = {
            "data": [
                {
                    "id": "LITE123",
                    "name": "Test Hotel",
                    "latitude": 35.6762,
                    "longitude": 139.6503,
                    "address": "Tokyo, Japan",
                }
            ]
        }

        # Mock httpx client
        with patch.object(liteapi_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            request = LiteAPIHotelSearchRequest(
                latitude=35.6762, longitude=139.6503, radius=5000, limit=10
            )

            result = await liteapi_client.search_hotels_by_geo(request)

            assert len(result) == 1
            assert result[0]["id"] == "LITE123"
            assert result[0]["name"] == "Test Hotel"
            mock_get.assert_called_once()

    async def test_search_hotels_by_geo_http_error(self, liteapi_client):
        """Test hotel search handles HTTP errors."""
        with patch.object(liteapi_client.client, "get") as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=Mock(), response=Mock(status_code=404, text="Not Found")
            )

            request = LiteAPIHotelSearchRequest(
                latitude=35.6762, longitude=139.6503, radius=5000, limit=10
            )

            with pytest.raises(ExternalAPIError, match="LiteAPI search error"):
                await liteapi_client.search_hotels_by_geo(request)

    async def test_search_hotels_by_geo_timeout(self, liteapi_client):
        """Test hotel search handles timeouts."""
        with patch.object(liteapi_client.client, "get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")

            request = LiteAPIHotelSearchRequest(
                latitude=35.6762, longitude=139.6503, radius=5000, limit=10
            )

            with pytest.raises(ExternalAPIError, match="LiteAPI search timeout"):
                await liteapi_client.search_hotels_by_geo(request)

    async def test_get_min_rates_success(self, liteapi_client):
        """Test successful minimum rates retrieval."""
        mock_response_data = {
            "data": [
                {
                    "hotel_id": "LITE123",
                    "rates": [
                        {"total_amount": 150.00, "currency": "USD"},
                        {"total_amount": 180.00, "currency": "USD"},
                    ],
                }
            ]
        }

        with patch.object(liteapi_client.client, "post") as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_post.return_value = mock_response

            stay = LiteAPIStay(check_in="2025-01-15", check_out="2025-01-17")
            occupancies = [LiteAPIOccupancy(rooms=1, adults=2, children=0)]
            request = LiteAPIMinRatesRequest(
                stay=stay, occupancies=occupancies, hotel_ids=["LITE123"]
            )

            result = await liteapi_client.get_min_rates(request)

            assert "data" in result
            assert len(result["data"]) == 1
            assert result["data"][0]["hotel_id"] == "LITE123"
            mock_post.assert_called_once()

    async def test_get_full_rates_success(self, liteapi_client):
        """Test successful full rates retrieval."""
        mock_response_data = {
            "data": [
                {
                    "hotel_id": "LITE123",
                    "rates": [
                        {
                            "total_amount": 150.00,
                            "currency": "USD",
                            "room_type": "Standard",
                            "board_type": "BB",
                            "cancellation_policy": "Non-refundable",
                        }
                    ],
                }
            ]
        }

        with patch.object(liteapi_client.client, "post") as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_post.return_value = mock_response

            stay = LiteAPIStay(check_in="2025-01-15", check_out="2025-01-17")
            occupancies = [LiteAPIOccupancy(rooms=1, adults=2, children=0)]
            request = LiteAPIRatesRequest(
                stay=stay, occupancies=occupancies, hotel_ids=["LITE123"], currency="USD"
            )

            result = await liteapi_client.get_full_rates(request)

            assert "data" in result
            assert len(result["data"]) == 1
            assert result["data"][0]["hotel_id"] == "LITE123"
            mock_post.assert_called_once()

    async def test_rate_limit_check(self, liteapi_client):
        """Test rate limit checking functionality."""
        # Set rate limit to a low value for testing
        liteapi_client._rate_limit = 1
        liteapi_client._request_count = 2  # Exceed limit

        with pytest.raises(ExternalAPIError, match="LiteAPI rate limit exceeded"):
            liteapi_client._check_rate_limit()

    async def test_get_headers(self, liteapi_client):
        """Test header generation."""
        headers = liteapi_client._get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "test_liteapi_key"
        assert headers["Content-Type"] == "application/json"

    async def test_circuit_breaker_integration(self, liteapi_client):
        """Test circuit breaker is triggered on repeated failures."""
        # Mock multiple failures
        with patch.object(liteapi_client.client, "get") as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=Mock(),
                response=Mock(status_code=500, text="Server Error"),
            )

            request = LiteAPIHotelSearchRequest(
                latitude=35.6762, longitude=139.6503, radius=5000, limit=10
            )

            # Trigger multiple failures to open circuit breaker
            for _ in range(5):
                with pytest.raises(ExternalAPIError):
                    await liteapi_client.search_hotels_by_geo(request)

            # Circuit should now be open
            assert liteapi_client._search_circuit.is_open

    @pytest.mark.parametrize(
        "stay_data,occupancy_data",
        [
            (
                {"check_in": "2025-01-15", "check_out": "2025-01-17"},
                {"rooms": 1, "adults": 2, "children": 0},
            ),
            (
                {"check_in": "2025-02-01", "check_out": "2025-02-05"},
                {"rooms": 2, "adults": 4, "children": 2},
            ),
        ],
    )
    async def test_request_models_validation(self, stay_data, occupancy_data):
        """Test request model validation with various inputs."""
        stay = LiteAPIStay(**stay_data)
        occupancy = LiteAPIOccupancy(**occupancy_data)

        assert stay.check_in == stay_data["check_in"]
        assert stay.check_out == stay_data["check_out"]
        assert occupancy.rooms == occupancy_data["rooms"]
        assert occupancy.adults == occupancy_data["adults"]
        assert occupancy.children == occupancy_data["children"]

    async def test_context_manager(self, mock_settings):
        """Test client works as async context manager."""
        async with LiteAPIClient() as client:
            assert client.api_key == "test_liteapi_key"
            # Client should be properly initialized

"""Tests for Geoapify hotel search functionality."""

from unittest.mock import Mock, patch

import httpx
import pytest

from travel_companion.services.external_apis.geoapify import GeoapifyClient
from travel_companion.utils.errors import ExternalAPIError


@pytest.fixture
def mock_settings():
    """Mock settings with Geoapify API key."""
    with patch("travel_companion.services.external_apis.geoapify.get_settings") as mock:
        mock.return_value.geoapify_api_key = "test_geoapify_key"
        yield mock


@pytest.fixture
async def geoapify_client(mock_settings):
    """Create Geoapify client for testing."""
    async with GeoapifyClient() as client:
        yield client


@pytest.mark.asyncio
class TestGeoapifyHotelSearch:
    """Test cases for Geoapify hotel search functionality."""

    async def test_search_hotels_success(self, geoapify_client):
        """Test successful hotel search."""
        # Mock Geoapify API response
        mock_response_data = {
            "features": [
                {
                    "properties": {
                        "name": "Tokyo Grand Hotel",
                        "place_id": "geo123456",
                        "address_line1": "1-1-1 Marunouchi",
                        "city": "Tokyo",
                        "country": "Japan",
                        "formatted": "1-1-1 Marunouchi, Tokyo, Japan",
                        "distance": 500,
                    },
                    "geometry": {
                        "coordinates": [139.6503, 35.6762]  # [lon, lat]
                    },
                },
                {
                    "properties": {
                        "name": "Shibuya Business Hotel",
                        "place_id": "geo789012",
                        "address_line1": "2-2-2 Shibuya",
                        "city": "Tokyo",
                        "country": "Japan",
                        "formatted": "2-2-2 Shibuya, Tokyo, Japan",
                        "distance": 1200,
                    },
                    "geometry": {"coordinates": [139.7016, 35.6596]},
                },
            ]
        }

        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            result = await geoapify_client.search_hotels(location="Tokyo", max_results=10)

            assert len(result) == 2
            assert result[0]["name"] == "Tokyo Grand Hotel"
            assert result[0]["latitude"] == 35.6762
            assert result[0]["longitude"] == 139.6503
            assert result[0]["place_id"] == "geo123456"
            assert result[1]["name"] == "Shibuya Business Hotel"

    async def test_search_hotels_with_coordinates(self, geoapify_client):
        """Test hotel search with latitude/longitude coordinates."""
        mock_response_data = {
            "features": [
                {
                    "properties": {
                        "name": "Central Hotel",
                        "place_id": "geo555",
                        "address_line1": "Central District",
                        "city": "Tokyo",
                        "country": "Japan",
                    },
                    "geometry": {"coordinates": [139.6503, 35.6762]},
                }
            ]
        }

        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            result = await geoapify_client.search_hotels(
                location="Tokyo",
                latitude=35.6762,
                longitude=139.6503,
                radius_meters=3000,
                max_results=5,
            )

            assert len(result) == 1
            assert result[0]["name"] == "Central Hotel"

            # Verify API call parameters
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert "filter" in params
            assert "circle:139.6503,35.6762,3000" in params["filter"]

    async def test_search_hotels_no_coordinates_error(self, geoapify_client):
        """Test error when neither location nor coordinates provided."""
        with pytest.raises(
            ExternalAPIError,
            match="Failed to search hotels: Either location name or lat/lon coordinates must be provided",
        ):
            await geoapify_client.search_hotels(
                location="",  # Empty location
                latitude=None,
                longitude=None,
            )

    async def test_search_hotels_empty_response(self, geoapify_client):
        """Test handling of empty response from API."""
        mock_response_data = {"features": []}

        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            result = await geoapify_client.search_hotels(location="NonexistentCity", max_results=10)

            assert result == []

    async def test_search_hotels_filters_invalid_entries(self, geoapify_client):
        """Test that invalid entries (no name, no coordinates) are filtered out."""
        mock_response_data = {
            "features": [
                {
                    "properties": {"name": "Valid Hotel", "place_id": "geo123"},
                    "geometry": {"coordinates": [139.6503, 35.6762]},
                },
                {
                    "properties": {
                        # Missing name
                        "place_id": "geo456"
                    },
                    "geometry": {"coordinates": [139.7016, 35.6596]},
                },
                {
                    "properties": {"name": "No Coordinates Hotel", "place_id": "geo789"},
                    "geometry": {
                        "coordinates": []  # Invalid coordinates
                    },
                },
            ]
        }

        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            result = await geoapify_client.search_hotels(location="Tokyo", max_results=10)

            # Only the valid hotel should be returned
            assert len(result) == 1
            assert result[0]["name"] == "Valid Hotel"

    async def test_search_hotels_http_error(self, geoapify_client):
        """Test handling of HTTP errors."""
        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=Mock(),
                response=Mock(status_code=401, text="Invalid API key"),
            )

            with pytest.raises(ExternalAPIError, match="Geoapify API error"):
                await geoapify_client.search_hotels(location="Tokyo", max_results=10)

    async def test_search_hotels_timeout(self, geoapify_client):
        """Test handling of request timeouts."""
        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(ExternalAPIError, match="Geoapify API request timeout"):
                await geoapify_client.search_hotels(location="Tokyo", max_results=10)

    async def test_search_hotels_rate_limit_exceeded(self, geoapify_client):
        """Test rate limit handling."""
        # Set rate limit to a low value and exceed it
        geoapify_client._rate_limit = 1
        geoapify_client._request_count = 2

        with pytest.raises(ExternalAPIError, match="Geoapify API rate limit exceeded"):
            await geoapify_client.search_hotels(location="Tokyo", max_results=10)

    async def test_search_hotels_circuit_breaker(self, geoapify_client):
        """Test circuit breaker functionality."""
        # Mock repeated failures
        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=Mock(),
                response=Mock(status_code=500, text="Server Error"),
            )

            # Trigger multiple failures to open circuit breaker
            for _ in range(5):
                with pytest.raises(ExternalAPIError):
                    await geoapify_client.search_hotels(location="Tokyo", max_results=10)

            # Circuit should now be open
            assert geoapify_client._hotel_circuit.is_open

    async def test_search_hotels_parameters_validation(self, geoapify_client):
        """Test that search parameters are properly validated and used."""
        mock_response_data = {"features": []}

        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            await geoapify_client.search_hotels(
                location="Paris", radius_meters=10000, max_results=50
            )

            # Verify API call parameters
            call_args = mock_get.call_args
            params = call_args[1]["params"]

            assert params["categories"] == "accommodation.hotel"
            assert params["limit"] == 50
            assert params["lang"] == "en"
            assert "circle:Paris,10000" in params["filter"]

    @pytest.mark.parametrize(
        "location,lat,lon,radius,expected_filter",
        [
            ("Tokyo", None, None, 5000, "circle:Tokyo,5000"),
            ("", 35.6762, 139.6503, 3000, "circle:139.6503,35.6762,3000"),
            ("Paris", 48.8566, 2.3522, 7500, "circle:2.3522,48.8566,7500"),
        ],
    )
    async def test_search_hotels_filter_construction(
        self, geoapify_client, location, lat, lon, radius, expected_filter
    ):
        """Test proper construction of API filter parameters."""
        mock_response_data = {"features": []}

        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            await geoapify_client.search_hotels(
                location=location, latitude=lat, longitude=lon, radius_meters=radius, max_results=10
            )

            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert expected_filter in params["filter"]

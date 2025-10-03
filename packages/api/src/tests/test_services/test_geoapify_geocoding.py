"""Tests for Geoapify geocoding functionality."""

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
class TestGeoapifyGeocoding:
    """Test cases for Geoapify geocoding functionality."""

    async def test_geocode_city_success(self, geoapify_client):
        """Test successful city geocoding."""
        # Mock Geoapify Geocoding API response (format=json structure)
        mock_response_data = {
            "results": [
                {
                    "lat": 35.6762,
                    "lon": 139.6503,
                    "formatted": "Tokyo, Japan",
                    "city": "Tokyo",
                    "country": "Japan",
                    "country_code": "JP",
                    "state": "Tokyo",
                    "county": "Tokyo",
                    "postcode": "100-0001",
                    "place_id": "geo_tokyo_123",
                    "osm_id": "123456",
                    "bbox": {
                        "lat1": 35.5289,
                        "lat2": 35.8984,
                        "lon1": 138.9428,
                        "lon2": 140.1771,
                    },
                    "rank": {
                        "confidence": 1.0,
                        "importance": 0.95,
                    },
                }
            ]
        }

        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            result = await geoapify_client.geocode_city("Tokyo")

            assert result["latitude"] == 35.6762
            assert result["longitude"] == 139.6503
            assert result["city"] == "Tokyo"
            assert result["country"] == "Japan"
            assert result["country_code"] == "JP"
            assert result["formatted_address"] == "Tokyo, Japan"
            assert result["confidence"] == 1.0
            assert result["bbox"]["min_lat"] == 35.5289
            assert result["bbox"]["max_lat"] == 35.8984

    async def test_geocode_city_with_country(self, geoapify_client):
        """Test geocoding with country specified."""
        mock_response_data = {
            "results": [
                {
                    "lat": 48.8566,
                    "lon": 2.3522,
                    "formatted": "Paris, France",
                    "city": "Paris",
                    "country": "France",
                    "country_code": "FR",
                    "state": "Île-de-France",
                    "place_id": "geo_paris_456",
                    "bbox": {},
                    "rank": {"confidence": 0.99, "importance": 0.98},
                }
            ]
        }

        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            result = await geoapify_client.geocode_city("Paris", country="France")

            assert result["latitude"] == 48.8566
            assert result["longitude"] == 2.3522
            assert result["city"] == "Paris"
            assert result["country"] == "France"
            assert result["state"] == "Île-de-France"

            # Verify API call parameters
            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert params["text"] == "Paris, France"
            assert params["type"] == "city"

    async def test_geocode_city_with_state_and_country(self, geoapify_client):
        """Test geocoding with state and country specified."""
        mock_response_data = {
            "results": [
                {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "formatted": "New York, NY, USA",
                    "city": "New York",
                    "country": "United States",
                    "country_code": "US",
                    "state": "New York",
                    "place_id": "geo_ny_789",
                    "bbox": {},
                    "rank": {"confidence": 1.0, "importance": 1.0},
                }
            ]
        }

        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            result = await geoapify_client.geocode_city("New York", state="New York", country="USA")

            assert result["latitude"] == 40.7128
            assert result["longitude"] == -74.0060
            assert result["city"] == "New York"
            assert result["country"] == "United States"
            assert result["state"] == "New York"

            # Verify API call parameters
            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert params["text"] == "New York, New York, USA"

    async def test_geocode_city_no_results(self, geoapify_client):
        """Test error when no geocoding results found."""
        mock_response_data = {"results": []}

        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            with pytest.raises(
                ExternalAPIError, match="No geocoding results found for city: NonexistentCity"
            ):
                await geoapify_client.geocode_city("NonexistentCity")

    async def test_geocode_city_invalid_coordinates(self, geoapify_client):
        """Test error when API returns invalid coordinates."""
        mock_response_data = {
            "results": [
                {
                    "lat": None,  # Invalid latitude
                    "lon": None,  # Invalid longitude
                    "formatted": "Invalid City",
                    "city": "Invalid City",
                    "bbox": {},
                    "rank": {},
                }
            ]
        }

        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            with pytest.raises(
                ExternalAPIError, match="Invalid coordinates returned for city: Invalid City"
            ):
                await geoapify_client.geocode_city("Invalid City")

    async def test_geocode_city_http_error(self, geoapify_client):
        """Test handling of HTTP errors."""
        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=Mock(),
                response=Mock(status_code=401, text="Invalid API key"),
            )

            with pytest.raises(ExternalAPIError, match="Geoapify Geocoding API error"):
                await geoapify_client.geocode_city("Tokyo")

    async def test_geocode_city_timeout(self, geoapify_client):
        """Test handling of request timeouts."""
        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(ExternalAPIError, match="Geoapify Geocoding API request timeout"):
                await geoapify_client.geocode_city("Tokyo")

    async def test_geocode_city_rate_limit_exceeded(self, geoapify_client):
        """Test rate limit handling."""
        # Set rate limit to a low value and exceed it
        geoapify_client._rate_limit = 1
        geoapify_client._request_count = 2

        with pytest.raises(ExternalAPIError, match="Geoapify API rate limit exceeded"):
            await geoapify_client.geocode_city("Tokyo")

    async def test_geocode_city_circuit_breaker(self, geoapify_client):
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
                    await geoapify_client.geocode_city("Tokyo")

            # Circuit should now be open
            assert geoapify_client._geocoding_circuit.is_open

    async def test_geocode_city_with_iso_country_code(self, geoapify_client):
        """Test geocoding with ISO country code."""
        mock_response_data = {
            "results": [
                {
                    "lat": 51.5074,
                    "lon": -0.1278,
                    "formatted": "London, United Kingdom",
                    "city": "London",
                    "country": "United Kingdom",
                    "country_code": "GB",
                    "state": "England",
                    "place_id": "geo_london_321",
                    "bbox": {},
                    "rank": {"confidence": 0.99, "importance": 0.99},
                }
            ]
        }

        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            result = await geoapify_client.geocode_city("London", country="GB")

            assert result["latitude"] == 51.5074
            assert result["longitude"] == -0.1278
            assert result["city"] == "London"
            assert result["country"] == "United Kingdom"
            assert result["country_code"] == "GB"

            # Verify API call parameters for ISO code
            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert params["filter"] == "countrycode:gb"

    async def test_geocode_city_fallback_name(self, geoapify_client):
        """Test fallback to city_name parameter when city field is missing."""
        mock_response_data = {
            "results": [
                {
                    "lat": 37.7749,
                    "lon": -122.4194,
                    "formatted": "San Francisco, CA, USA",
                    # No 'city' field - should fallback to city_name parameter
                    "country": "United States",
                    "country_code": "US",
                    "state": "California",
                    "place_id": "geo_sf_999",
                    "bbox": {},
                    "rank": {"confidence": 0.98, "importance": 0.96},
                }
            ]
        }

        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            result = await geoapify_client.geocode_city("San Francisco")

            assert result["latitude"] == 37.7749
            assert result["longitude"] == -122.4194
            assert result["city"] == "San Francisco"  # Should use 'name' field

    @pytest.mark.parametrize(
        "city,country,state,expected_text",
        [
            ("Tokyo", None, None, "Tokyo"),
            ("Paris", "France", None, "Paris, France"),
            ("New York", "USA", "New York", "New York, New York, USA"),
            ("London", None, "England", "London, England"),
        ],
    )
    async def test_geocode_city_search_text_construction(
        self, geoapify_client, city, country, state, expected_text
    ):
        """Test proper construction of search text from parameters."""
        mock_response_data = {
            "results": [
                {
                    "lat": 0.0,
                    "lon": 0.0,
                    "formatted": "Test City",
                    "city": "Test City",
                    "place_id": "test",
                    "bbox": {},
                    "rank": {},
                }
            ]
        }

        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            await geoapify_client.geocode_city(city, country=country, state=state)

            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert params["text"] == expected_text

    async def test_geocode_city_complete_response_fields(self, geoapify_client):
        """Test that all response fields are properly extracted."""
        mock_response_data = {
            "results": [
                {
                    "lat": 52.5200,
                    "lon": 13.4050,
                    "formatted": "Berlin, Germany",
                    "city": "Berlin",
                    "country": "Germany",
                    "country_code": "DE",
                    "state": "Berlin",
                    "county": "Berlin County",
                    "postcode": "10117",
                    "place_id": "geo_berlin_555",
                    "osm_id": "987654",
                    "bbox": {
                        "lat1": 52.3382,
                        "lat2": 52.6755,
                        "lon1": 13.0884,
                        "lon2": 13.7612,
                    },
                    "rank": {
                        "confidence": 0.97,
                        "importance": 0.93,
                    },
                }
            ]
        }

        with patch.object(geoapify_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response

            result = await geoapify_client.geocode_city("Berlin")

            # Check all fields are present
            assert result["latitude"] == 52.5200
            assert result["longitude"] == 13.4050
            assert result["formatted_address"] == "Berlin, Germany"
            assert result["city"] == "Berlin"
            assert result["country"] == "Germany"
            assert result["country_code"] == "DE"
            assert result["state"] == "Berlin"
            assert result["county"] == "Berlin County"
            assert result["postcode"] == "10117"
            assert result["bbox"]["min_lat"] == 52.3382
            assert result["bbox"]["max_lat"] == 52.6755
            assert result["bbox"]["min_lon"] == 13.0884
            assert result["bbox"]["max_lon"] == 13.7612
            assert result["confidence"] == 0.97
            assert result["importance"] == 0.93
            assert result["place_id"] == "geo_berlin_555"
            assert result["osm_id"] == "987654"
            assert "search_time_ms" in result

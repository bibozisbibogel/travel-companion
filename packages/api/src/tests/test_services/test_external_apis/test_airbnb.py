"""Tests for Airbnb API client."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import Response

from travel_companion.services.external_apis.airbnb import (
    AirbnbClient,
    AirbnbCredentials,
    AirbnbListingResult,
    AirbnbSearchParams,
)
from travel_companion.utils.errors import ExternalAPIError, RateLimitError


@pytest.fixture
def airbnb_credentials():
    """Mock Airbnb API credentials."""
    return AirbnbCredentials(api_key="test_airbnb_key")


@pytest.fixture
def airbnb_search_params():
    """Mock search parameters for Airbnb API."""
    return AirbnbSearchParams(
        location="Brooklyn, NY",
        check_in="2024-03-15",
        check_out="2024-03-18",
        guest_count=4,
        max_results=15,
        currency="USD",
        language="en",
        min_price=50.0,
        max_price=300.0,
    )


@pytest.fixture
def sample_airbnb_response():
    """Sample Airbnb API response data."""
    return {
        "search_results": [
            {
                "listing": {
                    "id": "67890",
                    "name": "Cozy Brooklyn Apartment",
                    "property_type": "Apartment",
                    "lat": 40.6782,
                    "lng": -73.9442,
                    "public_address": "Brooklyn, NY",
                    "star_rating": 4.8,
                    "reviews_count": 125,
                    "bedrooms": 2,
                    "bathrooms": 1.5,
                    "person_capacity": 4,
                    "amenities": [{"name": "WiFi"}, {"name": "Kitchen"}, {"name": "Washer"}],
                    "pictures": [
                        {"large": "https://example.com/large1.jpg"},
                        {"medium": "https://example.com/medium1.jpg"},
                    ],
                    "description": "Beautiful apartment in Brooklyn",
                    "instant_book": True,
                    "user": {"first_name": "Sarah"},
                },
                "pricing_quote": {"rate": {"amount": 120.0, "currency": "USD"}},
            }
        ]
    }


class TestAirbnbClient:
    """Test suite for AirbnbClient."""

    @pytest.fixture
    def airbnb_client(self, airbnb_credentials):
        """Create AirbnbClient instance for testing."""
        return AirbnbClient(credentials=airbnb_credentials)

    async def test_init_with_credentials(self, airbnb_credentials):
        """Test AirbnbClient initialization with custom credentials."""
        client = AirbnbClient(credentials=airbnb_credentials)
        assert client.credentials.api_key == "test_airbnb_key"
        assert client.base_url == "https://api.airbnb.com/v2"

        # Cleanup
        await client.close()

    @patch("travel_companion.services.external_apis.airbnb.get_settings")
    async def test_init_with_default_credentials(self, mock_settings):
        """Test AirbnbClient initialization with default credentials from settings."""
        mock_settings_instance = AsyncMock()
        mock_settings_instance.airbnb_api_key = "settings_airbnb_key"
        mock_settings.return_value = mock_settings_instance

        client = AirbnbClient()
        assert client.credentials.api_key == "settings_airbnb_key"

        # Cleanup
        await client.close()

    async def test_successful_listing_search(
        self, airbnb_client, airbnb_search_params, sample_airbnb_response
    ):
        """Test successful listing search via Airbnb API."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = sample_airbnb_response

        with patch.object(airbnb_client.client, "request", return_value=mock_response):
            results = await airbnb_client.search_listings(airbnb_search_params)

            assert len(results) == 1
            listing = results[0]
            assert isinstance(listing, AirbnbListingResult)
            assert listing.listing_id == "67890"
            assert listing.name == "Cozy Brooklyn Apartment"
            assert listing.property_type == "Apartment"
            assert listing.latitude == 40.6782
            assert listing.longitude == -73.9442
            assert listing.rating == 4.8
            assert listing.review_count == 125
            assert listing.price_per_night == 120.0
            assert listing.currency == "USD"
            assert "WiFi" in listing.amenities
            assert "Kitchen" in listing.amenities
            assert len(listing.photos) == 2
            assert listing.bedrooms == 2
            assert listing.bathrooms == 1.5
            assert listing.max_guests == 4
            assert listing.host_name == "Sarah"
            assert listing.instant_book is True
            assert listing.booking_url == "https://www.airbnb.com/rooms/67890"

    async def test_empty_search_results(self, airbnb_client, airbnb_search_params):
        """Test handling of empty search results."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"search_results": []}

        with patch.object(airbnb_client.client, "request", return_value=mock_response):
            results = await airbnb_client.search_listings(airbnb_search_params)
            assert results == []

    async def test_rate_limit_error(self, airbnb_client, airbnb_search_params):
        """Test handling of rate limit errors (429)."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 429

        # Mock the circuit breaker call to bypass it and test the specific error handling
        with (
            patch.object(airbnb_client.client, "request", return_value=mock_response),
            patch.object(
                airbnb_client.circuit_breaker,
                "call",
                side_effect=RateLimitError("Airbnb API rate limit exceeded"),
            ),
        ):
            with pytest.raises(
                ExternalAPIError,
                match="Airbnb listing search failed: Airbnb API rate limit exceeded",
            ):
                await airbnb_client.search_listings(airbnb_search_params)

    async def test_authentication_error(self, airbnb_client, airbnb_search_params):
        """Test handling of authentication errors (401)."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 401

        with patch.object(airbnb_client.client, "request", return_value=mock_response):
            with pytest.raises(ExternalAPIError, match="Airbnb API authentication failed"):
                await airbnb_client.search_listings(airbnb_search_params)

    async def test_server_error_with_message(self, airbnb_client, airbnb_search_params):
        """Test handling of server errors with error message."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 500
        mock_response.json.return_value = {"error_message": "Service temporarily unavailable"}

        with patch.object(airbnb_client.client, "request", return_value=mock_response):
            with pytest.raises(
                ExternalAPIError, match="Airbnb API error: Service temporarily unavailable"
            ):
                await airbnb_client.search_listings(airbnb_search_params)

    async def test_server_error_without_message(self, airbnb_client, airbnb_search_params):
        """Test handling of server errors without error message."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 404
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "response", 0)
        mock_response.text = "Page not found"

        with patch.object(airbnb_client.client, "request", return_value=mock_response):
            with pytest.raises(ExternalAPIError, match="Airbnb API error: Page not found"):
                await airbnb_client.search_listings(airbnb_search_params)

    async def test_request_timeout(self, airbnb_client, airbnb_search_params):
        """Test handling of request timeouts."""
        with patch.object(
            airbnb_client.client, "request", side_effect=httpx.TimeoutException("Request timed out")
        ):
            with pytest.raises(ExternalAPIError, match="Airbnb API timeout"):
                await airbnb_client.search_listings(airbnb_search_params)

    async def test_connection_error(self, airbnb_client, airbnb_search_params):
        """Test handling of connection errors."""
        with patch.object(
            airbnb_client.client, "request", side_effect=httpx.ConnectError("Connection failed")
        ):
            with pytest.raises(ExternalAPIError, match="Airbnb API request error"):
                await airbnb_client.search_listings(airbnb_search_params)

    async def test_malformed_listing_data(self, airbnb_client, airbnb_search_params):
        """Test handling of malformed listing data in response."""
        malformed_response = {
            "search_results": [
                {
                    # Missing required 'listing' field
                    "invalid_field": "invalid_value"
                },
                {"listing": {"id": "valid_id", "name": "Valid Listing"}},
            ]
        }

        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = malformed_response

        with patch.object(airbnb_client.client, "request", return_value=mock_response):
            results = await airbnb_client.search_listings(airbnb_search_params)

            # Should return results, including ones with missing fields (they get default values)
            assert len(results) == 2
            # The valid one should have proper data
            valid_listing = next((r for r in results if r.listing_id == "valid_id"), None)
            assert valid_listing is not None
            assert valid_listing.name == "Valid Listing"
            # The malformed one should have empty/default values
            malformed_listing = next((r for r in results if r.listing_id == ""), None)
            assert malformed_listing is not None

    async def test_get_listing_details_success(self, airbnb_client, sample_airbnb_response):
        """Test successful listing details retrieval."""
        listing_details_response = {
            "listing": sample_airbnb_response["search_results"][0]["listing"]
        }

        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = listing_details_response

        with patch.object(airbnb_client.client, "request", return_value=mock_response):
            result = await airbnb_client.get_listing_details("67890")

            assert result is not None
            assert result.listing_id == "67890"
            assert result.name == "Cozy Brooklyn Apartment"

    async def test_get_listing_details_not_found(self, airbnb_client):
        """Test listing details retrieval when listing not found."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        with patch.object(airbnb_client.client, "request", return_value=mock_response):
            result = await airbnb_client.get_listing_details("nonexistent")
            assert result is None

    async def test_circuit_breaker_functionality(self, airbnb_client, airbnb_search_params):
        """Test circuit breaker functionality with repeated failures."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 500
        mock_response.json.return_value = {"error_message": "Server error"}

        with patch.object(airbnb_client.client, "request", return_value=mock_response):
            # Make multiple requests to trigger circuit breaker (threshold is 3 for Airbnb)
            for _i in range(4):
                with pytest.raises(ExternalAPIError):
                    await airbnb_client.search_listings(airbnb_search_params)

    async def test_rate_limiting_enforcement(self, airbnb_client, airbnb_search_params):
        """Test that rate limiting is properly enforced."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"search_results": []}

        with patch.object(airbnb_client.client, "request", return_value=mock_response):
            # Make multiple concurrent requests
            start_time = asyncio.get_event_loop().time()

            tasks = []
            for _ in range(3):
                task = airbnb_client.search_listings(airbnb_search_params)
                tasks.append(task)

            await asyncio.gather(*tasks)
            end_time = asyncio.get_event_loop().time()

            # Should take some time due to rate limiting
            duration = end_time - start_time
            assert duration >= 1.0  # At least 1 second due to rate limiting

    async def test_search_parameters_with_filters(self, airbnb_client):
        """Test that search parameters with filters are properly handled."""
        params = AirbnbSearchParams(
            location="San Francisco, CA",
            check_in="2024-04-01",
            check_out="2024-04-05",
            guest_count=6,
            property_type="house",
            min_price=100.0,
            max_price=400.0,
        )

        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"search_results": []}

        with patch.object(
            airbnb_client.client, "request", return_value=mock_response
        ) as mock_request:
            await airbnb_client.search_listings(params)

            # Verify that the request was made with all parameters including filters
            call_args = mock_request.call_args
            request_params = call_args[1]["params"]

            assert request_params["location"] == "San Francisco, CA"
            assert request_params["guests"] == 6
            assert request_params["property_type_id"] == "house"
            assert request_params["price_min"] == 100
            assert request_params["price_max"] == 400

    async def test_request_headers_and_auth(self, airbnb_client, airbnb_search_params):
        """Test that proper headers and authentication are set."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"search_results": []}

        with patch.object(
            airbnb_client.client, "request", return_value=mock_response
        ) as mock_request:
            await airbnb_client.search_listings(airbnb_search_params)

            call_args = mock_request.call_args
            headers = call_args[1]["headers"]

            assert headers["X-Airbnb-API-Key"] == "test_airbnb_key"
            assert headers["Content-Type"] == "application/json"
            assert headers["Accept"] == "application/json"
            assert headers["User-Agent"] == "TravelCompanion/1.0"

    async def test_close_client(self, airbnb_client):
        """Test that the HTTP client is properly closed."""
        with patch.object(airbnb_client.client, "aclose") as mock_close:
            await airbnb_client.close()
            mock_close.assert_called_once()

    @pytest.mark.parametrize(
        "missing_field", ["lat", "lng", "star_rating", "reviews_count", "bedrooms"]
    )
    async def test_partial_listing_data_handling(
        self, airbnb_client, airbnb_search_params, missing_field
    ):
        """Test handling of partial listing data with missing optional fields."""
        listing_data = {
            "id": "12345",
            "name": "Test Listing",
            "lat": 40.7128,
            "lng": -74.0060,
            "star_rating": 4.5,
            "reviews_count": 100,
            "bedrooms": 1,
        }

        # Remove the specified field to test partial data handling
        del listing_data[missing_field]

        response_data = {
            "search_results": [
                {
                    "listing": listing_data,
                    "pricing_quote": {"rate": {"amount": 100.0, "currency": "USD"}},
                }
            ]
        }

        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = response_data

        with patch.object(airbnb_client.client, "request", return_value=mock_response):
            results = await airbnb_client.search_listings(airbnb_search_params)

            # Should still return results even with missing optional fields
            assert len(results) == 1
            listing = results[0]
            assert listing.listing_id == "12345"
            assert listing.name == "Test Listing"

    async def test_search_with_no_pricing_data(self, airbnb_client, airbnb_search_params):
        """Test handling of listings with no pricing data."""
        response_data = {
            "search_results": [
                {
                    "listing": {"id": "12345", "name": "Free Listing"}
                    # No pricing_quote field
                }
            ]
        }

        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = response_data

        with patch.object(airbnb_client.client, "request", return_value=mock_response):
            results = await airbnb_client.search_listings(airbnb_search_params)

            assert len(results) == 1
            listing = results[0]
            assert listing.listing_id == "12345"
            assert listing.name == "Free Listing"
            assert listing.price_per_night is None
            assert listing.currency == "USD"  # Default value

    async def test_search_with_max_results_limit(self, airbnb_client):
        """Test that max results limit is properly enforced."""
        # Create a large response
        large_response = {
            "search_results": [
                {"listing": {"id": f"listing_{i}", "name": f"Listing {i}"}}
                for i in range(150)  # More than the max limit
            ]
        }

        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = large_response

        params = AirbnbSearchParams(
            location="Test City",
            check_in="2024-03-15",
            check_out="2024-03-18",
            guest_count=2,
            max_results=50,
        )

        with patch.object(airbnb_client.client, "request", return_value=mock_response):
            results = await airbnb_client.search_listings(params)

            # Should be limited to max_results
            assert len(results) == 50

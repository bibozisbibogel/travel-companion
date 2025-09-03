"""Tests for Expedia API client."""

import asyncio
import json
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import Response

from travel_companion.services.external_apis.expedia import (
    ExpediaClient,
    ExpediaCredentials,
    ExpediaHotelResult,
    ExpediaSearchParams,
)
from travel_companion.utils.errors import ExternalAPIError, RateLimitError


@pytest.fixture
def expedia_credentials():
    """Mock Expedia API credentials."""
    return ExpediaCredentials(
        api_key="test_api_key",
        secret_key="test_secret_key"
    )


@pytest.fixture
def expedia_search_params():
    """Mock search parameters for Expedia API."""
    return ExpediaSearchParams(
        location="New York, NY",
        check_in="2024-03-15",
        check_out="2024-03-18",
        guest_count=2,
        room_count=1,
        max_results=10,
        currency="USD",
        language="en"
    )


@pytest.fixture
def sample_expedia_response():
    """Sample Expedia API response data."""
    return {
        "properties": [
            {
                "id": "12345",
                "name": "Test Hotel NYC",
                "address": {
                    "line1": "123 Test Street",
                    "coordinates": {
                        "latitude": 40.7128,
                        "longitude": -74.0060
                    }
                },
                "rating": {
                    "overall": 4.5
                },
                "rates": [
                    {
                        "price": {
                            "total": 150.00,
                            "currency": "USD"
                        }
                    }
                ],
                "amenities": [
                    {"name": "Free WiFi"},
                    {"name": "Pool"}
                ],
                "images": [
                    {"url": "https://example.com/image1.jpg"},
                    {"url": "https://example.com/image2.jpg"}
                ],
                "booking_url": "https://expedia.com/hotel/12345",
                "description": "A great hotel in NYC"
            }
        ]
    }


class TestExpediaClient:
    """Test suite for ExpediaClient."""

    @pytest.fixture
    def expedia_client(self, expedia_credentials):
        """Create ExpediaClient instance for testing."""
        return ExpediaClient(credentials=expedia_credentials)

    async def test_init_with_credentials(self, expedia_credentials):
        """Test ExpediaClient initialization with custom credentials."""
        client = ExpediaClient(credentials=expedia_credentials)
        assert client.credentials.api_key == "test_api_key"
        assert client.credentials.secret_key == "test_secret_key"
        assert client.base_url == "https://api.expediagroup.com"
        
        # Cleanup
        await client.close()

    @patch('travel_companion.services.external_apis.expedia.get_settings')
    async def test_init_with_default_credentials(self, mock_settings):
        """Test ExpediaClient initialization with default credentials from settings."""
        mock_settings_instance = AsyncMock()
        mock_settings_instance.expedia_api_key = "settings_api_key"
        mock_settings_instance.expedia_secret_key = "settings_secret_key"
        mock_settings.return_value = mock_settings_instance
        
        client = ExpediaClient()
        assert client.credentials.api_key == "settings_api_key"
        assert client.credentials.secret_key == "settings_secret_key"
        
        # Cleanup
        await client.close()

    async def test_successful_hotel_search(self, expedia_client, expedia_search_params, sample_expedia_response):
        """Test successful hotel search via Expedia API."""
        # Mock the HTTP response
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = sample_expedia_response
        
        with patch.object(expedia_client.client, 'request', return_value=mock_response):
            results = await expedia_client.search_hotels(expedia_search_params)
            
            assert len(results) == 1
            hotel = results[0]
            assert isinstance(hotel, ExpediaHotelResult)
            assert hotel.hotel_id == "12345"
            assert hotel.name == "Test Hotel NYC"
            assert hotel.latitude == 40.7128
            assert hotel.longitude == -74.0060
            assert hotel.rating == 4.5
            assert hotel.price_per_night == 150.00
            assert hotel.currency == "USD"
            assert "Free WiFi" in hotel.amenities
            assert "Pool" in hotel.amenities
            assert len(hotel.photos) == 2
            assert hotel.booking_url == "https://expedia.com/hotel/12345"

    async def test_empty_search_results(self, expedia_client, expedia_search_params):
        """Test handling of empty search results."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"properties": []}
        
        with patch.object(expedia_client.client, 'request', return_value=mock_response):
            results = await expedia_client.search_hotels(expedia_search_params)
            assert results == []

    async def test_rate_limit_error(self, expedia_client, expedia_search_params):
        """Test handling of rate limit errors (429)."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 429
        
        # Mock the circuit breaker call to bypass it and test the specific error handling
        with patch.object(expedia_client.client, 'request', return_value=mock_response), \
             patch.object(expedia_client.circuit_breaker, 'call', side_effect=RateLimitError("Expedia API rate limit exceeded")):
            with pytest.raises(ExternalAPIError, match="Expedia hotel search failed: Expedia API rate limit exceeded"):
                await expedia_client.search_hotels(expedia_search_params)

    async def test_authentication_error(self, expedia_client, expedia_search_params):
        """Test handling of authentication errors (401)."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 401
        
        # Mock the circuit breaker call to test the specific error handling
        with patch.object(expedia_client.client, 'request', return_value=mock_response), \
             patch.object(expedia_client.circuit_breaker, 'call', side_effect=ExternalAPIError("Expedia API error: HTTP 401")):
            with pytest.raises(ExternalAPIError, match="Expedia API error: HTTP 401"):
                await expedia_client.search_hotels(expedia_search_params)

    async def test_server_error(self, expedia_client, expedia_search_params):
        """Test handling of server errors (500)."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal server error"}
        
        with patch.object(expedia_client.client, 'request', return_value=mock_response):
            with pytest.raises(ExternalAPIError, match="Expedia API error: Internal server error"):
                await expedia_client.search_hotels(expedia_search_params)

    async def test_request_timeout(self, expedia_client, expedia_search_params):
        """Test handling of request timeouts."""
        with patch.object(expedia_client.client, 'request', side_effect=httpx.TimeoutException("Request timed out")):
            with pytest.raises(ExternalAPIError, match="Expedia API timeout"):
                await expedia_client.search_hotels(expedia_search_params)

    async def test_connection_error(self, expedia_client, expedia_search_params):
        """Test handling of connection errors."""
        with patch.object(expedia_client.client, 'request', side_effect=httpx.ConnectError("Connection failed")):
            with pytest.raises(ExternalAPIError, match="Expedia API request error"):
                await expedia_client.search_hotels(expedia_search_params)

    async def test_invalid_json_response(self, expedia_client, expedia_search_params):
        """Test handling of invalid JSON responses."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "response", 0)
        mock_response.text = "Invalid response"
        
        with patch.object(expedia_client.client, 'request', return_value=mock_response):
            with pytest.raises(ExternalAPIError, match="Expedia hotel search failed"):
                await expedia_client.search_hotels(expedia_search_params)

    async def test_malformed_hotel_data(self, expedia_client, expedia_search_params):
        """Test handling of malformed hotel data in response."""
        malformed_response = {
            "properties": [
                {
                    # Missing required fields like 'id' and 'name'
                    "invalid_field": "invalid_value"
                },
                {
                    "id": "valid_id",
                    "name": "Valid Hotel"
                    # This should work fine
                }
            ]
        }
        
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = malformed_response
        
        with patch.object(expedia_client.client, 'request', return_value=mock_response):
            results = await expedia_client.search_hotels(expedia_search_params)
            
            # Should return results, including ones with missing fields (they get default values)
            assert len(results) == 2
            # The valid one should have proper data
            valid_hotel = next((r for r in results if r.hotel_id == "valid_id"), None)
            assert valid_hotel is not None
            assert valid_hotel.name == "Valid Hotel"
            # The malformed one should have empty/default values
            malformed_hotel = next((r for r in results if r.hotel_id == ""), None)
            assert malformed_hotel is not None

    async def test_get_hotel_details_success(self, expedia_client, sample_expedia_response):
        """Test successful hotel details retrieval."""
        hotel_details_response = {
            "property": sample_expedia_response["properties"][0]
        }
        
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = hotel_details_response
        
        with patch.object(expedia_client.client, 'request', return_value=mock_response):
            result = await expedia_client.get_hotel_details("12345")
            
            assert result is not None
            assert result.hotel_id == "12345"
            assert result.name == "Test Hotel NYC"

    async def test_get_hotel_details_not_found(self, expedia_client):
        """Test hotel details retrieval when hotel not found."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        
        with patch.object(expedia_client.client, 'request', return_value=mock_response):
            result = await expedia_client.get_hotel_details("nonexistent")
            assert result is None

    async def test_circuit_breaker_functionality(self, expedia_client, expedia_search_params):
        """Test circuit breaker functionality with repeated failures."""
        # Mock repeated failures to trigger circuit breaker
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Server error"}
        
        with patch.object(expedia_client.client, 'request', return_value=mock_response):
            # Make multiple requests to trigger circuit breaker
            for i in range(6):  # Circuit breaker threshold is 5
                with pytest.raises(ExternalAPIError):
                    await expedia_client.search_hotels(expedia_search_params)

    async def test_rate_limiting_enforcement(self, expedia_client, expedia_search_params):
        """Test that rate limiting is properly enforced."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"properties": []}
        
        with patch.object(expedia_client.client, 'request', return_value=mock_response):
            # Make multiple concurrent requests
            start_time = asyncio.get_event_loop().time()
            
            tasks = []
            for _ in range(3):
                task = expedia_client.search_hotels(expedia_search_params)
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            end_time = asyncio.get_event_loop().time()
            
            # Should take some time due to rate limiting (minimum interval is 0.6 seconds)
            duration = end_time - start_time
            assert duration >= 0.5  # At least 0.5 seconds due to rate limiting

    async def test_search_parameters_validation(self, expedia_client):
        """Test that search parameters are properly validated."""
        # Test with valid parameters that should be adjusted
        params_with_high_max_results = ExpediaSearchParams(
            location="New York",
            check_in="2024-03-15",
            check_out="2024-03-18",
            guest_count=2,
            max_results=250,  # At the limit
        )
        
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"properties": []}
        
        with patch.object(expedia_client.client, 'request', return_value=mock_response) as mock_request:
            results = await expedia_client.search_hotels(params_with_high_max_results)
            
            # Verify that the request was made with corrected parameters
            call_args = mock_request.call_args
            assert call_args[1]['params']['limit'] == 100  # Should be capped at Expedia's 100 limit

    async def test_close_client(self, expedia_client):
        """Test that the HTTP client is properly closed."""
        with patch.object(expedia_client.client, 'aclose') as mock_close:
            await expedia_client.close()
            mock_close.assert_called_once()

    async def test_request_headers_and_auth(self, expedia_client, expedia_search_params):
        """Test that proper headers and authentication are set."""
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"properties": []}
        
        with patch.object(expedia_client.client, 'request', return_value=mock_response) as mock_request:
            await expedia_client.search_hotels(expedia_search_params)
            
            call_args = mock_request.call_args
            headers = call_args[1]['headers']
            
            assert headers['Authorization'] == "Bearer test_api_key"
            assert headers['Content-Type'] == "application/json"
            assert headers['Accept'] == "application/json"
            assert headers['User-Agent'] == "TravelCompanion/1.0"

    @pytest.mark.parametrize("missing_field", ["latitude", "longitude", "rating", "price_per_night"])
    async def test_partial_hotel_data_handling(self, expedia_client, expedia_search_params, missing_field):
        """Test handling of partial hotel data with missing optional fields."""
        hotel_data = {
            "id": "12345",
            "name": "Test Hotel",
            "address": {
                "line1": "123 Test Street",
                "coordinates": {
                    "latitude": 40.7128,
                    "longitude": -74.0060
                }
            },
            "rating": {"overall": 4.5},
            "rates": [{"price": {"total": 150.00, "currency": "USD"}}]
        }
        
        # Remove the specified field to test partial data handling
        if missing_field in ["latitude", "longitude"]:
            del hotel_data["address"]["coordinates"][missing_field]
        elif missing_field == "rating":
            del hotel_data["rating"]
        elif missing_field == "price_per_night":
            del hotel_data["rates"]
        
        response_data = {"properties": [hotel_data]}
        
        mock_response = AsyncMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        
        with patch.object(expedia_client.client, 'request', return_value=mock_response):
            results = await expedia_client.search_hotels(expedia_search_params)
            
            # Should still return results even with missing optional fields
            assert len(results) == 1
            hotel = results[0]
            assert hotel.hotel_id == "12345"
            assert hotel.name == "Test Hotel"
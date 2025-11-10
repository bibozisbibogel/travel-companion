"""Tests for geocoding service."""

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from travel_companion.services.geocoding_service import (
    GeocodeResult,
    GeocodingService,
    get_geocoding_service,
)


@pytest.fixture
def mock_settings() -> Any:
    """Mock settings for testing."""
    with patch("travel_companion.services.geocoding_service.get_settings") as mock:
        settings = Mock()
        settings.geoapify_api_key = "test-geoapify-api-key-12345678"
        settings.geocoding_retry_attempts = 3
        settings.geocoding_timeout_seconds = 5
        settings.geocoding_rate_limit_per_second = 50
        mock.return_value = settings
        yield settings


@pytest.fixture
def geocoding_service(mock_settings: Any) -> GeocodingService:
    """Create geocoding service for testing."""
    with patch("httpx.AsyncClient"):
        service = GeocodingService(api_key="test-geoapify-api-key-12345678")
        # Mock the client to avoid actual API calls
        service.client = AsyncMock()
        return service


class TestGeocodeResult:
    """Tests for GeocodeResult model."""

    def test_geocode_result_success(self) -> None:
        """Test successful geocode result."""
        result = GeocodeResult(
            status="success",
            latitude=48.8583701,
            longitude=2.2944813,
            formatted_address="Eiffel Tower, Paris, France",
            error_message=None,
        )

        assert result.status == "success"
        assert result.latitude == 48.8583701
        assert result.longitude == 2.2944813
        assert result.formatted_address == "Eiffel Tower, Paris, France"
        assert result.error_message is None

    def test_geocode_result_failed(self) -> None:
        """Test failed geocode result."""
        result = GeocodeResult(
            status="failed",
            latitude=None,
            longitude=None,
            formatted_address=None,
            error_message="No results found",
        )

        assert result.status == "failed"
        assert result.latitude is None
        assert result.longitude is None
        assert result.error_message == "No results found"

    def test_geocode_result_coordinate_validation(self) -> None:
        """Test coordinate validation."""
        # Valid coordinates
        result = GeocodeResult(
            status="success",
            latitude=45.123456789,
            longitude=-123.987654321,
            formatted_address=None,
            error_message=None,
        )
        assert result.latitude == 45.12345679  # Rounded to 8 decimal places
        assert result.longitude == -123.98765432

    def test_geocode_result_invalid_latitude(self) -> None:
        """Test invalid latitude validation."""
        with pytest.raises(ValueError):
            GeocodeResult(
                status="success",
                latitude=91.0,
                longitude=0.0,
                formatted_address=None,
                error_message=None,
            )

    def test_geocode_result_invalid_longitude(self) -> None:
        """Test invalid longitude validation."""
        with pytest.raises(ValueError):
            GeocodeResult(
                status="success",
                latitude=0.0,
                longitude=181.0,
                formatted_address=None,
                error_message=None,
            )


class TestGeocodingService:
    """Tests for GeocodingService."""

    def test_initialization_with_api_key(self, mock_settings: Any) -> None:
        """Test service initialization with API key."""
        with patch("httpx.AsyncClient"):
            service = GeocodingService(api_key="custom-geoapify-key-12345678")
            assert service.api_key == "custom-geoapify-key-12345678"
            assert service.max_retries == 3
            assert service.timeout == 5

    def test_initialization_from_settings(self, mock_settings: Any) -> None:
        """Test service initialization from settings."""
        with patch("httpx.AsyncClient"):
            service = GeocodingService()
            assert service.api_key == "test-geoapify-api-key-12345678"

    def test_initialization_no_api_key(self) -> None:
        """Test service initialization fails without API key."""
        with patch("travel_companion.services.geocoding_service.get_settings") as mock:
            settings = Mock()
            settings.geoapify_api_key = ""
            mock.return_value = settings

            with pytest.raises(ValueError, match="Geoapify API key not provided"):
                GeocodingService()

    def test_normalize_address(self, geocoding_service: GeocodingService) -> None:
        """Test address normalization."""
        assert geocoding_service._normalize_address("  Eiffel Tower, Paris  ") == (
            "eiffel tower, paris"
        )
        assert geocoding_service._normalize_address("ROME, ITALY") == "rome, italy"

    def test_get_cache_key(self, geocoding_service: GeocodingService) -> None:
        """Test cache key generation."""
        key1 = geocoding_service._get_cache_key("eiffel tower, paris")
        key2 = geocoding_service._get_cache_key("eiffel tower, paris")
        key3 = geocoding_service._get_cache_key("different address")

        assert key1 == key2  # Same address -> same key
        assert key1 != key3  # Different address -> different key
        assert len(key1) == 64  # SHA256 hash length

    @pytest.mark.asyncio
    async def test_geocode_location_success(self, geocoding_service: GeocodingService) -> None:
        """Test successful geocoding."""
        mock_response_data = {
            "results": [
                {
                    "lat": 41.9009,
                    "lon": 12.4833,
                    "formatted": "Trevi Fountain, Rome, Italy",
                }
            ]
        }

        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()

        geocoding_service.client.get = AsyncMock(return_value=mock_response)
        result = await geocoding_service.geocode_location("Trevi Fountain, Rome")

        assert result.status == "success"
        assert result.latitude == 41.9009
        assert result.longitude == 12.4833
        assert result.formatted_address == "Trevi Fountain, Rome, Italy"
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_geocode_location_zero_results(self, geocoding_service: GeocodingService) -> None:
        """Test geocoding with no results."""
        mock_response_data = {"results": []}

        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()

        geocoding_service.client.get = AsyncMock(return_value=mock_response)
        result = await geocoding_service.geocode_location("Invalid Address XYZ123")

        assert result.status == "failed"
        assert result.error_message is not None
        assert result.error_message.startswith("No geocoding results found")
        assert result.latitude is None
        assert result.longitude is None

    @pytest.mark.asyncio
    async def test_geocode_location_invalid_response(
        self, geocoding_service: GeocodingService
    ) -> None:
        """Test geocoding with invalid response structure."""
        mock_response_data = {"results": [{}]}  # Missing lat/lon

        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()

        geocoding_service.client.get = AsyncMock(return_value=mock_response)
        result = await geocoding_service.geocode_location("Some Address")

        assert result.status == "failed"
        assert result.error_message is not None
        assert "Invalid coordinates" in result.error_message

    @pytest.mark.asyncio
    async def test_geocode_location_api_error(self, geocoding_service: GeocodingService) -> None:
        """Test geocoding with API error."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Forbidden", request=Mock(), response=mock_response
        )

        geocoding_service.client.get = AsyncMock(return_value=mock_response)
        result = await geocoding_service.geocode_location("Some Address")

        assert result.status == "failed"
        assert result.error_message is not None
        assert "403" in result.error_message

    @pytest.mark.asyncio
    async def test_geocode_location_timeout(self, geocoding_service: GeocodingService) -> None:
        """Test geocoding with timeout."""
        geocoding_service.client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        result = await geocoding_service.geocode_location("Some Address")

        assert result.status == "failed"
        assert result.error_message is not None
        assert "timed out" in result.error_message

    @pytest.mark.asyncio
    async def test_geocode_location_retry_on_rate_limit(
        self, geocoding_service: GeocodingService
    ) -> None:
        """Test retry logic on rate limit error."""
        # First call: rate limit, second call: success
        success_response_data = {
            "results": [
                {
                    "lat": 41.9009,
                    "lon": 12.4833,
                    "formatted": "Rome, Italy",
                }
            ]
        }

        call_count = 0

        async def mock_get(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mock_response = Mock()
                mock_response.status_code = 429
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Rate Limit", request=Mock(), response=mock_response
                )
                return mock_response

            mock_response = Mock()
            mock_response.json.return_value = success_response_data
            mock_response.raise_for_status = Mock()
            return mock_response

        geocoding_service.client.get = mock_get

        with patch("asyncio.sleep", return_value=None):  # Skip actual sleep
            result = await geocoding_service.geocode_location("Rome, Italy")

        assert result.status == "success"
        assert call_count == 2  # Should retry once

    @pytest.mark.asyncio
    async def test_geocode_location_max_retries_exceeded(
        self, geocoding_service: GeocodingService
    ) -> None:
        """Test max retries exceeded on rate limit."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate Limit", request=Mock(), response=mock_response
        )

        geocoding_service.client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", return_value=None):  # Skip actual sleep
            result = await geocoding_service.geocode_location("Some Address")

        assert result.status == "failed"
        assert result.error_message is not None
        assert "429" in result.error_message

    @pytest.mark.asyncio
    async def test_geocode_location_cache_hit(self, geocoding_service: GeocodingService) -> None:
        """Test cache returns cached result."""
        mock_response_data = {
            "results": [
                {
                    "lat": 48.8584,
                    "lon": 2.2945,
                    "formatted": "Eiffel Tower, Paris",
                }
            ]
        }

        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()

        geocoding_service.client.get = AsyncMock(return_value=mock_response)
        # First call - should hit API
        result1 = await geocoding_service.geocode_location("Eiffel Tower, Paris")

        # Second call - should use cache (client.get should not be called)
        geocoding_service.client.get = AsyncMock(side_effect=Exception("Should not be called"))
        result2 = await geocoding_service.geocode_location("Eiffel Tower, Paris")

        # Both results should be identical
        assert result1.status == result2.status
        assert result1.latitude == result2.latitude
        assert result1.longitude == result2.longitude

    @pytest.mark.asyncio
    async def test_geocode_location_cache_normalization(
        self, geocoding_service: GeocodingService
    ) -> None:
        """Test cache works with different address formats."""
        mock_response_data = {
            "results": [
                {
                    "lat": 48.8584,
                    "lon": 2.2945,
                    "formatted": "Eiffel Tower, Paris",
                }
            ]
        }

        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()

        geocoding_service.client.get = AsyncMock(return_value=mock_response)
        result1 = await geocoding_service.geocode_location("  Eiffel Tower, Paris  ")

        # Different format but same normalized address
        geocoding_service.client.get = AsyncMock(side_effect=Exception("Should not be called"))
        result2 = await geocoding_service.geocode_location("EIFFEL TOWER, PARIS")

        assert result1.latitude == result2.latitude

    @pytest.mark.asyncio
    async def test_geocode_locations_batch(self, geocoding_service: GeocodingService) -> None:
        """Test batch geocoding."""
        addresses = ["Paris, France", "Rome, Italy", "London, UK"]

        mock_responses_data = [
            {"results": [{"lat": 48.8566, "lon": 2.3522, "formatted": "Paris, France"}]},
            {"results": [{"lat": 41.9028, "lon": 12.4964, "formatted": "Rome, Italy"}]},
            {"results": [{"lat": 51.5074, "lon": -0.1278, "formatted": "London, UK"}]},
        ]

        call_index = 0

        async def mock_get(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_index
            mock_response = Mock()
            mock_response.json.return_value = mock_responses_data[call_index]
            mock_response.raise_for_status = Mock()
            call_index += 1
            return mock_response

        geocoding_service.client.get = mock_get
        results = await geocoding_service.geocode_locations_batch(addresses)

        assert len(results) == 3
        assert all(r.status == "success" for r in results)
        assert results[0].latitude == 48.8566
        assert results[1].latitude == 41.9028
        assert results[2].latitude == 51.5074

    @pytest.mark.asyncio
    async def test_geocode_locations_batch_handles_errors(
        self, geocoding_service: GeocodingService
    ) -> None:
        """Test batch geocoding handles mixed success/failure."""
        addresses = ["Paris, France", "Invalid XYZ", "London, UK"]

        call_index = 0

        async def mock_get(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_index
            address = addresses[call_index]
            call_index += 1

            mock_response = Mock()
            if "Invalid" in address:
                mock_response.json.return_value = {"results": []}  # Zero results
            else:
                mock_response.json.return_value = {
                    "results": [{"lat": 48.0, "lon": 2.0, "formatted": address}]
                }
            mock_response.raise_for_status = Mock()
            return mock_response

        geocoding_service.client.get = mock_get
        results = await geocoding_service.geocode_locations_batch(addresses)

        assert len(results) == 3
        assert results[0].status == "success"
        assert results[1].status == "failed"  # Invalid address
        assert results[2].status == "success"

    def test_cache_eviction(self, geocoding_service: GeocodingService) -> None:
        """Test cache eviction when full."""
        # Set cache size to 3 for testing
        geocoding_service._cache_size = 3

        # Add 4 items to trigger eviction
        for i in range(4):
            result = GeocodeResult(
                status="success",
                latitude=float(i),
                longitude=float(i),
                formatted_address=f"Addr {i}",
                error_message=None,
            )
            geocoding_service._add_to_cache(f"address_{i}", result)

        # Cache should only have 3 items (first one evicted)
        assert len(geocoding_service._cache) == 3

        # First address should be evicted
        assert geocoding_service._get_from_cache("address_0") is None

        # Other addresses should still be cached
        assert geocoding_service._get_from_cache("address_1") is not None
        assert geocoding_service._get_from_cache("address_2") is not None
        assert geocoding_service._get_from_cache("address_3") is not None


class TestGetGeocodingService:
    """Tests for get_geocoding_service singleton."""

    def test_get_geocoding_service_singleton(self, mock_settings: Any) -> None:
        """Test that get_geocoding_service returns cached instance."""
        # Clear cache first
        get_geocoding_service.cache_clear()

        with patch("httpx.AsyncClient"):
            service1 = get_geocoding_service()
            service2 = get_geocoding_service()

            assert service1 is service2  # Should be the same instance

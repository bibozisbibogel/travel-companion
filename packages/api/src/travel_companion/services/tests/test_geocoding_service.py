"""Tests for geocoding service."""

from typing import Any
from unittest.mock import Mock, patch

import googlemaps.exceptions  # type: ignore[import-untyped]
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
        settings.google_places_api_key = "AIzaTest-API-Key-For-Testing-12345678"
        settings.geocoding_retry_attempts = 3
        settings.geocoding_timeout_seconds = 5
        settings.geocoding_rate_limit_per_second = 50
        mock.return_value = settings
        yield settings


@pytest.fixture
def geocoding_service(mock_settings: Any) -> GeocodingService:
    """Create geocoding service for testing."""
    with patch("googlemaps.Client"):
        service = GeocodingService(api_key="AIzaTest-API-Key-For-Testing-12345678")
        # Mock the client to avoid actual API calls
        service.client = Mock()
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
        with patch("googlemaps.Client"):
            service = GeocodingService(api_key="AIzaCustom-API-Key-12345678")
            assert service.api_key == "AIzaCustom-API-Key-12345678"
            assert service.max_retries == 3
            assert service.timeout == 5

    def test_initialization_from_settings(self, mock_settings: Any) -> None:
        """Test service initialization from settings."""
        with patch("googlemaps.Client"):
            service = GeocodingService()
            assert service.api_key == "AIzaTest-API-Key-For-Testing-12345678"

    def test_initialization_no_api_key(self) -> None:
        """Test service initialization fails without API key."""
        with patch("travel_companion.services.geocoding_service.get_settings") as mock:
            settings = Mock()
            settings.google_places_api_key = ""
            mock.return_value = settings

            with pytest.raises(ValueError, match="Google Maps Platform API key not provided"):
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
        mock_response = [
            {
                "geometry": {"location": {"lat": 41.9009, "lng": 12.4833}},
                "formatted_address": "Trevi Fountain, Rome, Italy",
            }
        ]

        with patch.object(geocoding_service.client, "geocode", return_value=mock_response):
            result = await geocoding_service.geocode_location("Trevi Fountain, Rome")

        assert result.status == "success"
        assert result.latitude == 41.9009
        assert result.longitude == 12.4833
        assert result.formatted_address == "Trevi Fountain, Rome, Italy"
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_geocode_location_zero_results(self, geocoding_service: GeocodingService) -> None:
        """Test geocoding with no results."""
        with patch.object(geocoding_service.client, "geocode", return_value=[]):
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
        mock_response: list[dict[str, Any]] = [{"geometry": {}}]  # Missing location data

        with patch.object(geocoding_service.client, "geocode", return_value=mock_response):
            result = await geocoding_service.geocode_location("Some Address")

        assert result.status == "failed"
        assert result.error_message is not None
        assert "Invalid coordinates" in result.error_message

    @pytest.mark.asyncio
    async def test_geocode_location_api_error(self, geocoding_service: GeocodingService) -> None:
        """Test geocoding with API error."""
        with patch.object(
            geocoding_service.client,
            "geocode",
            side_effect=googlemaps.exceptions.ApiError("REQUEST_DENIED"),
        ):
            result = await geocoding_service.geocode_location("Some Address")

        assert result.status == "failed"
        assert result.error_message is not None
        assert "REQUEST_DENIED" in result.error_message

    @pytest.mark.asyncio
    async def test_geocode_location_timeout(self, geocoding_service: GeocodingService) -> None:
        """Test geocoding with timeout."""
        with patch.object(
            geocoding_service.client,
            "geocode",
            side_effect=googlemaps.exceptions.Timeout("Timeout"),
        ):
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
        mock_response = [
            {
                "geometry": {"location": {"lat": 41.9009, "lng": 12.4833}},
                "formatted_address": "Rome, Italy",
            }
        ]

        call_count = 0

        def mock_geocode(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise googlemaps.exceptions.ApiError("OVER_QUERY_LIMIT")
            return mock_response

        with patch.object(geocoding_service.client, "geocode", side_effect=mock_geocode):
            with patch("asyncio.sleep", return_value=None):  # Skip actual sleep
                result = await geocoding_service.geocode_location("Rome, Italy")

        assert result.status == "success"
        assert call_count == 2  # Should retry once

    @pytest.mark.asyncio
    async def test_geocode_location_max_retries_exceeded(
        self, geocoding_service: GeocodingService
    ) -> None:
        """Test max retries exceeded on rate limit."""
        with patch.object(
            geocoding_service.client,
            "geocode",
            side_effect=googlemaps.exceptions.ApiError("OVER_QUERY_LIMIT"),
        ):
            with patch("asyncio.sleep", return_value=None):  # Skip actual sleep
                result = await geocoding_service.geocode_location("Some Address")

        assert result.status == "failed"
        assert result.error_message is not None
        assert "OVER_QUERY_LIMIT" in result.error_message

    @pytest.mark.asyncio
    async def test_geocode_location_cache_hit(self, geocoding_service: GeocodingService) -> None:
        """Test cache returns cached result."""
        mock_response = [
            {
                "geometry": {"location": {"lat": 48.8584, "lng": 2.2945}},
                "formatted_address": "Eiffel Tower, Paris",
            }
        ]

        with patch.object(geocoding_service.client, "geocode", return_value=mock_response):
            # First call - should hit API
            result1 = await geocoding_service.geocode_location("Eiffel Tower, Paris")

        # Second call - should use cache (client.geocode should not be called)
        with patch.object(
            geocoding_service.client, "geocode", side_effect=Exception("Should not be called")
        ):
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
        mock_response = [
            {
                "geometry": {"location": {"lat": 48.8584, "lng": 2.2945}},
                "formatted_address": "Eiffel Tower, Paris",
            }
        ]

        with patch.object(geocoding_service.client, "geocode", return_value=mock_response):
            result1 = await geocoding_service.geocode_location("  Eiffel Tower, Paris  ")

        # Different format but same normalized address
        with patch.object(
            geocoding_service.client, "geocode", side_effect=Exception("Should not be called")
        ):
            result2 = await geocoding_service.geocode_location("EIFFEL TOWER, PARIS")

        assert result1.latitude == result2.latitude

    @pytest.mark.asyncio
    async def test_geocode_locations_batch(self, geocoding_service: GeocodingService) -> None:
        """Test batch geocoding."""
        addresses = ["Paris, France", "Rome, Italy", "London, UK"]

        mock_responses = [
            [
                {
                    "geometry": {"location": {"lat": 48.8566, "lng": 2.3522}},
                    "formatted_address": "Paris, France",
                }
            ],
            [
                {
                    "geometry": {"location": {"lat": 41.9028, "lng": 12.4964}},
                    "formatted_address": "Rome, Italy",
                }
            ],
            [
                {
                    "geometry": {"location": {"lat": 51.5074, "lng": -0.1278}},
                    "formatted_address": "London, UK",
                }
            ],
        ]

        call_index = 0

        def mock_geocode(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_index
            response = mock_responses[call_index]
            call_index += 1
            return response

        with patch.object(geocoding_service.client, "geocode", side_effect=mock_geocode):
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

        def mock_geocode(address: str, **kwargs: Any) -> Any:
            if "Invalid" in address:
                return []  # Zero results
            return [
                {
                    "geometry": {"location": {"lat": 48.0, "lng": 2.0}},
                    "formatted_address": address,
                }
            ]

        with patch.object(geocoding_service.client, "geocode", side_effect=mock_geocode):
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

        with patch("googlemaps.Client"):
            service1 = get_geocoding_service()
            service2 = get_geocoding_service()

            assert service1 is service2  # Should be the same instance

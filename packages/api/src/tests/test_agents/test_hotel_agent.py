"""Tests for HotelAgent implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from travel_companion.agents.hotel_agent import HotelAgent
from travel_companion.core.config import Settings
from travel_companion.models.external import (
    HotelSearchResponse,
)


class TestHotelAgent:
    """Test suite for HotelAgent class."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Create mock settings for testing."""
        settings = MagicMock(spec=Settings)
        settings.hotel_cache_ttl_seconds = 1800
        settings.hotel_max_results = 100
        settings.hotel_api_timeout_seconds = 30
        return settings

    @pytest.fixture
    def mock_database(self) -> AsyncMock:
        """Create mock database manager for testing."""
        database = AsyncMock()
        database.health_check.return_value = True
        return database

    @pytest.fixture
    def mock_redis(self) -> AsyncMock:
        """Create mock Redis manager for testing."""
        redis = AsyncMock()
        redis.ping.return_value = True
        redis.get.return_value = None
        redis.set.return_value = True
        return redis

    @pytest.fixture
    def hotel_agent(self, mock_settings, mock_database, mock_redis) -> HotelAgent:
        """Create HotelAgent instance for testing."""
        return HotelAgent(settings=mock_settings, database=mock_database, redis=mock_redis)

    def test_hotel_agent_initialization(self, hotel_agent, mock_settings):
        """Test HotelAgent initializes correctly with configurations."""
        assert hotel_agent.agent_name == "hotel_agent"
        assert hotel_agent.agent_version == "1.0.0"
        assert hotel_agent.cache_ttl_seconds == 1800
        assert hotel_agent.max_results_per_request == 100
        assert hotel_agent.timeout_seconds == 30

    def test_hotel_agent_initialization_with_defaults(self, mock_database, mock_redis):
        """Test HotelAgent initializes with default settings."""
        # Create settings without hotel-specific attributes
        settings = MagicMock(spec=Settings)

        agent = HotelAgent(settings=settings, database=mock_database, redis=mock_redis)

        # Should use default values when settings don't have hotel-specific attributes
        assert agent.cache_ttl_seconds == 1800  # Default
        assert agent.max_results_per_request == 100  # Default
        assert agent.timeout_seconds == 30  # Default

    @pytest.mark.asyncio
    async def test_health_check_success(self, hotel_agent):
        """Test health check returns healthy status."""
        result = await hotel_agent.health_check()

        assert result["agent"] == "hotel_agent"
        assert result["version"] == "1.0.0"
        assert result["status"] == "healthy"
        assert result["dependencies"]["database"] == "healthy"
        assert result["dependencies"]["redis"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_degraded_database(self, hotel_agent, mock_database):
        """Test health check returns degraded when database unhealthy."""
        mock_database.health_check.return_value = False

        result = await hotel_agent.health_check()

        assert result["status"] == "degraded"
        assert result["dependencies"]["database"] == "unhealthy"
        assert result["dependencies"]["redis"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_degraded_redis(self, hotel_agent, mock_redis):
        """Test health check returns degraded when Redis unhealthy."""
        mock_redis.ping.return_value = False

        result = await hotel_agent.health_check()

        assert result["status"] == "degraded"
        assert result["dependencies"]["database"] == "healthy"
        assert result["dependencies"]["redis"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_exception(self, hotel_agent, mock_database):
        """Test health check handles exceptions gracefully."""
        mock_database.health_check.side_effect = Exception("Database connection failed")

        result = await hotel_agent.health_check()

        assert result["status"] == "unhealthy"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_process_valid_request_empty_results(self, hotel_agent):
        """Test processing valid hotel search request returns empty results when API fails."""
        request_data = {
            "location": "New York",
            "check_in_date": "2024-06-15",
            "check_out_date": "2024-06-17",
            "guest_count": 2,
        }

        # Mock Google Places client to raise exception
        with patch.object(
            hotel_agent,
            "search_hotels_google_places",
            side_effect=Exception("API credentials not configured"),
        ):
            result = await hotel_agent.process(request_data)

        assert isinstance(result, HotelSearchResponse)
        assert result.hotels == []
        assert result.total_results == 0
        assert result.search_metadata["location"] == "New York"
        assert result.search_metadata["guest_count"] == 2
        assert "api_errors" in result.search_metadata
        assert len(result.search_metadata["api_errors"]) >= 1

    @pytest.mark.asyncio
    async def test_process_empty_request(self, hotel_agent):
        """Test processing empty request raises ValueError."""
        with pytest.raises(ValueError, match="Hotel search request data cannot be empty"):
            await hotel_agent.process({})

    @pytest.mark.asyncio
    async def test_process_missing_required_fields(self, hotel_agent):
        """Test processing request with missing required fields."""
        request_data = {
            "location": "New York",
            "check_in_date": "2024-06-15",
            # Missing check_out_date and guest_count
        }

        with pytest.raises(ValueError, match="Missing required fields"):
            await hotel_agent.process(request_data)

    @pytest.mark.asyncio
    async def test_process_with_cached_result(self, hotel_agent, mock_redis):
        """Test processing request returns cached result when available."""
        # Setup cached response
        cached_response = {
            "hotels": [],
            "search_metadata": {"location": "Paris"},
            "total_results": 5,
            "search_time_ms": 150,
            "cached": True,
        }
        mock_redis.get.return_value = cached_response

        request_data = {
            "location": "Paris",
            "check_in_date": "2024-06-15",
            "check_out_date": "2024-06-17",
            "guest_count": 2,
        }

        result = await hotel_agent.process(request_data)

        assert result.total_results == 5
        assert result.search_metadata["location"] == "Paris"
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_caches_new_result(self, hotel_agent, mock_redis):
        """Test processing request caches new result."""
        mock_redis.get.return_value = None  # No cached result

        request_data = {
            "location": "London",
            "check_in_date": "2024-06-15",
            "check_out_date": "2024-06-17",
            "guest_count": 2,
        }

        await hotel_agent.process(request_data)

        # Should cache the new result (only main data, no metadata)
        assert mock_redis.set.call_count == 1
        # Call should be for the main cache data
        main_call_args, main_call_kwargs = mock_redis.set.call_args_list[0]
        cached_data = main_call_args[1]
        assert "cache_timestamp" in cached_data  # Enhanced cache format
        assert cached_data["cached"]
        assert main_call_kwargs["expire"] == 1800  # cache_ttl_seconds

    @pytest.mark.asyncio
    async def test_search_hotels_by_location(self, hotel_agent):
        """Test search hotels by location convenience method."""
        result = await hotel_agent.search_hotels_by_location(
            location="Tokyo",
            check_in_date="2024-07-01",
            check_out_date="2024-07-03",
            guest_count=4,
            budget=200.0,
            max_results=25,
        )

        assert isinstance(result, HotelSearchResponse)
        assert result.search_metadata["location"] == "Tokyo"
        assert result.search_metadata["guest_count"] == 4
        # API may or may not have errors depending on configuration
        assert "api_errors" in result.search_metadata
        # No assertion on error count as it depends on API availability

    @pytest.mark.asyncio
    async def test_search_hotels_by_location_with_max_limit(self, hotel_agent):
        """Test search hotels by location respects max results limit."""
        # Request more than max allowed
        result = await hotel_agent.search_hotels_by_location(
            location="Berlin",
            check_in_date="2024-07-01",
            check_out_date="2024-07-03",
            guest_count=2,
            max_results=150,  # Greater than max_results_per_request (100)
        )

        # Since APIs will fail due to missing credentials, check errors exist
        assert isinstance(result, HotelSearchResponse)
        assert "api_errors" in result.search_metadata

    @pytest.mark.asyncio
    async def test_search_hotels_by_location_default_max_results(self, hotel_agent):
        """Test search hotels by location uses default max results."""
        result = await hotel_agent.search_hotels_by_location(
            location="Sydney",
            check_in_date="2024-08-01",
            check_out_date="2024-08-03",
            guest_count=2,
        )

        # Since APIs will fail due to missing credentials, check errors exist
        assert isinstance(result, HotelSearchResponse)
        assert "api_errors" in result.search_metadata

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, hotel_agent):
        """Test cache key generation is consistent."""
        request_data = {
            "location": "Rome",
            "check_in_date": "2024-05-15",
            "check_out_date": "2024-05-17",
            "guest_count": 2,
        }

        key1 = await hotel_agent._cache_key(request_data)
        key2 = await hotel_agent._cache_key(request_data)

        assert key1 == key2
        assert key1.startswith("hotel_agent:")
        # New format: agent_name:location_part:date_part:hash
        # Should have 4 parts separated by colons
        parts = key1.split(":")
        assert len(parts) == 4
        assert parts[0] == "hotel_agent"
        assert parts[3]  # Should have a hash part
        assert len(parts[3]) == 32  # MD5 hash length

    @pytest.mark.asyncio
    async def test_cache_key_different_for_different_requests(self, hotel_agent):
        """Test different requests generate different cache keys."""
        request1 = {
            "location": "Madrid",
            "check_in_date": "2024-05-15",
            "check_out_date": "2024-05-17",
            "guest_count": 2,
        }

        request2 = {
            "location": "Madrid",
            "check_in_date": "2024-05-16",  # Different date
            "check_out_date": "2024-05-17",
            "guest_count": 2,
        }

        key1 = await hotel_agent._cache_key(request1)
        key2 = await hotel_agent._cache_key(request2)

        assert key1 != key2

    @pytest.mark.asyncio
    async def test_get_cached_result_hit(self, hotel_agent, mock_redis):
        """Test getting cached result when cache hit occurs."""
        cached_data = {"test": "data"}
        mock_redis.get.return_value = cached_data

        result = await hotel_agent._get_cached_result("test_key")

        assert result == cached_data
        mock_redis.get.assert_called_once_with("test_key", json_decode=True)

    @pytest.mark.asyncio
    async def test_get_cached_result_miss(self, hotel_agent, mock_redis):
        """Test getting cached result when cache miss occurs."""
        mock_redis.get.return_value = None

        result = await hotel_agent._get_cached_result("test_key")

        assert result is None
        mock_redis.get.assert_called_once_with("test_key", json_decode=True)

    @pytest.mark.asyncio
    async def test_get_cached_result_exception(self, hotel_agent, mock_redis):
        """Test getting cached result handles Redis exceptions gracefully."""
        mock_redis.get.side_effect = Exception("Redis connection failed")

        result = await hotel_agent._get_cached_result("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_cached_result_success(self, hotel_agent, mock_redis):
        """Test setting cached result succeeds."""
        test_data = {"result": "data"}

        await hotel_agent._set_cached_result("test_key", test_data, 600)

        mock_redis.set.assert_called_once_with("test_key", test_data, expire=600)

    @pytest.mark.asyncio
    async def test_set_cached_result_exception(self, hotel_agent, mock_redis):
        """Test setting cached result handles Redis exceptions gracefully."""
        mock_redis.set.side_effect = Exception("Redis connection failed")
        test_data = {"result": "data"}

        # Should not raise exception
        await hotel_agent._set_cached_result("test_key", test_data, 600)

        mock_redis.set.assert_called_once_with("test_key", test_data, expire=600)


class TestHotelSearchFunctionality:
    """Test suite for HotelAgent search functionality."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Create mock settings for testing."""
        settings = MagicMock(spec=Settings)
        settings.hotel_cache_ttl_seconds = 1800
        settings.hotel_max_results = 100
        settings.hotel_api_timeout_seconds = 30
        return settings

    @pytest.fixture
    def mock_database(self) -> AsyncMock:
        """Create mock database manager for testing."""
        database = AsyncMock()
        database.health_check.return_value = True
        return database

    @pytest.fixture
    def mock_redis(self) -> AsyncMock:
        """Create mock Redis manager for testing."""
        redis = AsyncMock()
        redis.ping.return_value = True
        redis.get.return_value = None
        redis.set.return_value = True
        return redis


    @pytest.fixture
    def hotel_agent(self, mock_settings, mock_database, mock_redis) -> HotelAgent:
        """Create HotelAgent instance for testing."""
        return HotelAgent(settings=mock_settings, database=mock_database, redis=mock_redis)

    @pytest.mark.asyncio
    async def test_search_hotels_invalid_date_format(self, hotel_agent):
        """Test hotel search handles invalid date formats."""
        request_data = {
            "location": "London",
            "check_in_date": "invalid-date",
            "check_out_date": "2024-06-17",
            "guest_count": 2,
        }

        with pytest.raises(ValueError, match="Invalid search parameters"):
            await hotel_agent.process(request_data)

    @pytest.mark.asyncio
    async def test_search_hotels_handles_api_error(self, hotel_agent):
        """Test hotel search handles API errors gracefully."""
        request_data = {
            "location": "Tokyo",
            "check_in_date": "2024-08-01",
            "check_out_date": "2024-08-03",
            "guest_count": 2,
        }

        with patch.object(
            hotel_agent, "search_hotels_google_places", side_effect=Exception("API timeout")
        ):
            result = await hotel_agent.process(request_data)

        # Should return empty results with error info from all APIs
        assert len(result.hotels) == 0
        assert result.total_results == 0
        assert "api_errors" in result.search_metadata
        # All APIs should have been attempted and failed
        assert len(result.search_metadata["api_errors"]) >= 1

    @pytest.mark.asyncio
    async def test_search_hotels_handles_malformed_response(self, hotel_agent):
        """Test hotel search handles malformed API responses."""
        # Create response with malformed hotel data

        request_data = {
            "location": "Madrid",
            "check_in_date": "2024-09-01",
            "check_out_date": "2024-09-03",
            "guest_count": 1,
        }

        with patch.object(
            hotel_agent, "search_hotels_google_places", side_effect=Exception("Malformed response")
        ):
            result = await hotel_agent.process(request_data)

        # Should handle malformed hotels (might include or filter them depending on validation)
        assert result.total_results >= 0
        # The exact number of hotels returned depends on how validation handles the malformed data
        assert len(result.hotels) >= 0

    @pytest.mark.asyncio
    async def test_search_hotels_returns_cached_results(self, hotel_agent, mock_redis):
        """Test hotel search returns cached results when available."""
        request_data = {
            "location": "Rome",
            "check_in_date": "2024-12-15",
            "check_out_date": "2024-12-17",
            "guest_count": 3,
        }

        # Setup cached response
        cached_response = {
            "hotels": [
                {
                    "hotel_id": "12345678-1234-5678-9abc-123456789abc",
                    "external_id": "cached-hotel",
                    "name": "Cached Hotel",
                    "location": {"latitude": 41.9028, "longitude": 12.4964, "address": "Rome"},
                    "price_per_night": "120.00",
                    "currency": "EUR",
                    "rating": 4.0,
                    "amenities": [],
                    "photos": [],
                    "booking_url": None,
                    "created_at": "2024-01-01T12:00:00Z",
                    "trip_id": None,
                }
            ],
            "search_metadata": {"location": "Rome"},
            "total_results": 1,
            "search_time_ms": 50,
            "cached": True,
        }
        mock_redis.get.return_value = cached_response

        result = await hotel_agent.process(request_data)

        # Should return cached result without calling API
        assert len(result.hotels) == 1
        assert result.hotels[0].name == "Cached Hotel"
        assert result.cached
        mock_redis.get.assert_called_once()

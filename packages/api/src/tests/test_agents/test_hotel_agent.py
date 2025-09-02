"""Tests for HotelAgent implementation."""

from unittest.mock import AsyncMock, MagicMock

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
        return HotelAgent(
            settings=mock_settings,
            database=mock_database,
            redis=mock_redis
        )

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

        agent = HotelAgent(
            settings=settings,
            database=mock_database,
            redis=mock_redis
        )

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
    async def test_process_valid_request(self, hotel_agent):
        """Test processing valid hotel search request."""
        request_data = {
            "location": "New York",
            "check_in_date": "2024-06-15",
            "check_out_date": "2024-06-17",
            "guest_count": 2,
        }

        result = await hotel_agent.process(request_data)

        assert isinstance(result, HotelSearchResponse)
        assert result.hotels == []  # Empty for now (placeholder implementation)
        assert result.total_results == 0
        assert result.search_metadata["location"] == "New York"
        assert result.search_metadata["guest_count"] == 2

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

        result = await hotel_agent.process(request_data)

        # Should cache the new result
        mock_redis.set.assert_called_once()
        args, kwargs = mock_redis.set.call_args
        assert args[1] == result.model_dump()
        assert kwargs["expire"] == 1800  # cache_ttl_seconds

    @pytest.mark.asyncio
    async def test_search_hotels_by_location(self, hotel_agent):
        """Test search hotels by location convenience method."""
        result = await hotel_agent.search_hotels_by_location(
            location="Tokyo",
            check_in_date="2024-07-01",
            check_out_date="2024-07-03",
            guest_count=4,
            budget=200.0,
            max_results=25
        )

        assert isinstance(result, HotelSearchResponse)
        assert result.search_metadata["location"] == "Tokyo"
        assert result.search_metadata["guest_count"] == 4
        assert result.search_metadata["budget"] == 200.0

    @pytest.mark.asyncio
    async def test_search_hotels_by_location_with_max_limit(self, hotel_agent):
        """Test search hotels by location respects max results limit."""
        # Request more than max allowed
        result = await hotel_agent.search_hotels_by_location(
            location="Berlin",
            check_in_date="2024-07-01",
            check_out_date="2024-07-03",
            guest_count=2,
            max_results=150  # Greater than max_results_per_request (100)
        )

        # Should be limited to max_results_per_request
        assert result.search_metadata["max_results"] == 100

    @pytest.mark.asyncio
    async def test_search_hotels_by_location_default_max_results(self, hotel_agent):
        """Test search hotels by location uses default max results."""
        result = await hotel_agent.search_hotels_by_location(
            location="Sydney",
            check_in_date="2024-08-01",
            check_out_date="2024-08-03",
            guest_count=2
        )

        assert result.search_metadata["max_results"] == 100

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
        assert len(key1) == len("hotel_agent:") + 32  # MD5 hash length

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

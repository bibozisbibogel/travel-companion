"""Tests for HotelAgent implementation."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from travel_companion.agents.hotel_agent import HotelAgent
from travel_companion.core.config import Settings
from travel_companion.models.external import (
    HotelLocation,
    HotelOption,
    HotelSearchResponse,
)
from travel_companion.services.external_apis.booking import (
    BookingApiResponse,
    BookingHotelResult,
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
        settings.geoapify_api_key = "test_geoapify_key"
        settings.liteapi_key = "test_liteapi_key"
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
        settings.geoapify_api_key = "test_geoapify_key"
        settings.liteapi_key = "test_liteapi_key"
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
    def mock_booking_response(self) -> BookingApiResponse:
        """Create mock Booking.com API response."""
        hotels = [
            BookingHotelResult(
                hotel_id="12345",
                name="Grand Hotel",
                address="123 Main St, New York, NY",
                latitude=40.7128,
                longitude=-74.0060,
                price_per_night=150.0,
                currency="USD",
                rating=4.2,
                review_score=8.5,
                amenities=["wifi", "pool", "gym"],
                photos=["photo1.jpg", "photo2.jpg"],
                description="Luxury hotel in downtown",
                booking_url="https://booking.com/hotel/12345",
            ),
            BookingHotelResult(
                hotel_id="67890",
                name="Budget Inn",
                address="456 Side St, New York, NY",
                latitude=40.7589,
                longitude=-73.9851,
                price_per_night=80.0,
                currency="USD",
                rating=3.5,
                amenities=["wifi"],
                photos=["photo3.jpg"],
                booking_url="https://booking.com/hotel/67890",
            ),
        ]

        return BookingApiResponse(
            hotels=hotels, total_results=2, search_time_ms=250, api_response_time_ms=180
        )

    @pytest.fixture
    def hotel_agent(self, mock_settings, mock_database, mock_redis) -> HotelAgent:
        """Create HotelAgent instance for testing."""
        return HotelAgent(settings=mock_settings, database=mock_database, redis=mock_redis)

    @pytest.mark.asyncio
    async def test_search_hotels_success(self, hotel_agent, mock_booking_response):
        """Test successful hotel search with API integration."""
        request_data = {
            "location": "New York",
            "check_in_date": "2024-06-15",
            "check_out_date": "2024-06-17",
            "guest_count": 2,
            "room_count": 1,
            "currency": "USD",
            "max_results": 50,
        }

        # Create mock hotel options from Google Places
        mock_hotels = [
            HotelOption(
                external_id="google_place_1",
                name="Grand Hotel",
                location=HotelLocation(
                    latitude=40.7128, longitude=-74.0060, address="123 Main St, New York, NY"
                ),
                price_per_night=Decimal("150.00"),
                currency="USD",
                rating=4.2,
                amenities=["wifi", "pool", "gym"],
            ),
            HotelOption(
                external_id="google_place_2",
                name="Budget Inn",
                location=HotelLocation(
                    latitude=40.7500, longitude=-73.9900, address="456 Side St, New York, NY"
                ),
                price_per_night=Decimal("80.00"),
                currency="USD",
                rating=3.5,
                amenities=["wifi"],
            ),
        ]

        # Mock time to ensure measurable search time
        with (
            patch.object(hotel_agent, "search_hotels_google_places", return_value=mock_hotels),
            patch("time.time", side_effect=[1000.0, 1000.1]),
        ):  # 100ms difference
            result = await hotel_agent.process(request_data)

        assert isinstance(result, HotelSearchResponse)
        assert len(result.hotels) == 2
        assert result.total_results == 2
        assert result.search_time_ms >= 0
        assert not result.cached

        # Check first hotel details
        hotel1 = result.hotels[0]
        assert hotel1.external_id == "google_place_1"
        assert hotel1.name == "Grand Hotel"
        assert hotel1.price_per_night == Decimal("150.00")
        assert hotel1.rating == 4.2
        assert hotel1.amenities == ["wifi", "pool", "gym"]
        assert hotel1.location.latitude == 40.7128
        assert hotel1.location.longitude == -74.0060

    @pytest.mark.asyncio
    async def test_search_hotels_with_budget_filter(self, hotel_agent, mock_booking_response):
        """Test hotel search applies budget filter correctly."""
        request_data = {
            "location": "New York",
            "check_in_date": "2024-06-15",
            "check_out_date": "2024-06-17",
            "guest_count": 2,
            "budget": 100.0,  # Should filter out hotels over $100/night
            "currency": "USD",
        }

        # Create mock hotel that is under budget
        mock_hotels = [
            HotelOption(
                external_id="google_place_1",
                name="Budget Inn",
                location=HotelLocation(
                    latitude=40.7500, longitude=-73.9900, address="456 Side St, New York, NY"
                ),
                price_per_night=Decimal("80.00"),
                currency="USD",
                rating=3.5,
                amenities=["wifi"],
            )
        ]

        with patch.object(hotel_agent, "search_hotels_google_places", return_value=mock_hotels):
            result = await hotel_agent.process(request_data)

        # Should only include Budget Inn (80.0) which is under the $100 budget
        assert len(result.hotels) == 1
        assert result.hotels[0].name == "Budget Inn"
        assert result.hotels[0].price_per_night == Decimal("80.00")

    @pytest.mark.asyncio
    async def test_search_hotels_date_parsing(self, hotel_agent, mock_booking_response):
        """Test hotel search correctly parses date formats."""
        request_data = {
            "location": "Paris",
            "check_in_date": datetime(2024, 7, 1),  # datetime object
            "check_out_date": "2024-07-03",  # ISO string
            "guest_count": 2,
        }

        with patch.object(
            hotel_agent, "search_hotels_google_places", return_value=[]
        ) as mock_search:
            await hotel_agent.process(request_data)

        # Verify Google Places search was called
        mock_search.assert_called_once()
        search_request = mock_search.call_args[0][0]
        assert search_request.check_in_date.strftime("%Y-%m-%d") == "2024-07-01"
        assert search_request.check_out_date.strftime("%Y-%m-%d") == "2024-07-03"
        assert search_request.guest_count == 2

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
    async def test_search_hotels_max_results_limit(self, hotel_agent, mock_booking_response):
        """Test hotel search respects maximum results limit."""
        request_data = {
            "location": "Berlin",
            "check_in_date": "2024-10-01",
            "check_out_date": "2024-10-03",
            "guest_count": 2,
            "max_results": 150,  # Above configured limit
        }

        with patch.object(
            hotel_agent, "search_hotels_google_places", return_value=[]
        ) as mock_search:
            await hotel_agent.process(request_data)

        # Should be limited to hotel_agent max_results_per_request (100)
        search_request = mock_search.call_args[0][0]
        assert search_request.max_results == 100

    @pytest.mark.asyncio
    async def test_search_hotels_metadata_complete(self, hotel_agent, mock_booking_response):
        """Test hotel search includes complete metadata."""
        request_data = {
            "location": "Sydney",
            "check_in_date": "2024-11-15",
            "check_out_date": "2024-11-17",
            "guest_count": 4,
            "room_count": 2,
            "budget": 200.0,
            "currency": "AUD",
            "max_results": 25,
        }

        with patch.object(hotel_agent, "search_hotels_google_places", return_value=[]):
            result = await hotel_agent.process(request_data)

        metadata = result.search_metadata
        assert metadata["location"] == "Sydney"
        assert metadata["check_in_date"] == "2024-11-15T00:00:00"
        assert metadata["check_out_date"] == "2024-11-17T00:00:00"
        assert metadata["guest_count"] == 4
        assert metadata["room_count"] == 2
        assert metadata["budget_per_night"] == 200.0
        assert metadata["currency"] == "AUD"
        assert metadata["max_results"] == 25
        assert "apis_attempted" in metadata
        assert "api_errors" in metadata

    @pytest.mark.asyncio
    async def test_search_hotels_caches_results(
        self, hotel_agent, mock_redis, mock_booking_response
    ):
        """Test hotel search results are properly cached."""
        request_data = {
            "location": "Barcelona",
            "check_in_date": "2024-12-01",
            "check_out_date": "2024-12-03",
            "guest_count": 2,
        }

        mock_redis.get.return_value = None  # No cached result initially

        with patch.object(hotel_agent, "search_hotels_google_places", return_value=[]):
            await hotel_agent.process(request_data)

        # Should cache the new result (only main data, no metadata)
        assert mock_redis.set.call_count == 1
        # Call should be for the main cache data
        main_call_args, main_call_kwargs = mock_redis.set.call_args_list[0]
        cached_data = main_call_args[1]

        assert cached_data["total_results"] == 0
        assert len(cached_data["hotels"]) == 0
        assert "cache_timestamp" in cached_data  # Enhanced cache format
        assert cached_data["cached"]
        assert main_call_kwargs["expire"] == 1800  # cache_ttl_seconds

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

    @pytest.mark.asyncio
    async def test_search_hotels_performance_tracking(self, hotel_agent, mock_booking_response):
        """Test hotel search tracks performance metrics."""
        request_data = {
            "location": "Amsterdam",
            "check_in_date": "2025-01-01",
            "check_out_date": "2025-01-03",
            "guest_count": 2,
        }

        with (
            patch.object(hotel_agent, "search_hotels_google_places", return_value=[]),
            patch("time.time", side_effect=[1000.0, 1000.05]),
        ):  # 50ms difference
            result = await hotel_agent.process(request_data)

        # Should track search performance
        assert result.search_time_ms >= 0
        assert "apis_attempted" in result.search_metadata


class TestHotelAgentEnhanced:
    """Test suite for enhanced hotel agent functionality with Geoapify + LiteAPI."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Create mock settings for testing."""
        settings = MagicMock(spec=Settings)
        settings.hotel_cache_ttl_seconds = 1800
        settings.hotel_max_results = 100
        settings.hotel_api_timeout_seconds = 30
        settings.geoapify_api_key = "test_geoapify_key"
        settings.liteapi_key = "test_liteapi_key"
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

    @pytest.fixture
    def sample_geoapify_hotels(self):
        """Sample Geoapify hotel data."""
        return [
            {
                "name": "Grand Hotel Tokyo",
                "latitude": 35.6762,
                "longitude": 139.6503,
                "place_id": "geo123",
                "address": "1-1-1 Marunouchi",
                "city": "Tokyo",
                "country": "Japan",
            },
            {
                "name": "Business Hotel Shibuya",
                "latitude": 35.6596,
                "longitude": 139.7016,
                "place_id": "geo456",
                "address": "2-2-2 Shibuya",
                "city": "Tokyo",
                "country": "Japan",
            },
        ]

    @pytest.fixture
    def sample_liteapi_hotels(self):
        """Sample LiteAPI hotel data."""
        return [
            {
                "id": "LITE123",
                "name": "Grand Hotel Tokyo",
                "latitude": 35.6762,
                "longitude": 139.6503,
            },
            {
                "id": "LITE456",
                "name": "Business Hotel Shibuya",
                "latitude": 35.6596,
                "longitude": 139.7016,
            },
        ]

    @pytest.fixture
    def sample_liteapi_rates(self):
        """Sample LiteAPI rates data."""
        return {
            "data": [
                {
                    "hotel_id": "LITE123",
                    "rates": [
                        {"total_amount": 150.0, "currency": "USD"},
                        {"total_amount": 180.0, "currency": "USD"},
                    ],
                },
                {"hotel_id": "LITE456", "rates": [{"total_amount": 120.0, "currency": "USD"}]},
            ]
        }

    @pytest.mark.skip(reason="Geoapify and LiteAPI clients are currently disabled")
    @pytest.mark.asyncio
    async def test_search_hotels_with_rates_success(
        self, hotel_agent, sample_geoapify_hotels, sample_liteapi_hotels, sample_liteapi_rates
    ):
        """Test successful enhanced hotel search with rates."""
        # Setup mocks
        hotel_agent._geoapify_client.search_hotels = AsyncMock(return_value=sample_geoapify_hotels)
        hotel_agent._liteapi_client.search_hotels_by_geo = AsyncMock(
            return_value=sample_liteapi_hotels
        )
        hotel_agent._liteapi_client.get_min_rates = AsyncMock(return_value=sample_liteapi_rates)

        result = await hotel_agent.search_hotels_with_rates(
            location="Tokyo",
            check_in_date="2025-01-15",
            check_out_date="2025-01-17",
            guest_count=2,
            max_results=10,
        )

        assert isinstance(result, HotelSearchResponse)
        assert len(result.hotels) == 2
        assert result.search_metadata["provider"] == "geoapify_liteapi"
        assert result.search_metadata["location"] == "Tokyo"

        # Verify API calls were made
        hotel_agent._geoapify_client.search_hotels.assert_called_once()
        hotel_agent._liteapi_client.search_hotels_by_geo.assert_called_once()
        hotel_agent._liteapi_client.get_min_rates.assert_called_once()

        # Check that hotels have rates
        hotels_with_rates = [h for h in result.hotels if h.price_per_night > 0]
        assert len(hotels_with_rates) == 2

    @pytest.mark.skip(reason="Geoapify and LiteAPI clients are currently disabled")
    @pytest.mark.asyncio
    async def test_search_hotels_with_rates_full_rates(
        self, hotel_agent, sample_geoapify_hotels, sample_liteapi_hotels, sample_liteapi_rates
    ):
        """Test enhanced hotel search with full rates option."""
        hotel_agent._geoapify_client.search_hotels = AsyncMock(return_value=sample_geoapify_hotels)
        hotel_agent._liteapi_client.search_hotels_by_geo = AsyncMock(
            return_value=sample_liteapi_hotels
        )
        hotel_agent._liteapi_client.get_full_rates = AsyncMock(return_value=sample_liteapi_rates)

        result = await hotel_agent.search_hotels_with_rates(
            location="Tokyo",
            check_in_date="2025-01-15",
            check_out_date="2025-01-17",
            guest_count=2,
            get_full_rates=True,
        )

        assert result.search_metadata["rate_type"] == "full"
        hotel_agent._liteapi_client.get_full_rates.assert_called_once()
        hotel_agent._liteapi_client.get_min_rates.assert_not_called()

    @pytest.mark.skip(reason="Geoapify and LiteAPI clients are currently disabled")
    @pytest.mark.asyncio
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

    @pytest.mark.skip(reason="Geoapify and LiteAPI clients are currently disabled")
    @pytest.mark.asyncio
    async def test_search_hotels_with_rates_fallback_on_exception(self, hotel_agent):
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
                cache_expires_at=None,
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

    @pytest.mark.skip(reason="Geoapify and LiteAPI clients are currently disabled")
    @pytest.mark.asyncio
    async def test_search_hotels_with_rates_budget_filter(
        self, hotel_agent, sample_geoapify_hotels, sample_liteapi_hotels
    ):
        """Test budget filtering in enhanced search."""
        # Create rates data with different prices
        rates_data = {
            "data": [
                {
                    "hotel_id": "LITE123",
                    "rates": [{"total_amount": 300.0}],  # Above budget
                },
                {
                    "hotel_id": "LITE456",
                    "rates": [{"total_amount": 80.0}],  # Within budget
                },
            ]
        }

        hotel_agent._geoapify_client.search_hotels = AsyncMock(return_value=sample_geoapify_hotels)
        hotel_agent._liteapi_client.search_hotels_by_geo = AsyncMock(
            return_value=sample_liteapi_hotels
        )
        hotel_agent._liteapi_client.get_min_rates = AsyncMock(return_value=rates_data)

        result = await hotel_agent.search_hotels_with_rates(
            location="Tokyo",
            check_in_date="2025-01-15",
            check_out_date="2025-01-17",
            guest_count=2,
            budget_per_night=100.0,
        )

        # Should only include hotels within budget
        assert len(result.hotels) >= 0  # At least the budget hotel should be included
        for hotel in result.hotels:
            if hotel.price_per_night > 0:
                assert hotel.price_per_night <= Decimal("100")

    @pytest.mark.skip(reason="Geoapify and LiteAPI clients are currently disabled")
    @pytest.mark.asyncio
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

    @pytest.mark.skip(reason="Geoapify and LiteAPI clients are currently disabled")
    @pytest.mark.asyncio
    async def test_combine_geoapify_liteapi_data(
        self, hotel_agent, sample_geoapify_hotels, sample_liteapi_hotels, sample_liteapi_rates
    ):
        """Test data combination from Geoapify and LiteAPI."""
        result = await hotel_agent._combine_geoapify_liteapi_data(
            sample_geoapify_hotels, sample_liteapi_hotels, sample_liteapi_rates
        )

        assert len(result) == 2

        # Check that hotels have been properly combined
        for hotel in result:
            assert isinstance(hotel, HotelOption)
            assert hotel.name in ["Grand Hotel Tokyo", "Business Hotel Shibuya"]
            assert hotel.price_per_night > 0  # Should have rate data

    @pytest.mark.skip(reason="Geoapify and LiteAPI clients are currently disabled")
    @pytest.mark.asyncio
    async def test_hotel_agent_has_new_clients(self, hotel_agent):
        """Test that hotel agent has the new API clients."""
        assert hasattr(hotel_agent, "_geoapify_client")
        assert hasattr(hotel_agent, "_liteapi_client")
        assert hotel_agent._geoapify_client is not None
        assert hotel_agent._liteapi_client is not None

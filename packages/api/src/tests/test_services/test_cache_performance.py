"""Performance tests for caching effectiveness in hotel search."""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from travel_companion.agents.hotel_agent import HotelAgent
from travel_companion.core.redis import RedisManager
from travel_companion.models.external import (
    HotelLocation,
    HotelOption,
    HotelSearchResponse,
)
from travel_companion.services.cache import CacheManager
from travel_companion.services.cache_warming import CacheWarmingService


class TestCachePerformance:
    """Test suite for cache performance and effectiveness."""

    @pytest.fixture
    async def mock_redis_manager(self):
        """Create mock Redis manager for testing."""
        manager = MagicMock(spec=RedisManager)
        manager.get = AsyncMock()
        manager.set = AsyncMock(return_value=True)
        manager.delete = AsyncMock(return_value=True)
        manager.exists = AsyncMock(return_value=False)
        manager.client = MagicMock()
        manager.client.scan_iter = AsyncMock()
        return manager

    @pytest.fixture
    def sample_hotel_options(self):
        """Create sample hotel options for testing."""
        return [
            HotelOption(
                external_id="test_hotel_1",
                name="Test Hotel 1",
                location=HotelLocation(
                    latitude=40.7589, longitude=-73.9851, address="New York, NY"
                ),
                price_per_night=Decimal("150.00"),
                currency="USD",
                rating=4.2,
                amenities=["wifi", "pool", "gym"],
                photos=["photo1.jpg"],
                booking_url="https://example.com/book/1",
                created_at=datetime.now(UTC),
            ),
            HotelOption(
                external_id="test_hotel_2",
                name="Test Hotel 2",
                location=HotelLocation(
                    latitude=40.7614, longitude=-73.9776, address="New York, NY"
                ),
                price_per_night=Decimal("200.00"),
                currency="USD",
                rating=4.5,
                amenities=["wifi", "spa", "restaurant"],
                photos=["photo2.jpg"],
                booking_url="https://example.com/book/2",
                created_at=datetime.now(UTC),
            ),
        ]

    @pytest.fixture
    def sample_search_response(self, sample_hotel_options):
        """Create sample search response for testing."""
        return HotelSearchResponse(
            hotels=sample_hotel_options,
            search_metadata={
                "location": "New York, NY",
                "check_in_date": "2025-01-15",
                "check_out_date": "2025-01-17",
                "guest_count": 2,
            },
            total_results=2,
            search_time_ms=1500,
            cached=False,
        )

    async def test_cache_hit_performance(self, mock_redis_manager, sample_search_response):
        """Test cache hit performance vs fresh search."""
        cache_manager = CacheManager(mock_redis_manager)

        # Mock cache hit - return data instantly
        mock_redis_manager.get.return_value = sample_search_response.model_dump()
        mock_redis_manager.get.return_value["cache_timestamp"] = datetime.now(UTC).isoformat()

        # Measure cache hit time
        start_time = time.time()
        cached_result = await cache_manager.get_hotel_search_cache("test_key")
        cache_hit_time = (time.time() - start_time) * 1000  # Convert to ms

        assert cached_result is not None
        assert cache_hit_time < 50  # Cache hit should be under 50ms
        assert len(cached_result.hotels) == 2

    async def test_cache_miss_with_api_call_timing(self, mock_redis_manager):
        """Test timing difference between cache miss and API call."""
        # Create hotel agent with mocked dependencies
        with patch("travel_companion.agents.hotel_agent.BookingClient") as mock_booking:
            mock_booking_instance = AsyncMock()
            mock_booking.return_value = mock_booking_instance

            # Mock API response with realistic delay
            async def slow_api_response(*args, **kwargs):
                await asyncio.sleep(1.5)  # Simulate 1.5s API call
                return MagicMock(hotels=[], total_results=0, api_response_time_ms=1500)

            mock_booking_instance.search_hotels = slow_api_response

            hotel_agent = HotelAgent(redis=mock_redis_manager)

            # Mock cache miss
            mock_redis_manager.get.return_value = None

            request_data = {
                "location": "Test City",
                "check_in_date": "2025-01-15",
                "check_out_date": "2025-01-17",
                "guest_count": 2,
            }

            # Measure API call time
            start_time = time.time()
            response = await hotel_agent.process(request_data)
            api_call_time = (time.time() - start_time) * 1000

            # API call should take significantly longer than cache hit
            assert api_call_time > 1000  # Should be over 1 second
            assert response.cached is False

    async def test_cache_warming_performance(self, mock_redis_manager):
        """Test cache warming performance and effectiveness."""
        cache_warming_service = CacheWarmingService()

        # Mock the hotel agent to return quick responses
        with patch.object(cache_warming_service, "get_hotel_agent") as mock_get_agent:
            mock_agent = AsyncMock()
            mock_agent.process = AsyncMock()

            # Mock fast API responses
            async def fast_process(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms simulated response
                return HotelSearchResponse(
                    hotels=[],
                    search_metadata={},
                    total_results=0,
                    search_time_ms=100,
                    cached=False,
                )

            mock_agent.process = fast_process
            mock_get_agent.return_value = mock_agent

            # Test warming 5 destinations
            destinations = ["City1", "City2", "City3", "City4", "City5"]

            start_time = time.time()
            results = await cache_warming_service.warm_popular_destinations(
                destinations=destinations, max_concurrent=3
            )
            warming_time = time.time() - start_time

            # Should complete warming in reasonable time with concurrency
            assert warming_time < 5  # Should be under 5 seconds with 3 concurrent
            assert results["destinations_warmed"] == 5
            assert results["patterns_warmed"] > 0

    async def test_cache_key_generation_performance(self, mock_redis_manager):
        """Test cache key generation performance for different search parameters."""
        hotel_agent = HotelAgent(redis=mock_redis_manager)

        # Test data with various complexity levels
        test_cases = [
            # Simple search
            {
                "location": "Paris",
                "check_in_date": "2025-01-15",
                "check_out_date": "2025-01-17",
                "guest_count": 2,
            },
            # Complex search with many parameters
            {
                "location": "New York City, NY, USA",
                "check_in_date": datetime(2025, 1, 15),
                "check_out_date": datetime(2025, 1, 17),
                "guest_count": 4,
                "room_count": 2,
                "budget": Decimal("250.50"),
                "currency": "usd",
                "max_results": 50,
                "amenities": ["wifi", "pool", "gym"],
            },
        ]

        # Measure key generation performance
        for test_case in test_cases:
            start_time = time.time()
            cache_key = await hotel_agent._cache_key(test_case)
            key_gen_time = (time.time() - start_time) * 1000

            # Key generation should be very fast
            assert key_gen_time < 10  # Under 10ms
            assert len(cache_key) > 20  # Should generate meaningful key
            assert "hotel_agent:" in cache_key

    async def test_cache_invalidation_performance(self, mock_redis_manager):
        """Test performance of cache invalidation operations."""
        cache_manager = CacheManager(mock_redis_manager)

        # Mock Redis scan operations
        mock_keys = [
            "hotel_agent:paris:20250115:hash1",
            "hotel_agent:paris:20250116:hash2",
            "hotel_agent:london:20250115:hash3",
        ]

        async def mock_scan_iter(match=None):
            for key in mock_keys:
                if not match or "paris" in key:
                    yield key

        mock_redis_manager.client.scan_iter = mock_scan_iter

        # Test location-based invalidation
        start_time = time.time()
        invalidated_count = await cache_manager.invalidate_hotel_location_cache("paris")
        invalidation_time = (time.time() - start_time) * 1000

        # Invalidation should be reasonably fast
        assert invalidation_time < 100  # Under 100ms for small dataset
        assert invalidated_count >= 0  # Should return count

    async def test_concurrent_cache_operations_performance(self, mock_redis_manager):
        """Test performance under concurrent cache operations."""
        cache_manager = CacheManager(mock_redis_manager)

        # Mock successful cache operations
        mock_redis_manager.get.return_value = None  # Cache miss
        mock_redis_manager.set.return_value = True

        # Create multiple concurrent cache operations
        async def cache_operation(i):
            cache_key = f"test_key_{i}"

            # Try to get from cache
            await cache_manager.get_hotel_search_cache(cache_key)

            # Set in cache
            sample_response = HotelSearchResponse(
                hotels=[],
                search_metadata={"test": i},
                total_results=0,
                search_time_ms=100,
                cached=False,
            )
            await cache_manager.set_hotel_search_cache(cache_key, sample_response)

        # Run 10 concurrent cache operations
        start_time = time.time()
        await asyncio.gather(*[cache_operation(i) for i in range(10)])
        concurrent_time = time.time() - start_time

        # Concurrent operations should complete reasonably quickly
        assert concurrent_time < 2  # Under 2 seconds for 10 operations

    async def test_cache_size_and_memory_efficiency(self, mock_redis_manager):
        """Test cache size estimation and memory efficiency."""
        cache_manager = CacheManager(mock_redis_manager)

        # Mock cache statistics with proper async iterator
        async def mock_scan_iter(match=None):
            keys = ["hotel_agent:key1", "hotel_agent:key2", "hotel_agent:key3"]
            for key in keys:
                yield key

        mock_redis_manager.client.scan_iter = mock_scan_iter

        stats = await cache_manager.get_cache_statistics()

        # Should provide useful statistics
        assert "total_hotel_cache_keys" in stats
        assert "cache_memory_usage" in stats
        assert isinstance(stats.get("cache_memory_usage"), int)

    @pytest.mark.parametrize(
        "num_searches,expected_max_time",
        [
            (1, 50),  # Single search should be very fast from cache
            (10, 200),  # 10 searches should complete under 200ms
            (50, 500),  # 50 searches should complete under 500ms
        ],
    )
    async def test_cache_throughput_performance(
        self, mock_redis_manager, sample_search_response, num_searches, expected_max_time
    ):
        """Test cache throughput with different loads."""
        cache_manager = CacheManager(mock_redis_manager)

        # Mock cache hits for all requests
        mock_redis_manager.get.return_value = sample_search_response.model_dump()
        mock_redis_manager.get.return_value["cache_timestamp"] = datetime.now(UTC).isoformat()

        # Perform multiple cache retrievals
        start_time = time.time()
        tasks = []
        for i in range(num_searches):
            task = cache_manager.get_hotel_search_cache(f"test_key_{i}")
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        total_time = (time.time() - start_time) * 1000  # Convert to ms

        # All results should be cache hits
        assert all(result is not None for result in results)
        assert len(results) == num_searches

        # Performance should meet expectations
        assert total_time < expected_max_time

        # Calculate throughput
        throughput = num_searches / (total_time / 1000)  # searches per second
        print(f"Cache throughput: {throughput:.2f} searches/second for {num_searches} searches")

    async def test_cache_expiration_and_cleanup_performance(self, mock_redis_manager):
        """Test performance of cache expiration and cleanup operations."""
        cache_manager = CacheManager(mock_redis_manager)

        # Mock old cache entries
        old_timestamp = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        mock_cache_data = {
            "hotels": [],
            "search_metadata": {},
            "total_results": 0,
            "search_time_ms": 100,
            "cached": True,
            "cache_timestamp": old_timestamp,
        }

        async def mock_scan_with_data(match=None):
            for i in range(100):  # Simulate 100 cache entries
                yield f"hotel_agent:key_{i}"

        mock_redis_manager.client.scan_iter = mock_scan_with_data
        mock_redis_manager.get.return_value = mock_cache_data

        # Test cleanup performance
        start_time = time.time()
        invalidated = await cache_manager.invalidate_outdated_hotel_cache(max_age_minutes=60)
        cleanup_time = (time.time() - start_time) * 1000

        # Cleanup should complete in reasonable time
        assert cleanup_time < 1000  # Under 1 second for 100 entries
        assert invalidated >= 0

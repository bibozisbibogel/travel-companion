"""Tests for ActivityCacheManager with Redis testcontainer."""

import pytest
from datetime import datetime, UTC, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, Mock, patch

from travel_companion.services.activity_cache import ActivityCacheManager
from travel_companion.models.external import (
    ActivityCategory,
    ActivityLocation,
    ActivityOption,
    ActivitySearchRequest,
    ActivitySearchResponse,
)


@pytest.fixture
def mock_redis():
    """Mock Redis manager for testing."""
    redis = AsyncMock()
    redis.get.return_value = None
    redis.set.return_value = True
    redis.delete.return_value = True
    redis.exists.return_value = False
    redis.scan_keys.return_value = []
    redis.incr.return_value = 1
    redis.expire.return_value = True
    redis.delete_keys.return_value = True
    return redis


@pytest.fixture
def activity_cache_manager(mock_redis):
    """Create ActivityCacheManager with mocked Redis."""
    return ActivityCacheManager(mock_redis)


@pytest.fixture
def sample_search_request():
    """Sample activity search request."""
    return ActivitySearchRequest(
        location="Paris, France",
        category=ActivityCategory.CULTURAL,
        guest_count=2,
        budget_per_person=Decimal("50.00"),
        duration_hours=3,
        max_results=10,
    )


@pytest.fixture
def sample_search_response():
    """Sample activity search response."""
    activities = [
        ActivityOption(
            external_id="ta_123",
            name="Louvre Museum",
            description="Famous art museum",
            category=ActivityCategory.CULTURAL,
            location=ActivityLocation(latitude=48.8606, longitude=2.3376),
            price=Decimal("45.00"),
            provider="tripadvisor",
        ),
        ActivityOption(
            external_id="viator_456",
            name="Eiffel Tower Tour",
            description="Tower visit",
            category=ActivityCategory.CULTURAL,
            location=ActivityLocation(latitude=48.8584, longitude=2.2945),
            price=Decimal("35.00"),
            provider="viator",
        ),
    ]
    
    return ActivitySearchResponse(
        activities=activities,
        total_results=2,
        search_time_ms=250,
        search_metadata={"location": "Paris, France"},
    )


class TestActivityCacheManager:
    """Test cases for ActivityCacheManager."""

    @pytest.mark.asyncio
    async def test_cache_search_results(self, activity_cache_manager, sample_search_request, sample_search_response, mock_redis):
        """Test caching of activity search results."""
        result = await activity_cache_manager.cache_search_results(
            sample_search_request, 
            sample_search_response
        )
        
        assert result is True
        mock_redis.set.assert_called_once()
        
        # Verify cache key generation
        call_args = mock_redis.set.call_args
        cache_key = call_args[0][0]
        assert "activity:search" in cache_key
        assert "paris_france" in cache_key
        assert "cultural" in cache_key

    @pytest.mark.asyncio
    async def test_get_search_results_cache_hit(self, activity_cache_manager, sample_search_request, sample_search_response, mock_redis):
        """Test successful retrieval of cached search results."""
        # Mock cache hit
        cached_data = sample_search_response.model_dump()
        mock_redis.get.return_value = cached_data
        
        result = await activity_cache_manager.get_search_results(sample_search_request)
        
        assert result is not None
        assert result.cached is True
        assert len(result.activities) == 2
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_search_results_cache_miss(self, activity_cache_manager, sample_search_request, mock_redis):
        """Test cache miss returns None."""
        mock_redis.get.return_value = None
        
        result = await activity_cache_manager.get_search_results(sample_search_request)
        
        assert result is None
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_activity_pricing(self, activity_cache_manager, mock_redis):
        """Test caching of activity pricing information."""
        external_id = "ta_123456"
        provider = "tripadvisor"
        pricing_data = {
            "price": 45.00,
            "currency": "EUR",
            "availability": "high",
        }
        
        result = await activity_cache_manager.cache_activity_pricing(
            external_id, provider, pricing_data
        )
        
        assert result is True
        mock_redis.set.assert_called_once()
        
        # Verify cache key and TTL
        call_args = mock_redis.set.call_args
        cache_key = call_args[0][0]
        cached_data = call_args[0][1]
        ttl = call_args[1]["expire"]
        
        assert f"activity:pricing:{provider}:{external_id}" == cache_key
        assert "cached_at" in cached_data
        assert ttl == activity_cache_manager.PRICING_TTL

    @pytest.mark.asyncio
    async def test_get_activity_pricing_cache_hit(self, activity_cache_manager, mock_redis):
        """Test successful retrieval of cached pricing data."""
        external_id = "ta_123456"
        provider = "tripadvisor"
        pricing_data = {"price": 45.00, "currency": "EUR"}
        
        mock_redis.get.return_value = pricing_data
        
        result = await activity_cache_manager.get_activity_pricing(external_id, provider)
        
        assert result == pricing_data
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_activity_pricing_cache_miss(self, activity_cache_manager, mock_redis):
        """Test pricing cache miss returns None."""
        mock_redis.get.return_value = None
        
        result = await activity_cache_manager.get_activity_pricing("test_id", "test_provider")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_warm_popular_destinations(self, activity_cache_manager, mock_redis):
        """Test cache warming for popular destinations."""
        destinations = [
            {"location": "Paris, France", "priority": "high"},
            {"location": "London, UK", "priority": "medium"},
            {"location": "New York, USA", "priority": "high"},
        ]
        
        result = await activity_cache_manager.warm_popular_destinations(destinations)
        
        assert result == 3  # All destinations warmed
        assert mock_redis.set.call_count == 3

    @pytest.mark.asyncio
    async def test_invalidate_stale_activity_data(self, activity_cache_manager, mock_redis):
        """Test invalidation of stale cache entries."""
        # Mock stale cache entries
        stale_keys = [
            "activity:search:paris:cultural",
            "activity:pricing:tripadvisor:123"
        ]
        mock_redis.scan_keys.side_effect = [
            ["activity:search:paris:cultural"],
            ["activity:pricing:tripadvisor:123"]
        ]
        
        # Mock stale data (older than 24 hours)
        stale_time = (datetime.now(UTC) - timedelta(hours=25)).isoformat()
        mock_redis.get.return_value = {"cached_at": stale_time}
        
        result = await activity_cache_manager.invalidate_stale_activity_data(max_age_hours=24)
        
        assert result == 2  # Both entries invalidated
        assert mock_redis.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_get_cache_performance_stats(self, activity_cache_manager, mock_redis):
        """Test retrieval of cache performance statistics."""
        # Mock statistics data
        mock_redis.get.side_effect = [100, 25, 50, 10]  # hits and misses
        mock_redis.scan_keys.side_effect = [
            ["key1", "key2", "key3"],  # search entries
            ["key4", "key5"],          # pricing entries  
            ["key6"],                  # popular entries
        ]
        
        stats = await activity_cache_manager.get_cache_performance_stats()
        
        assert "search" in stats
        assert "pricing" in stats
        assert "cache_counts" in stats
        
        assert stats["search"]["hits"] == 100
        assert stats["search"]["misses"] == 25
        assert stats["search"]["hit_rate"] == 0.8  # 100/125
        
        assert stats["pricing"]["hits"] == 50
        assert stats["pricing"]["misses"] == 10
        assert stats["pricing"]["hit_rate"] == 5/6  # 50/60
        
        assert stats["cache_counts"]["search_entries"] == 3
        assert stats["cache_counts"]["pricing_entries"] == 2
        assert stats["cache_counts"]["popular_entries"] == 1

    @pytest.mark.asyncio
    async def test_clear_all_activity_cache(self, activity_cache_manager, mock_redis):
        """Test clearing all activity-related cache entries."""
        # Mock existing cache keys
        mock_redis.scan_keys.side_effect = [
            ["activity:search:key1", "activity:search:key2"],
            ["activity:pricing:key3"],
            ["activity:popular:key4"],
            ["activity:location:key5"]
        ]
        
        result = await activity_cache_manager.clear_all_activity_cache()
        
        assert result == 5  # All entries cleared
        mock_redis.delete_keys.assert_called()

    @pytest.mark.asyncio
    async def test_dynamic_ttl_calculation(self, activity_cache_manager, sample_search_request, sample_search_response, mock_redis):
        """Test dynamic TTL calculation based on search parameters."""
        # Test with popular destination
        with patch.object(activity_cache_manager, '_is_popular_destination', return_value=True):
            ttl = await activity_cache_manager._calculate_dynamic_ttl(sample_search_request, sample_search_response)
            assert ttl == activity_cache_manager.POPULAR_DESTINATION_TTL

    @pytest.mark.asyncio
    async def test_search_cache_key_generation(self, activity_cache_manager, sample_search_request):
        """Test generation of search cache keys."""
        cache_key = await activity_cache_manager._generate_search_cache_key(sample_search_request)
        
        assert "activity:search" in cache_key
        assert "paris_france" in cache_key
        assert "cultural" in cache_key
        assert "guests_2" in cache_key
        assert "budget_50.00" in cache_key
        assert "duration_3" in cache_key

    @pytest.mark.asyncio
    async def test_cache_key_normalization(self, activity_cache_manager):
        """Test cache key normalization handles special characters."""
        request = ActivitySearchRequest(
            location="New York, NY",  # Contains spaces and comma
            category=ActivityCategory.ENTERTAINMENT,
            guest_count=1,
        )
        
        cache_key = await activity_cache_manager._generate_search_cache_key(request)
        
        assert "new_york,_ny" in cache_key
        assert "entertainment" in cache_key

    @pytest.mark.asyncio
    async def test_error_handling_redis_failure(self, activity_cache_manager, sample_search_request, mock_redis):
        """Test error handling when Redis operations fail."""
        mock_redis.get.side_effect = Exception("Redis connection failed")
        
        # Should not raise exception, should return None
        result = await activity_cache_manager.get_search_results(sample_search_request)
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_statistics_increment(self, activity_cache_manager, mock_redis):
        """Test cache statistics are properly incremented."""
        await activity_cache_manager._increment_cache_stats("test_metric", 5)
        
        mock_redis.incr.assert_called_with("activity:stats:test_metric", 5)
        mock_redis.expire.assert_called_with("activity:stats:test_metric", 86400)

    @pytest.mark.asyncio
    async def test_location_data_caching(self, activity_cache_manager, sample_search_request, sample_search_response, mock_redis):
        """Test caching of location-specific data."""
        await activity_cache_manager._cache_location_data(sample_search_request, sample_search_response)
        
        # Should call set with location-specific key
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        cache_key = call_args[0][0]
        cached_data = call_args[0][1]
        
        assert "activity:location:paris,_france" == cache_key
        assert "total_activities" in cached_data
        assert "avg_price" in cached_data
        assert "categories" in cached_data


class TestActivityCacheIntegration:
    """Integration tests that would run with Redis testcontainer."""
    
    @pytest.mark.skip(reason="Requires Redis testcontainer setup")
    @pytest.mark.asyncio
    async def test_full_cache_lifecycle_with_real_redis(self):
        """Test complete cache lifecycle with real Redis.
        
        This test would:
        1. Start Redis testcontainer
        2. Cache search results
        3. Retrieve cached data
        4. Test TTL expiration
        5. Test cache warming
        6. Test invalidation
        """
        pass

    @pytest.mark.skip(reason="Requires Redis testcontainer setup")
    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self):
        """Test concurrent cache operations with real Redis.
        
        This test would verify:
        1. Concurrent reads and writes
        2. Cache key conflicts
        3. Statistics consistency
        """
        pass

    @pytest.mark.skip(reason="Requires Redis testcontainer setup")
    @pytest.mark.asyncio
    async def test_cache_performance_under_load(self):
        """Test cache performance under high load.
        
        This test would measure:
        1. Cache hit/miss ratios
        2. Response times
        3. Memory usage
        4. Throughput metrics
        """
        pass

    @pytest.mark.skip(reason="Requires Redis testcontainer setup")
    @pytest.mark.asyncio
    async def test_cache_persistence_across_restarts(self):
        """Test cache data persistence across Redis restarts."""
        pass

    @pytest.mark.skip(reason="Requires Redis testcontainer setup")
    @pytest.mark.asyncio
    async def test_cache_warming_performance(self):
        """Test cache warming performance with large datasets."""
        pass
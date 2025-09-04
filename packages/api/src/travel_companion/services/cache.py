"""Enhanced caching service for travel companion agents."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from travel_companion.core.redis import RedisManager
from travel_companion.models.external import (
    HotelSearchResponse,
    RestaurantSearchResponse,
    WeatherSearchResponse,
)


class CacheManager:
    """Enhanced cache management with specialized strategies for different data types."""

    def __init__(self, redis_manager: RedisManager) -> None:
        """Initialize cache manager.

        Args:
            redis_manager: Redis manager instance for cache operations
        """
        self.redis = redis_manager
        self.logger = logging.getLogger("travel_companion.services.cache")

    async def get_hotel_search_cache(self, cache_key: str) -> HotelSearchResponse | None:
        """Get cached hotel search results.

        Args:
            cache_key: Cache key for hotel search results

        Returns:
            Cached HotelSearchResponse or None if not found/expired
        """
        try:
            cached_data = await self.redis.get(cache_key, json_decode=True)
            if not cached_data:
                return None

            # Check if cache is still valid (not just TTL but also data freshness)
            cache_timestamp = cached_data.get("cache_timestamp")
            if cache_timestamp:
                cache_time = datetime.fromisoformat(cache_timestamp)
                # Hotel availability data should not be older than 30 minutes
                if datetime.now(UTC) - cache_time > timedelta(minutes=30):
                    await self.redis.delete(cache_key)
                    self.logger.info(f"Invalidated stale hotel cache: {cache_key}")
                    return None

            # Convert back to HotelSearchResponse
            return HotelSearchResponse(**cached_data)

        except Exception as e:
            self.logger.warning(f"Failed to get cached hotel search: {e}")
            return None

    async def set_hotel_search_cache(
        self,
        cache_key: str,
        response: HotelSearchResponse,
        ttl_seconds: int = 1800,  # 30 minutes default
    ) -> bool:
        """Cache hotel search results with enhanced metadata.

        Args:
            cache_key: Cache key for storage
            response: HotelSearchResponse to cache
            ttl_seconds: Time to live in seconds

        Returns:
            True if caching succeeded, False otherwise
        """
        try:
            # Add cache timestamp for freshness checking
            cache_data = response.model_dump()
            cache_data["cache_timestamp"] = datetime.now(UTC).isoformat()
            cache_data["cached"] = True

            success = await self.redis.set(cache_key, cache_data, expire=ttl_seconds)

            if success:
                self.logger.info(f"Cached hotel search results: {cache_key} (TTL: {ttl_seconds}s)")

                # Store cache metadata for analytics and warming
                metadata_key = f"{cache_key}:meta"
                metadata = {
                    "created_at": datetime.now(UTC).isoformat(),
                    "ttl_seconds": ttl_seconds,
                    "result_count": len(response.hotels),
                    "search_params": response.search_metadata,
                }
                await self.redis.set(
                    metadata_key, metadata, expire=ttl_seconds + 300
                )  # Keep metadata slightly longer

            return success

        except Exception as e:
            self.logger.error(f"Failed to cache hotel search results: {e}")
            return False

    async def invalidate_hotel_location_cache(self, location: str) -> int:
        """Invalidate all cached hotel results for a specific location.

        Args:
            location: Location identifier to invalidate

        Returns:
            Number of cache entries invalidated
        """
        try:
            # Create pattern to match all hotel cache keys for this location
            location_pattern = f"hotel_agent:*{location.lower()}*"

            # Use Redis SCAN to find matching keys (more efficient than KEYS for large datasets)
            invalidated_count = 0
            async for key in self.redis.client.scan_iter(match=location_pattern):
                await self.redis.delete(key)
                invalidated_count += 1

            if invalidated_count > 0:
                self.logger.info(
                    f"Invalidated {invalidated_count} hotel cache entries for location: {location}"
                )

            return invalidated_count

        except Exception as e:
            self.logger.error(f"Failed to invalidate location cache: {e}")
            return 0

    async def invalidate_outdated_hotel_cache(self, max_age_minutes: int = 30) -> int:
        """Invalidate hotel cache entries older than specified age.

        Args:
            max_age_minutes: Maximum age in minutes before invalidation

        Returns:
            Number of cache entries invalidated
        """
        try:
            cutoff_time = datetime.now(UTC) - timedelta(minutes=max_age_minutes)
            invalidated_count = 0

            # Scan for all hotel agent cache keys
            async for key in self.redis.client.scan_iter(match="hotel_agent:*"):
                try:
                    cached_data = await self.redis.get(key, json_decode=True)
                    if not cached_data:
                        continue

                    cache_timestamp = cached_data.get("cache_timestamp")
                    if cache_timestamp:
                        cache_time = datetime.fromisoformat(cache_timestamp)
                        if cache_time < cutoff_time:
                            await self.redis.delete(key)
                            invalidated_count += 1

                except Exception as e:
                    self.logger.warning(f"Error checking cache age for key {key}: {e}")
                    continue

            if invalidated_count > 0:
                self.logger.info(f"Invalidated {invalidated_count} outdated hotel cache entries")

            return invalidated_count

        except Exception as e:
            self.logger.error(f"Failed to invalidate outdated cache: {e}")
            return 0

    async def warm_popular_hotel_destinations(
        self, destinations: list[str], search_params: dict[str, Any] | None = None
    ) -> dict[str, bool]:
        """Pre-warm cache for popular hotel destinations.

        Args:
            destinations: List of popular destination names/locations
            search_params: Default search parameters for warming

        Returns:
            Dictionary mapping destination to warming success status
        """
        if search_params is None:
            # Default search parameters for warming
            from datetime import date

            tomorrow = date.today() + timedelta(days=1)
            day_after = tomorrow + timedelta(days=1)

            search_params = {
                "check_in_date": tomorrow.isoformat(),
                "check_out_date": day_after.isoformat(),
                "guest_count": 2,
                "room_count": 1,
                "max_results": 50,
            }

        results = {}

        for destination in destinations:
            try:
                # Import here to avoid circular import
                from travel_companion.agents.hotel_agent import HotelAgent

                hotel_agent = HotelAgent()

                # Create warming request
                warming_request = {"location": destination, **search_params}

                self.logger.info(f"Warming hotel cache for destination: {destination}")

                # Execute search to warm cache
                response = await hotel_agent.process(warming_request)
                results[destination] = len(response.hotels) > 0

                self.logger.info(
                    f"Warmed hotel cache for {destination}: {len(response.hotels)} results"
                )

            except Exception as e:
                self.logger.error(f"Failed to warm cache for destination {destination}: {e}")
                results[destination] = False

        return results

    async def get_cache_statistics(self) -> dict[str, Any]:
        """Get caching statistics and metrics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            stats: dict[str, Any] = {
                "total_hotel_cache_keys": 0,
                "total_metadata_keys": 0,
                "cache_memory_usage": 0,
                "oldest_cache_entry": None,
                "newest_cache_entry": None,
                "popular_locations": {},
            }

            # Count cache keys
            hotel_keys = []
            async for key in self.redis.client.scan_iter(match="hotel_agent:*"):
                if not key.endswith(":meta"):
                    hotel_keys.append(key)
                    stats["total_hotel_cache_keys"] = int(stats["total_hotel_cache_keys"]) + 1
                else:
                    stats["total_metadata_keys"] = int(stats["total_metadata_keys"]) + 1

            # Analyze cache timestamps
            timestamps = []
            for key in hotel_keys[:100]:  # Sample first 100 keys for performance
                try:
                    cached_data = await self.redis.get(key, json_decode=True)
                    if cached_data and cached_data.get("cache_timestamp"):
                        timestamps.append(datetime.fromisoformat(cached_data["cache_timestamp"]))
                except Exception:
                    continue

            if timestamps:
                stats["oldest_cache_entry"] = min(timestamps).isoformat()
                stats["newest_cache_entry"] = max(timestamps).isoformat()

            # Estimate memory usage (rough calculation)
            stats["cache_memory_usage"] = (
                int(stats["total_hotel_cache_keys"]) * 10240
            )  # ~10KB per entry estimate

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get cache statistics: {e}")
            return {"error": str(e)}

    async def generate_cache_key_variants(self, base_params: dict[str, Any]) -> list[str]:
        """Generate cache key variants for related searches.

        Args:
            base_params: Base search parameters

        Returns:
            List of cache keys for related searches that might be cached
        """
        from travel_companion.agents.hotel_agent import HotelAgent

        variants = []
        agent = HotelAgent()

        try:
            # Generate key for exact search
            base_key = await agent._cache_key(base_params)
            variants.append(base_key)

            # Generate variants with different guest counts
            for guest_count in [1, 2, 3, 4]:
                if guest_count != base_params.get("guest_count"):
                    variant_params = base_params.copy()
                    variant_params["guest_count"] = guest_count
                    variant_key = await agent._cache_key(variant_params)
                    variants.append(variant_key)

            # Generate variants with different date ranges (±1 day)
            if "check_in_date" in base_params:
                try:
                    base_checkin = datetime.fromisoformat(base_params["check_in_date"])

                    for day_offset in [-1, 1]:
                        variant_params = base_params.copy()
                        new_checkin = base_checkin + timedelta(days=day_offset)
                        variant_params["check_in_date"] = new_checkin.isoformat()

                        if "check_out_date" in base_params:
                            base_checkout = datetime.fromisoformat(base_params["check_out_date"])
                            new_checkout = base_checkout + timedelta(days=day_offset)
                            variant_params["check_out_date"] = new_checkout.isoformat()

                        variant_key = await agent._cache_key(variant_params)
                        variants.append(variant_key)

                except Exception:
                    pass  # Skip date variants if parsing fails

            return list(set(variants))  # Remove duplicates

        except Exception as e:
            self.logger.warning(f"Failed to generate cache key variants: {e}")
            return [base_key] if "base_key" in locals() else []

    async def get_weather_cache(self, cache_key: str) -> WeatherSearchResponse | None:
        """Get cached weather search results.

        Args:
            cache_key: Cache key for weather search results

        Returns:
            Cached WeatherSearchResponse or None if not found/expired
        """
        try:
            cached_data = await self.redis.get(cache_key, json_decode=True)
            if not cached_data:
                return None

            # Check if cache is still valid (weather data should not be older than 3 hours)
            cache_timestamp = cached_data.get("cache_timestamp")
            if cache_timestamp:
                cache_time = datetime.fromisoformat(cache_timestamp)
                # Weather data should not be older than 3 hours for forecast reliability
                if datetime.now(UTC) - cache_time > timedelta(hours=3):
                    await self.redis.delete(cache_key)
                    self.logger.info(f"Invalidated stale weather cache: {cache_key}")
                    return None

            # Convert back to WeatherSearchResponse
            return WeatherSearchResponse(**cached_data)

        except Exception as e:
            self.logger.warning(f"Failed to get cached weather search: {e}")
            return None

    async def set_weather_cache(
        self,
        cache_key: str,
        response: WeatherSearchResponse,
        ttl_seconds: int = 10800,  # 3 hours default
    ) -> bool:
        """Cache weather search results.

        Args:
            cache_key: Cache key for storage
            response: WeatherSearchResponse to cache
            ttl_seconds: Time to live in seconds (default 3 hours)

        Returns:
            True if caching succeeded, False otherwise
        """
        try:
            # Add cache timestamp and expiration info
            cache_data = response.model_dump()
            cache_data["cache_timestamp"] = datetime.now(UTC).isoformat()
            cache_data["cached"] = True
            cache_data["cache_expires_at"] = (
                datetime.now(UTC) + timedelta(seconds=ttl_seconds)
            ).isoformat()

            success = await self.redis.set(cache_key, cache_data, expire=ttl_seconds)

            if success:
                self.logger.info(
                    f"Cached weather search results: {cache_key} (TTL: {ttl_seconds}s)"
                )

                # Store cache metadata for analytics
                metadata_key = f"{cache_key}:meta"
                metadata = {
                    "created_at": datetime.now(UTC).isoformat(),
                    "ttl_seconds": ttl_seconds,
                    "forecast_days": len(response.forecast.daily),
                    "alert_count": len(response.forecast.alerts),
                    "historical_points": len(response.historical_data),
                    "search_params": response.search_metadata,
                }
                await self.redis.set(
                    metadata_key, metadata, expire=ttl_seconds + 300
                )  # Keep metadata slightly longer

            return success

        except Exception as e:
            self.logger.error(f"Failed to cache weather search results: {e}")
            return False

    async def invalidate_weather_location_cache(self, location: str) -> int:
        """Invalidate all cached weather results for a specific location.

        Args:
            location: Location identifier to invalidate

        Returns:
            Number of cache entries invalidated
        """
        try:
            # Create pattern to match all weather cache keys for this location
            location_pattern = f"weather_agent:*{location.lower()}*"

            # Use Redis SCAN to find matching keys
            invalidated_count = 0
            async for key in self.redis.client.scan_iter(match=location_pattern):
                await self.redis.delete(key)
                invalidated_count += 1

            if invalidated_count > 0:
                self.logger.info(
                    f"Invalidated {invalidated_count} weather cache entries for location: {location}"
                )

            return invalidated_count

        except Exception as e:
            self.logger.error(f"Failed to invalidate weather location cache: {e}")
            return 0

    async def get_restaurant_cache(self, cache_key: str) -> RestaurantSearchResponse | None:
        """Get cached restaurant search results.

        Args:
            cache_key: Cache key for restaurant search results

        Returns:
            Cached RestaurantSearchResponse or None if not found/expired
        """
        try:
            cached_data = await self.redis.get(cache_key, json_decode=True)
            if not cached_data:
                return None

            # Check if cache is still valid (restaurant data should not be older than 30 minutes)
            cache_timestamp = cached_data.get("cache_timestamp")
            if cache_timestamp:
                cache_time = datetime.fromisoformat(cache_timestamp)
                # Restaurant data should not be older than 30 minutes for freshness
                if datetime.now(UTC) - cache_time > timedelta(minutes=30):
                    await self.redis.delete(cache_key)
                    self.logger.info(f"Invalidated stale restaurant cache: {cache_key}")
                    return None

            # Convert back to RestaurantSearchResponse
            return RestaurantSearchResponse(**cached_data)

        except Exception as e:
            self.logger.warning(f"Failed to get cached restaurant search: {e}")
            return None

    async def set_restaurant_cache(
        self,
        cache_key: str,
        response: RestaurantSearchResponse,
        ttl_seconds: int = 1800,  # 30 minutes default
    ) -> bool:
        """Cache restaurant search results.

        Args:
            cache_key: Cache key for storage
            response: RestaurantSearchResponse to cache
            ttl_seconds: Time to live in seconds (default 30 minutes)

        Returns:
            True if caching succeeded, False otherwise
        """
        try:
            # Add cache timestamp and expiration info
            cache_data = response.model_dump()
            cache_data["cache_timestamp"] = datetime.now(UTC).isoformat()
            cache_data["cached"] = True
            cache_data["cache_expires_at"] = (
                datetime.now(UTC) + timedelta(seconds=ttl_seconds)
            ).isoformat()

            success = await self.redis.set(cache_key, cache_data, expire=ttl_seconds)

            if success:
                self.logger.info(
                    f"Cached restaurant search results: {cache_key} (TTL: {ttl_seconds}s)"
                )

                # Store cache metadata for analytics
                metadata_key = f"{cache_key}:meta"
                metadata = {
                    "created_at": datetime.now(UTC).isoformat(),
                    "ttl_seconds": ttl_seconds,
                    "restaurant_count": len(response.restaurants),
                    "search_params": response.search_metadata,
                }
                await self.redis.set(
                    metadata_key, metadata, expire=ttl_seconds + 300
                )  # Keep metadata slightly longer

            return success

        except Exception as e:
            self.logger.error(f"Failed to cache restaurant search results: {e}")
            return False

    async def invalidate_restaurant_location_cache(self, location: str) -> int:
        """Invalidate all cached restaurant results for a specific location.

        Args:
            location: Location identifier to invalidate

        Returns:
            Number of cache entries invalidated
        """
        try:
            # Create pattern to match all restaurant cache keys for this location
            location_pattern = f"food_agent:*{location.lower()}*"

            # Use Redis SCAN to find matching keys
            invalidated_count = 0
            async for key in self.redis.client.scan_iter(match=location_pattern):
                await self.redis.delete(key)
                invalidated_count += 1

            if invalidated_count > 0:
                self.logger.info(
                    f"Invalidated {invalidated_count} restaurant cache entries for location: {location}"
                )

            return invalidated_count

        except Exception as e:
            self.logger.error(f"Failed to invalidate restaurant location cache: {e}")
            return 0

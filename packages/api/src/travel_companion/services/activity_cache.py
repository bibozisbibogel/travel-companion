"""Advanced Redis caching strategy for activity searches."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, cast

from travel_companion.core.redis import RedisManager
from travel_companion.models.external import ActivitySearchRequest, ActivitySearchResponse


class ActivityCacheManager:
    """Advanced caching manager for activity search results."""

    def __init__(self, redis: RedisManager) -> None:
        """Initialize activity cache manager.

        Args:
            redis: Redis manager instance
        """
        self.redis = redis
        self.logger = logging.getLogger("travel_companion.services.activity_cache")

        # Cache configuration
        self.DEFAULT_TTL = 1800  # 30 minutes for search results
        self.PRICING_TTL = 900  # 15 minutes for pricing data
        self.POPULAR_DESTINATION_TTL = 3600  # 1 hour for popular destinations
        self.CACHE_WARMING_BATCH_SIZE = 10

        # Cache key prefixes
        self.SEARCH_PREFIX = "activity:search"
        self.PRICING_PREFIX = "activity:pricing"
        self.POPULAR_PREFIX = "activity:popular"
        self.LOCATION_PREFIX = "activity:location"
        self.STATS_PREFIX = "activity:stats"

    async def get_search_results(
        self, search_request: ActivitySearchRequest
    ) -> ActivitySearchResponse | None:
        """Get cached activity search results.

        Args:
            search_request: Activity search parameters

        Returns:
            Cached search response or None if not found
        """
        try:
            cache_key = await self._generate_search_cache_key(search_request)
            cached_data = await self.redis.get(cache_key, json_decode=True)

            if cached_data:
                # Update cache hit statistics
                await self._increment_cache_stats("search_hits")

                # Reconstruct ActivitySearchResponse
                response = ActivitySearchResponse(**cached_data)
                response.cached = True

                self.logger.debug(f"Cache hit for activity search: {cache_key}")
                return response

            await self._increment_cache_stats("search_misses")
            return None

        except Exception as e:
            self.logger.warning(f"Failed to get cached search results: {e}")
            return None

    async def cache_search_results(
        self,
        search_request: ActivitySearchRequest,
        search_response: ActivitySearchResponse,
        custom_ttl: int | None = None,
    ) -> bool:
        """Cache activity search results with intelligent TTL.

        Args:
            search_request: Search parameters used
            search_response: Search response to cache
            custom_ttl: Custom TTL in seconds, uses default if None

        Returns:
            True if cached successfully, False otherwise
        """
        try:
            cache_key = await self._generate_search_cache_key(search_request)
            ttl = custom_ttl or await self._calculate_dynamic_ttl(search_request, search_response)

            # Add caching metadata
            response_dict = search_response.model_dump(mode="json")
            response_dict["cache_expires_at"] = datetime.now(UTC).timestamp() + ttl

            await self.redis.set(cache_key, response_dict, expire=ttl)

            # Cache location-specific data for warming
            await self._cache_location_data(search_request, search_response)

            # Update cache statistics
            await self._increment_cache_stats("search_cached")

            self.logger.debug(f"Cached activity search results: {cache_key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            self.logger.error(f"Failed to cache search results: {e}")
            return False

    async def get_activity_pricing(self, external_id: str, provider: str) -> dict[str, Any] | None:
        """Get cached activity pricing information.

        Args:
            external_id: External activity ID
            provider: API provider name

        Returns:
            Cached pricing data or None if not found
        """
        try:
            cache_key = f"{self.PRICING_PREFIX}:{provider}:{external_id}"
            pricing_data = await self.redis.get(cache_key, json_decode=True)

            if pricing_data:
                await self._increment_cache_stats("pricing_hits")
                self.logger.debug(f"Cache hit for activity pricing: {cache_key}")
                return cast(dict[str, Any], pricing_data)

            await self._increment_cache_stats("pricing_misses")
            return None

        except Exception as e:
            self.logger.warning(f"Failed to get cached pricing: {e}")
            return None

    async def cache_activity_pricing(
        self, external_id: str, provider: str, pricing_data: dict[str, Any]
    ) -> bool:
        """Cache activity pricing with shorter TTL.

        Args:
            external_id: External activity ID
            provider: API provider name
            pricing_data: Pricing information to cache

        Returns:
            True if cached successfully, False otherwise
        """
        try:
            cache_key = f"{self.PRICING_PREFIX}:{provider}:{external_id}"

            # Add timestamp for staleness detection
            pricing_data["cached_at"] = datetime.now(UTC).isoformat()

            await self.redis.set(cache_key, pricing_data, expire=self.PRICING_TTL)

            self.logger.debug(f"Cached activity pricing: {cache_key}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to cache pricing: {e}")
            return False

    async def warm_popular_destinations(self, destinations: list[dict[str, Any]]) -> int:
        """Warm cache for popular destinations.

        Args:
            destinations: List of popular destination data

        Returns:
            Number of destinations warmed
        """
        warmed_count = 0

        try:
            # Process destinations in batches
            for i in range(0, len(destinations), self.CACHE_WARMING_BATCH_SIZE):
                batch = destinations[i : i + self.CACHE_WARMING_BATCH_SIZE]

                # Create warming tasks
                warming_tasks = [self._warm_destination_cache(dest) for dest in batch]

                # Execute batch
                results = await asyncio.gather(*warming_tasks, return_exceptions=True)

                # Count successful warming operations
                warmed_count += sum(
                    1 for result in results if result and not isinstance(result, Exception)
                )

                # Small delay between batches to avoid overwhelming APIs
                if i + self.CACHE_WARMING_BATCH_SIZE < len(destinations):
                    await asyncio.sleep(0.1)

            await self._increment_cache_stats("destinations_warmed", warmed_count)
            self.logger.info(f"Warmed cache for {warmed_count} popular destinations")

        except Exception as e:
            self.logger.error(f"Failed to warm popular destinations: {e}")

        return warmed_count

    async def invalidate_stale_activity_data(self, max_age_hours: int = 24) -> int:
        """Invalidate outdated activity information.

        Args:
            max_age_hours: Maximum age in hours before data is considered stale

        Returns:
            Number of cache entries invalidated
        """
        try:
            invalidated_count = 0

            # Get all activity-related cache keys
            search_keys = await self.redis.scan_keys(f"{self.SEARCH_PREFIX}:*")
            pricing_keys = await self.redis.scan_keys(f"{self.PRICING_PREFIX}:*")

            all_keys = search_keys + pricing_keys

            # Check each key for staleness
            for key in all_keys:
                try:
                    cached_data = await self.redis.get(key, json_decode=True)
                    if not cached_data:
                        continue

                    # Check if data is stale based on cached_at timestamp
                    cached_at_str = cached_data.get("cached_at")
                    if not cached_at_str:
                        continue

                    cached_at = datetime.fromisoformat(cached_at_str.replace("Z", "+00:00"))
                    age_hours = (datetime.now(UTC) - cached_at).total_seconds() / 3600

                    if age_hours > max_age_hours:
                        await self.redis.delete(key)
                        invalidated_count += 1

                except Exception as e:
                    self.logger.debug(f"Error checking key {key}: {e}")
                    continue

            await self._increment_cache_stats("entries_invalidated", invalidated_count)
            self.logger.info(f"Invalidated {invalidated_count} stale cache entries")

            return invalidated_count

        except Exception as e:
            self.logger.error(f"Failed to invalidate stale data: {e}")
            return 0

    async def get_cache_performance_stats(self) -> dict[str, Any]:
        """Get cache performance statistics.

        Returns:
            Dictionary with cache performance metrics
        """
        try:
            stats = {}

            # Get hit/miss ratios
            search_hits = await self.redis.get(f"{self.STATS_PREFIX}:search_hits") or 0
            search_misses = await self.redis.get(f"{self.STATS_PREFIX}:search_misses") or 0
            pricing_hits = await self.redis.get(f"{self.STATS_PREFIX}:pricing_hits") or 0
            pricing_misses = await self.redis.get(f"{self.STATS_PREFIX}:pricing_misses") or 0

            # Calculate ratios
            total_search = int(search_hits) + int(search_misses)
            total_pricing = int(pricing_hits) + int(pricing_misses)

            stats = {
                "search": {
                    "hits": int(search_hits),
                    "misses": int(search_misses),
                    "hit_rate": int(search_hits) / total_search if total_search > 0 else 0,
                },
                "pricing": {
                    "hits": int(pricing_hits),
                    "misses": int(pricing_misses),
                    "hit_rate": int(pricing_hits) / total_pricing if total_pricing > 0 else 0,
                },
                "cache_counts": {
                    "search_entries": len(await self.redis.scan_keys(f"{self.SEARCH_PREFIX}:*")),
                    "pricing_entries": len(await self.redis.scan_keys(f"{self.PRICING_PREFIX}:*")),
                    "popular_entries": len(await self.redis.scan_keys(f"{self.POPULAR_PREFIX}:*")),
                },
            }

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return {}

    async def _generate_search_cache_key(self, request: ActivitySearchRequest) -> str:
        """Generate cache key for activity search request.

        Args:
            request: Activity search request

        Returns:
            Cache key string
        """
        # Create normalized key from search parameters
        # Handle both enum and string values for category
        category_str = "any"
        if request.category:
            category_str = (
                request.category.value
                if hasattr(request.category, "value")
                else str(request.category)
            )

        key_parts = [
            self.SEARCH_PREFIX,
            request.location.lower().replace(" ", "_").replace(",", "")[:20],
            category_str,
            f"guests_{request.guest_count}",
            f"budget_{request.budget_per_person}" if request.budget_per_person else "no_budget",
            f"duration_{request.duration_hours}" if request.duration_hours else "any_duration",
        ]

        return ":".join(key_parts)

    async def _calculate_dynamic_ttl(
        self, request: ActivitySearchRequest, response: ActivitySearchResponse
    ) -> int:
        """Calculate dynamic TTL based on search parameters and results.

        Args:
            request: Search request parameters
            response: Search response data

        Returns:
            TTL in seconds
        """
        base_ttl = self.DEFAULT_TTL

        # Check if popular destination first (highest priority)
        is_popular = await self._is_popular_destination(request.location)

        if is_popular:
            # Popular destinations get longer TTL regardless of other factors
            base_ttl = self.POPULAR_DESTINATION_TTL
        else:
            # Shorter TTL for searches with pricing data
            if request.budget_per_person:
                base_ttl = min(base_ttl, self.PRICING_TTL)

            # Shorter TTL for searches with very few results (likely to change)
            if response.total_results < 3:
                base_ttl = int(base_ttl * 0.5)

        return base_ttl

    async def _cache_location_data(
        self, request: ActivitySearchRequest, response: ActivitySearchResponse
    ) -> None:
        """Cache location-specific data for warming purposes.

        Args:
            request: Search request parameters
            response: Search response data
        """
        try:
            location_key = f"{self.LOCATION_PREFIX}:{request.location.lower().replace(' ', '_')}"

            location_data = {
                "location": request.location,
                "total_activities": response.total_results,
                "avg_price": sum(a.price for a in response.activities) / len(response.activities)
                if response.activities
                else 0,
                "categories": list({a.category for a in response.activities}),
                "last_updated": datetime.now(UTC).isoformat(),
            }

            await self.redis.set(location_key, location_data, expire=self.POPULAR_DESTINATION_TTL)

        except Exception as e:
            self.logger.debug(f"Failed to cache location data: {e}")

    async def _warm_destination_cache(self, destination: dict[str, Any]) -> bool:
        """Warm cache for a specific destination.

        Args:
            destination: Destination data with location info

        Returns:
            True if warming was successful
        """
        try:
            # This would typically trigger actual searches for the destination
            # For now, we'll just mark it as warmed
            cache_key = f"{self.POPULAR_PREFIX}:{destination['location'].lower().replace(' ', '_')}"

            warm_data = {
                "location": destination["location"],
                "warmed_at": datetime.now(UTC).isoformat(),
                "priority": destination.get("priority", "normal"),
            }

            await self.redis.set(cache_key, warm_data, expire=self.POPULAR_DESTINATION_TTL)

            return True

        except Exception as e:
            self.logger.debug(f"Failed to warm destination cache: {e}")
            return False

    async def _is_popular_destination(self, location: str) -> bool:
        """Check if location is a popular destination.

        Args:
            location: Location string

        Returns:
            True if location is popular
        """
        try:
            popular_key = f"{self.POPULAR_PREFIX}:{location.lower().replace(' ', '_')}"
            return await self.redis.exists(popular_key)
        except Exception:
            return False

    async def _increment_cache_stats(self, metric: str, count: int = 1) -> None:
        """Increment cache performance statistics.

        Args:
            metric: Metric name to increment
            count: Amount to increment by
        """
        try:
            stat_key = f"{self.STATS_PREFIX}:{metric}"
            await self.redis.incr(stat_key, count)

            # Set expiration for stats (keep for 24 hours)
            await self.redis.expire(stat_key, 86400)

        except Exception as e:
            self.logger.debug(f"Failed to increment cache stats: {e}")

    async def clear_all_activity_cache(self) -> int:
        """Clear all activity-related cache entries.

        Returns:
            Number of entries cleared
        """
        try:
            prefixes = [
                self.SEARCH_PREFIX,
                self.PRICING_PREFIX,
                self.POPULAR_PREFIX,
                self.LOCATION_PREFIX,
            ]

            cleared_count = 0
            for prefix in prefixes:
                keys = await self.redis.scan_keys(f"{prefix}:*")
                if keys:
                    await self.redis.delete_keys(keys)
                    cleared_count += len(keys)

            self.logger.info(f"Cleared {cleared_count} activity cache entries")
            return cleared_count

        except Exception as e:
            self.logger.error(f"Failed to clear activity cache: {e}")
            return 0

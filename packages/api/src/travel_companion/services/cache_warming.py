"""Background cache warming service for popular hotel destinations."""

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from travel_companion.agents.hotel_agent import HotelAgent
from travel_companion.core.redis import get_redis_manager


class CacheWarmingService:
    """Service for warming cache with popular hotel destinations and search patterns."""

    # Popular destinations for cache warming
    POPULAR_DESTINATIONS = [
        "New York, NY",
        "Paris, France",
        "London, UK",
        "Tokyo, Japan",
        "Los Angeles, CA",
        "Barcelona, Spain",
        "Rome, Italy",
        "Amsterdam, Netherlands",
        "Berlin, Germany",
        "Sydney, Australia",
        "Miami, FL",
        "Las Vegas, NV",
        "Chicago, IL",
        "San Francisco, CA",
        "Madrid, Spain",
        "Istanbul, Turkey",
        "Bangkok, Thailand",
        "Dubai, UAE",
        "Singapore",
        "Hong Kong",
    ]

    # Common search patterns for warming
    COMMON_SEARCH_PATTERNS = [
        {"guest_count": 2, "room_count": 1, "days_ahead": 1},  # Tomorrow, 2 guests
        {"guest_count": 2, "room_count": 1, "days_ahead": 7},  # Next week, 2 guests
        {"guest_count": 4, "room_count": 2, "days_ahead": 14},  # 2 weeks, family
        {"guest_count": 1, "room_count": 1, "days_ahead": 3},  # Business travel
        {"guest_count": 2, "room_count": 1, "days_ahead": 30},  # Vacation planning
    ]

    def __init__(self) -> None:
        """Initialize cache warming service."""
        self.logger = logging.getLogger("travel_companion.services.cache_warming")
        self._hotel_agent: HotelAgent | None = None

    async def get_hotel_agent(self) -> HotelAgent:
        """Get or create hotel agent instance."""
        if self._hotel_agent is None:
            self._hotel_agent = HotelAgent()
        return self._hotel_agent

    async def warm_popular_destinations(
        self, destinations: list[str] | None = None, max_concurrent: int = 3
    ) -> dict[str, Any]:
        """Warm cache for popular hotel destinations.

        Args:
            destinations: Custom list of destinations, uses default if None
            max_concurrent: Maximum concurrent warming operations

        Returns:
            Warming results summary
        """
        if destinations is None:
            destinations = self.POPULAR_DESTINATIONS[:10]  # Limit to top 10 for performance

        self.logger.info(f"Starting cache warming for {len(destinations)} destinations")

        results = {
            "started_at": datetime.now(UTC).isoformat(),
            "destinations_warmed": 0,
            "patterns_warmed": 0,
            "total_cache_entries": 0,
            "errors": [],
            "destination_results": {},
        }

        # Use semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(max_concurrent)

        # Create warming tasks
        warming_tasks = []
        for destination in destinations:
            task = asyncio.create_task(self._warm_destination_with_patterns(destination, semaphore))
            warming_tasks.append(task)

        # Execute warming tasks and collect results
        task_results = await asyncio.gather(*warming_tasks, return_exceptions=True)

        # Process results
        for destination, result in zip(destinations, task_results, strict=False):
            if isinstance(result, Exception):
                error_msg = f"Failed to warm {destination}: {result}"
                self.logger.error(error_msg)
                results["errors"].append(error_msg)
                results["destination_results"][destination] = {
                    "success": False,
                    "error": str(result),
                }
            else:
                results["destinations_warmed"] += 1
                results["patterns_warmed"] += result["patterns_warmed"]
                results["total_cache_entries"] += result["cache_entries"]
                results["destination_results"][destination] = result

        results["completed_at"] = datetime.now(UTC).isoformat()

        self.logger.info(
            f"Cache warming completed: {results['destinations_warmed']} destinations, "
            f"{results['patterns_warmed']} patterns, {results['total_cache_entries']} cache entries"
        )

        return results

    async def _warm_destination_with_patterns(
        self, destination: str, semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        """Warm cache for a destination using common search patterns.

        Args:
            destination: Destination to warm cache for
            semaphore: Semaphore for concurrency control

        Returns:
            Warming results for this destination
        """
        async with semaphore:
            self.logger.info(f"Warming cache for destination: {destination}")

            hotel_agent = await self.get_hotel_agent()
            result = {
                "success": True,
                "patterns_warmed": 0,
                "cache_entries": 0,
                "search_times": [],
                "errors": [],
            }

            # Warm cache with different search patterns
            for pattern in self.COMMON_SEARCH_PATTERNS:
                try:
                    # Calculate dates
                    check_in_date = date.today() + timedelta(days=pattern["days_ahead"])
                    check_out_date = check_in_date + timedelta(days=2)  # 2-night stay

                    # Create search request
                    search_request = {
                        "location": destination,
                        "check_in_date": check_in_date.isoformat(),
                        "check_out_date": check_out_date.isoformat(),
                        "guest_count": pattern["guest_count"],
                        "room_count": pattern["room_count"],
                        "max_results": 20,  # Smaller result set for warming
                    }

                    # Execute search (will cache results)
                    start_time = datetime.now(UTC)
                    response = await hotel_agent.process(search_request)
                    end_time = datetime.now(UTC)

                    search_time_ms = int((end_time - start_time).total_seconds() * 1000)
                    result["search_times"].append(search_time_ms)
                    result["patterns_warmed"] += 1
                    result["cache_entries"] += len(response.hotels)

                    self.logger.debug(
                        f"Warmed {destination} pattern (guests={pattern['guest_count']}, "
                        f"days_ahead={pattern['days_ahead']}): {len(response.hotels)} results in {search_time_ms}ms"
                    )

                    # Small delay between pattern requests to avoid overwhelming APIs
                    await asyncio.sleep(0.1)

                except Exception as e:
                    error_msg = f"Failed to warm pattern {pattern} for {destination}: {e}"
                    self.logger.warning(error_msg)
                    result["errors"].append(error_msg)

            return result

    async def schedule_periodic_warming(self, interval_hours: int = 6) -> None:
        """Schedule periodic cache warming.

        Args:
            interval_hours: Hours between warming cycles
        """
        self.logger.info(f"Starting periodic cache warming every {interval_hours} hours")

        while True:
            try:
                # Warm popular destinations
                await self.warm_popular_destinations()

                # Clean up outdated cache entries
                hotel_agent = await self.get_hotel_agent()
                invalidated = await hotel_agent.invalidate_outdated_cache(max_age_minutes=45)
                if invalidated > 0:
                    self.logger.info(f"Cleaned up {invalidated} outdated cache entries")

                # Wait for next cycle
                await asyncio.sleep(interval_hours * 3600)

            except asyncio.CancelledError:
                self.logger.info("Periodic cache warming cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in periodic cache warming: {e}")
                # Wait shorter time on error before retry
                await asyncio.sleep(600)  # 10 minutes

    async def warm_user_search_history(
        self, recent_searches: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Warm cache based on recent user search patterns.

        Args:
            recent_searches: List of recent search requests to warm cache for

        Returns:
            Warming results summary
        """
        self.logger.info(f"Warming cache for {len(recent_searches)} recent user searches")

        results = {
            "searches_warmed": 0,
            "cache_entries": 0,
            "errors": [],
        }

        hotel_agent = await self.get_hotel_agent()

        for search in recent_searches:
            try:
                # Create similar search for future dates (people often search for similar trips)
                future_search = search.copy()

                # Adjust dates to near future
                if "check_in_date" in search:
                    try:
                        original_date = datetime.fromisoformat(search["check_in_date"])
                        # Create searches for 1-4 weeks in the future
                        for weeks_ahead in [1, 2, 4]:
                            future_date = original_date + timedelta(weeks=weeks_ahead)
                            future_search["check_in_date"] = future_date.date().isoformat()

                            if "check_out_date" in search:
                                original_checkout = datetime.fromisoformat(search["check_out_date"])
                                stay_duration = original_checkout - original_date
                                future_checkout = future_date + stay_duration
                                future_search["check_out_date"] = future_checkout.date().isoformat()

                            # Execute search to warm cache
                            response = await hotel_agent.process(future_search)
                            results["cache_entries"] += len(response.hotels)

                    except (ValueError, KeyError) as e:
                        self.logger.warning(f"Could not parse dates in search: {e}")
                        continue

                results["searches_warmed"] += 1

            except Exception as e:
                error_msg = f"Failed to warm cache for search {search}: {e}"
                self.logger.warning(error_msg)
                results["errors"].append(error_msg)

        return results

    async def get_warming_statistics(self) -> dict[str, Any]:
        """Get cache warming statistics.

        Returns:
            Dictionary with warming statistics
        """
        try:
            redis_manager = get_redis_manager()
            hotel_agent = await self.get_hotel_agent()

            # Get general cache statistics
            cache_stats = await hotel_agent.get_cache_statistics()

            # Add warming-specific statistics
            warming_stats = {
                "popular_destinations_count": len(self.POPULAR_DESTINATIONS),
                "search_patterns_count": len(self.COMMON_SEARCH_PATTERNS),
                "last_warming_time": None,  # Could be stored in Redis
                "next_scheduled_warming": None,  # Could be calculated
                "cache_hit_rate": None,  # Would need tracking over time
            }

            # Try to get last warming metadata
            try:
                last_warming = await redis_manager.get("cache_warming:last_run", json_decode=True)
                if last_warming:
                    warming_stats["last_warming_time"] = last_warming.get("completed_at")
            except Exception:
                pass

            return {
                **cache_stats,
                "warming_stats": warming_stats,
            }

        except Exception as e:
            self.logger.error(f"Failed to get warming statistics: {e}")
            return {"error": str(e)}


# Singleton instance for application-wide use
_cache_warming_service: CacheWarmingService | None = None


def get_cache_warming_service() -> CacheWarmingService:
    """Get singleton cache warming service instance."""
    global _cache_warming_service
    if _cache_warming_service is None:
        _cache_warming_service = CacheWarmingService()
    return _cache_warming_service

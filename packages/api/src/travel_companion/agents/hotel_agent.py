"""Hotel Agent for accommodation search and booking services."""

from typing import Any

from travel_companion.agents.base import BaseAgent
from travel_companion.core.config import Settings
from travel_companion.core.database import DatabaseManager
from travel_companion.core.redis import RedisManager
from travel_companion.models.external import HotelSearchResponse


class HotelAgent(BaseAgent[HotelSearchResponse]):
    """Hotel agent for finding and comparing accommodation options."""

    def __init__(
        self,
        settings: Settings | None = None,
        database: DatabaseManager | None = None,
        redis: RedisManager | None = None,
    ) -> None:
        """Initialize hotel agent with hotel-specific configurations.

        Args:
            settings: Application settings instance
            database: Database manager instance
            redis: Redis manager instance
        """
        super().__init__(settings, database, redis)

        # Hotel-specific configuration
        self.cache_ttl_seconds = getattr(
            self.settings, 'hotel_cache_ttl_seconds', 1800
        )  # 30 minutes default
        self.max_results_per_request = getattr(
            self.settings, 'hotel_max_results', 100
        )
        self.timeout_seconds = getattr(
            self.settings, 'hotel_api_timeout_seconds', 30
        )

        self.logger.info(
            f"Hotel agent initialized with cache_ttl={self.cache_ttl_seconds}s, "
            f"max_results={self.max_results_per_request}, "
            f"timeout={self.timeout_seconds}s"
        )

    @property
    def agent_name(self) -> str:
        """Name of the hotel agent."""
        return "hotel_agent"

    @property
    def agent_version(self) -> str:
        """Version of the hotel agent."""
        return "1.0.0"

    async def process(self, request_data: dict[str, Any]) -> HotelSearchResponse:
        """Process hotel search request and return results.

        Args:
            request_data: Hotel search request data containing location,
                         check-in/out dates, guest count, and budget filters

        Returns:
            HotelSearchResponse with found accommodation options

        Raises:
            ValueError: For invalid request data
            TimeoutError: For API timeout scenarios
        """
        self.logger.info(f"Processing hotel search request: {request_data}")

        # Validate request data
        if not request_data:
            raise ValueError("Hotel search request data cannot be empty")

        # Required fields validation
        required_fields = ['location', 'check_in_date', 'check_out_date', 'guest_count']
        missing_fields = [field for field in required_fields if field not in request_data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        # Generate cache key
        cache_key = await self._cache_key(request_data)

        # Try to get cached result
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            self.logger.info("Returning cached hotel search results")
            # Convert dict back to HotelSearchResponse if needed
            if isinstance(cached_result, dict):
                return HotelSearchResponse(**cached_result)
            return cached_result

        # Process new search request
        try:
            search_response = await self._search_hotels(request_data)

            # Cache the result
            await self._set_cached_result(
                cache_key,
                search_response.model_dump(),
                expire_seconds=self.cache_ttl_seconds
            )

            self.logger.info(
                f"Hotel search completed: found {len(search_response.hotels)} options"
            )
            return search_response

        except Exception as e:
            self.logger.error(f"Hotel search failed: {e}")
            raise

    async def _search_hotels(self, request_data: dict[str, Any]) -> HotelSearchResponse:
        """Execute hotel search logic.

        Args:
            request_data: Validated search request data

        Returns:
            HotelSearchResponse with search results
        """
        # Placeholder implementation - will be implemented with actual API integration
        self.logger.warning("Hotel search not yet implemented - returning empty results")

        return HotelSearchResponse(
            hotels=[],
            search_metadata={
                "location": request_data.get("location"),
                "check_in_date": request_data.get("check_in_date"),
                "check_out_date": request_data.get("check_out_date"),
                "guest_count": request_data.get("guest_count"),
                "budget": request_data.get("budget"),
                "max_results": request_data.get("max_results"),
            },
            total_results=0,
            search_time_ms=0,
            cached=False,
        )

    async def search_hotels_by_location(
        self,
        location: str,
        check_in_date: str,
        check_out_date: str,
        guest_count: int,
        budget: float | None = None,
        max_results: int | None = None
    ) -> HotelSearchResponse:
        """Search hotels by location with date and guest filters.

        Args:
            location: Hotel search location (city, address, or coordinates)
            check_in_date: Check-in date in ISO format
            check_out_date: Check-out date in ISO format
            guest_count: Number of guests
            budget: Optional budget filter per night
            max_results: Maximum number of results to return

        Returns:
            HotelSearchResponse with filtered results
        """
        request_data = {
            "location": location,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "guest_count": guest_count,
        }

        if budget is not None:
            request_data["budget"] = budget

        if max_results is not None:
            request_data["max_results"] = min(max_results, self.max_results_per_request)
        else:
            request_data["max_results"] = self.max_results_per_request

        return await self.process(request_data)

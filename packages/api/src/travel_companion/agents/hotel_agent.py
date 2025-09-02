"""Hotel Agent for accommodation search and booking services."""

import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from travel_companion.agents.base import BaseAgent
from travel_companion.core.config import Settings
from travel_companion.core.database import DatabaseManager
from travel_companion.core.redis import RedisManager
from travel_companion.models.external import (
    HotelLocation,
    HotelOption,
    HotelSearchRequest,
    HotelSearchResponse,
)
from travel_companion.services.external_apis.booking import (
    BookingClient,
    HotelSearchParams,
)


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

        # Initialize Booking.com API client
        self._booking_client = BookingClient(timeout=self.timeout_seconds)

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
        start_time = time.time()

        # Validate and parse search request
        try:
            # Convert string dates to datetime objects if needed
            check_in_date = request_data.get("check_in_date")
            check_out_date = request_data.get("check_out_date")

            if isinstance(check_in_date, str):
                check_in_date = datetime.fromisoformat(check_in_date)
            if isinstance(check_out_date, str):
                check_out_date = datetime.fromisoformat(check_out_date)

            # Create HotelSearchRequest for validation
            search_request = HotelSearchRequest(
                location=request_data["location"],
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                guest_count=request_data["guest_count"],
                room_count=request_data.get("room_count", 1),
                budget_per_night=Decimal(str(request_data["budget"])) if request_data.get("budget") else None,
                currency=request_data.get("currency", "USD"),
                max_results=min(
                    request_data.get("max_results", self.max_results_per_request),
                    self.max_results_per_request
                )
            )

        except (ValueError, KeyError) as e:
            self.logger.error(f"Invalid hotel search request: {e}")
            raise ValueError(f"Invalid search parameters: {e}") from e

        self.logger.info(
            f"Executing hotel search: location={search_request.location}, "
            f"check_in={search_request.check_in_date.date()}, "
            f"check_out={search_request.check_out_date.date()}, "
            f"guests={search_request.guest_count}, "
            f"rooms={search_request.room_count}"
        )

        try:
            # Create Booking.com API search parameters
            booking_params = HotelSearchParams(
                location=search_request.location,
                check_in=search_request.check_in_date.strftime("%Y-%m-%d"),
                check_out=search_request.check_out_date.strftime("%Y-%m-%d"),
                guest_count=search_request.guest_count,
                room_count=search_request.room_count,
                max_results=search_request.max_results,
                currency=search_request.currency,
                language="en"
            )

            # Search hotels via Booking.com API
            booking_response = await self._booking_client.search_hotels(booking_params)

            # Convert Booking.com results to internal HotelOption models
            hotels = []
            for booking_hotel in booking_response.hotels:
                try:
                    # Apply budget filter if specified
                    if (search_request.budget_per_night and
                        Decimal(str(booking_hotel.price_per_night)) > search_request.budget_per_night):
                        continue

                    hotel_location = HotelLocation(
                        latitude=booking_hotel.latitude or 0.0,
                        longitude=booking_hotel.longitude or 0.0,
                        address=booking_hotel.address,
                        city=None,  # Extract from address if needed
                        country=None,  # Extract from address if needed
                        postal_code=None
                    )

                    hotel_option = HotelOption(
                        external_id=booking_hotel.hotel_id,
                        name=booking_hotel.name,
                        location=hotel_location,
                        price_per_night=Decimal(str(booking_hotel.price_per_night)),
                        currency=booking_hotel.currency,
                        rating=booking_hotel.rating,
                        amenities=booking_hotel.amenities,
                        photos=booking_hotel.photos,
                        booking_url=booking_hotel.booking_url,
                        created_at=datetime.now(UTC)
                    )
                    hotels.append(hotel_option)

                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Failed to convert hotel result: {e}")
                    continue

            # Calculate search time
            end_time = time.time()
            search_time_ms = int((end_time - start_time) * 1000)

            # Create response with search metadata
            response = HotelSearchResponse(
                hotels=hotels,
                search_metadata={
                    "location": search_request.location,
                    "check_in_date": search_request.check_in_date.isoformat(),
                    "check_out_date": search_request.check_out_date.isoformat(),
                    "guest_count": search_request.guest_count,
                    "room_count": search_request.room_count,
                    "budget_per_night": float(search_request.budget_per_night) if search_request.budget_per_night else None,
                    "currency": search_request.currency,
                    "max_results": search_request.max_results,
                    "booking_api_response_time": booking_response.api_response_time_ms
                },
                total_results=booking_response.total_results,
                search_time_ms=search_time_ms,
                cached=False
            )

            self.logger.info(
                f"Hotel search completed: found {len(hotels)} hotels "
                f"(filtered from {booking_response.total_results} total) in {search_time_ms}ms"
            )

            return response

        except Exception as e:
            self.logger.error(f"Hotel search failed: {e}")
            # Return empty results on error to maintain consistency
            end_time = time.time()
            search_time_ms = int((end_time - start_time) * 1000)

            return HotelSearchResponse(
                hotels=[],
                search_metadata={
                    "location": request_data.get("location"),
                    "check_in_date": request_data.get("check_in_date"),
                    "check_out_date": request_data.get("check_out_date"),
                    "guest_count": request_data.get("guest_count"),
                    "error": str(e)
                },
                total_results=0,
                search_time_ms=search_time_ms,
                cached=False
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

"""Hotel Agent for accommodation search and booking services."""

import math
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from travel_companion.agents.base import BaseAgent
from travel_companion.core.config import Settings
from travel_companion.core.database import DatabaseManager
from travel_companion.core.redis import RedisManager
from travel_companion.models.external import (
    HotelComparisonResult,
    HotelLocation,
    HotelOption,
    HotelSearchRequest,
    HotelSearchResponse,
)
from travel_companion.services.cache import CacheManager
from travel_companion.services.external_apis.airbnb import (
    AirbnbClient,
    AirbnbSearchParams,
)
from travel_companion.services.external_apis.booking import (
    BookingClient,
    HotelSearchParams,
)
from travel_companion.services.external_apis.expedia import (
    ExpediaClient,
    ExpediaSearchParams,
)
from travel_companion.services.external_apis.geoapify import GeoapifyClient
from travel_companion.services.external_apis.liteapi import (
    LiteAPIClient,
    LiteAPIHotelSearchRequest,
    LiteAPIMinRatesRequest,
    LiteAPIOccupancy,
    LiteAPIRatesRequest,
    LiteAPIStay,
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
            self.settings, "hotel_cache_ttl_seconds", 1800
        )  # 30 minutes default
        self.max_results_per_request = getattr(self.settings, "hotel_max_results", 100)
        self.timeout_seconds = getattr(self.settings, "hotel_api_timeout_seconds", 30)

        # Initialize API clients with fallback chain
        self._booking_client = BookingClient(timeout=self.timeout_seconds)
        self._expedia_client = ExpediaClient()
        self._airbnb_client = AirbnbClient()

        # Initialize new API clients
        self._geoapify_client = GeoapifyClient()
        self._liteapi_client = LiteAPIClient(timeout=self.timeout_seconds)

        # Initialize enhanced cache manager
        self._cache_manager = CacheManager(self.redis)

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
        required_fields = ["location", "check_in_date", "check_out_date", "guest_count"]
        missing_fields = [field for field in required_fields if field not in request_data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        # Generate cache key
        cache_key = await self._cache_key(request_data)

        # Try to get cached result using enhanced cache manager
        cached_result = await self._cache_manager.get_hotel_search_cache(cache_key)
        if cached_result:
            self.logger.info("Returning cached hotel search results")
            return cached_result

        # Process new search request
        try:
            search_response = await self._search_hotels(request_data)

            # Cache the result using enhanced cache manager
            await self._cache_manager.set_hotel_search_cache(
                cache_key, search_response, ttl_seconds=self.cache_ttl_seconds
            )

            self.logger.info(f"Hotel search completed: found {len(search_response.hotels)} options")
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
            check_in_raw = request_data.get("check_in_date")
            check_out_raw = request_data.get("check_out_date")

            if isinstance(check_in_raw, str):
                check_in_date = datetime.fromisoformat(check_in_raw)
            elif isinstance(check_in_raw, datetime):
                check_in_date = check_in_raw
            else:
                raise ValueError("Invalid check_in_date format")

            if isinstance(check_out_raw, str):
                check_out_date = datetime.fromisoformat(check_out_raw)
            elif isinstance(check_out_raw, datetime):
                check_out_date = check_out_raw
            else:
                raise ValueError("Invalid check_out_date format")

            # Create HotelSearchRequest for validation
            search_request = HotelSearchRequest(
                location=request_data["location"],
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                guest_count=request_data["guest_count"],
                room_count=request_data.get("room_count", 1),
                budget_per_night=Decimal(str(request_data["budget"]))
                if request_data.get("budget")
                else None,
                currency=request_data.get("currency", "USD"),
                max_results=min(
                    request_data.get("max_results", self.max_results_per_request),
                    self.max_results_per_request,
                ),
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

        # Implement API fallback chain: Booking.com → Expedia → Airbnb
        hotels: list[HotelOption] = []
        search_metadata: dict[str, Any] = {
            "location": search_request.location,
            "check_in_date": search_request.check_in_date.isoformat(),
            "check_out_date": search_request.check_out_date.isoformat(),
            "guest_count": search_request.guest_count,
            "room_count": search_request.room_count,
            "budget_per_night": float(search_request.budget_per_night)
            if search_request.budget_per_night
            else None,
            "currency": search_request.currency,
            "max_results": search_request.max_results,
            "apis_attempted": [],
            "successful_api": None,
            "api_errors": {},
        }

        # Try Booking.com first
        try:
            self.logger.info("Attempting Booking.com API search")
            search_metadata["apis_attempted"].append("booking.com")

            booking_params = HotelSearchParams(
                location=search_request.location,
                check_in=search_request.check_in_date.strftime("%Y-%m-%d"),
                check_out=search_request.check_out_date.strftime("%Y-%m-%d"),
                guest_count=search_request.guest_count,
                room_count=search_request.room_count,
                max_results=search_request.max_results,
                currency=search_request.currency,
                language="en",
            )

            booking_response = await self._booking_client.search_hotels(booking_params)

            # Convert Booking.com results to internal HotelOption models
            for booking_hotel in booking_response.hotels:
                try:
                    # Apply budget filter if specified
                    if (
                        search_request.budget_per_night
                        and booking_hotel.price_per_night
                        and Decimal(str(booking_hotel.price_per_night))
                        > search_request.budget_per_night
                    ):
                        continue

                    hotel_location = HotelLocation(
                        latitude=booking_hotel.latitude or 0.0,
                        longitude=booking_hotel.longitude or 0.0,
                        address=booking_hotel.address,
                        city=None,  # Extract from address if needed
                        country=None,  # Extract from address if needed
                        postal_code=None,
                    )

                    hotel_option = HotelOption(
                        trip_id=None,
                        external_id=f"booking_{booking_hotel.hotel_id}",
                        name=booking_hotel.name,
                        location=hotel_location,
                        price_per_night=Decimal(str(booking_hotel.price_per_night))
                        if booking_hotel.price_per_night
                        else Decimal("0"),
                        currency=booking_hotel.currency,
                        rating=booking_hotel.rating,
                        amenities=booking_hotel.amenities,
                        photos=booking_hotel.photos,
                        booking_url=booking_hotel.booking_url,
                        created_at=datetime.now(UTC),
                    )
                    hotels.append(hotel_option)

                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Failed to convert Booking.com hotel result: {e}")
                    continue

            search_metadata["successful_api"] = "booking.com"
            search_metadata["booking_api_response_time"] = booking_response.api_response_time_ms
            search_metadata["booking_total_results"] = booking_response.total_results
            self.logger.info(f"Booking.com API returned {len(hotels)} hotels")

        except Exception as e:
            self.logger.warning(f"Booking.com API failed: {e}")
            search_metadata["api_errors"]["booking.com"] = str(e)

            # Try Expedia as fallback
            try:
                self.logger.info("Attempting Expedia API search (fallback)")
                search_metadata["apis_attempted"].append("expedia")

                expedia_params = ExpediaSearchParams(
                    location=search_request.location,
                    check_in=search_request.check_in_date.strftime("%Y-%m-%d"),
                    check_out=search_request.check_out_date.strftime("%Y-%m-%d"),
                    guest_count=search_request.guest_count,
                    room_count=search_request.room_count,
                    max_results=search_request.max_results,
                    currency=search_request.currency,
                    language="en",
                )

                expedia_results = await self._expedia_client.search_hotels(expedia_params)

                # Convert Expedia results to internal HotelOption models
                for expedia_hotel in expedia_results:
                    try:
                        # Apply budget filter if specified
                        if (
                            search_request.budget_per_night
                            and expedia_hotel.price_per_night
                            and Decimal(str(expedia_hotel.price_per_night))
                            > search_request.budget_per_night
                        ):
                            continue

                        hotel_location = HotelLocation(
                            latitude=expedia_hotel.latitude or 0.0,
                            longitude=expedia_hotel.longitude or 0.0,
                            address=expedia_hotel.address,
                            city=None,  # Extract from address if needed
                            country=None,  # Extract from address if needed
                            postal_code=None,
                        )

                        hotel_option = HotelOption(
                            trip_id=None,
                            external_id=f"expedia_{expedia_hotel.hotel_id}",
                            name=expedia_hotel.name,
                            location=hotel_location,
                            price_per_night=Decimal(str(expedia_hotel.price_per_night))
                            if expedia_hotel.price_per_night
                            else Decimal("0"),
                            currency=expedia_hotel.currency,
                            rating=expedia_hotel.rating,
                            amenities=expedia_hotel.amenities,
                            photos=expedia_hotel.photos,
                            booking_url=expedia_hotel.booking_url,
                            created_at=datetime.now(UTC),
                        )
                        hotels.append(hotel_option)

                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Failed to convert Expedia hotel result: {e}")
                        continue

                search_metadata["successful_api"] = "expedia"
                search_metadata["expedia_total_results"] = len(expedia_results)
                self.logger.info(f"Expedia API returned {len(hotels)} hotels")

            except Exception as e:
                self.logger.warning(f"Expedia API failed: {e}")
                search_metadata["api_errors"]["expedia"] = str(e)

                # Try Airbnb as final fallback
                try:
                    self.logger.info("Attempting Airbnb API search (final fallback)")
                    search_metadata["apis_attempted"].append("airbnb")

                    airbnb_params = AirbnbSearchParams(
                        location=search_request.location,
                        check_in=search_request.check_in_date.strftime("%Y-%m-%d"),
                        check_out=search_request.check_out_date.strftime("%Y-%m-%d"),
                        guest_count=search_request.guest_count,
                        max_results=search_request.max_results,
                        currency=search_request.currency,
                        language="en",
                        property_type=None,
                        min_price=None,
                        max_price=float(search_request.budget_per_night)
                        if search_request.budget_per_night
                        else None,
                    )

                    airbnb_results = await self._airbnb_client.search_listings(airbnb_params)

                    # Convert Airbnb results to internal HotelOption models
                    for airbnb_listing in airbnb_results:
                        try:
                            hotel_location = HotelLocation(
                                latitude=airbnb_listing.latitude or 0.0,
                                longitude=airbnb_listing.longitude or 0.0,
                                address=airbnb_listing.address,
                                city=None,  # Extract from address if needed
                                country=None,  # Extract from address if needed
                                postal_code=None,
                            )

                            hotel_option = HotelOption(
                                trip_id=None,
                                external_id=f"airbnb_{airbnb_listing.listing_id}",
                                name=airbnb_listing.name,
                                location=hotel_location,
                                price_per_night=Decimal(str(airbnb_listing.price_per_night))
                                if airbnb_listing.price_per_night
                                else Decimal("0"),
                                currency=airbnb_listing.currency,
                                rating=airbnb_listing.rating,
                                amenities=airbnb_listing.amenities,
                                photos=airbnb_listing.photos,
                                booking_url=airbnb_listing.booking_url,
                                created_at=datetime.now(UTC),
                            )
                            hotels.append(hotel_option)

                        except (ValueError, TypeError) as e:
                            self.logger.warning(f"Failed to convert Airbnb listing result: {e}")
                            continue

                    search_metadata["successful_api"] = "airbnb"
                    search_metadata["airbnb_total_results"] = len(airbnb_results)
                    self.logger.info(f"Airbnb API returned {len(hotels)} hotels")

                except Exception as e:
                    self.logger.error(f"All APIs failed. Last error (Airbnb): {e}")
                    search_metadata["api_errors"]["airbnb"] = str(e)

        # Calculate search time
        end_time = time.time()
        search_time_ms = int((end_time - start_time) * 1000)

        # Create response with search metadata
        response = HotelSearchResponse(
            hotels=hotels,
            search_metadata=search_metadata,
            total_results=len(hotels),
            search_time_ms=search_time_ms,
            cached=False,
            cache_expires_at=None,
        )

        self.logger.info(
            f"Hotel search completed using {search_metadata['successful_api'] or 'no APIs'}: "
            f"found {len(hotels)} hotels in {search_time_ms}ms"
        )

        return response

    async def search_hotels_by_location(
        self,
        location: str,
        check_in_date: str,
        check_out_date: str,
        guest_count: int,
        budget: float | None = None,
        max_results: int | None = None,
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

    async def search_hotels_with_rates(
        self,
        location: str,
        check_in_date: str,
        check_out_date: str,
        guest_count: int,
        room_count: int = 1,
        budget_per_night: float | None = None,
        max_results: int = 20,
        get_full_rates: bool = False,
    ) -> HotelSearchResponse:
        """
        Enhanced hotel search using Geoapify + LiteAPI integration.

        First gets hotel list from Geoapify, then fetches rates from LiteAPI.

        Args:
            location: Search location (city, address, etc.)
            check_in_date: Check-in date in ISO format (YYYY-MM-DD)
            check_out_date: Check-out date in ISO format (YYYY-MM-DD)
            guest_count: Number of guests
            room_count: Number of rooms needed
            budget_per_night: Optional budget filter per night
            max_results: Maximum number of results
            get_full_rates: Whether to get detailed rates or just minimum rates

        Returns:
            HotelSearchResponse with hotels and pricing from LiteAPI
        """
        start_time = time.time()

        try:
            # Step 1: Get hotels from Geoapify
            self.logger.info(f"Searching hotels in {location} via Geoapify")
            geoapify_hotels = await self._geoapify_client.search_hotels(
                location=location,
                max_results=max_results * 2,  # Get more to account for LiteAPI filtering
            )

            if not geoapify_hotels:
                self.logger.warning("No hotels found via Geoapify")
                return HotelSearchResponse(
                    hotels=[],
                    search_metadata={
                        "provider": "geoapify_liteapi",
                        "location": location,
                        "error": "No hotels found in location",
                    },
                    total_results=0,
                    search_time_ms=int((time.time() - start_time) * 1000),
                    cached=False,
                    cache_expires_at=None,
                )

            self.logger.info(f"Found {len(geoapify_hotels)} hotels from Geoapify")

            # Step 2: Get LiteAPI hotel IDs for the same location
            # Use first hotel coordinates as search center
            center_hotel = geoapify_hotels[0]
            liteapi_search = LiteAPIHotelSearchRequest(
                latitude=center_hotel["latitude"],
                longitude=center_hotel["longitude"],
                radius=5000,  # 5km radius
                limit=100,
            )

            liteapi_hotels_data = await self._liteapi_client.search_hotels_by_geo(liteapi_search)

            if not liteapi_hotels_data:
                self.logger.warning("No hotels found in LiteAPI for the location")
                # Return Geoapify results without rates as fallback
                return await self._create_fallback_response(geoapify_hotels, location, start_time)

            # Extract LiteAPI hotel IDs
            liteapi_hotel_ids = [
                hotel.get("id") for hotel in liteapi_hotels_data if hotel.get("id")
            ][:max_results]  # Limit to requested count

            if not liteapi_hotel_ids:
                self.logger.warning("No valid LiteAPI hotel IDs found")
                return await self._create_fallback_response(geoapify_hotels, location, start_time)

            self.logger.info(f"Found {len(liteapi_hotel_ids)} LiteAPI hotel IDs")

            # Step 3: Get rates from LiteAPI
            stay = LiteAPIStay(check_in=check_in_date, check_out=check_out_date)
            occupancies = [LiteAPIOccupancy(rooms=room_count, adults=guest_count, children=0)]

            if get_full_rates:
                rates_request = LiteAPIRatesRequest(
                    stay=stay,
                    occupancies=occupancies,
                    hotel_ids=[id for id in liteapi_hotel_ids if id is not None],
                    currency="USD",
                )
                rates_data = await self._liteapi_client.get_full_rates(rates_request)
            else:
                min_rates_request = LiteAPIMinRatesRequest(
                    stay=stay,
                    occupancies=occupancies,
                    hotel_ids=[id for id in liteapi_hotel_ids if id is not None],
                )
                rates_data = await self._liteapi_client.get_min_rates(min_rates_request)

            # Step 4: Combine data and create HotelOption objects
            hotels = await self._combine_geoapify_liteapi_data(
                geoapify_hotels, liteapi_hotels_data, rates_data, budget_per_night
            )

            # Filter by budget if specified
            if budget_per_night:
                hotels = [
                    hotel
                    for hotel in hotels
                    if hotel.price_per_night <= Decimal(str(budget_per_night))
                ]

            # Limit results
            hotels = hotels[:max_results]

            search_time_ms = int((time.time() - start_time) * 1000)

            return HotelSearchResponse(
                hotels=hotels,
                search_metadata={
                    "provider": "geoapify_liteapi",
                    "location": location,
                    "check_in_date": check_in_date,
                    "check_out_date": check_out_date,
                    "guest_count": guest_count,
                    "room_count": room_count,
                    "geoapify_results": len(geoapify_hotels),
                    "liteapi_hotel_count": len(liteapi_hotel_ids),
                    "final_results": len(hotels),
                    "rate_type": "full" if get_full_rates else "minimum",
                },
                total_results=len(hotels),
                search_time_ms=search_time_ms,
                cached=False,
                cache_expires_at=None,
            )

        except Exception as e:
            self.logger.error(f"Enhanced hotel search failed: {e}")
            # Fallback to original search method
            self.logger.info("Falling back to original hotel search method")
            return await self.search_hotels_by_location(
                location=location,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                guest_count=guest_count,
                budget=budget_per_night,
                max_results=max_results,
            )

    async def _create_fallback_response(
        self, geoapify_hotels: list[dict[str, Any]], location: str, start_time: float
    ) -> HotelSearchResponse:
        """Create fallback response with Geoapify data only."""
        hotels = []
        for hotel_data in geoapify_hotels:
            hotel_location = HotelLocation(
                latitude=hotel_data["latitude"],
                longitude=hotel_data["longitude"],
                address=hotel_data.get("address"),
                city=hotel_data.get("city"),
                country=hotel_data.get("country"),
                postal_code=None,
            )

            hotel = HotelOption(
                external_id=f"geoapify_{hotel_data.get('place_id', '')}",
                name=hotel_data["name"],
                location=hotel_location,
                price_per_night=Decimal("0.01"),  # Minimum valid price for fallback
                currency="USD",
                rating=None,
                amenities=[],
                photos=[],
                booking_url=None,
                trip_id=None,
                created_at=datetime.now(UTC),
            )
            hotels.append(hotel)

        return HotelSearchResponse(
            hotels=hotels,
            search_metadata={
                "provider": "geoapify_fallback",
                "location": location,
                "note": "Pricing unavailable - using location data only",
            },
            total_results=len(hotels),
            search_time_ms=int((time.time() - start_time) * 1000),
            cached=False,
            cache_expires_at=None,
        )

    async def _combine_geoapify_liteapi_data(
        self,
        geoapify_hotels: list[dict[str, Any]],
        liteapi_hotels: list[dict[str, Any]],
        rates_data: dict[str, Any],
        budget_filter: float | None = None,
    ) -> list[HotelOption]:
        """Combine Geoapify location data with LiteAPI rates."""
        hotels = []

        # Get rates from response
        hotel_rates = {}
        if rates_data and "data" in rates_data:
            for hotel_data in rates_data["data"]:
                hotel_id = hotel_data.get("hotel_id")
                if hotel_id:
                    # Extract minimum rate
                    min_rate = None
                    if "rates" in hotel_data and hotel_data["rates"]:
                        # Find cheapest rate
                        rates = hotel_data["rates"]
                        if rates:
                            min_rate = min(
                                float(rate.get("total_amount", 0))
                                for rate in rates
                                if rate.get("total_amount")
                            )

                    hotel_rates[hotel_id] = {
                        "min_rate": min_rate,
                        "hotel_data": hotel_data,
                    }

        # Create LiteAPI hotel lookup by approximate location
        liteapi_by_location = {}
        for liteapi_hotel in liteapi_hotels:
            if "latitude" in liteapi_hotel and "longitude" in liteapi_hotel:
                # Round coordinates for matching
                lat_key = round(liteapi_hotel["latitude"], 3)
                lon_key = round(liteapi_hotel["longitude"], 3)
                location_key = (lat_key, lon_key)
                liteapi_by_location[location_key] = liteapi_hotel

        # Match Geoapify hotels with LiteAPI data
        for geo_hotel in geoapify_hotels:
            # Find matching LiteAPI hotel by proximity
            geo_lat = round(geo_hotel["latitude"], 3)
            geo_lon = round(geo_hotel["longitude"], 3)
            location_key = (geo_lat, geo_lon)

            matched_liteapi_hotel = liteapi_by_location.get(location_key)
            if not matched_liteapi_hotel:
                # Try finding closest match within small radius
                for (lat, lon), lite_hotel in liteapi_by_location.items():
                    distance = abs(lat - geo_lat) + abs(lon - geo_lon)  # Manhattan distance
                    if distance < 0.01:  # ~1km tolerance
                        matched_liteapi_hotel = lite_hotel
                        break

            # Get rate data
            rate_info = None
            if matched_liteapi_hotel and matched_liteapi_hotel.get("id"):
                rate_info = hotel_rates.get(matched_liteapi_hotel["id"])

            # Apply budget filter early if we have rate data
            min_rate = rate_info.get("min_rate") if rate_info else None
            if budget_filter and min_rate and min_rate > budget_filter:
                continue

            # Create hotel location
            hotel_location = HotelLocation(
                latitude=geo_hotel["latitude"],
                longitude=geo_hotel["longitude"],
                address=geo_hotel.get("address"),
                city=geo_hotel.get("city"),
                country=geo_hotel.get("country"),
                postal_code=None,
            )

            # Create hotel option
            hotel = HotelOption(
                external_id=(
                    f"liteapi_{matched_liteapi_hotel['id']}"
                    if matched_liteapi_hotel and matched_liteapi_hotel.get("id")
                    else f"geoapify_{geo_hotel.get('place_id', '')}"
                ),
                name=geo_hotel["name"],
                location=hotel_location,
                price_per_night=Decimal(str(min_rate)) if min_rate else Decimal("0.01"),
                currency="USD",
                rating=None,  # LiteAPI might provide this
                amenities=[],  # Could be enriched from LiteAPI
                photos=[],
                booking_url=None,
                trip_id=None,
                created_at=datetime.now(UTC),
            )
            hotels.append(hotel)

        return hotels

    def _calculate_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula.

        Args:
            lat1, lon1: First coordinate pair (latitude, longitude)
            lat2, lon2: Second coordinate pair (latitude, longitude)

        Returns:
            Distance in kilometers
        """
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        # Radius of earth in kilometers
        r = 6371
        return c * r

    def _parse_location_coordinates(self, location: str) -> tuple[float, float] | None:
        """Parse coordinates from location string if available.

        Args:
            location: Location string, may contain coordinates

        Returns:
            (latitude, longitude) tuple if found, None otherwise
        """
        try:
            # Simple coordinate parsing - look for "lat,lon" pattern
            parts = location.replace(" ", "").split(",")
            if len(parts) == 2:
                lat = float(parts[0])
                lon = float(parts[1])
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lat, lon)
        except (ValueError, IndexError):
            pass
        return None

    def _calculate_hotel_ranking_score(
        self,
        hotel: HotelOption,
        search_center: tuple[float, float] | None = None,
        preferences: dict[str, float] | None = None,
    ) -> tuple[float, list[str]]:
        """Calculate ranking score for a hotel based on multiple factors.

        Args:
            hotel: Hotel option to score
            search_center: (latitude, longitude) of search location for proximity scoring
            preferences: Weighting preferences for different factors

        Returns:
            (score, reasons) tuple where score is 0-100 and reasons explain the ranking
        """
        if preferences is None:
            preferences = {
                "price_weight": 0.3,  # 30% weight on price competitiveness
                "rating_weight": 0.4,  # 40% weight on hotel rating
                "location_weight": 0.2,  # 20% weight on location proximity
                "amenities_weight": 0.1,  # 10% weight on amenities count
            }

        scores = {}
        reasons = []

        # Price competitiveness score (lower price = higher score)
        if hotel.price_per_night:
            # Normalize price against a reasonable range (e.g., $50-500 per night)
            min_price = Decimal("50")
            max_price = Decimal("500")
            normalized_price = min(max(hotel.price_per_night, min_price), max_price)
            price_score = float(1 - (normalized_price - min_price) / (max_price - min_price))
            scores["price"] = price_score * 100
            reasons.append(f"Price ${hotel.price_per_night}/night")
        else:
            scores["price"] = 50  # Neutral score if no price available
            reasons.append("Price not available")

        # Rating score (1-5 stars normalized to 0-100)
        if hotel.rating:
            rating_score = (hotel.rating / 5.0) * 100
            scores["rating"] = rating_score
            reasons.append(f"Rating {hotel.rating:.1f}/5")
        else:
            scores["rating"] = 50  # Neutral score if no rating available
            reasons.append("Rating not available")

        # Location proximity score
        if search_center and hotel.location:
            distance_km = self._calculate_distance_km(
                search_center[0],
                search_center[1],
                hotel.location.latitude,
                hotel.location.longitude,
            )
            # Score decreases with distance (max useful distance ~50km)
            max_distance = 50.0
            proximity_score = (
                max(0, (max_distance - min(distance_km, max_distance)) / max_distance) * 100
            )
            scores["location"] = proximity_score
            reasons.append(f"Distance {distance_km:.1f}km")
        else:
            scores["location"] = 50  # Neutral score if no location data
            reasons.append("Location proximity unavailable")

        # Amenities score (more amenities = better score)
        amenity_count = len(hotel.amenities)
        # Normalize against typical amenity counts (0-20)
        max_amenities = 20
        amenities_score = min(amenity_count / max_amenities, 1.0) * 100
        scores["amenities"] = amenities_score
        reasons.append(f"{amenity_count} amenities")

        # Calculate weighted total score
        total_score = (
            scores["price"] * preferences["price_weight"]
            + scores["rating"] * preferences["rating_weight"]
            + scores["location"] * preferences["location_weight"]
            + scores["amenities"] * preferences["amenities_weight"]
        )

        return total_score, reasons

    def rank_hotels(
        self,
        hotels: list[HotelOption],
        search_location: str | None = None,
        preferences: dict[str, float] | None = None,
        budget_filter: Decimal | None = None,
        required_amenities: list[str] | None = None,
        max_distance_km: float | None = None,
    ) -> list[HotelComparisonResult]:
        """Rank and compare hotels based on multiple criteria.

        Args:
            hotels: List of hotel options to rank
            search_location: Original search location for proximity calculation
            preferences: Weighting preferences for ranking factors
            budget_filter: Maximum price per night filter
            required_amenities: List of required amenities to filter by
            max_distance_km: Maximum distance from search location in km

        Returns:
            List of HotelComparisonResult objects sorted by score (highest first)
        """
        if not hotels:
            return []

        # Parse search location coordinates if available
        search_center = None
        if search_location:
            search_center = self._parse_location_coordinates(search_location)

        # Apply filters
        filtered_hotels = []
        for hotel in hotels:
            # Budget filter
            if budget_filter and hotel.price_per_night > budget_filter:
                continue

            # Required amenities filter
            if required_amenities:
                hotel_amenities_lower = [amenity.lower() for amenity in hotel.amenities]
                if not all(req.lower() in hotel_amenities_lower for req in required_amenities):
                    continue

            # Distance filter
            if max_distance_km and search_center and hotel.location:
                distance = self._calculate_distance_km(
                    search_center[0],
                    search_center[1],
                    hotel.location.latitude,
                    hotel.location.longitude,
                )
                if distance > max_distance_km:
                    continue

            filtered_hotels.append(hotel)

        # Calculate scores and create comparison results
        comparison_results = []
        for hotel in filtered_hotels:
            score, reasons = self._calculate_hotel_ranking_score(hotel, search_center, preferences)

            comparison_results.append(
                HotelComparisonResult(
                    hotel=hotel,
                    score=score,
                    price_rank=1,  # Will be calculated after sorting
                    location_rank=1,  # Will be calculated after sorting
                    rating_rank=1,  # Will be calculated after sorting
                    value_score=0.0,  # Will be calculated after sorting
                    reasons=reasons,
                )
            )

        # Sort by score (highest first)
        comparison_results.sort(key=lambda x: x.score, reverse=True)

        # Calculate individual rankings
        self._calculate_individual_rankings(comparison_results, search_center)

        return comparison_results

    def _calculate_individual_rankings(
        self, results: list[HotelComparisonResult], search_center: tuple[float, float] | None
    ) -> None:
        """Calculate individual rankings for price, location, and rating.

        Args:
            results: List of comparison results to update rankings for
            search_center: Search location center for distance calculations
        """
        if not results:
            return

        # Price ranking (cheapest first)
        price_sorted = sorted(results, key=lambda x: x.hotel.price_per_night)
        for i, result in enumerate(price_sorted):
            result.price_rank = i + 1

        # Location ranking (closest first, if location data available)
        if search_center:
            location_sorted = sorted(
                results,
                key=lambda x: self._calculate_distance_km(
                    search_center[0],
                    search_center[1],
                    x.hotel.location.latitude,
                    x.hotel.location.longitude,
                )
                if x.hotel.location
                else float("inf"),
            )
            for i, result in enumerate(location_sorted):
                result.location_rank = i + 1
        else:
            # No location data, assign equal ranking
            for result in results:
                result.location_rank = 1

        # Rating ranking (highest first)
        rating_sorted = sorted(results, key=lambda x: x.hotel.rating or 0, reverse=True)
        for i, result in enumerate(rating_sorted):
            result.rating_rank = i + 1

        # Calculate value score (rating per dollar spent)
        for result in results:
            if result.hotel.rating and result.hotel.price_per_night:
                # Higher rating per dollar = better value
                value_score = float(result.hotel.rating) / float(result.hotel.price_per_night)
                # Normalize to 0-1 scale (typical range: 0.01 to 0.1)
                max_value = 0.1
                result.value_score = min(value_score / max_value, 1.0)
            else:
                result.value_score = 0.5  # Neutral score if data missing

    def filter_hotels_by_criteria(
        self,
        hotels: list[HotelOption],
        budget_max: Decimal | None = None,
        budget_min: Decimal | None = None,
        min_rating: float | None = None,
        required_amenities: list[str] | None = None,
        max_distance_km: float | None = None,
        search_location: str | None = None,
    ) -> list[HotelOption]:
        """Filter hotels by various criteria.

        Args:
            hotels: List of hotels to filter
            budget_max: Maximum price per night
            budget_min: Minimum price per night
            min_rating: Minimum hotel rating
            required_amenities: List of required amenities
            max_distance_km: Maximum distance from search location
            search_location: Search location for distance filtering

        Returns:
            Filtered list of hotels
        """
        if not hotels:
            return []

        search_center = None
        if search_location:
            search_center = self._parse_location_coordinates(search_location)

        filtered_hotels = []
        for hotel in hotels:
            # Budget filters
            if budget_max and hotel.price_per_night > budget_max:
                continue
            if budget_min and hotel.price_per_night < budget_min:
                continue

            # Rating filter
            if min_rating and (not hotel.rating or hotel.rating < min_rating):
                continue

            # Amenities filter
            if required_amenities:
                hotel_amenities_lower = [amenity.lower() for amenity in hotel.amenities]
                if not all(req.lower() in hotel_amenities_lower for req in required_amenities):
                    continue

            # Distance filter
            if max_distance_km and search_center and hotel.location:
                distance = self._calculate_distance_km(
                    search_center[0],
                    search_center[1],
                    hotel.location.latitude,
                    hotel.location.longitude,
                )
                if distance > max_distance_km:
                    continue

            filtered_hotels.append(hotel)

        return filtered_hotels

    def paginate_results(
        self,
        results: list[HotelComparisonResult] | list[HotelOption],
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[HotelComparisonResult] | list[HotelOption], dict[str, Any]]:
        """Paginate hotel results.

        Args:
            results: List of results to paginate
            page: Page number (1-based)
            per_page: Number of results per page

        Returns:
            (paginated_results, pagination_metadata) tuple
        """
        if not results:
            return [], {
                "page": 1,
                "per_page": per_page,
                "total": 0,
                "pages": 0,
                "has_next": False,
                "has_prev": False,
            }

        total = len(results)
        pages = math.ceil(total / per_page)
        page = max(1, min(page, pages))  # Clamp page to valid range

        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_results = results[start_idx:end_idx]

        metadata = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1,
        }

        return paginated_results, metadata

    async def invalidate_location_cache(self, location: str) -> int:
        """Invalidate all cached hotel results for a specific location.

        Args:
            location: Location identifier to invalidate

        Returns:
            Number of cache entries invalidated
        """
        return await self._cache_manager.invalidate_hotel_location_cache(location)

    async def invalidate_outdated_cache(self, max_age_minutes: int = 30) -> int:
        """Invalidate hotel cache entries older than specified age.

        Args:
            max_age_minutes: Maximum age in minutes before invalidation

        Returns:
            Number of cache entries invalidated
        """
        return await self._cache_manager.invalidate_outdated_hotel_cache(max_age_minutes)

    async def warm_popular_destinations_cache(
        self, destinations: list[str], search_params: dict[str, Any] | None = None
    ) -> dict[str, bool]:
        """Pre-warm cache for popular hotel destinations.

        Args:
            destinations: List of popular destination names/locations
            search_params: Default search parameters for warming

        Returns:
            Dictionary mapping destination to warming success status
        """
        return await self._cache_manager.warm_popular_hotel_destinations(
            destinations, search_params
        )

    async def get_cache_statistics(self) -> dict[str, Any]:
        """Get hotel caching statistics and metrics.

        Returns:
            Dictionary with cache statistics
        """
        return await self._cache_manager.get_cache_statistics()

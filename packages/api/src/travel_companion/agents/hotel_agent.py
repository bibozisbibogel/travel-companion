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
from travel_companion.services.external_apis.google_places_client import (
    GooglePlacesClient,
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
        # self._booking_client = BookingClient(timeout=self.timeout_seconds)
        # self._expedia_client = ExpediaClient()
        # self._airbnb_client = AirbnbClient()
        # self._geoapify_client = GeoapifyClient()
        # self._liteapi_client = LiteAPIClient(timeout=self.timeout_seconds)
        self._google_places_client = GooglePlacesClient(redis_manager=self.redis)

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

    async def search_hotels_google_places(
        self, search_request: HotelSearchRequest
    ) -> list[HotelOption]:
        """
        Search for hotels using Google Places API.

        Args:
            search_request: Hotel search request parameters

        Returns:
            List of hotel options from Google Places

        Raises:
            ExternalAPIError: If API request fails
        """
        try:
            # Build hotel search query
            query = f"hotels in {search_request.location}"

            # Determine location coordinates if available
            coordinates = self._parse_location_coordinates(search_request.location)
            location_bias = coordinates if coordinates else None

            # Map budget to price levels if provided
            price_levels = None
            if search_request.budget_per_night:
                price_levels = self._map_hotel_price_levels(float(search_request.budget_per_night))

            # Search for hotel places using GooglePlacesClient
            async with self._google_places_client as client:
                places = await client.places_api.text_search(
                    text_query=query,
                    location_bias=location_bias,
                    radius=5000,  # 5km search radius
                    min_rating=None,  # Could be configurable
                    price_levels=price_levels,
                    open_now=None,  # Hotels are typically always "open"
                    max_result_count=min(search_request.max_results, 20),
                )

            # Convert places to hotel options
            hotels = []
            for place in places:
                hotel = await self._convert_place_to_hotel(place, search_request)
                if hotel:
                    # Apply budget filter if specified
                    if (
                        search_request.budget_per_night
                        and hotel.price_per_night > search_request.budget_per_night
                    ):
                        continue
                    hotels.append(hotel)

            self.logger.info(f"Found {len(hotels)} hotels via Google Places API")
            return hotels

        except Exception as e:
            self.logger.error(f"Google Places hotel search error: {str(e)}")
            raise

    def _map_hotel_price_levels(self, max_price: float) -> list[str]:
        """
        Map maximum price to Google Places price levels for hotels.

        Args:
            max_price: Maximum price per night

        Returns:
            List of applicable price levels
        """
        price_levels = []

        # Hotel price level thresholds (higher than activities)
        # Note: PRICE_LEVEL_FREE is not supported by Google Places API for hotels
        if max_price >= 50:  # Budget hotels
            price_levels.append("PRICE_LEVEL_INEXPENSIVE")
        if max_price >= 100:  # Mid-range hotels
            price_levels.append("PRICE_LEVEL_MODERATE")
        if max_price >= 200:  # Upscale hotels
            price_levels.append("PRICE_LEVEL_EXPENSIVE")
        if max_price >= 400:  # Luxury hotels
            price_levels.append("PRICE_LEVEL_VERY_EXPENSIVE")

        return price_levels

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

        # Implement API fallback chain: Google Places → Booking.com → Expedia → Airbnb
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

        # Try Google Places first
        try:
            self.logger.info("Attempting Google Places API search")
            search_metadata["apis_attempted"].append("google_places")

            hotels_from_google = await self.search_hotels_google_places(search_request)
            hotels.extend(hotels_from_google)

            search_metadata["successful_api"] = "google_places"
            search_metadata["google_places_results"] = len(hotels_from_google)
            self.logger.info(f"Google Places API returned {len(hotels_from_google)} hotels")

        except Exception as e:
            self.logger.warning(f"Google Places API failed: {e}")
            search_metadata["api_errors"]["google_places"] = str(e)

            # Try Booking.com as fallback
            # try:
            #     self.logger.info("Attempting Booking.com API search (fallback)")
            #     search_metadata["apis_attempted"].append("booking.com")

            #     booking_params = HotelSearchParams(
            #         location=search_request.location,
            #         check_in=search_request.check_in_date.strftime("%Y-%m-%d"),
            #         check_out=search_request.check_out_date.strftime("%Y-%m-%d"),
            #         guest_count=search_request.guest_count,
            #         room_count=search_request.room_count,
            #         max_results=search_request.max_results,
            #         currency=search_request.currency,
            #         language="en",
            #     )

            #     booking_response = await self._booking_client.search_hotels(booking_params)

            #     # Convert Booking.com results to internal HotelOption models
            #     for booking_hotel in booking_response.hotels:
            #         try:
            #             # Apply budget filter if specified
            #             if (
            #                 search_request.budget_per_night
            #                 and booking_hotel.price_per_night
            #                 and Decimal(str(booking_hotel.price_per_night))
            #                 > search_request.budget_per_night
            #             ):
            #                 continue

            #             hotel_location = HotelLocation(
            #                 latitude=booking_hotel.latitude or 0.0,
            #                 longitude=booking_hotel.longitude or 0.0,
            #                 address=booking_hotel.address,
            #                 city=None,  # Extract from address if needed
            #                 country=None,  # Extract from address if needed
            #                 postal_code=None,
            #             )

            #             hotel_option = HotelOption(
            #                 trip_id=None,
            #                 external_id=f"booking_{booking_hotel.hotel_id}",
            #                 name=booking_hotel.name,
            #                 location=hotel_location,
            #                 price_per_night=Decimal(str(booking_hotel.price_per_night))
            #                 if booking_hotel.price_per_night
            #                 else Decimal("0"),
            #                 currency=booking_hotel.currency,
            #                 rating=booking_hotel.rating,
            #                 amenities=booking_hotel.amenities,
            #                 photos=booking_hotel.photos,
            #                 booking_url=booking_hotel.booking_url,
            #                 created_at=datetime.now(UTC),
            #             )
            #             hotels.append(hotel_option)

            #         except (ValueError, TypeError) as e:
            #             self.logger.warning(f"Failed to convert Booking.com hotel result: {e}")
            #             continue

            #     search_metadata["successful_api"] = "booking.com"
            #     search_metadata["booking_api_response_time"] = booking_response.api_response_time_ms
            #     search_metadata["booking_total_results"] = booking_response.total_results
            #     self.logger.info(f"Booking.com API returned {len(hotels)} hotels")

            # except Exception as e:
            #     self.logger.warning(f"Booking.com API failed: {e}")
            #     search_metadata["api_errors"]["booking.com"] = str(e)

            #     # Try Expedia as fallback
            #     try:
            #         self.logger.info("Attempting Expedia API search (fallback)")
            #         search_metadata["apis_attempted"].append("expedia")

            #         expedia_params = ExpediaSearchParams(
            #             location=search_request.location,
            #             check_in=search_request.check_in_date.strftime("%Y-%m-%d"),
            #             check_out=search_request.check_out_date.strftime("%Y-%m-%d"),
            #             guest_count=search_request.guest_count,
            #             room_count=search_request.room_count,
            #             max_results=search_request.max_results,
            #             currency=search_request.currency,
            #             language="en",
            #         )

            #         expedia_results = await self._expedia_client.search_hotels(expedia_params)

            #         # Convert Expedia results to internal HotelOption models
            #         for expedia_hotel in expedia_results:
            #             try:
            #                 # Apply budget filter if specified
            #                 if (
            #                     search_request.budget_per_night
            #                     and expedia_hotel.price_per_night
            #                     and Decimal(str(expedia_hotel.price_per_night))
            #                     > search_request.budget_per_night
            #                 ):
            #                     continue

            #                 hotel_location = HotelLocation(
            #                     latitude=expedia_hotel.latitude or 0.0,
            #                     longitude=expedia_hotel.longitude or 0.0,
            #                     address=expedia_hotel.address,
            #                     city=None,  # Extract from address if needed
            #                     country=None,  # Extract from address if needed
            #                     postal_code=None,
            #                 )

            #                 hotel_option = HotelOption(
            #                     trip_id=None,
            #                     external_id=f"expedia_{expedia_hotel.hotel_id}",
            #                     name=expedia_hotel.name,
            #                     location=hotel_location,
            #                     price_per_night=Decimal(str(expedia_hotel.price_per_night))
            #                     if expedia_hotel.price_per_night
            #                     else Decimal("0"),
            #                     currency=expedia_hotel.currency,
            #                     rating=expedia_hotel.rating,
            #                     amenities=expedia_hotel.amenities,
            #                     photos=expedia_hotel.photos,
            #                     booking_url=expedia_hotel.booking_url,
            #                     created_at=datetime.now(UTC),
            #                 )
            #                 hotels.append(hotel_option)

            #             except (ValueError, TypeError) as e:
            #                 self.logger.warning(f"Failed to convert Expedia hotel result: {e}")
            #                 continue

            #         search_metadata["successful_api"] = "expedia"
            #         search_metadata["expedia_total_results"] = len(expedia_results)
            #         self.logger.info(f"Expedia API returned {len(hotels)} hotels")

            #     except Exception as e:
            #         self.logger.warning(f"Expedia API failed: {e}")
            #         search_metadata["api_errors"]["expedia"] = str(e)

            #         # Try Airbnb as final fallback
            #         try:
            #             self.logger.info("Attempting Airbnb API search (final fallback)")
            #             search_metadata["apis_attempted"].append("airbnb")

            #             airbnb_params = AirbnbSearchParams(
            #                 location=search_request.location,
            #                 check_in=search_request.check_in_date.strftime("%Y-%m-%d"),
            #                 check_out=search_request.check_out_date.strftime("%Y-%m-%d"),
            #                 guest_count=search_request.guest_count,
            #                 max_results=search_request.max_results,
            #                 currency=search_request.currency,
            #                 language="en",
            #                 property_type=None,
            #                 min_price=None,
            #                 max_price=float(search_request.budget_per_night)
            #                 if search_request.budget_per_night
            #                 else None,
            #             )

            #             airbnb_results = await self._airbnb_client.search_listings(airbnb_params)

            #             # Convert Airbnb results to internal HotelOption models
            #             for airbnb_listing in airbnb_results:
            #                 try:
            #                     hotel_location = HotelLocation(
            #                         latitude=airbnb_listing.latitude or 0.0,
            #                         longitude=airbnb_listing.longitude or 0.0,
            #                         address=airbnb_listing.address,
            #                         city=None,  # Extract from address if needed
            #                         country=None,  # Extract from address if needed
            #                         postal_code=None,
            #                     )

            #                     hotel_option = HotelOption(
            #                         trip_id=None,
            #                         external_id=f"airbnb_{airbnb_listing.listing_id}",
            #                         name=airbnb_listing.name,
            #                         location=hotel_location,
            #                         price_per_night=Decimal(str(airbnb_listing.price_per_night))
            #                         if airbnb_listing.price_per_night
            #                         else Decimal("0"),
            #                         currency=airbnb_listing.currency,
            #                         rating=airbnb_listing.rating,
            #                         amenities=airbnb_listing.amenities,
            #                         photos=airbnb_listing.photos,
            #                         booking_url=airbnb_listing.booking_url,
            #                         created_at=datetime.now(UTC),
            #                     )
            #                     hotels.append(hotel_option)

            #                 except (ValueError, TypeError) as e:
            #                     self.logger.warning(f"Failed to convert Airbnb listing result: {e}")
            #                     continue

            #             search_metadata["successful_api"] = "airbnb"
            #             search_metadata["airbnb_total_results"] = len(airbnb_results)
            #             self.logger.info(f"Airbnb API returned {len(hotels)} hotels")

            #         except Exception as e:
            #             self.logger.error(f"All APIs failed. Last error (Airbnb): {e}")
            #             search_metadata["api_errors"]["airbnb"] = str(e)

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
        raise NotImplementedError(
            "search_hotels_with_rates is disabled because Geoapify and LiteAPI clients are currently disabled. "
            "Use the main search_hotels_by_location method which uses Google Places API instead."
        )

    async def _create_fallback_response(
        self, geoapify_hotels: list[dict[str, Any]], location: str, start_time: float
    ) -> HotelSearchResponse:
        """Create fallback response with Geoapify data only."""
        raise NotImplementedError(
            "_create_fallback_response is disabled because Geoapify client is currently disabled."
        )

    async def _combine_geoapify_liteapi_data(
        self,
        geoapify_hotels: list[dict[str, Any]],
        liteapi_hotels: list[dict[str, Any]],
        rates_data: dict[str, Any],
        budget_filter: float | None = None,
    ) -> list[HotelOption]:
        """Combine Geoapify location data with LiteAPI rates."""
        raise NotImplementedError(
            "_combine_geoapify_liteapi_data is disabled because Geoapify and LiteAPI clients are currently disabled."
        )

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

    async def _convert_place_to_hotel(
        self, place: Any, search_request: HotelSearchRequest
    ) -> HotelOption | None:
        """
        Convert Google Place to HotelOption.

        Args:
            place: Google Place object from GooglePlacesClient
            search_request: Original hotel search request

        Returns:
            HotelOption or None if conversion fails
        """
        try:
            # Extract name
            name = place.display_name.get("text", "Unknown Hotel")
            if not name or name == "Unknown Hotel":
                return None

            # Create hotel location
            location = HotelLocation(
                latitude=place.location.latitude if place.location else 0.0,
                longitude=place.location.longitude if place.location else 0.0,
                address=place.formatted_address,
                city=self._extract_city_from_address(place.formatted_address),
                country=self._extract_country_from_address(place.formatted_address),
                postal_code=None,  # Not readily available from Google Places
            )

            # Estimate price based on price level (convert to per night rate)
            estimated_price = self._estimate_hotel_price_from_level(place.price_level)

            # Extract images
            images = []
            if place.photos:
                # Get URLs for first 3 photos
                for photo in place.photos[:3]:
                    async with self._google_places_client as client:
                        photo_url = client.places_api.get_photo_url(
                            photo.name, max_width=800, max_height=600
                        )
                        images.append(photo_url)

            # Extract amenities from place types
            amenities = self._extract_hotel_amenities_from_types(place.types)

            # Create hotel option
            hotel = HotelOption(
                trip_id=None,
                external_id=f"google_places_{place.id}",
                name=name,
                location=location,
                price_per_night=estimated_price,
                currency=search_request.currency,
                rating=place.rating,
                amenities=amenities,
                photos=images,
                booking_url=place.website_uri or place.google_maps_uri,
                created_at=datetime.now(UTC),
            )

            return hotel

        except Exception as e:
            self.logger.warning(f"Failed to convert place to hotel: {e}")
            return None

    def _estimate_hotel_price_from_level(self, price_level: str | None) -> Decimal:
        """
        Estimate hotel price per night from Google's price level.

        Args:
            price_level: Google Places price level string

        Returns:
            Estimated price per night in the request currency
        """
        if not price_level:
            return Decimal("120")  # Default mid-range hotel price

        # Hotel price mapping (higher than activity prices)
        price_mapping = {
            "PRICE_LEVEL_FREE": Decimal("30"),  # Budget hostel/basic
            "PRICE_LEVEL_INEXPENSIVE": Decimal("70"),  # Budget hotel
            "PRICE_LEVEL_MODERATE": Decimal("150"),  # Mid-range hotel
            "PRICE_LEVEL_EXPENSIVE": Decimal("300"),  # Upscale hotel
            "PRICE_LEVEL_VERY_EXPENSIVE": Decimal("500"),  # Luxury hotel
        }

        return price_mapping.get(price_level, Decimal("120"))

    def _extract_hotel_amenities_from_types(self, types: list[str]) -> list[str]:
        """
        Extract hotel amenities from Google Places types.

        Args:
            types: List of place types from Google

        Returns:
            List of amenities based on place types
        """
        amenities = []

        # Map place types to hotel amenities
        type_amenity_mapping = {
            "spa": "Spa",
            "gym": "Fitness Center",
            "restaurant": "Restaurant",
            "bar": "Bar/Lounge",
            "swimming_pool": "Pool",
            "parking": "Parking",
            "wifi": "WiFi",
            "airport_shuttle": "Airport Shuttle",
            "room_service": "Room Service",
            "business_center": "Business Center",
            "pet_friendly": "Pet Friendly",
            "accessible": "Accessible",
        }

        for place_type in types:
            if place_type in type_amenity_mapping:
                amenities.append(type_amenity_mapping[place_type])

        # Add common hotel amenities based on type
        if "lodging" in types:
            amenities.extend(["Air Conditioning", "Daily Housekeeping"])

        return amenities

    def _extract_city_from_address(self, address: str | None) -> str | None:
        """Extract city from formatted address."""
        if not address:
            return None
        # Simple extraction - takes the second to last part before country
        parts = address.split(", ")
        if len(parts) >= 2:
            return parts[-2]
        return None

    def _extract_country_from_address(self, address: str | None) -> str | None:
        """Extract country from formatted address."""
        if not address:
            return None
        # Simple extraction - takes the last part
        parts = address.split(", ")
        if parts:
            return parts[-1]
        return None

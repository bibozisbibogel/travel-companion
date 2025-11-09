"""Food and restaurant recommendation agent using Google Places API."""

from typing import Any

from travel_companion.agents.base import BaseAgent
from travel_companion.models.external import (
    RestaurantComparisonResult,
    RestaurantLocation,
    RestaurantOption,
    RestaurantSearchRequest,
    RestaurantSearchResponse,
)
from travel_companion.services.cache import CacheManager
from travel_companion.services.external_apis.google_places import GooglePlacesNewAPI, Place
from travel_companion.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from travel_companion.utils.errors import ExternalAPIError


class FoodAgent(BaseAgent[RestaurantSearchResponse]):
    """Food and restaurant recommendation agent with Google Places API integration."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize food agent with Google Places API client and circuit breaker."""
        super().__init__(**kwargs)

        # Initialize Google Places client
        self.places_client = GooglePlacesNewAPI(api_key=self.settings.google_places_api_key)

        # Circuit breaker for Google Places API
        self.places_circuit_breaker = CircuitBreaker(
            name="google_places_api", failure_threshold=5, recovery_timeout=60
        )

        # Initialize cache manager
        self._cache_manager = CacheManager(self.redis)
        self.cache_ttl_seconds = getattr(
            self.settings, "food_cache_ttl_seconds", 1800
        )  # 30 minutes default

        self.logger.info("FoodAgent initialized with Google Places API client and circuit breaker")

    @property
    def agent_name(self) -> str:
        """Name of the agent for logging and identification."""
        return "food_agent"

    @property
    def agent_version(self) -> str:
        """Version of the agent for compatibility and debugging."""
        return "3.0.0"  # Updated version for Google Places integration

    def _convert_place_to_restaurant(
        self, place: Place, search_lat: float | None = None, search_lon: float | None = None
    ) -> RestaurantOption | None:
        """Convert Google Place to RestaurantOption.

        Args:
            place: Google Place object
            search_lat: Search origin latitude for distance calculation
            search_lon: Search origin longitude for distance calculation

        Returns:
            RestaurantOption or None if conversion fails
        """
        try:
            # Extract name
            name = place.display_name.get("text", "Unknown Restaurant")
            if not name or name == "Unknown Restaurant":
                return None

            # Create location
            location = RestaurantLocation(
                latitude=place.location.latitude if place.location else 0.0,
                longitude=place.location.longitude if place.location else 0.0,
                address=place.formatted_address,
                city=self._extract_city_from_address(place.formatted_address),
                country=self._extract_country_from_address(place.formatted_address),
            )

            # Calculate distance if search coordinates provided
            distance_meters = None
            if (
                search_lat is not None
                and search_lon is not None
                and place.location is not None
            ):
                distance_meters = int(
                    self._calculate_distance(
                        search_lat, search_lon, place.location.latitude, place.location.longitude
                    )
                )

            # Extract categories from types
            categories = [f"restaurant.{t}" for t in place.types if t]

            # Create restaurant option
            restaurant = RestaurantOption(
                external_id=f"google_places_{place.id}",
                name=name,
                categories=categories,
                location=location,
                formatted_address=place.formatted_address,
                distance_meters=distance_meters,
                provider="google_places",
            )

            return restaurant

        except Exception as e:
            self.logger.warning(f"Failed to convert place to restaurant: {e}")
            return None

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

    def _calculate_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two coordinates using Haversine formula.

        Args:
            lat1: Latitude of first point
            lon1: Longitude of first point
            lat2: Latitude of second point
            lon2: Longitude of second point

        Returns:
            Distance in meters
        """
        import math

        # Earth radius in meters
        R = 6371000

        # Convert to radians
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        # Haversine formula
        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    async def process(self, request_data: dict[str, Any]) -> RestaurantSearchResponse:
        """Process restaurant search request using Google Places API.

        Args:
            request_data: Restaurant search parameters

        Returns:
            RestaurantSearchResponse with restaurant recommendations
        """
        import time

        try:
            # Generate cache key
            cache_key = await self._cache_key(request_data)

            # Try to get cached result
            cached_result = await self._cache_manager.get_restaurant_cache(cache_key)
            if cached_result:
                self.logger.info("Returning cached restaurant search results")
                return cached_result

            # Validate and parse request
            search_request = RestaurantSearchRequest(**request_data)

            # Build search query
            query = self._build_restaurant_query(search_request)

            # Determine location bias
            location_bias = None
            if search_request.latitude is not None and search_request.longitude is not None:
                location_bias = (search_request.latitude, search_request.longitude)

            # Log what we're searching
            if location_bias:
                self.logger.info(
                    f"Processing restaurant search at coordinates: {location_bias} "
                    f"with query: '{query}'"
                )
            elif search_request.location:
                self.logger.info(
                    f"Processing restaurant search for location: {search_request.location} "
                    f"with query: '{query}'"
                )

            # Search using Google Places with circuit breaker protection
            start_time = time.time()
            async with self.places_circuit_breaker:
                places = await self.places_client.text_search(
                    text_query=query,
                    location_bias=location_bias,
                    radius=search_request.radius_meters,
                    max_result_count=min(search_request.max_results, 20),
                )
            search_time_ms = int((time.time() - start_time) * 1000)

            # Convert places to restaurants
            restaurants = []
            for place in places:
                restaurant = self._convert_place_to_restaurant(
                    place,
                    search_lat=search_request.latitude,
                    search_lon=search_request.longitude,
                )
                if restaurant:
                    restaurants.append(restaurant)

            # Sort by distance if we have distance data
            if restaurants and any(r.distance_meters is not None for r in restaurants):
                restaurants = sorted(
                    restaurants, key=lambda r: r.distance_meters or float("inf")
                )

            # Build response
            response = RestaurantSearchResponse(
                restaurants=restaurants,
                search_metadata={
                    "query": query,
                    "location_bias": location_bias,
                    "radius_meters": search_request.radius_meters,
                },
                total_results=len(restaurants),
                search_time_ms=search_time_ms,
                cached=False,
            )

            # Cache the result
            await self._cache_manager.set_restaurant_cache(
                cache_key, response, ttl_seconds=self.cache_ttl_seconds
            )

            self.logger.info(
                f"Restaurant search completed: {len(restaurants)} restaurants found "
                f"in {search_time_ms}ms"
            )

            return response

        except Exception as e:
            self.logger.error(f"Restaurant search failed: {e}")
            raise ExternalAPIError(f"Restaurant search failed: {e}") from e

    def _build_restaurant_query(self, request: RestaurantSearchRequest) -> str:
        """Build Google Places search query from restaurant search request.

        Args:
            request: Restaurant search request

        Returns:
            Search query string for Google Places
        """
        query_parts = []

        # Add location if provided
        if request.location:
            query_parts.append(f"restaurants in {request.location}")
        else:
            query_parts.append("restaurants")

        # Add category keywords if specific categories provided
        if request.categories and request.categories != ["catering.restaurant"]:
            # Extract cuisine types from categories
            for category in request.categories:
                cuisine_type = self._extract_cuisine_from_category(category)
                if cuisine_type:
                    query_parts.append(cuisine_type)

        return " ".join(query_parts)

    def _extract_cuisine_from_category(self, category: str) -> str | None:
        """Extract cuisine type from category string.

        Args:
            category: Category string (e.g., 'restaurant.italian', 'catering.fast_food')

        Returns:
            Cuisine type or None
        """
        # Map common category patterns to cuisine types
        category_lower = category.lower()

        # Extract from restaurant.* pattern
        if "restaurant." in category_lower:
            cuisine = category_lower.split("restaurant.")[-1]
            return cuisine.replace("_", " ")

        # Extract from catering.* pattern
        if "catering." in category_lower:
            cuisine = category_lower.split("catering.")[-1]
            if cuisine != "restaurant":  # Don't return generic "restaurant"
                return cuisine.replace("_", " ")

        # Extract from cafe.* or fast_food.* patterns
        if "cafe." in category_lower or "fast_food." in category_lower:
            return category_lower.split(".")[-1].replace("_", " ")

        return None

    async def search_by_cuisine(
        self,
        location: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        cuisine_type: str = "restaurant",
        radius_meters: int = 5000,
        max_results: int = 50,
    ) -> RestaurantSearchResponse:
        """Search for restaurants by specific cuisine type.

        Args:
            location: Location name to search near
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            cuisine_type: Cuisine type (e.g., 'italian', 'chinese', 'mexican')
            radius_meters: Search radius in meters
            max_results: Maximum number of results

        Returns:
            RestaurantSearchResponse with filtered restaurants
        """
        import time

        try:
            self.logger.info(f"Searching for {cuisine_type} restaurants")

            # Build search query with cuisine type
            if location:
                query = f"{cuisine_type} restaurants in {location}"
            else:
                query = f"{cuisine_type} restaurants"

            # Determine location bias
            location_bias = None
            if latitude is not None and longitude is not None:
                location_bias = (latitude, longitude)

            # Search using Google Places
            start_time = time.time()
            async with self.places_circuit_breaker:
                places = await self.places_client.text_search(
                    text_query=query,
                    location_bias=location_bias,
                    radius=radius_meters,
                    max_result_count=min(max_results, 20),
                )
            search_time_ms = int((time.time() - start_time) * 1000)

            # Convert places to restaurants
            restaurants = []
            for place in places:
                restaurant = self._convert_place_to_restaurant(
                    place, search_lat=latitude, search_lon=longitude
                )
                if restaurant:
                    restaurants.append(restaurant)

            # Build response
            response = RestaurantSearchResponse(
                restaurants=restaurants,
                search_metadata={"cuisine_type": cuisine_type, "query": query},
                total_results=len(restaurants),
                search_time_ms=search_time_ms,
                cached=False,
            )

            self.logger.info(f"Found {len(restaurants)} {cuisine_type} restaurants")
            return response

        except Exception as e:
            self.logger.error(f"Cuisine-specific search failed: {e}")
            raise ExternalAPIError(f"Cuisine search failed: {e}") from e

    async def search_local_specialties(
        self,
        location: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> RestaurantSearchResponse:
        """Search for local specialty restaurants based on location.

        Args:
            location: Location name to search for specialties
            latitude: Latitude coordinate
            longitude: Longitude coordinate

        Returns:
            RestaurantSearchResponse with local specialty restaurants
        """
        import time

        try:
            # Determine local cuisines based on location
            local_cuisines = self._get_local_cuisines(location)

            # Build search query
            if location:
                if local_cuisines:
                    # Search for specific local cuisines
                    query = f"{', '.join(local_cuisines)} restaurants in {location}"
                else:
                    # Generic local/regional restaurants
                    query = f"local restaurants in {location}"
            else:
                query = "local specialty restaurants"

            self.logger.info(f"Searching local specialties with query: '{query}'")

            # Determine location bias
            location_bias = None
            if latitude is not None and longitude is not None:
                location_bias = (latitude, longitude)

            # Search using Google Places
            start_time = time.time()
            async with self.places_circuit_breaker:
                places = await self.places_client.text_search(
                    text_query=query,
                    location_bias=location_bias,
                    radius=3000,  # Smaller radius for local places
                    max_result_count=20,
                )
            search_time_ms = int((time.time() - start_time) * 1000)

            # Convert places to restaurants
            restaurants = []
            for place in places:
                restaurant = self._convert_place_to_restaurant(
                    place, search_lat=latitude, search_lon=longitude
                )
                if restaurant:
                    restaurants.append(restaurant)

            # Build response
            response = RestaurantSearchResponse(
                restaurants=restaurants,
                search_metadata={
                    "search_type": "local_specialties",
                    "local_cuisines": local_cuisines,
                    "query": query,
                },
                total_results=len(restaurants),
                search_time_ms=search_time_ms,
                cached=False,
            )

            self.logger.info(f"Found {len(restaurants)} local specialty restaurants")
            return response

        except Exception as e:
            self.logger.error(f"Local specialty search failed: {e}")
            return RestaurantSearchResponse(
                restaurants=[],
                cache_expires_at=None,
                search_metadata={"error": str(e)},
                total_results=0,
                search_time_ms=0,
                cached=False,
            )

    def _get_local_cuisines(self, location: str | None) -> list[str]:
        """Map location to relevant local cuisine types for Google Places queries.

        Args:
            location: Location name

        Returns:
            List of cuisine types for the location
        """
        if not location:
            return []

        location_lower = location.lower()
        cuisines: list[str] = []

        # Location-based cuisine mapping for Google Places
        location_cuisines_map = {
            "italy": ["italian"],
            "rome": ["italian"],
            "milan": ["italian"],
            "florence": ["italian"],
            "france": ["french"],
            "paris": ["french"],
            "lyon": ["french"],
            "mexico": ["mexican"],
            "japan": ["japanese", "sushi", "ramen"],
            "tokyo": ["japanese", "sushi"],
            "china": ["chinese"],
            "beijing": ["chinese"],
            "shanghai": ["chinese"],
            "india": ["indian"],
            "thailand": ["thai"],
            "bangkok": ["thai"],
            "greece": ["greek"],
            "athens": ["greek"],
            "spain": ["spanish", "tapas"],
            "barcelona": ["spanish", "tapas"],
            "madrid": ["spanish"],
            "germany": ["german"],
            "munich": ["bavarian", "german"],
            "berlin": ["german"],
            "turkey": ["turkish"],
            "istanbul": ["turkish"],
            "korea": ["korean"],
            "seoul": ["korean"],
            "vietnam": ["vietnamese"],
            "hanoi": ["vietnamese"],
            "texas": ["tex-mex", "barbecue"],
            "new york": ["pizza", "american"],
            "louisiana": ["cajun", "creole", "seafood"],
            "caribbean": ["caribbean"],
            "jamaica": ["jamaican"],
        }

        # Check for matches
        for loc_key, loc_cuisines in location_cuisines_map.items():
            if loc_key in location_lower:
                cuisines.extend(loc_cuisines)

        return list(set(cuisines))  # Remove duplicates

    async def compare_restaurants(
        self, restaurants: list[RestaurantOption], preferred_categories: list[str] | None = None
    ) -> list[RestaurantComparisonResult]:
        """Compare and rank restaurants based on various factors.

        Args:
            restaurants: List of restaurants to compare
            preferred_categories: User's preferred cuisine categories

        Returns:
            List of RestaurantComparisonResult with scoring
        """
        if not restaurants:
            return []

        comparison_results: list[RestaurantComparisonResult] = []

        # Sort by distance for ranking
        sorted_by_distance = sorted(
            restaurants,
            key=lambda r: r.distance_meters if r.distance_meters is not None else float("inf"),
        )

        for restaurant in restaurants:
            # Calculate distance rank
            distance_rank = sorted_by_distance.index(restaurant) + 1

            # Calculate category match score
            category_match_score = 0.0
            if preferred_categories and restaurant.categories:
                matches = sum(1 for cat in restaurant.categories if cat in preferred_categories)
                if matches > 0:
                    category_match_score = matches / len(preferred_categories)

            # Calculate overall score (simplified for Geoapify)
            score = 0.0
            reasons: list[str] = []

            # Distance component (40% weight)
            if restaurant.distance_meters is not None:
                # Closer is better - normalize to 0-40 scale
                max_distance = 5000  # 5km max
                distance_score = (
                    max(0, (max_distance - restaurant.distance_meters) / max_distance) * 40
                )
                score += distance_score
                reasons.append(f"Distance: {restaurant.distance_meters}m")

            # Category match component (30% weight)
            score += category_match_score * 30
            if category_match_score > 0:
                reasons.append(f"Category match: {category_match_score:.0%}")

            # Has specific cuisine subcategory (20% weight)
            if restaurant.categories:
                # Bonus for specific cuisine vs generic
                for cat in restaurant.categories:
                    if "restaurant." in cat or "fast_food." in cat or "cafe." in cat:
                        score += 20
                        reasons.append("Specific cuisine type")
                        break

            # Name recognition (10% weight) - well-known places often have longer names
            if len(restaurant.name) > 20:
                score += 5
                reasons.append("Established restaurant")

            comparison_result = RestaurantComparisonResult(
                restaurant=restaurant,
                score=min(score, 100.0),  # Cap at 100
                distance_rank=distance_rank,
                category_match_score=category_match_score,
                reasons=reasons,
            )
            comparison_results.append(comparison_result)

        # Sort by score descending
        comparison_results.sort(key=lambda x: x.score, reverse=True)
        return comparison_results

    def filter_by_category_type(
        self, restaurants: list[RestaurantOption], category_type: str
    ) -> list[RestaurantOption]:
        """Filter restaurants by category type (e.g., 'cafe', 'fast_food', 'restaurant').

        Args:
            restaurants: List of restaurants to filter
            category_type: Category type to filter by

        Returns:
            Filtered list of restaurants
        """
        filtered: list[RestaurantOption] = []

        for restaurant in restaurants:
            if restaurant.categories:
                # Check if any category matches the type
                for cat in restaurant.categories:
                    if category_type.lower() in cat.lower():
                        filtered.append(restaurant)
                        break

        self.logger.info(
            f"Filtered {len(restaurants)} restaurants to {len(filtered)} "
            f"matching category type '{category_type}'"
        )
        return filtered

    async def get_nearby_cafes(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 1000,
    ) -> RestaurantSearchResponse:
        """Get nearby cafes for a quick coffee or snack.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            radius_meters: Search radius (default 1km)

        Returns:
            RestaurantSearchResponse with nearby cafes
        """
        import time

        try:
            query = "cafes coffee shops"

            self.logger.info(f"Searching for cafes near {latitude}, {longitude}")

            # Search using Google Places
            start_time = time.time()
            async with self.places_circuit_breaker:
                places = await self.places_client.text_search(
                    text_query=query,
                    location_bias=(latitude, longitude),
                    radius=radius_meters,
                    max_result_count=20,
                )
            search_time_ms = int((time.time() - start_time) * 1000)

            # Convert places to restaurants
            restaurants = []
            for place in places:
                restaurant = self._convert_place_to_restaurant(
                    place, search_lat=latitude, search_lon=longitude
                )
                if restaurant:
                    restaurants.append(restaurant)

            # Build response
            return RestaurantSearchResponse(
                restaurants=restaurants,
                search_metadata={"search_type": "cafes", "query": query},
                total_results=len(restaurants),
                search_time_ms=search_time_ms,
                cached=False,
            )

        except Exception as e:
            self.logger.error(f"Cafe search failed: {e}")
            return RestaurantSearchResponse(
                restaurants=[],
                cache_expires_at=None,
                search_metadata={"error": str(e)},
                total_results=0,
                search_time_ms=0,
                cached=False,
            )

    async def get_fast_food_options(
        self,
        location: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_meters: int = 2000,
    ) -> RestaurantSearchResponse:
        """Get fast food options for quick meals.

        Args:
            location: Location name
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            radius_meters: Search radius (default 2km)

        Returns:
            RestaurantSearchResponse with fast food options
        """
        import time

        try:
            # Build search query
            if location:
                query = f"fast food restaurants in {location}"
            else:
                query = "fast food restaurants"

            self.logger.info(f"Searching for fast food with query: '{query}'")

            # Determine location bias
            location_bias = None
            if latitude is not None and longitude is not None:
                location_bias = (latitude, longitude)

            # Search using Google Places
            start_time = time.time()
            async with self.places_circuit_breaker:
                places = await self.places_client.text_search(
                    text_query=query,
                    location_bias=location_bias,
                    radius=radius_meters,
                    max_result_count=20,
                )
            search_time_ms = int((time.time() - start_time) * 1000)

            # Convert places to restaurants
            restaurants = []
            for place in places:
                restaurant = self._convert_place_to_restaurant(
                    place, search_lat=latitude, search_lon=longitude
                )
                if restaurant:
                    restaurants.append(restaurant)

            # Build response
            return RestaurantSearchResponse(
                restaurants=restaurants,
                search_metadata={"search_type": "fast_food", "query": query},
                total_results=len(restaurants),
                search_time_ms=search_time_ms,
                cached=False,
            )

        except Exception as e:
            self.logger.error(f"Fast food search failed: {e}")
            return RestaurantSearchResponse(
                restaurants=[],
                cache_expires_at=None,
                search_metadata={"error": str(e)},
                total_results=0,
                search_time_ms=0,
                cached=False,
            )

    async def search_restaurants(
        self, search_request: RestaurantSearchRequest
    ) -> RestaurantSearchResponse:
        """Direct search using Google Places with the provided request.

        Args:
            search_request: Search request with parameters

        Returns:
            RestaurantSearchResponse with results
        """
        try:
            # Use the process method which handles Google Places search
            result = await self.process(search_request.model_dump())
            return result
        except CircuitBreakerOpenError as e:
            self.logger.warning(f"Google Places circuit breaker is open: {e}")
            return RestaurantSearchResponse(
                restaurants=[],
                cache_expires_at=None,
                search_metadata={
                    "error": "Service temporarily unavailable",
                    "circuit_breaker": "open",
                },
                total_results=0,
                search_time_ms=0,
                cached=False,
            )
        except Exception as e:
            self.logger.error(f"Restaurant search failed: {e}")
            return RestaurantSearchResponse(
                restaurants=[],
                cache_expires_at=None,
                search_metadata={"error": str(e)},
                total_results=0,
                search_time_ms=0,
                cached=False,
            )

    async def health_check(self) -> dict[str, Any]:
        """Enhanced health check including Google Places API service status."""
        status = await super().health_check()

        # Add Google Places API health check
        api_health: dict[str, str] = {}

        try:
            api_health["google_places"] = (
                "healthy" if self.places_circuit_breaker.is_closed else "circuit_open"
            )
        except Exception:
            api_health["google_places"] = "unhealthy"

        status["dependencies"]["apis"] = api_health

        # Overall status degraded if API is unhealthy or circuit is open
        if api_health.get("google_places") != "healthy":
            status["status"] = "degraded"

        return status

    async def __aenter__(self) -> "FoodAgent":
        """Async context manager entry."""
        await self.places_client.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.places_client.__aexit__(exc_type, exc_val, exc_tb)

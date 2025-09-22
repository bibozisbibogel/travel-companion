"""Food and restaurant recommendation agent using Geoapify API."""

from typing import Any

from travel_companion.agents.base import BaseAgent
from travel_companion.models.external import (
    GeoapifyCateringCategory,
    RestaurantComparisonResult,
    RestaurantOption,
    RestaurantSearchRequest,
    RestaurantSearchResponse,
)
from travel_companion.services.external_apis.geoapify import GeoapifyClient
from travel_companion.utils.circuit_breaker import CircuitBreaker
from travel_companion.utils.errors import ExternalAPIError


class FoodAgent(BaseAgent[RestaurantSearchResponse]):
    """Food and restaurant recommendation agent with Geoapify API integration."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize food agent with Geoapify API client and circuit breaker."""
        super().__init__(**kwargs)

        # Initialize Geoapify client
        self.geoapify_client = GeoapifyClient()

        # Circuit breaker for Geoapify API
        self.geoapify_circuit_breaker = CircuitBreaker(
            name="geoapify_api", failure_threshold=5, recovery_timeout=60
        )

        self.logger.info("FoodAgent initialized with Geoapify API client and circuit breaker")

    @property
    def agent_name(self) -> str:
        """Name of the agent for logging and identification."""
        return "food_agent"

    @property
    def agent_version(self) -> str:
        """Version of the agent for compatibility and debugging."""
        return "2.0.0"  # Updated version for Geoapify integration

    async def process(self, request_data: dict[str, Any]) -> RestaurantSearchResponse:
        """Process restaurant search request using Geoapify Places API.

        Args:
            request_data: Restaurant search parameters

        Returns:
            RestaurantSearchResponse with restaurant recommendations
        """
        try:
            # Validate and parse request
            search_request = RestaurantSearchRequest(**request_data)

            # If location string is provided and no coordinates, log for clarity
            if search_request.location and not (search_request.latitude and search_request.longitude):
                self.logger.info(f"Processing restaurant search for location: {search_request.location}")
            elif search_request.latitude and search_request.longitude:
                self.logger.info(
                    f"Processing restaurant search at coordinates: "
                    f"{search_request.latitude}, {search_request.longitude}"
                )

            # Search using Geoapify with circuit breaker protection
            async with self.geoapify_circuit_breaker:
                response = await self.geoapify_client.search_restaurants(search_request)

            # If we have results, sort by distance
            if response.restaurants and any(r.distance_meters is not None for r in response.restaurants):
                response.restaurants = sorted(
                    response.restaurants,
                    key=lambda r: r.distance_meters or float('inf')
                )

            self.logger.info(
                f"Restaurant search completed: {len(response.restaurants)} restaurants found "
                f"in {response.search_time_ms}ms"
            )

            return response

        except Exception as e:
            self.logger.error(f"Restaurant search failed: {e}")
            raise ExternalAPIError(f"Restaurant search failed: {e}") from e

    async def search_by_cuisine(
        self,
        location: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        cuisine_category: GeoapifyCateringCategory | str = GeoapifyCateringCategory.RESTAURANT,
        radius_meters: int = 5000,
        max_results: int = 50,
    ) -> RestaurantSearchResponse:
        """Search for restaurants by specific cuisine category.

        Args:
            location: Location name to search near
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            cuisine_category: Geoapify cuisine category
            radius_meters: Search radius in meters
            max_results: Maximum number of results

        Returns:
            RestaurantSearchResponse with filtered restaurants
        """
        try:
            # Convert enum to string if needed
            if isinstance(cuisine_category, GeoapifyCateringCategory):
                category_str = cuisine_category.value
            else:
                category_str = cuisine_category

            # Build search request
            search_request = RestaurantSearchRequest(
                location=location,
                latitude=latitude,
                longitude=longitude,
                categories=[category_str],
                radius_meters=radius_meters,
                max_results=max_results,
            )

            self.logger.info(f"Searching for {category_str} restaurants")

            # Search using Geoapify
            async with self.geoapify_circuit_breaker:
                response = await self.geoapify_client.search_restaurants(search_request)

            self.logger.info(f"Found {len(response.restaurants)} {category_str} restaurants")
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
        try:
            # Determine cuisine categories based on location
            specialty_categories = self._get_local_cuisine_categories(location)

            if not specialty_categories:
                # Default to regional/international if no specific match
                specialty_categories = [
                    GeoapifyCateringCategory.RESTAURANT_REGIONAL.value,
                    GeoapifyCateringCategory.RESTAURANT_INTERNATIONAL.value,
                ]

            self.logger.info(
                f"Searching local specialties with categories: {specialty_categories}"
            )

            # Build search request with local specialty categories
            search_request = RestaurantSearchRequest(
                location=location,
                latitude=latitude,
                longitude=longitude,
                categories=specialty_categories,
                radius_meters=3000,  # Smaller radius for local places
                max_results=30,
            )

            # Search using Geoapify
            async with self.geoapify_circuit_breaker:
                response = await self.geoapify_client.search_restaurants(search_request)

            # Update metadata to indicate specialty search
            response.search_metadata["search_type"] = "local_specialties"
            response.search_metadata["specialty_categories"] = specialty_categories

            self.logger.info(f"Found {len(response.restaurants)} local specialty restaurants")
            return response

        except Exception as e:
            self.logger.error(f"Local specialty search failed: {e}")
            return RestaurantSearchResponse(
                restaurants=[],
                search_metadata={"error": str(e)},
                total_results=0,
                search_time_ms=0,
                cached=False,
            )

    def _get_local_cuisine_categories(self, location: str | None) -> list[str]:
        """Map location to relevant local cuisine categories."""
        if not location:
            return []

        location_lower = location.lower()
        categories: list[str] = []

        # Location-based cuisine mapping using Geoapify categories
        location_cuisines = {
            "italy": [GeoapifyCateringCategory.RESTAURANT_ITALIAN.value],
            "rome": [GeoapifyCateringCategory.RESTAURANT_ITALIAN.value],
            "milan": [GeoapifyCateringCategory.RESTAURANT_ITALIAN.value],
            "france": [GeoapifyCateringCategory.RESTAURANT_FRENCH.value],
            "paris": [GeoapifyCateringCategory.RESTAURANT_FRENCH.value],
            "mexico": [
                GeoapifyCateringCategory.RESTAURANT_MEXICAN.value,
                GeoapifyCateringCategory.RESTAURANT_TEX_MEX.value,
            ],
            "japan": [
                GeoapifyCateringCategory.RESTAURANT_JAPANESE.value,
                GeoapifyCateringCategory.RESTAURANT_SUSHI.value,
                GeoapifyCateringCategory.RESTAURANT_RAMEN.value,
            ],
            "tokyo": [
                GeoapifyCateringCategory.RESTAURANT_JAPANESE.value,
                GeoapifyCateringCategory.RESTAURANT_SUSHI.value,
            ],
            "china": [
                GeoapifyCateringCategory.RESTAURANT_CHINESE.value,
                GeoapifyCateringCategory.RESTAURANT_DUMPLING.value,
            ],
            "beijing": [GeoapifyCateringCategory.RESTAURANT_CHINESE.value],
            "india": [
                GeoapifyCateringCategory.RESTAURANT_INDIAN.value,
                GeoapifyCateringCategory.RESTAURANT_CURRY.value,
            ],
            "thailand": [GeoapifyCateringCategory.RESTAURANT_THAI.value],
            "bangkok": [GeoapifyCateringCategory.RESTAURANT_THAI.value],
            "greece": [GeoapifyCateringCategory.RESTAURANT_GREEK.value],
            "athens": [GeoapifyCateringCategory.RESTAURANT_GREEK.value],
            "spain": [
                GeoapifyCateringCategory.RESTAURANT_SPANISH.value,
                GeoapifyCateringCategory.RESTAURANT_TAPAS.value,
            ],
            "barcelona": [
                GeoapifyCateringCategory.RESTAURANT_SPANISH.value,
                GeoapifyCateringCategory.RESTAURANT_TAPAS.value,
            ],
            "germany": [
                GeoapifyCateringCategory.RESTAURANT_GERMAN.value,
                GeoapifyCateringCategory.RESTAURANT_BAVARIAN.value,
            ],
            "munich": [GeoapifyCateringCategory.RESTAURANT_BAVARIAN.value],
            "turkey": [
                GeoapifyCateringCategory.RESTAURANT_TURKISH.value,
                GeoapifyCateringCategory.RESTAURANT_KEBAB.value,
            ],
            "istanbul": [GeoapifyCateringCategory.RESTAURANT_TURKISH.value],
            "korea": [GeoapifyCateringCategory.RESTAURANT_KOREAN.value],
            "seoul": [GeoapifyCateringCategory.RESTAURANT_KOREAN.value],
            "vietnam": [GeoapifyCateringCategory.RESTAURANT_VIETNAMESE.value],
            "texas": [
                GeoapifyCateringCategory.RESTAURANT_TEX_MEX.value,
                GeoapifyCateringCategory.RESTAURANT_BARBECUE.value,
                GeoapifyCateringCategory.RESTAURANT_STEAK_HOUSE.value,
            ],
            "new york": [
                GeoapifyCateringCategory.RESTAURANT_PIZZA.value,
                GeoapifyCateringCategory.RESTAURANT_AMERICAN.value,
            ],
            "louisiana": [
                GeoapifyCateringCategory.RESTAURANT_SEAFOOD.value,
                GeoapifyCateringCategory.RESTAURANT_AMERICAN.value,
            ],
            "caribbean": [GeoapifyCateringCategory.RESTAURANT_CARIBBEAN.value],
            "jamaica": [GeoapifyCateringCategory.RESTAURANT_JAMAICAN.value],
        }

        # Check for matches
        for loc_key, cuisine_categories in location_cuisines.items():
            if loc_key in location_lower:
                categories.extend(cuisine_categories)

        return list(set(categories))  # Remove duplicates

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
            key=lambda r: r.distance_meters if r.distance_meters is not None else float('inf')
        )

        for restaurant in restaurants:
            # Calculate distance rank
            distance_rank = sorted_by_distance.index(restaurant) + 1

            # Calculate category match score
            category_match_score = 0.0
            if preferred_categories and restaurant.categories:
                matches = sum(
                    1 for cat in restaurant.categories if cat in preferred_categories
                )
                if matches > 0:
                    category_match_score = matches / len(preferred_categories)

            # Calculate overall score (simplified for Geoapify)
            score = 0.0
            reasons: list[str] = []

            # Distance component (40% weight)
            if restaurant.distance_meters is not None:
                # Closer is better - normalize to 0-40 scale
                max_distance = 5000  # 5km max
                distance_score = max(
                    0, (max_distance - restaurant.distance_meters) / max_distance
                ) * 40
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
        cafe_categories = [
            GeoapifyCateringCategory.CAFE.value,
            GeoapifyCateringCategory.CAFE_COFFEE.value,
            GeoapifyCateringCategory.CAFE_COFFEE_SHOP.value,
        ]

        search_request = RestaurantSearchRequest(
            latitude=latitude,
            longitude=longitude,
            categories=cafe_categories,
            radius_meters=radius_meters,
            max_results=20,
        )

        return await self.search_restaurants(search_request)

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
        fast_food_categories = [
            GeoapifyCateringCategory.FAST_FOOD.value,
            GeoapifyCateringCategory.FAST_FOOD_BURGER.value,
            GeoapifyCateringCategory.FAST_FOOD_PIZZA.value,
            GeoapifyCateringCategory.FAST_FOOD_SANDWICH.value,
        ]

        search_request = RestaurantSearchRequest(
            location=location,
            latitude=latitude,
            longitude=longitude,
            categories=fast_food_categories,
            radius_meters=radius_meters,
            max_results=30,
        )

        return await self.search_restaurants(search_request)

    async def search_restaurants(
        self, search_request: RestaurantSearchRequest
    ) -> RestaurantSearchResponse:
        """Direct search using Geoapify with the provided request.

        Args:
            search_request: Search request with parameters

        Returns:
            RestaurantSearchResponse with results
        """
        async with self.geoapify_circuit_breaker:
            return await self.geoapify_client.search_restaurants(search_request)

    async def health_check(self) -> dict[str, Any]:
        """Enhanced health check including Geoapify API service status."""
        status = await super().health_check()

        # Add Geoapify API health check
        api_health: dict[str, str] = {}

        try:
            api_health["geoapify"] = (
                "healthy" if self.geoapify_circuit_breaker.is_closed else "circuit_open"
            )
        except Exception:
            api_health["geoapify"] = "unhealthy"

        status["dependencies"]["apis"] = api_health

        # Overall status degraded if API is unhealthy or circuit is open
        if api_health.get("geoapify") != "healthy":
            status["status"] = "degraded"

        return status

    async def __aenter__(self) -> "FoodAgent":
        """Async context manager entry."""
        await self.geoapify_client.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.geoapify_client.__aexit__(exc_type, exc_val, exc_tb)

"""Food and restaurant recommendation agent."""

import asyncio
from typing import Any

from travel_companion.agents.base import BaseAgent
from travel_companion.models.external import (
    CuisineType,
    DietaryRestriction,
    PopularDish,
    PriceRange,
    RestaurantOption,
    RestaurantSearchRequest,
    RestaurantSearchResponse,
)
from travel_companion.services.external_apis.google_places import GooglePlacesClient
from travel_companion.services.external_apis.yelp import YelpClient
from travel_companion.services.external_apis.zomato import ZomatoClient
from travel_companion.utils.circuit_breaker import CircuitBreaker
from travel_companion.utils.errors import ExternalAPIError


class FoodAgent(BaseAgent[RestaurantSearchResponse]):
    """Food and restaurant recommendation agent with multiple API integrations."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize food agent with API clients and circuit breakers."""
        super().__init__(**kwargs)

        # Initialize API clients
        self.yelp_client = YelpClient(self.settings.yelp_api_key)
        self.google_places_client = GooglePlacesClient(self.settings.google_places_api_key)
        self.zomato_client = ZomatoClient(self.settings.zomato_api_key)

        # Circuit breakers for each API
        self.yelp_circuit_breaker = CircuitBreaker(
            name="yelp_api", failure_threshold=5, recovery_timeout=60
        )
        self.google_circuit_breaker = CircuitBreaker(
            name="google_places_api", failure_threshold=5, recovery_timeout=60
        )
        self.zomato_circuit_breaker = CircuitBreaker(
            name="zomato_api", failure_threshold=5, recovery_timeout=60
        )

        self.logger.info("FoodAgent initialized with API clients and circuit breakers")

    @property
    def agent_name(self) -> str:
        """Name of the agent for logging and identification."""
        return "food_agent"

    @property
    def agent_version(self) -> str:
        """Version of the agent for compatibility and debugging."""
        return "1.0.0"

    async def process(self, request_data: dict[str, Any]) -> RestaurantSearchResponse:
        """Process restaurant search request with multiple API aggregation.

        Args:
            request_data: Restaurant search parameters

        Returns:
            RestaurantSearchResponse with aggregated restaurant recommendations
        """
        try:
            # Validate and parse request
            search_request = RestaurantSearchRequest(**request_data)
            self.logger.info(f"Processing restaurant search for {search_request.location}")

            # Generate cache key and check cache
            cache_key = await self._cache_key(request_data)
            cached_result = await self._get_cached_result(cache_key)
            if cached_result:
                return cached_result

            # Aggregate results from multiple APIs concurrently
            start_time = asyncio.get_event_loop().time()

            # Run API calls concurrently with circuit breaker protection
            tasks = [
                self._search_yelp(search_request),
                self._search_google_places(search_request),
                self._search_zomato(search_request),
            ]

            api_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process and aggregate results
            all_restaurants: list[RestaurantOption] = []
            api_metadata: dict[str, Any] = {}

            for i, result in enumerate(api_results):
                api_name = ["yelp", "google_places", "zomato"][i]

                if isinstance(result, Exception):
                    self.logger.warning(f"{api_name} API failed: {result}")
                    api_metadata[api_name] = {"status": "failed", "error": str(result)}
                elif result and not isinstance(result, BaseException):
                    all_restaurants.extend(result)
                    api_metadata[api_name] = {
                        "status": "success",
                        "results_count": str(len(result)),
                    }
                else:
                    api_metadata[api_name] = {"status": "no_results"}

            # Remove duplicates and rank results
            unique_restaurants = self._deduplicate_restaurants(all_restaurants)
            ranked_restaurants = self._rank_restaurants(unique_restaurants, search_request)

            # Limit results to max_results
            final_restaurants = ranked_restaurants[: search_request.max_results]

            # Calculate search time
            search_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

            # Create response
            response = RestaurantSearchResponse(
                restaurants=final_restaurants,
                search_metadata=api_metadata,
                total_results=len(final_restaurants),
                search_time_ms=search_time_ms,
                cached=False,
                cache_expires_at=None,
            )

            # Cache the result for future requests
            await self._set_cached_result(cache_key, response, expire_seconds=1800)  # 30 minutes

            self.logger.info(
                f"Restaurant search completed: {len(final_restaurants)} restaurants found in {search_time_ms}ms"
            )

            return response

        except Exception as e:
            self.logger.error(f"Restaurant search failed: {e}")
            raise ExternalAPIError(f"Restaurant search failed: {e}") from e

    async def _search_yelp(self, request: RestaurantSearchRequest) -> list[RestaurantOption]:
        """Search restaurants using Yelp Fusion API with circuit breaker."""
        try:
            async with self.yelp_circuit_breaker:
                return await self.yelp_client.search_restaurants(request)
        except Exception as e:
            self.logger.warning(f"Yelp search failed: {e}")
        return []

    async def _search_google_places(
        self, request: RestaurantSearchRequest
    ) -> list[RestaurantOption]:
        """Search restaurants using Google Places API with circuit breaker."""
        try:
            async with self.google_circuit_breaker:
                return await self.google_places_client.search_restaurants(request)
        except Exception as e:
            self.logger.warning(f"Google Places search failed: {e}")
        return []

    async def _search_zomato(self, request: RestaurantSearchRequest) -> list[RestaurantOption]:
        """Search restaurants using Zomato API with circuit breaker."""
        try:
            async with self.zomato_circuit_breaker:
                return await self.zomato_client.search_restaurants(request)
        except Exception as e:
            self.logger.warning(f"Zomato search failed: {e}")
        return []

    def _deduplicate_restaurants(
        self, restaurants: list[RestaurantOption]
    ) -> list[RestaurantOption]:
        """Remove duplicate restaurants based on name and location proximity."""
        if not restaurants:
            return restaurants

        unique_restaurants: list[RestaurantOption] = []
        seen_combinations: set[tuple[str, str]] = set()

        for restaurant in restaurants:
            # Create identifier based on name similarity and location proximity
            name_key = restaurant.name.lower().strip().replace(" ", "")
            location_key = f"{restaurant.location.latitude:.4f},{restaurant.location.longitude:.4f}"

            # Check for similar names within close proximity (100m)
            is_duplicate = False
            for seen_name, seen_location in seen_combinations:
                if self._names_similar(name_key, seen_name):
                    # Check if locations are within 100 meters
                    seen_lat, seen_lng = map(float, seen_location.split(","))
                    if (
                        restaurant.location.latitude is not None
                        and restaurant.location.longitude is not None
                    ):
                        distance = self._calculate_distance(
                            restaurant.location.latitude,
                            restaurant.location.longitude,
                            seen_lat,
                            seen_lng,
                        )
                        if distance < 0.1:  # Less than 100 meters
                            is_duplicate = True
                            break

            if not is_duplicate:
                unique_restaurants.append(restaurant)
                seen_combinations.add((name_key, location_key))

        self.logger.info(
            f"Deduplicated {len(restaurants)} to {len(unique_restaurants)} restaurants"
        )
        return unique_restaurants

    def _rank_restaurants(
        self, restaurants: list[RestaurantOption], request: RestaurantSearchRequest
    ) -> list[RestaurantOption]:
        """Rank restaurants based on ratings, price, and user preferences."""
        if not restaurants:
            return restaurants

        scored_restaurants: list[tuple[RestaurantOption, float]] = []

        for restaurant in restaurants:
            score = self._calculate_restaurant_score(restaurant, request)
            scored_restaurants.append((restaurant, score))

        # Sort by score descending
        scored_restaurants.sort(key=lambda x: x[1], reverse=True)

        return [restaurant for restaurant, score in scored_restaurants]

    def _names_similar(self, name1: str, name2: str) -> bool:
        """Check if two restaurant names are similar enough to be duplicates."""
        # Simple similarity check - could be enhanced with fuzzy matching
        if name1 == name2:
            return True

        # Remove spaces and compare
        name1_clean = name1.replace(" ", "").lower()
        name2_clean = name2.replace(" ", "").lower()

        if name1_clean == name2_clean:
            return True

        # Check if one name is contained in the other
        if len(name1_clean) > 3 and len(name2_clean) > 3:
            if name1_clean in name2_clean or name2_clean in name1_clean:
                return True

        return False

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers using Haversine formula."""
        import math

        # Convert to radians
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # Earth's radius in kilometers
        r = 6371

        return c * r

    def _calculate_restaurant_score(
        self, restaurant: RestaurantOption, request: RestaurantSearchRequest
    ) -> float:
        """Calculate ranking score for a restaurant based on multiple factors."""
        score = 0.0

        # Rating score (40% weight) - normalize to 0-40 scale
        if restaurant.rating:
            score += (restaurant.rating / 5.0) * 40

        # Review count bonus (10% weight) - logarithmic scale
        if restaurant.review_count and restaurant.review_count > 0:
            import math

            review_score = min(math.log10(restaurant.review_count + 1) / 3.0, 1.0) * 10
            score += review_score

        # Cuisine type matching (20% weight)
        if request.cuisine_type:
            if restaurant.cuisine_type == request.cuisine_type:
                score += 20
            elif restaurant.cuisine_type == CuisineType.LOCAL_SPECIALTY:
                score += 15  # Local specialties get bonus points

        # Price range matching (15% weight)
        if request.price_range:
            if restaurant.price_range == request.price_range:
                score += 15
            else:
                # Partial credit for adjacent price ranges
                price_order = [
                    PriceRange.BUDGET,
                    PriceRange.MODERATE,
                    PriceRange.EXPENSIVE,
                    PriceRange.VERY_EXPENSIVE,
                ]
                if request.price_range in price_order and restaurant.price_range in price_order:
                    req_idx = price_order.index(request.price_range)
                    rest_idx = price_order.index(restaurant.price_range)
                    if abs(req_idx - rest_idx) == 1:
                        score += 7.5  # Half credit for adjacent ranges

        # Dietary restrictions matching (10% weight)
        if request.dietary_restrictions:
            if restaurant.dietary_accommodations:
                matched_restrictions = len(
                    set(request.dietary_restrictions) & set(restaurant.dietary_accommodations)
                )
                if matched_restrictions > 0:
                    score += (matched_restrictions / len(request.dietary_restrictions)) * 10

        # Distance penalty (5% weight) - closer is better
        if restaurant.distance_km is not None:
            max_distance = request.radius_km or 10.0
            distance_score = max(0, (max_distance - restaurant.distance_km) / max_distance) * 5
            score += distance_score

        return min(score, 100.0)  # Cap at 100

    async def search_local_specialties(
        self, location: str, cuisine_type: str | None = None
    ) -> list[RestaurantOption]:
        """Search for local specialty restaurants and dishes.

        Args:
            location: Location to search for specialties
            cuisine_type: Optional specific cuisine type to focus on

        Returns:
            List of restaurants with local specialty recommendations
        """
        self.logger.info(f"Searching local specialties for {location}")

        try:
            # Build search request for local specialties
            specialty_search = RestaurantSearchRequest(
                location=location,
                latitude=None,
                longitude=None,
                cuisine_type=CuisineType.LOCAL_SPECIALTY if not cuisine_type else None,
                price_range=None,
                budget_per_person=None,
                meal_type=None,
                max_results=20,
                currency="USD",
                party_size=2,
            )

            # Search using Yelp and Google Places (better for local insights)
            tasks = [
                self._search_yelp(specialty_search),
                self._search_google_places(specialty_search),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            all_restaurants: list[RestaurantOption] = []
            for result in results:
                if isinstance(result, list):
                    all_restaurants.extend(result)

            # Filter for truly local specialties and high-rated places
            specialty_restaurants: list[RestaurantOption] = []
            for restaurant in all_restaurants:
                if self._is_local_specialty(restaurant, location):
                    # Enhance with local dish recommendations
                    restaurant = await self._enhance_with_local_dishes(restaurant, location)
                    specialty_restaurants.append(restaurant)

            # Remove duplicates and rank by specialty score
            unique_specialties = self._deduplicate_restaurants(specialty_restaurants)
            ranked_specialties = sorted(
                unique_specialties, key=lambda r: self._calculate_specialty_score(r), reverse=True
            )

            self.logger.info(f"Found {len(ranked_specialties)} local specialty restaurants")
            return ranked_specialties[:10]  # Top 10 specialties

        except Exception as e:
            self.logger.error(f"Local specialty search failed: {e}")
            return []

    async def filter_by_dietary_restrictions(
        self, restaurants: list[RestaurantOption], restrictions: list[str]
    ) -> list[RestaurantOption]:
        """Filter restaurants by dietary restrictions.

        Args:
            restaurants: List of restaurant options to filter
            restrictions: List of dietary restrictions (vegetarian, vegan, gluten-free, etc.)

        Returns:
            Filtered list of restaurants matching dietary requirements
        """
        self.logger.info(f"Filtering restaurants by dietary restrictions: {restrictions}")

        if not restrictions:
            return restaurants

        filtered_restaurants: list[tuple[RestaurantOption, float]] = []

        for restaurant in restaurants:
            # Check if restaurant accommodates all requested restrictions
            accommodates_all = True
            match_score = 0

            for restriction in restrictions:
                if self._restaurant_accommodates_restriction(restaurant, restriction):
                    match_score += 1
                else:
                    # For strict restrictions like vegan, must be explicitly accommodated
                    if restriction in ["vegan", "kosher", "halal"]:
                        accommodates_all = False
                        break
                    # For other restrictions, check cuisine type compatibility
                    elif restaurant.cuisine_type and not self._cuisine_compatible_with_restriction(
                        restaurant.cuisine_type, restriction
                    ):
                        accommodates_all = False
                        break

            if accommodates_all:
                filtered_restaurants.append((restaurant, match_score / len(restrictions)))

        # Sort by dietary compatibility score and extract restaurants
        filtered_restaurants.sort(key=lambda x: x[1], reverse=True)
        result = [restaurant for restaurant, score in filtered_restaurants]

        self.logger.info(f"Filtered to {len(result)} restaurants matching dietary restrictions")
        return result

    def _is_local_specialty(self, restaurant: RestaurantOption, location: str) -> bool:
        """Determine if a restaurant represents a local specialty."""
        # Check cuisine type
        if restaurant.cuisine_type == CuisineType.LOCAL_SPECIALTY:
            return True

        # Check if it's a highly rated local cuisine
        if restaurant.rating and restaurant.rating >= 4.0:
            # Look for location-specific cuisine indicators
            location_lower = location.lower()
            restaurant_name_lower = restaurant.name.lower()

            # Location-specific cuisine mapping
            local_indicators = {
                "new york": ["deli", "bagel", "pizza"],
                "chicago": ["deep dish", "italian beef"],
                "philadelphia": ["cheesesteak", "hoagie"],
                "new orleans": ["creole", "cajun", "beignet"],
                "san francisco": ["sourdough", "dim sum"],
                "boston": ["clam chowder", "lobster roll"],
                "texas": ["bbq", "tex-mex"],
                "maine": ["lobster"],
                "maryland": ["crab cake"],
            }

            for loc_key, indicators in local_indicators.items():
                if loc_key in location_lower:
                    for indicator in indicators:
                        if indicator in restaurant_name_lower:
                            return True

        return False

    async def _enhance_with_local_dishes(
        self, restaurant: RestaurantOption, location: str
    ) -> RestaurantOption:
        """Enhance restaurant with local dish recommendations."""
        # This would typically involve additional API calls or local knowledge base
        # For now, we'll add some basic local dish suggestions based on location
        local_dishes = self._get_local_dish_suggestions(location, restaurant.cuisine_type)

        if local_dishes:
            if not restaurant.popular_dishes:
                restaurant.popular_dishes = []
            restaurant.popular_dishes.extend(local_dishes)

        return restaurant

    def _get_local_dish_suggestions(
        self, location: str, cuisine_type: CuisineType | None
    ) -> list[PopularDish]:
        """Get local dish suggestions based on location and cuisine."""
        location_lower = location.lower()
        dishes: list[PopularDish] = []

        # Location-based specialty dishes
        if "new york" in location_lower:
            if cuisine_type == CuisineType.AMERICAN:
                dishes.append(
                    PopularDish(
                        name="New York Style Pizza",
                        description="Thin crust pizza with classic toppings",
                        is_specialty=True,
                        price=None,
                    )
                )
                dishes.append(
                    PopularDish(
                        name="Pastrami on Rye",
                        description="Classic NY deli sandwich",
                        is_specialty=True,
                        price=None,
                    )
                )
        elif "chicago" in location_lower:
            if cuisine_type == CuisineType.PIZZA:
                dishes.append(
                    PopularDish(
                        name="Chicago Deep Dish Pizza",
                        description="Thick crust pizza with layers of cheese and toppings",
                        is_specialty=True,
                        price=None,
                    )
                )
        elif "philadelphia" in location_lower:
            if cuisine_type == CuisineType.AMERICAN:
                dishes.append(
                    PopularDish(
                        name="Philly Cheesesteak",
                        description="Grilled sandwich with steak and cheese",
                        is_specialty=True,
                        price=None,
                    )
                )

        return dishes

    def _calculate_specialty_score(self, restaurant: RestaurantOption) -> float:
        """Calculate specialty score for local restaurants."""
        score = 0.0

        # Base rating score
        if restaurant.rating:
            score += restaurant.rating * 10

        # Local specialty bonus
        if restaurant.cuisine_type == CuisineType.LOCAL_SPECIALTY:
            score += 25

        # Popular dishes with specialty flag
        if restaurant.popular_dishes:
            specialty_dish_count = sum(1 for dish in restaurant.popular_dishes if dish.is_specialty)
            score += specialty_dish_count * 5

        # Review count indicates popularity
        if restaurant.review_count:
            import math

            score += min(math.log10(restaurant.review_count + 1), 10)

        return score

    def _restaurant_accommodates_restriction(
        self, restaurant: RestaurantOption, restriction: str
    ) -> bool:
        """Check if restaurant explicitly accommodates dietary restriction."""
        # Check explicitly listed accommodations
        accommodation_map = {
            "vegetarian": [DietaryRestriction.VEGETARIAN, DietaryRestriction.VEGAN],
            "vegan": [DietaryRestriction.VEGAN],
            "gluten_free": [DietaryRestriction.GLUTEN_FREE],
            "dairy_free": [DietaryRestriction.DAIRY_FREE],
            "nut_free": [DietaryRestriction.NUT_FREE],
            "halal": [DietaryRestriction.HALAL],
            "kosher": [DietaryRestriction.KOSHER],
            "keto": [DietaryRestriction.KETO],
            "paleo": [DietaryRestriction.PALEO],
        }

        required_accommodations = accommodation_map.get(restriction, [])
        if restaurant.dietary_accommodations:
            return any(acc in restaurant.dietary_accommodations for acc in required_accommodations)
        return False

    def _cuisine_compatible_with_restriction(
        self, cuisine_type: CuisineType, restriction: str
    ) -> bool:
        """Check if cuisine type is generally compatible with dietary restriction."""
        # Cuisine compatibility matrix
        compatibility = {
            "vegetarian": [
                CuisineType.VEGETARIAN,
                CuisineType.VEGAN,
                CuisineType.INDIAN,
                CuisineType.MEDITERRANEAN,
                CuisineType.THAI,
                CuisineType.ITALIAN,
            ],
            "vegan": [CuisineType.VEGAN, CuisineType.VEGETARIAN],
            "gluten_free": [
                CuisineType.SEAFOOD,
                CuisineType.STEAKHOUSE,
                CuisineType.INDIAN,
                CuisineType.THAI,
                CuisineType.MEXICAN,
            ],
            "dairy_free": [
                CuisineType.VEGAN,
                CuisineType.THAI,
                CuisineType.CHINESE,
                CuisineType.JAPANESE,
                CuisineType.SEAFOOD,
            ],
        }

        compatible_cuisines = compatibility.get(restriction, [])
        return cuisine_type in compatible_cuisines

    async def health_check(self) -> dict[str, Any]:
        """Enhanced health check including API service status."""
        status = await super().health_check()

        # Add API service health checks
        api_health: dict[str, str] = {}

        try:
            # Test Yelp API health
            api_health["yelp"] = (
                "healthy" if self.yelp_circuit_breaker.is_closed else "circuit_open"
            )
        except Exception:
            api_health["yelp"] = "unhealthy"

        try:
            # Test Google Places API health
            api_health["google_places"] = (
                "healthy" if self.google_circuit_breaker.is_closed else "circuit_open"
            )
        except Exception:
            api_health["google_places"] = "unhealthy"

        try:
            # Test Zomato API health
            api_health["zomato"] = (
                "healthy" if self.zomato_circuit_breaker.is_closed else "circuit_open"
            )
        except Exception:
            api_health["zomato"] = "unhealthy"

        status["dependencies"]["apis"] = api_health

        # Overall status degraded if any API is unhealthy or circuit is open
        if any(health != "healthy" for health in api_health.values()):
            status["status"] = "degraded"

        return status

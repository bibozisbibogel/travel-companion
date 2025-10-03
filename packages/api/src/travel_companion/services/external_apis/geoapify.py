"""Geoapify API client for restaurant and place discovery."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, cast

import httpx

from travel_companion.core.config import get_settings
from travel_companion.models.external import (
    ActivityCategory,
    ActivityLocation,
    ActivityOption,
    ActivitySearchRequest,
    RestaurantLocation,
    RestaurantOption,
    RestaurantSearchRequest,
    RestaurantSearchResponse,
)

# Note: Caching would use CacheManager when properly integrated
from travel_companion.utils.circuit_breaker import CircuitBreaker
from travel_companion.utils.errors import ExternalAPIError


class GeoapifyClient:
    """Client for interacting with Geoapify Places and Place Details APIs."""

    BASE_URL = "https://api.geoapify.com/v2"
    GEOCODING_URL = "https://api.geoapify.com/v1/geocode"
    PLACES_ENDPOINT = f"{BASE_URL}/places"
    PLACE_DETAILS_ENDPOINT = f"{BASE_URL}/place-details"
    GEOCODING_ENDPOINT = f"{GEOCODING_URL}/search"

    def __init__(self, redis_manager: Any = None) -> None:
        """Initialize Geoapify client with API credentials."""
        settings = get_settings()
        self.api_key = settings.geoapify_api_key
        if not self.api_key:
            raise ValueError("GEOAPIFY_API_KEY not configured")

        # For now, we'll handle caching more simply without redis dependency
        self.client = httpx.AsyncClient(timeout=30.0)
        self._request_count = 0
        self._rate_limit = 3000  # Free tier limit per day
        self._last_reset = datetime.now()
        self.logger = logging.getLogger(__name__)

        # Initialize circuit breakers for resilience
        self._restaurant_circuit = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=(ExternalAPIError, httpx.HTTPError, httpx.TimeoutException),
            name="geoapify_restaurants",
        )
        self._hotel_circuit = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=(ExternalAPIError, httpx.HTTPError, httpx.TimeoutException),
            name="geoapify_hotels",
        )
        self._activity_circuit = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=(ExternalAPIError, httpx.HTTPError, httpx.TimeoutException),
            name="geoapify_activities",
        )
        self._geocoding_circuit = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=(ExternalAPIError, httpx.HTTPError, httpx.TimeoutException),
            name="geoapify_geocoding",
        )

    async def __aenter__(self) -> "GeoapifyClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.client.aclose()

    def _check_rate_limit(self) -> None:
        """Check if we've exceeded rate limits."""
        # Reset counter if it's a new day
        if datetime.now().date() > self._last_reset.date():
            self._request_count = 0
            self._last_reset = datetime.now()

        if self._request_count >= self._rate_limit:
            raise ExternalAPIError(
                f"Geoapify API rate limit exceeded ({self._rate_limit} requests/day)"
            )

    async def search_restaurants(
        self, request: RestaurantSearchRequest
    ) -> RestaurantSearchResponse:
        """
        Search for restaurants using Geoapify Places API.

        Args:
            request: Restaurant search request parameters

        Returns:
            RestaurantSearchResponse with found restaurants

        Raises:
            ExternalAPIError: If API request fails
        """
        return cast(
            RestaurantSearchResponse,
            await self._restaurant_circuit.call(self._search_restaurants_impl, request),
        )

    async def _search_restaurants_impl(
        self, request: RestaurantSearchRequest
    ) -> RestaurantSearchResponse:
        """Implementation of restaurant search with circuit breaker protection."""
        try:
            # Check rate limit
            self._check_rate_limit()

            # Note: Caching would be implemented here with proper Redis integration

            # Build API parameters
            params: dict[str, str | int] = {
                "apiKey": self.api_key,
                "categories": ",".join(request.categories),
                "limit": request.max_results,
                "lang": "en",
            }

            # Add location filter
            if request.latitude is not None and request.longitude is not None:
                # Use circle filter with radius
                params["filter"] = (
                    f"circle:{request.longitude},{request.latitude},{request.radius_meters}"
                )
            elif request.location:
                # Need to geocode location name first to get coordinates
                try:
                    geocode_result = await self.geocode_city(request.location)
                    lon = geocode_result["longitude"]
                    lat = geocode_result["latitude"]
                    params["filter"] = f"circle:{lon},{lat},{request.radius_meters}"
                except ExternalAPIError as geocode_error:
                    self.logger.warning(
                        f"Failed to geocode location '{request.location}': {geocode_error}. "
                        "Falling back to text-based search."
                    )
                    # Fallback: use text parameter without filter (less precise)
                    params["text"] = request.location
                    # Remove filter as we don't have coordinates
                    params.pop("filter", None)

            # Make API request
            start_time = datetime.now()
            response = await self.client.get(self.PLACES_ENDPOINT, params=params)
            response.raise_for_status()
            self._request_count += 1

            # Parse response
            data = response.json()
            search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Transform to our model
            restaurants = []
            for feature in data.get("features", []):
                properties = feature.get("properties", {})
                geometry = feature.get("geometry", {})

                # Skip if no name
                if not properties.get("name"):
                    continue

                # Extract coordinates
                coords = geometry.get("coordinates", [0, 0])

                # Create restaurant option
                restaurant = RestaurantOption(
                    trip_id=None,  # No trip_id at search time
                    external_id=properties.get("place_id", ""),
                    name=properties.get("name", "Unknown"),
                    categories=properties.get("categories", []),
                    location=RestaurantLocation(
                        latitude=coords[1],
                        longitude=coords[0],
                        address=properties.get("address_line1"),
                        address_line2=properties.get("address_line2"),
                        city=properties.get("city"),
                        state=properties.get("state"),
                        country=properties.get("country"),
                        postal_code=properties.get("postcode"),
                        neighborhood=properties.get("neighbourhood"),
                    ),
                    formatted_address=properties.get("formatted"),
                    distance_meters=properties.get("distance"),
                    provider="geoapify",
                )
                restaurants.append(restaurant)

            # Create response
            result = RestaurantSearchResponse(
                restaurants=restaurants,
                total_results=len(restaurants),
                search_time_ms=search_time_ms,
                cached=False,
                cache_expires_at=datetime.now() + timedelta(minutes=30),
                search_metadata={
                    "provider": "geoapify",
                    "categories": request.categories,
                    "location": request.location or f"{request.latitude},{request.longitude}",
                },
            )

            # Note: Result caching would be implemented here

            self.logger.info(f"Found {len(restaurants)} restaurants via Geoapify")
            return result

        except httpx.HTTPStatusError as e:
            self.logger.error(f"Geoapify API HTTP error: {e.response.status_code}")
            raise ExternalAPIError(f"Geoapify API error: {e.response.text}") from e
        except httpx.TimeoutException:
            self.logger.error("Geoapify API request timeout")
            raise ExternalAPIError("Geoapify API request timeout") from None
        except Exception as e:
            self.logger.error(f"Unexpected error in Geoapify search: {str(e)}")
            raise ExternalAPIError(f"Failed to search restaurants: {str(e)}") from e

    async def get_place_details(self, place_id: str) -> dict[str, Any]:
        """
        Get detailed information about a specific place.

        Args:
            place_id: Geoapify place ID

        Returns:
            Dictionary with place details

        Raises:
            ExternalAPIError: If API request fails
        """
        try:
            # Check rate limit
            self._check_rate_limit()

            # Note: Place details caching would be implemented here

            # Make API request
            params = {
                "id": place_id,
                "apiKey": self.api_key,
                "features": "details,radius_500.restaurant",  # Get details and nearby restaurants
            }

            response = await self.client.get(self.PLACE_DETAILS_ENDPOINT, params=params)
            response.raise_for_status()
            self._request_count += 1

            data: dict[str, Any] = response.json()

            # Note: Result caching would be implemented here

            self.logger.info(f"Retrieved place details for {place_id}")
            return data

        except httpx.HTTPStatusError as e:
            self.logger.error(f"Geoapify Place Details API error: {e.response.status_code}")
            raise ExternalAPIError(f"Geoapify API error: {e.response.text}") from e
        except httpx.TimeoutException:
            self.logger.error("Geoapify Place Details API timeout")
            raise ExternalAPIError("Geoapify API request timeout") from None
        except Exception as e:
            self.logger.error(f"Unexpected error getting place details: {str(e)}")
            raise ExternalAPIError(f"Failed to get place details: {str(e)}") from e

    def _build_cache_key(self, request: RestaurantSearchRequest) -> str:
        """Build cache key from search request."""
        parts = ["geoapify", "restaurants"]

        if request.location:
            parts.append(request.location.lower().replace(" ", "_"))
        elif request.latitude and request.longitude:
            parts.append(f"{request.latitude:.3f}_{request.longitude:.3f}")

        parts.append("_".join(sorted(request.categories)))
        parts.append(f"r{request.radius_meters}")
        parts.append(f"l{request.max_results}")

        return ":".join(parts)

    async def search_hotels(
        self,
        location: str,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_meters: int = 5000,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search for hotels using Geoapify Places API.

        Args:
            location: Search location (city name, address, etc.)
            latitude: Latitude for geo-based search
            longitude: Longitude for geo-based search
            radius_meters: Search radius in meters (default: 5000m)
            max_results: Maximum number of results (default: 20)

        Returns:
            List of hotel data dictionaries with coordinates and names

        Raises:
            ExternalAPIError: If API request fails
        """
        return cast(
            list[dict[str, Any]],
            await self._hotel_circuit.call(
                self._search_hotels_impl, location, latitude, longitude, radius_meters, max_results
            ),
        )

    async def _search_hotels_impl(
        self,
        location: str,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_meters: int = 5000,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """Implementation of hotel search with circuit breaker protection."""
        try:
            # Check rate limit
            self._check_rate_limit()

            # Build API parameters for hotel search
            params: dict[str, str | int] = {
                "apiKey": self.api_key,
                "categories": "accommodation.hotel",  # Geoapify hotel category
                "limit": max_results,
                "lang": "en",
            }

            # Add location filter
            if latitude is not None and longitude is not None:
                # Use circle filter with coordinates
                params["filter"] = f"circle:{longitude},{latitude},{radius_meters}"
            elif location:
                # Use filter for location name search (bias requires coordinates)
                params["filter"] = f"circle:{location},{radius_meters}"
            else:
                raise ValueError("Either location name or lat/lon coordinates must be provided")

            # Make API request
            start_time = datetime.now()
            response = await self.client.get(self.PLACES_ENDPOINT, params=params)
            response.raise_for_status()
            self._request_count += 1

            # Parse response
            data = response.json()
            search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Transform to simplified hotel data
            hotels = []
            for feature in data.get("features", []):
                properties = feature.get("properties", {})
                geometry = feature.get("geometry", {})

                # Skip if no name
                name = properties.get("name")
                if not name:
                    continue

                # Extract coordinates
                coords = geometry.get("coordinates", [0, 0])
                if len(coords) < 2:
                    continue

                # Create hotel data dict
                hotel_data = {
                    "name": name,
                    "latitude": coords[1],  # GeoJSON uses [lon, lat] format
                    "longitude": coords[0],
                    "address": properties.get("address_line1"),
                    "city": properties.get("city"),
                    "country": properties.get("country"),
                    "place_id": properties.get("place_id", ""),
                    "distance_meters": properties.get("distance"),
                    "formatted_address": properties.get("formatted"),
                }
                hotels.append(hotel_data)

            self.logger.info(f"Found {len(hotels)} hotels via Geoapify in {search_time_ms}ms")
            return hotels

        except httpx.HTTPStatusError as e:
            self.logger.error(f"Geoapify Hotels API HTTP error: {e.response.status_code}")
            raise ExternalAPIError(f"Geoapify API error: {e.response.text}") from e
        except httpx.TimeoutException:
            self.logger.error("Geoapify Hotels API request timeout")
            raise ExternalAPIError("Geoapify API request timeout") from None
        except Exception as e:
            self.logger.error(f"Unexpected error in Geoapify hotel search: {str(e)}")
            raise ExternalAPIError(f"Failed to search hotels: {str(e)}") from e

    async def search_activities(
        self,
        request: ActivitySearchRequest,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_meters: int = 5000,
    ) -> list[ActivityOption]:
        """
        Search for activities using Geoapify Places API.

        Args:
            request: Activity search request with filters
            latitude: Latitude for geo-based search
            longitude: Longitude for geo-based search
            radius_meters: Search radius in meters (default: 5000m)

        Returns:
            List of ActivityOption objects

        Raises:
            ExternalAPIError: If API request fails
        """
        return cast(
            list[ActivityOption],
            await self._activity_circuit.call(
                self._search_activities_impl, request, latitude, longitude, radius_meters
            ),
        )

    async def _search_activities_impl(
        self,
        request: ActivitySearchRequest,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_meters: int = 5000,
    ) -> list[ActivityOption]:
        """Implementation of activity search with circuit breaker protection."""
        try:
            # Check rate limit
            self._check_rate_limit()

            # Map activity categories to Geoapify categories
            geoapify_categories = self._map_activity_categories(request.category)

            # Build API parameters for activity search
            params: dict[str, str | int] = {
                "apiKey": self.api_key,
                "categories": ",".join(geoapify_categories),
                "limit": min(request.max_results, 100),  # Geoapify limit
                "lang": "en",
            }

            # Add location filter - Geoapify requires at least one location parameter
            if latitude is not None and longitude is not None:
                # Use circle filter with coordinates
                params["filter"] = f"circle:{longitude},{latitude},{radius_meters}"
            elif request.location:
                # Use text search (bias parameter requires coordinates, not location names)
                params["text"] = request.location
            else:
                raise ValueError("Either location name or lat/lon coordinates must be provided")

            # Make API request
            start_time = datetime.now()
            response = await self.client.get(self.PLACES_ENDPOINT, params=params)
            response.raise_for_status()
            self._request_count += 1

            # Parse response
            data = response.json()
            search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Transform to ActivityOption objects
            activities = []
            for feature in data.get("features", []):
                properties = feature.get("properties", {})
                geometry = feature.get("geometry", {})

                # Skip if no name
                name = properties.get("name")
                if not name:
                    continue

                # Extract coordinates
                coords = geometry.get("coordinates", [0, 0])
                if len(coords) < 2:
                    continue

                # Create activity location
                activity_location = ActivityLocation(
                    latitude=coords[1],  # GeoJSON uses [lon, lat] format
                    longitude=coords[0],
                    address=properties.get("address_line1"),
                    city=properties.get("city"),
                    country=properties.get("country"),
                    postal_code=properties.get("postcode"),
                )

                # Determine activity category from Geoapify data
                activity_category = self._determine_activity_category(properties, request.category)

                # Create activity option
                activity = ActivityOption(
                    external_id=f"geoapify_{properties.get('place_id', '')}",
                    name=name,
                    description=properties.get("description", ""),
                    category=activity_category,
                    location=activity_location,
                    duration_minutes=None,  # Geoapify doesn't provide duration
                    price=Decimal("0"),  # Geoapify doesn't provide pricing
                    currency="USD",
                    rating=None,  # Geoapify doesn't provide ratings
                    review_count=None,
                    images=[],
                    booking_url=properties.get("website"),
                    provider="geoapify",
                    trip_id=None,  # Not associated with a specific trip at search time
                    created_at=datetime.now(),
                )
                activities.append(activity)

            self.logger.info(
                f"Found {len(activities)} activities via Geoapify in {search_time_ms}ms"
            )
            return activities

        except httpx.HTTPStatusError as e:
            self.logger.error(f"Geoapify Activities API HTTP error: {e.response.status_code}")
            raise ExternalAPIError(f"Geoapify API error: {e.response.text}") from e
        except httpx.TimeoutException:
            self.logger.error("Geoapify Activities API request timeout")
            raise ExternalAPIError("Geoapify API request timeout") from None
        except Exception as e:
            self.logger.error(f"Unexpected error in Geoapify activity search: {str(e)}")
            raise ExternalAPIError(f"Failed to search activities: {str(e)}") from e

    def _map_activity_categories(self, category: ActivityCategory | None) -> list[str]:
        """
        Map ActivityCategory to Geoapify place categories.

        Args:
            category: Activity category filter

        Returns:
            List of Geoapify category strings
        """
        # Default categories for general activity search using valid Geoapify categories
        if not category:
            return [
                "tourism.attraction",
                "entertainment.museum",
                "entertainment.cinema",
                "leisure.park",
                "commercial.shopping_mall",
                "catering.restaurant",
            ]

        # Map specific categories to valid Geoapify categories
        category_mapping = {
            ActivityCategory.CULTURAL: [
                "entertainment.museum",
                "tourism.attraction.artwork",
                "tourism.sights.place_of_worship",
                "tourism.sights.castle",
                "tourism.sights.memorial",
                "tourism.sights",
            ],
            ActivityCategory.ADVENTURE: [
                "sport.stadium",
                "sport.swimming_pool",
                "sport.fitness",
                "entertainment.activity_park",
                "commercial.outdoor_and_sport",
            ],
            ActivityCategory.FOOD: [
                "catering.restaurant",
                "catering.cafe",
                "catering.bar",
                "catering.fast_food",
                "commercial.food_and_drink",
            ],
            ActivityCategory.ENTERTAINMENT: [
                "entertainment.cinema",
                "entertainment.culture.theatre",
                "entertainment.zoo",
                "entertainment.aquarium",
                "entertainment.culture",
                "entertainment.amusement_arcade",
            ],
            ActivityCategory.NATURE: [
                "leisure.park",
                "natural.forest",
                "natural.water",
                "natural.mountain",
                "national_park",
                "leisure.playground",
            ],
            ActivityCategory.SHOPPING: [
                "commercial.shopping_mall",
                "commercial.marketplace",
                "commercial.department_store",
                "commercial.books",
                "commercial.clothing",
            ],
            ActivityCategory.RELAXATION: [
                "leisure.spa",
                "leisure.park.garden",
                "service.beauty.spa",
                "leisure.picnic",
                "beach",
            ],
            ActivityCategory.NIGHTLIFE: [
                "catering.bar",
                "catering.pub",
                "adult.nightclub",
                "adult.casino",
                "catering.biergarten",
            ],
        }

        return category_mapping.get(
            category, ["tourism.attraction", "entertainment", "leisure.park"]
        )

    def _determine_activity_category(
        self, properties: dict[str, Any], requested_category: ActivityCategory | None
    ) -> ActivityCategory:
        """
        Determine activity category from Geoapify properties.

        Args:
            properties: Geoapify place properties
            requested_category: User-requested category (preferred if matches)

        Returns:
            Determined ActivityCategory
        """
        geoapify_categories = properties.get("categories", [])

        # If user requested a specific category and we have matches, use it
        if requested_category:
            category_keywords = {
                ActivityCategory.CULTURAL: [
                    "museum",
                    "heritage",
                    "monument",
                    "gallery",
                    "historic",
                ],
                ActivityCategory.ADVENTURE: ["sport", "climbing", "water_sports", "adventure"],
                ActivityCategory.FOOD: ["restaurant", "cafe", "bar", "food", "catering"],
                ActivityCategory.ENTERTAINMENT: ["cinema", "theatre", "casino", "entertainment"],
                ActivityCategory.NATURE: ["park", "forest", "beach", "mountain", "natural"],
                ActivityCategory.SHOPPING: ["shopping", "mall", "marketplace", "retail"],
                ActivityCategory.RELAXATION: ["spa", "garden", "leisure"],
                ActivityCategory.NIGHTLIFE: ["nightclub", "bar", "pub", "casino"],
            }

            keywords = category_keywords.get(requested_category, [])
            if any(keyword in str(geoapify_categories).lower() for keyword in keywords):
                return requested_category

        # Auto-detect based on Geoapify categories
        categories_str = " ".join(geoapify_categories).lower()

        if any(word in categories_str for word in ["museum", "heritage", "monument", "gallery"]):
            return ActivityCategory.CULTURAL
        elif any(word in categories_str for word in ["sport", "climbing", "adventure"]):
            return ActivityCategory.ADVENTURE
        elif any(word in categories_str for word in ["restaurant", "cafe", "bar", "food"]):
            return ActivityCategory.FOOD
        elif any(word in categories_str for word in ["cinema", "theatre", "entertainment"]):
            return ActivityCategory.ENTERTAINMENT
        elif any(word in categories_str for word in ["park", "forest", "beach", "natural"]):
            return ActivityCategory.NATURE
        elif any(word in categories_str for word in ["shopping", "mall", "retail"]):
            return ActivityCategory.SHOPPING
        elif any(word in categories_str for word in ["spa", "leisure"]):
            return ActivityCategory.RELAXATION
        elif any(word in categories_str for word in ["nightclub", "casino"]):
            return ActivityCategory.NIGHTLIFE
        else:
            # Default fallback
            return requested_category or ActivityCategory.ENTERTAINMENT

    async def geocode_city(
        self, city_name: str, country: str | None = None, state: str | None = None
    ) -> dict[str, Any]:
        """
        Get coordinates for a city using Geoapify Geocoding API.

        Args:
            city_name: Name of the city to geocode
            country: Optional country name or ISO code for more precise results
            state: Optional state/province name for more precise results

        Returns:
            Dictionary with city coordinates and details:
                - latitude: City latitude
                - longitude: City longitude
                - formatted_address: Full formatted address
                - city: Normalized city name
                - country: Country name
                - state: State/province name
                - bbox: Bounding box coordinates
                - confidence: Geocoding confidence score

        Raises:
            ExternalAPIError: If geocoding fails or no results found
        """
        return cast(
            dict[str, Any],
            await self._geocoding_circuit.call(self._geocode_city_impl, city_name, country, state),
        )

    async def _geocode_city_impl(
        self, city_name: str, country: str | None = None, state: str | None = None
    ) -> dict[str, Any]:
        """Implementation of city geocoding with circuit breaker protection."""
        try:
            # Check rate limit
            self._check_rate_limit()

            # Build search text
            search_parts = [city_name]
            if state:
                search_parts.append(state)
            if country:
                search_parts.append(country)
            search_text = ", ".join(search_parts)

            # Build API parameters
            params: dict[str, str | int] = {
                "apiKey": self.api_key,
                "text": search_text,
                "type": "city",  # Focus on city-level results
                "format": "json",
                "limit": 1,  # Get best match only
                "lang": "en",
            }

            # Add filters if provided
            if country:
                # Support both country names and ISO codes
                params["filter"] = f"countrycode:{country.lower()}" if len(country) == 2 else ""

            # Make API request
            start_time = datetime.now()
            response = await self.client.get(self.GEOCODING_ENDPOINT, params=params)
            response.raise_for_status()
            self._request_count += 1

            # Parse response
            data = response.json()
            search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Check if we got results
            results = data.get("results", [])
            if not results:
                raise ExternalAPIError(f"No geocoding results found for city: {search_text}")

            # Get the best result (first one)
            best_result = results[0]

            # Extract bounding box
            bbox = best_result.get("bbox", {})

            # Build response dictionary
            # Note: Geocoding API returns fields at result level, not in properties
            geocoding_result = {
                "latitude": best_result.get("lat"),
                "longitude": best_result.get("lon"),
                "formatted_address": best_result.get("formatted", ""),
                "city": best_result.get("city", city_name),
                "country": best_result.get("country", ""),
                "country_code": best_result.get("country_code", ""),
                "state": best_result.get("state", ""),
                "county": best_result.get("county", ""),
                "postcode": best_result.get("postcode", ""),
                "bbox": {
                    "min_lat": bbox.get("lat1"),
                    "max_lat": bbox.get("lat2"),
                    "min_lon": bbox.get("lon1"),
                    "max_lon": bbox.get("lon2"),
                },
                "confidence": best_result.get("rank", {}).get("confidence", 0),
                "importance": best_result.get("rank", {}).get("importance", 0),
                "place_id": best_result.get("place_id", ""),
                "osm_id": best_result.get("osm_id", ""),
                "search_time_ms": search_time_ms,
            }

            # Validate we have coordinates
            if geocoding_result["latitude"] is None or geocoding_result["longitude"] is None:
                raise ExternalAPIError(f"Invalid coordinates returned for city: {search_text}")

            self.logger.info(
                f"Geocoded city '{search_text}' to "
                f"({geocoding_result['latitude']}, {geocoding_result['longitude']}) "
                f"in {search_time_ms}ms"
            )

            return geocoding_result

        except httpx.HTTPStatusError as e:
            self.logger.error(f"Geoapify Geocoding API HTTP error: {e.response.status_code}")
            raise ExternalAPIError(f"Geoapify Geocoding API error: {e.response.text}") from e
        except httpx.TimeoutException:
            self.logger.error("Geoapify Geocoding API request timeout")
            raise ExternalAPIError("Geoapify Geocoding API request timeout") from None
        except ExternalAPIError:
            # Re-raise our custom errors as-is
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in Geoapify geocoding: {str(e)}")
            raise ExternalAPIError(f"Failed to geocode city: {str(e)}") from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

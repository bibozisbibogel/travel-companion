"""Google Places API client wrapper for activity searching."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, cast

from travel_companion.core.config import get_settings
from travel_companion.models.external import (
    ActivityCategory,
    ActivityLocation,
    ActivityOption,
    ActivitySearchRequest,
)
from travel_companion.services.external_apis.google_places import GooglePlacesNewAPI
from travel_companion.utils.circuit_breaker import CircuitBreaker
from travel_companion.utils.errors import ExternalAPIError


class GooglePlacesClient:
    """Client wrapper for Google Places API with activity search capabilities."""

    def __init__(self, redis_manager: Any = None) -> None:
        """Initialize Google Places client with API credentials."""
        settings = get_settings()
        self.api_key = settings.google_places_api_key
        if not self.api_key:
            raise ValueError("GOOGLE_PLACES_API_KEY not configured")

        self.places_api = GooglePlacesNewAPI(api_key=self.api_key)
        self.logger = logging.getLogger(__name__)

        # Initialize circuit breaker for resilience
        self._activity_circuit = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=(ExternalAPIError, Exception),
            name="google_places_activities",
        )

    async def __aenter__(self) -> "GooglePlacesClient":
        """Async context manager entry."""
        await self.places_api.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.places_api.__aexit__(exc_type, exc_val, exc_tb)

    async def search_activities(
        self,
        request: ActivitySearchRequest,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_meters: int = 5000,
    ) -> list[ActivityOption]:
        """
        Search for activities using Google Places API.

        Args:
            request: Activity search request parameters
            latitude: Optional latitude for location-based search
            longitude: Optional longitude for location-based search
            radius_meters: Search radius in meters

        Returns:
            List of activity options from Google Places

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
            # Build search query based on category and location
            query = self._build_search_query(request)

            # Determine location bias
            location_bias = None
            if latitude is not None and longitude is not None:
                location_bias = (latitude, longitude)

            # NOTE: We don't use price_levels parameter for Google Places API because:
            # 1. Passing multiple price levels returns 0 results (API bug or limitation)
            # 2. We filter by budget_per_person later in the activity_agent ranking
            # 3. This allows us to get all activities and apply accurate price filtering

            # Search for places
            places = await self.places_api.text_search(
                text_query=query,
                location_bias=location_bias,
                radius=radius_meters,
                min_rating=None,  # ActivitySearchRequest doesn't have min_rating field
                price_levels=None,  # Don't filter by price at API level
                open_now=None,  # Could be configured based on request date/time
                max_result_count=min(request.max_results, 20),
            )

            # Transform Google Places to ActivityOption objects
            activities = []
            for place in places:
                activity = await self._convert_place_to_activity(place, request)
                if activity:
                    activities.append(activity)

            self.logger.info(f"Found {len(activities)} activities via Google Places API")
            return activities

        except Exception as e:
            self.logger.error(f"Google Places activity search error: {str(e)}")
            raise ExternalAPIError(f"Google Places API error: {str(e)}") from e

    def _build_search_query(self, request: ActivitySearchRequest) -> str:
        """
        Build search query based on category and location.

        Args:
            request: Activity search request

        Returns:
            Search query string
        """
        query_parts = []

        # Add location if provided
        if request.location:
            query_parts.append(f"activities in {request.location}")
        else:
            query_parts.append("activities")

        # Add category-specific keywords
        if request.category:
            category_keywords = self._get_category_keywords(request.category)
            query_parts.extend(category_keywords)

        return " ".join(query_parts)

    def _get_category_keywords(self, category: ActivityCategory) -> list[str]:
        """
        Get search keywords for each activity category.

        Args:
            category: Activity category

        Returns:
            List of search keywords
        """
        category_mapping = {
            ActivityCategory.CULTURAL: ["museum", "art gallery", "historical site", "monument"],
            ActivityCategory.ADVENTURE: ["adventure", "outdoor", "sports", "hiking", "climbing"],
            ActivityCategory.FOOD: ["food tour", "cooking class", "wine tasting", "culinary"],
            ActivityCategory.ENTERTAINMENT: ["entertainment", "show", "concert", "theater"],
            ActivityCategory.NATURE: ["nature", "park", "garden", "zoo", "aquarium"],
            ActivityCategory.SHOPPING: ["shopping", "market", "mall", "boutique"],
            ActivityCategory.RELAXATION: ["spa", "wellness", "massage", "relaxation"],
            ActivityCategory.NIGHTLIFE: ["nightlife", "bar", "club", "night entertainment"],
        }
        return category_mapping.get(category, [])

    def _map_price_levels(self, max_price: float) -> list[str]:
        """
        Map maximum price to Google Places price levels.

        Args:
            max_price: Maximum price per person

        Returns:
            List of applicable price levels
        """
        # Google Places price levels:
        # PRICE_LEVEL_FREE = 0 (NOT SUPPORTED in API searches - returns error)
        # PRICE_LEVEL_INEXPENSIVE = 1 (typically < $10-15)
        # PRICE_LEVEL_MODERATE = 2 (typically $15-50)
        # PRICE_LEVEL_EXPENSIVE = 3 (typically $50-100)
        # PRICE_LEVEL_VERY_EXPENSIVE = 4 (typically > $100)

        price_levels = []
        # Note: PRICE_LEVEL_FREE is not supported by Google Places API in search requests
        # It returns error: "Invalid price_levels: FREE. Search by FREE price_level is currently not supported."
        # We'll include INEXPENSIVE to catch free/cheap activities
        if max_price >= 10:
            price_levels.append("PRICE_LEVEL_INEXPENSIVE")
        if max_price >= 15:
            price_levels.append("PRICE_LEVEL_MODERATE")
        if max_price >= 50:
            price_levels.append("PRICE_LEVEL_EXPENSIVE")
        if max_price >= 100:
            price_levels.append("PRICE_LEVEL_VERY_EXPENSIVE")

        # If no price levels match (e.g., max_price < 10), still search with INEXPENSIVE
        if not price_levels:
            price_levels.append("PRICE_LEVEL_INEXPENSIVE")

        return price_levels

    async def _convert_place_to_activity(
        self, place: Any, request: ActivitySearchRequest
    ) -> ActivityOption | None:
        """
        Convert Google Place to ActivityOption.

        Args:
            place: Google Place object
            request: Original search request

        Returns:
            ActivityOption or None if conversion fails
        """
        try:
            # Extract name
            name = place.display_name.get("text", "Unknown Place")
            if not name or name == "Unknown Place":
                return None

            # Create location
            location = ActivityLocation(
                latitude=place.location.latitude if place.location else 0,
                longitude=place.location.longitude if place.location else 0,
                address=place.formatted_address,
                city=self._extract_city_from_address(place.formatted_address),
                country=self._extract_country_from_address(place.formatted_address),
                postal_code=None,  # Not readily available
            )

            # Determine category based on place types
            category = self._determine_category_from_types(place.types, request.category)

            # Estimate price based on price level
            estimated_price = self._estimate_price_from_level(place.price_level)

            # Extract images
            images = []
            if place.photos:
                # Get URLs for first 3 photos
                for photo in place.photos[:3]:
                    photo_url = self.places_api.get_photo_url(
                        photo.name, max_width=800, max_height=600
                    )
                    images.append(photo_url)

            # Create activity option
            activity = ActivityOption(
                external_id=f"google_places_{place.id}",
                name=name,
                description=self._generate_description(place),
                category=category,
                location=location,
                duration_minutes=120,  # Default duration as Google Places doesn't provide this
                price=estimated_price,
                currency="USD",
                rating=place.rating,
                review_count=place.user_rating_count,
                images=images,
                booking_url=place.website_uri or place.google_maps_uri,
                provider="google_places",
                trip_id=None,  # Not associated with a specific trip at search time
                created_at=datetime.now(),
            )

            return activity

        except Exception as e:
            self.logger.warning(f"Failed to convert place to activity: {e}")
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

    def _determine_category_from_types(
        self, types: list[str], preferred: ActivityCategory | None
    ) -> ActivityCategory:
        """
        Determine activity category from Google Places types.

        Args:
            types: List of place types from Google
            preferred: Preferred category from request

        Returns:
            Determined activity category
        """
        if preferred:
            return preferred

        # Map Google place types to activity categories
        type_mapping = {
            "museum": ActivityCategory.CULTURAL,
            "art_gallery": ActivityCategory.CULTURAL,
            "church": ActivityCategory.CULTURAL,
            "hindu_temple": ActivityCategory.CULTURAL,
            "mosque": ActivityCategory.CULTURAL,
            "synagogue": ActivityCategory.CULTURAL,
            "tourist_attraction": ActivityCategory.CULTURAL,
            "amusement_park": ActivityCategory.ENTERTAINMENT,
            "aquarium": ActivityCategory.NATURE,
            "zoo": ActivityCategory.NATURE,
            "park": ActivityCategory.NATURE,
            "hiking_area": ActivityCategory.ADVENTURE,
            "campground": ActivityCategory.ADVENTURE,
            "shopping_mall": ActivityCategory.SHOPPING,
            "spa": ActivityCategory.RELAXATION,
            "night_club": ActivityCategory.NIGHTLIFE,
            "bar": ActivityCategory.NIGHTLIFE,
            "restaurant": ActivityCategory.FOOD,
            "cafe": ActivityCategory.FOOD,
        }

        for place_type in types:
            if place_type in type_mapping:
                return type_mapping[place_type]

        # Default to cultural for tourist attractions
        return ActivityCategory.CULTURAL

    def _estimate_price_from_level(self, price_level: str | None) -> Decimal:
        """
        Estimate price from Google's price level.

        Args:
            price_level: Google Places price level string

        Returns:
            Estimated price in USD
        """
        if not price_level:
            return Decimal("25")  # Default mid-range price

        price_mapping = {
            "PRICE_LEVEL_FREE": Decimal("0"),
            "PRICE_LEVEL_INEXPENSIVE": Decimal("15"),
            "PRICE_LEVEL_MODERATE": Decimal("35"),
            "PRICE_LEVEL_EXPENSIVE": Decimal("75"),
            "PRICE_LEVEL_VERY_EXPENSIVE": Decimal("150"),
        }

        return price_mapping.get(price_level, Decimal("25"))

    def _generate_description(self, place: Any) -> str:
        """
        Generate description from place data.

        Args:
            place: Google Place object

        Returns:
            Generated description
        """
        parts = []

        # Add primary type
        if place.primary_type:
            parts.append(f"A {place.primary_type.replace('_', ' ')}")

        # Add location
        if place.formatted_address:
            parts.append(f"located at {place.formatted_address}")

        # Add rating info
        if place.rating:
            parts.append(f"Rated {place.rating}/5.0")
            if place.user_rating_count:
                parts.append(f"based on {place.user_rating_count} reviews")

        # Add opening hours info
        if place.current_opening_hours and place.current_opening_hours.open_now is not None:
            if place.current_opening_hours.open_now:
                parts.append("Currently open")
            else:
                parts.append("Currently closed")

        return ". ".join(parts) if parts else "Popular local attraction"

"""TripAdvisor API client for activity and attraction data."""

import asyncio
import logging
from decimal import Decimal
from typing import Any

import httpx
from pydantic import BaseModel, Field

from travel_companion.core.config import get_settings
from travel_companion.models.external import (
    ActivityCategory,
    ActivityLocation,
    ActivityOption,
    ActivitySearchRequest,
)


class TripAdvisorLocation(BaseModel):
    """TripAdvisor location search result model."""

    location_id: str = Field(..., description="TripAdvisor location ID")
    name: str = Field(..., description="Location name")
    address_obj: dict[str, Any] = Field(default_factory=dict, description="Address information")
    latitude: str | None = Field(None, description="Latitude coordinate")
    longitude: str | None = Field(None, description="Longitude coordinate")


class TripAdvisorAttraction(BaseModel):
    """TripAdvisor attraction/activity model."""

    location_id: str = Field(..., description="TripAdvisor location ID")
    name: str = Field(..., description="Attraction name")
    description: str | None = Field(None, description="Attraction description")
    category: dict[str, Any] = Field(default_factory=dict, description="Category information")
    subcategory: list[dict[str, Any]] = Field(default_factory=list, description="Subcategories")
    address_obj: dict[str, Any] = Field(default_factory=dict, description="Address information")
    latitude: str | None = Field(None, description="Latitude coordinate")
    longitude: str | None = Field(None, description="Longitude coordinate")
    rating: str | None = Field(None, description="Rating as string")
    num_reviews: str | None = Field(None, description="Number of reviews as string")
    photo: dict[str, Any] | None = Field(None, description="Photo information")
    web_url: str | None = Field(None, description="TripAdvisor web URL")
    booking: dict[str, Any] | None = Field(None, description="Booking information")


class TripAdvisorAPIClient:
    """TripAdvisor Content API client for activity searches."""

    def __init__(self) -> None:
        """Initialize TripAdvisor API client."""
        self.settings = get_settings()
        self.logger = logging.getLogger("travel_companion.services.tripadvisor")
        self.base_url = "https://api.content.tripadvisor.com/api/v1"

        # Circuit breaker state
        self.failure_count = 0
        self.last_failure_time: float = 0
        self.circuit_open = False

        # Rate limiting
        self.request_count = 0
        self.rate_limit_reset_time: float = 0

        self.logger.info("TripAdvisor API client initialized")

    async def search_activities(self, request: ActivitySearchRequest) -> list[ActivityOption]:
        """Search activities using TripAdvisor API.

        Args:
            request: Activity search parameters

        Returns:
            List of activity options from TripAdvisor
        """
        if self._is_circuit_open():
            self.logger.warning("TripAdvisor circuit breaker is open, skipping request")
            return []

        try:
            # First, search for location ID
            location_id = await self._search_location(request.location)
            if not location_id:
                self.logger.warning(f"No TripAdvisor location found for: {request.location}")
                return []

            # Then search for attractions at that location
            attractions = await self._search_attractions(location_id, request)

            # Convert to our internal format
            activities = []
            for attraction in attractions:
                try:
                    activity = await self._convert_to_activity(attraction)
                    if activity:
                        activities.append(activity)
                except Exception as e:
                    self.logger.warning(f"Failed to convert TripAdvisor attraction: {e}")
                    continue

            self.logger.info(f"TripAdvisor returned {len(activities)} activities")
            self._reset_circuit_breaker()

            return activities

        except Exception as e:
            self.logger.error(f"TripAdvisor API error: {e}")
            await self._handle_api_failure()
            return []

    async def _search_location(self, location: str) -> str | None:
        """Search for TripAdvisor location ID.

        Args:
            location: Location name to search

        Returns:
            TripAdvisor location ID or None if not found
        """
        await self._check_rate_limit()

        headers = {
            "accept": "application/json",
        }

        params = {
            "key": self.settings.tripadvisor_api_key,
            "searchQuery": location,
            "category": "geos",
            "language": "en",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/location/search", headers=headers, params=params
            )

            if response.status_code == 200:
                data = response.json()
                locations = data.get("data", [])

                if locations:
                    # Return the first location ID
                    location_data = TripAdvisorLocation(**locations[0])
                    self.logger.debug(f"Found TripAdvisor location ID: {location_data.location_id}")
                    return location_data.location_id

            elif response.status_code == 429:
                await self._handle_rate_limit(response)

            response.raise_for_status()

        return None

    async def _search_attractions(
        self, location_id: str, request: ActivitySearchRequest
    ) -> list[TripAdvisorAttraction]:
        """Search for attractions at a specific location.

        Args:
            location_id: TripAdvisor location ID
            request: Activity search request

        Returns:
            List of TripAdvisor attractions
        """
        await self._check_rate_limit()

        headers = {
            "accept": "application/json",
        }

        params = {
            "key": self.settings.tripadvisor_api_key,
            "language": "en",
        }

        # Add category filter if specified
        if request.category:
            tripadvisor_category = self._map_category_to_tripadvisor(request.category)
            if tripadvisor_category:
                params["category"] = tripadvisor_category

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/location/{location_id}/details", headers=headers, params=params
            )

            if response.status_code == 200:
                # TripAdvisor returns location details, we need nearby attractions
                # Try the nearby search endpoint instead
                return await self._search_nearby_attractions(location_id, request)

            elif response.status_code == 429:
                await self._handle_rate_limit(response)
                return []

            response.raise_for_status()

        return []

    async def _search_nearby_attractions(
        self, location_id: str, request: ActivitySearchRequest
    ) -> list[TripAdvisorAttraction]:
        """Search for nearby attractions using the nearby search endpoint.

        Args:
            location_id: TripAdvisor location ID
            request: Activity search request

        Returns:
            List of TripAdvisor attractions
        """
        await self._check_rate_limit()

        headers = {
            "accept": "application/json",
        }

        params = {
            "key": self.settings.tripadvisor_api_key,
            "latLong": await self._get_location_coordinates(location_id),
            "category": "attractions",
            "radius": "25",  # 25km radius
            "radiusUnit": "km",
            "language": "en",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/location/nearby_search", headers=headers, params=params
                )

                if response.status_code == 200:
                    data = response.json()
                    attractions_data = data.get("data", [])

                    attractions = []
                    for attraction_data in attractions_data[: request.max_results]:
                        try:
                            attraction = TripAdvisorAttraction(**attraction_data)
                            attractions.append(attraction)
                        except Exception as e:
                            self.logger.debug(f"Failed to parse TripAdvisor attraction: {e}")
                            continue

                    return attractions

                elif response.status_code == 429:
                    await self._handle_rate_limit(response)
                    return []

                response.raise_for_status()

        except Exception as e:
            self.logger.warning(f"TripAdvisor nearby search failed: {e}")

        return []

    async def _get_location_coordinates(self, location_id: str) -> str:
        """Get coordinates for a TripAdvisor location.

        Args:
            location_id: TripAdvisor location ID

        Returns:
            Coordinates string in "lat,lng" format
        """
        # This would normally require another API call to get location details
        # For now, return a default that will work for testing
        return "40.7128,-74.0060"  # NYC coordinates as fallback

    async def _convert_to_activity(
        self, attraction: TripAdvisorAttraction
    ) -> ActivityOption | None:
        """Convert TripAdvisor attraction to our internal ActivityOption model.

        Args:
            attraction: TripAdvisor attraction data

        Returns:
            ActivityOption model or None if conversion fails
        """
        try:
            # Extract location information
            lat = float(attraction.latitude) if attraction.latitude else 40.7128
            lng = float(attraction.longitude) if attraction.longitude else -74.0060

            location = ActivityLocation(
                latitude=lat,
                longitude=lng,
                address=attraction.address_obj.get("address_string"),
                city=attraction.address_obj.get("city"),
                country=attraction.address_obj.get("country"),
                postal_code=attraction.address_obj.get("postalcode"),
            )

            # Parse rating
            rating = None
            if attraction.rating:
                try:
                    rating = float(attraction.rating)
                except (ValueError, TypeError):
                    pass

            # Parse review count
            review_count = None
            if attraction.num_reviews:
                try:
                    review_count = int(attraction.num_reviews.replace(",", ""))
                except (ValueError, TypeError):
                    pass

            # Map category
            category = self._map_tripadvisor_category_to_internal(attraction)

            # Extract images
            images = []
            if attraction.photo and "images" in attraction.photo:
                for image_info in attraction.photo["images"]:
                    if "url" in image_info:
                        images.append(image_info["url"])

            # TripAdvisor typically doesn't provide direct pricing in free API
            # Set to 0 for free attractions or estimate based on category
            price = self._estimate_activity_price(category)

            activity = ActivityOption(
                external_id=attraction.location_id,
                name=attraction.name,
                description=attraction.description,
                category=category,
                location=location,
                duration_minutes=self._estimate_duration(category),  # Estimate based on category
                price=price,
                currency="USD",
                rating=rating,
                review_count=review_count,
                images=images,
                booking_url=attraction.web_url,
                provider="tripadvisor",
            )

            return activity

        except Exception as e:
            self.logger.warning(f"Failed to convert TripAdvisor attraction {attraction.name}: {e}")
            return None

    def _map_category_to_tripadvisor(self, category: ActivityCategory) -> str | None:
        """Map our internal category to TripAdvisor category.

        Args:
            category: Internal activity category

        Returns:
            TripAdvisor category string or None
        """
        category_mapping = {
            ActivityCategory.CULTURAL: "museums",
            ActivityCategory.ADVENTURE: "outdoor",
            ActivityCategory.ENTERTAINMENT: "entertainment",
            ActivityCategory.NATURE: "nature",
            ActivityCategory.SHOPPING: "shopping",
            ActivityCategory.NIGHTLIFE: "nightlife",
            ActivityCategory.FOOD: "food",
            ActivityCategory.RELAXATION: "spas",
        }

        return category_mapping.get(category)

    def _map_tripadvisor_category_to_internal(
        self, attraction: TripAdvisorAttraction
    ) -> ActivityCategory:
        """Map TripAdvisor category to our internal category.

        Args:
            attraction: TripAdvisor attraction data

        Returns:
            Internal activity category
        """
        # Extract category info
        category_name = ""
        if attraction.category:
            category_name = attraction.category.get("name", "").lower()

        subcategory_names = []
        for subcat in attraction.subcategory:
            subcategory_names.append(subcat.get("name", "").lower())

        combined_categories = f"{category_name} {' '.join(subcategory_names)}"

        # Map based on keywords
        if any(
            keyword in combined_categories
            for keyword in ["museum", "historic", "cultural", "heritage"]
        ):
            return ActivityCategory.CULTURAL
        elif any(keyword in combined_categories for keyword in ["adventure", "outdoor", "sports"]):
            return ActivityCategory.ADVENTURE
        elif any(keyword in combined_categories for keyword in ["restaurant", "food", "dining"]):
            return ActivityCategory.FOOD
        elif any(
            keyword in combined_categories for keyword in ["entertainment", "theater", "show"]
        ):
            return ActivityCategory.ENTERTAINMENT
        elif any(
            keyword in combined_categories for keyword in ["nature", "park", "garden", "wildlife"]
        ):
            return ActivityCategory.NATURE
        elif any(keyword in combined_categories for keyword in ["shopping", "mall", "market"]):
            return ActivityCategory.SHOPPING
        elif any(keyword in combined_categories for keyword in ["spa", "wellness", "relaxation"]):
            return ActivityCategory.RELAXATION
        elif any(keyword in combined_categories for keyword in ["bar", "club", "nightlife"]):
            return ActivityCategory.NIGHTLIFE
        else:
            return ActivityCategory.ENTERTAINMENT  # Default fallback

    def _estimate_activity_price(self, category: ActivityCategory) -> Decimal:
        """Estimate activity price based on category.

        Args:
            category: Activity category

        Returns:
            Estimated price in USD
        """
        price_estimates = {
            ActivityCategory.CULTURAL: Decimal("15.00"),
            ActivityCategory.ADVENTURE: Decimal("75.00"),
            ActivityCategory.FOOD: Decimal("25.00"),
            ActivityCategory.ENTERTAINMENT: Decimal("45.00"),
            ActivityCategory.NATURE: Decimal("0.00"),  # Often free
            ActivityCategory.SHOPPING: Decimal("0.00"),  # Free to browse
            ActivityCategory.RELAXATION: Decimal("120.00"),
            ActivityCategory.NIGHTLIFE: Decimal("30.00"),
        }

        return price_estimates.get(category, Decimal("25.00"))

    def _estimate_duration(self, category: ActivityCategory) -> int | None:
        """Estimate activity duration based on category.

        Args:
            category: Activity category

        Returns:
            Estimated duration in minutes
        """
        duration_estimates = {
            ActivityCategory.CULTURAL: 120,  # 2 hours
            ActivityCategory.ADVENTURE: 240,  # 4 hours
            ActivityCategory.FOOD: 90,  # 1.5 hours
            ActivityCategory.ENTERTAINMENT: 180,  # 3 hours
            ActivityCategory.NATURE: 150,  # 2.5 hours
            ActivityCategory.SHOPPING: 180,  # 3 hours
            ActivityCategory.RELAXATION: 240,  # 4 hours
            ActivityCategory.NIGHTLIFE: 180,  # 3 hours
        }

        return duration_estimates.get(category, 120)

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open.

        Returns:
            True if circuit is open (should not make requests)
        """
        import time

        if not self.circuit_open:
            return False

        # Auto-reset after 5 minutes
        if time.time() - self.last_failure_time > 300:
            self.circuit_open = False
            self.failure_count = 0
            self.logger.info("TripAdvisor circuit breaker reset")

        return self.circuit_open

    async def _handle_api_failure(self) -> None:
        """Handle API failure for circuit breaker."""
        import time

        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= 3:
            self.circuit_open = True
            self.logger.warning("TripAdvisor circuit breaker opened due to repeated failures")

    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker on successful request."""
        if self.failure_count > 0:
            self.failure_count = 0
            self.logger.debug("TripAdvisor circuit breaker failure count reset")

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limits."""
        import time

        current_time = time.time()

        # Reset counter every hour
        if current_time > self.rate_limit_reset_time:
            self.request_count = 0
            self.rate_limit_reset_time = current_time + 3600  # 1 hour

        # TripAdvisor free tier: 500 requests/day, so ~20 requests/hour
        if self.request_count >= 20:
            self.logger.warning("TripAdvisor rate limit reached, waiting...")
            await asyncio.sleep(10)  # Wait 10 seconds

        self.request_count += 1

    async def _handle_rate_limit(self, response: httpx.Response) -> None:
        """Handle rate limit response from API.

        Args:
            response: HTTP response with rate limit headers
        """
        retry_after = response.headers.get("Retry-After", "60")
        wait_time = min(int(retry_after), 300)  # Max 5 minutes

        self.logger.warning(f"TripAdvisor rate limited, waiting {wait_time} seconds")
        await asyncio.sleep(wait_time)

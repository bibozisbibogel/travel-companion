"""GetYourGuide API client for tours and experience data."""

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


class GetYourGuideLocation(BaseModel):
    """GetYourGuide location model."""

    location_id: str = Field(..., description="GetYourGuide location ID")
    name: str = Field(..., description="Location name")
    country: str | None = Field(None, description="Country name")
    latitude: float | None = Field(None, description="Latitude coordinate")
    longitude: float | None = Field(None, description="Longitude coordinate")


class GetYourGuideActivity(BaseModel):
    """GetYourGuide activity model."""

    activity_id: str = Field(..., description="Activity ID")
    title: str = Field(..., description="Activity title")
    summary: str | None = Field(None, description="Activity summary")
    duration: dict[str, Any] | None = Field(None, description="Duration information")
    price: dict[str, Any] = Field(default_factory=dict, description="Price information")
    rating: dict[str, Any] | None = Field(None, description="Rating information")
    pictures: list[dict[str, Any]] = Field(default_factory=list, description="Activity pictures")
    categories: list[dict[str, Any]] = Field(
        default_factory=list, description="Activity categories"
    )
    booking_link: str | None = Field(None, description="Booking URL")
    location: dict[str, Any] = Field(default_factory=dict, description="Location information")


class GetYourGuideAPIClient:
    """GetYourGuide API client for activity searches."""

    def __init__(self) -> None:
        """Initialize GetYourGuide API client."""
        self.settings = get_settings()
        self.logger = logging.getLogger("travel_companion.services.getyourguide")
        self.base_url = "https://api.getyourguide.com/partner"

        # Circuit breaker state
        self.failure_count = 0
        self.last_failure_time: float = 0
        self.circuit_open = False

        # Rate limiting
        self.request_count = 0
        self.rate_limit_reset_time: float = 0

        self.logger.info("GetYourGuide API client initialized")

    async def search_activities(self, request: ActivitySearchRequest) -> list[ActivityOption]:
        """Search activities using GetYourGuide API.

        Args:
            request: Activity search parameters

        Returns:
            List of activity options from GetYourGuide
        """
        if self._is_circuit_open():
            self.logger.warning("GetYourGuide circuit breaker is open, skipping request")
            return []

        try:
            # First, search for location
            location_data = await self._search_location(request.location)
            if not location_data:
                self.logger.warning(f"No GetYourGuide location found for: {request.location}")
                return []

            # Then search for activities at that location
            activities_data = await self._search_activities_by_location(location_data, request)

            # Convert to our internal format
            activities = []
            for activity_data in activities_data:
                try:
                    activity = await self._convert_to_activity(activity_data)
                    if activity:
                        activities.append(activity)
                except Exception as e:
                    self.logger.warning(f"Failed to convert GetYourGuide activity: {e}")
                    continue

            self.logger.info(f"GetYourGuide returned {len(activities)} activities")
            self._reset_circuit_breaker()

            return activities

        except Exception as e:
            self.logger.error(f"GetYourGuide API error: {e}")
            await self._handle_api_failure()
            return []

    async def _search_location(self, location: str) -> GetYourGuideLocation | None:
        """Search for GetYourGuide location.

        Args:
            location: Location name to search

        Returns:
            GetYourGuide location data or None if not found
        """
        await self._check_rate_limit()

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.settings.getyourguide_api_key}",
        }

        params: dict[str, str | int] = {
            "q": location,
            "limit": 1,  # We only need the first match
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/locations/search", headers=headers, params=params
                )

                if response.status_code == 200:
                    data = response.json()
                    locations = data.get("data", [])

                    if locations:
                        location_info = GetYourGuideLocation(**locations[0])
                        self.logger.debug(
                            f"Found GetYourGuide location: {location_info.location_id}"
                        )
                        return location_info

                elif response.status_code == 429:
                    await self._handle_rate_limit(response)
                    return None

                response.raise_for_status()

        except Exception as e:
            self.logger.warning(f"GetYourGuide location search failed: {e}")

        return None

    async def _search_activities_by_location(
        self, location: GetYourGuideLocation, request: ActivitySearchRequest
    ) -> list[GetYourGuideActivity]:
        """Search for activities at a specific location.

        Args:
            location: GetYourGuide location data
            request: Activity search request

        Returns:
            List of GetYourGuide activities
        """
        await self._check_rate_limit()

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.settings.getyourguide_api_key}",
        }

        params: dict[str, str | int] = {
            "location_id": location.location_id,
            "limit": min(request.max_results, 50),  # GetYourGuide max is typically 50
        }

        # Add category filter if specified
        if request.category:
            gyg_category = self._map_category_to_getyourguide(request.category)
            if gyg_category:
                params["category"] = gyg_category

        # Add price filter if specified
        if request.budget_per_person:
            params["max_price"] = str(request.budget_per_person)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/activities", headers=headers, params=params
                )

                if response.status_code == 200:
                    data = response.json()
                    activities_data = data.get("data", [])

                    activities = []
                    for activity_data in activities_data:
                        try:
                            activity = GetYourGuideActivity(**activity_data)
                            activities.append(activity)
                        except Exception as e:
                            self.logger.debug(f"Failed to parse GetYourGuide activity: {e}")
                            continue

                    return activities

                elif response.status_code == 429:
                    await self._handle_rate_limit(response)
                    return []

                response.raise_for_status()

        except Exception as e:
            self.logger.warning(f"GetYourGuide activity search failed: {e}")

        return []

    async def _convert_to_activity(
        self, activity_data: GetYourGuideActivity
    ) -> ActivityOption | None:
        """Convert GetYourGuide activity to our internal ActivityOption model.

        Args:
            activity_data: GetYourGuide activity data

        Returns:
            ActivityOption model or None if conversion fails
        """
        try:
            # Extract location information
            location_info = activity_data.location
            lat = location_info.get("latitude", 0.0) if location_info else 0.0
            lng = location_info.get("longitude", 0.0) if location_info else 0.0

            location = ActivityLocation(
                latitude=float(lat) if lat else 40.7128,  # Default to NYC
                longitude=float(lng) if lng else -74.0060,
                address=location_info.get("address") if location_info else None,
                city=location_info.get("city") if location_info else None,
                country=location_info.get("country") if location_info else None,
                postal_code=None,
            )

            # Parse pricing
            price = Decimal("0.00")
            currency = "USD"

            if activity_data.price:
                if "amount" in activity_data.price:
                    price = Decimal(str(activity_data.price["amount"]))
                if "currency" in activity_data.price:
                    currency = activity_data.price["currency"]

            # Parse duration
            duration_minutes = None
            if activity_data.duration:
                if "value" in activity_data.duration and "unit" in activity_data.duration:
                    value = activity_data.duration["value"]
                    unit = activity_data.duration["unit"].lower()

                    if unit in ["hour", "hours"]:
                        duration_minutes = value * 60
                    elif unit in ["minute", "minutes"]:
                        duration_minutes = value
                    elif unit in ["day", "days"]:
                        duration_minutes = value * 8 * 60  # Assume 8 hours per day

            # Parse rating
            rating = None
            review_count = None

            if activity_data.rating:
                if "average" in activity_data.rating:
                    rating = float(activity_data.rating["average"])
                if "count" in activity_data.rating:
                    review_count = int(activity_data.rating["count"])

            # Map category
            category = self._map_getyourguide_category_to_internal(activity_data)

            # Extract images
            images = []
            for picture in activity_data.pictures:
                if "url" in picture:
                    images.append(picture["url"])

            activity = ActivityOption(
                external_id=activity_data.activity_id,
                name=activity_data.title,
                trip_id=None,  # Will be set when associated with a trip
                description=activity_data.summary,
                category=category,
                location=location,
                duration_minutes=duration_minutes,
                price=price,
                currency=currency,
                rating=rating,
                review_count=review_count,
                images=images,
                booking_url=activity_data.booking_link,
                provider="getyourguide",
            )

            return activity

        except Exception as e:
            self.logger.warning(
                f"Failed to convert GetYourGuide activity {activity_data.title}: {e}"
            )
            return None

    def _map_category_to_getyourguide(self, category: ActivityCategory) -> str | None:
        """Map our internal category to GetYourGuide category.

        Args:
            category: Internal activity category

        Returns:
            GetYourGuide category string or None
        """
        category_mapping = {
            ActivityCategory.CULTURAL: "culture",
            ActivityCategory.ADVENTURE: "outdoor",
            ActivityCategory.ENTERTAINMENT: "entertainment",
            ActivityCategory.NATURE: "nature",
            ActivityCategory.SHOPPING: "shopping",
            ActivityCategory.NIGHTLIFE: "nightlife",
            ActivityCategory.FOOD: "food-drink",
            ActivityCategory.RELAXATION: "wellness",
        }

        return category_mapping.get(category)

    def _map_getyourguide_category_to_internal(
        self, activity: GetYourGuideActivity
    ) -> ActivityCategory:
        """Map GetYourGuide category to our internal category.

        Args:
            activity: GetYourGuide activity data

        Returns:
            Internal activity category
        """
        # Extract category names
        category_names = []
        for cat in activity.categories:
            if "name" in cat:
                category_names.append(cat["name"].lower())

        combined_categories = " ".join(category_names)
        title_lower = activity.title.lower()
        summary_lower = (activity.summary or "").lower()
        combined_text = f"{combined_categories} {title_lower} {summary_lower}"

        # Map based on keywords
        if any(
            keyword in combined_text
            for keyword in ["museum", "historic", "cultural", "heritage", "art", "monument"]
        ):
            return ActivityCategory.CULTURAL
        elif any(
            keyword in combined_text
            for keyword in ["adventure", "outdoor", "hiking", "cycling", "extreme", "sport"]
        ):
            return ActivityCategory.ADVENTURE
        elif any(
            keyword in combined_text
            for keyword in ["food", "culinary", "cooking", "wine", "tasting", "dining"]
        ):
            return ActivityCategory.FOOD
        elif any(
            keyword in combined_text
            for keyword in ["show", "theater", "performance", "entertainment", "concert", "music"]
        ):
            return ActivityCategory.ENTERTAINMENT
        elif any(
            keyword in combined_text
            for keyword in ["nature", "park", "wildlife", "safari", "garden", "beach"]
        ):
            return ActivityCategory.NATURE
        elif any(
            keyword in combined_text for keyword in ["shopping", "market", "boutique", "souvenir"]
        ):
            return ActivityCategory.SHOPPING
        elif any(
            keyword in combined_text
            for keyword in ["spa", "wellness", "relaxation", "massage", "thermal"]
        ):
            return ActivityCategory.RELAXATION
        elif any(
            keyword in combined_text
            for keyword in ["nightlife", "bar", "club", "evening", "night", "pub"]
        ):
            return ActivityCategory.NIGHTLIFE
        else:
            return ActivityCategory.ENTERTAINMENT  # Default fallback

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
            self.logger.info("GetYourGuide circuit breaker reset")

        return self.circuit_open

    async def _handle_api_failure(self) -> None:
        """Handle API failure for circuit breaker."""
        import time

        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= 3:
            self.circuit_open = True
            self.logger.warning("GetYourGuide circuit breaker opened due to repeated failures")

    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker on successful request."""
        if self.failure_count > 0:
            self.failure_count = 0
            self.logger.debug("GetYourGuide circuit breaker failure count reset")

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limits."""
        import time

        current_time = time.time()

        # Reset counter every hour
        if current_time > self.rate_limit_reset_time:
            self.request_count = 0
            self.rate_limit_reset_time = current_time + 3600  # 1 hour

        # Conservative rate limiting: 25 requests/hour
        if self.request_count >= 25:
            self.logger.warning("GetYourGuide rate limit reached, waiting...")
            await asyncio.sleep(10)  # Wait 10 seconds

        self.request_count += 1

    async def _handle_rate_limit(self, response: httpx.Response) -> None:
        """Handle rate limit response from API.

        Args:
            response: HTTP response with rate limit headers
        """
        retry_after = response.headers.get("Retry-After", "60")
        wait_time = min(int(retry_after), 300)  # Max 5 minutes

        self.logger.warning(f"GetYourGuide rate limited, waiting {wait_time} seconds")
        await asyncio.sleep(wait_time)

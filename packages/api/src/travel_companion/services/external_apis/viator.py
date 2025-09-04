"""Viator API client for tours and experience data."""

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


class ViatorDestination(BaseModel):
    """Viator destination model."""

    destination_id: int = Field(..., description="Viator destination ID")
    destination_name: str = Field(..., description="Destination name")
    country_code: str | None = Field(None, description="Country code")


class ViatorProduct(BaseModel):
    """Viator product/tour model."""

    code: str = Field(..., description="Product code")
    title: str = Field(..., description="Product title")
    description: str | None = Field(None, description="Product description")
    duration: str | None = Field(None, description="Duration string")
    price: dict[str, Any] = Field(default_factory=dict, description="Pricing information")
    rating: float | None = Field(None, description="Average rating")
    review_count: int | None = Field(None, description="Number of reviews")
    images: list[dict[str, Any]] = Field(default_factory=list, description="Product images")
    categories: list[dict[str, Any]] = Field(default_factory=list, description="Product categories")
    booking_url: str | None = Field(None, description="Booking URL")


class ViatorAPIClient:
    """Viator API client for tour and experience searches."""

    def __init__(self) -> None:
        """Initialize Viator API client."""
        self.settings = get_settings()
        self.logger = logging.getLogger("travel_companion.services.viator")
        self.base_url = "https://api.viator.com/partner"

        # Circuit breaker state
        self.failure_count = 0
        self.last_failure_time: float = 0
        self.circuit_open = False

        # Rate limiting
        self.request_count = 0
        self.rate_limit_reset_time: float = 0

        self.logger.info("Viator API client initialized")

    async def search_activities(self, request: ActivitySearchRequest) -> list[ActivityOption]:
        """Search activities using Viator API.

        Args:
            request: Activity search parameters

        Returns:
            List of activity options from Viator
        """
        if self._is_circuit_open():
            self.logger.warning("Viator circuit breaker is open, skipping request")
            return []

        try:
            # First, search for destination ID
            destination_id = await self._search_destination(request.location)
            if not destination_id:
                self.logger.warning(f"No Viator destination found for: {request.location}")
                return []

            # Then search for products at that destination
            products = await self._search_products(destination_id, request)

            # Convert to our internal format
            activities = []
            for product in products:
                try:
                    activity = await self._convert_to_activity(product, request.location)
                    if activity:
                        activities.append(activity)
                except Exception as e:
                    self.logger.warning(f"Failed to convert Viator product: {e}")
                    continue

            self.logger.info(f"Viator returned {len(activities)} activities")
            self._reset_circuit_breaker()

            return activities

        except Exception as e:
            self.logger.error(f"Viator API error: {e}")
            await self._handle_api_failure()
            return []

    async def _search_destination(self, location: str) -> int | None:
        """Search for Viator destination ID.

        Args:
            location: Location name to search

        Returns:
            Viator destination ID or None if not found
        """
        await self._check_rate_limit()

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.settings.viator_api_key}",
        }

        params = {
            "q": location,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/destinations/search", headers=headers, params=params
                )

                if response.status_code == 200:
                    data = response.json()
                    destinations = data.get("destinations", [])

                    if destinations:
                        # Return the first destination ID
                        destination = ViatorDestination(**destinations[0])
                        self.logger.debug(
                            f"Found Viator destination ID: {destination.destination_id}"
                        )
                        return destination.destination_id

                elif response.status_code == 429:
                    await self._handle_rate_limit(response)
                    return None

                response.raise_for_status()

        except Exception as e:
            self.logger.warning(f"Viator destination search failed: {e}")

        return None

    async def _search_products(
        self, destination_id: int, request: ActivitySearchRequest
    ) -> list[ViatorProduct]:
        """Search for products at a specific destination.

        Args:
            destination_id: Viator destination ID
            request: Activity search request

        Returns:
            List of Viator products
        """
        await self._check_rate_limit()

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.settings.viator_api_key}",
        }

        params = {
            "destination_id": destination_id,
            "count": min(request.max_results, 100),  # Viator max is typically 100
        }

        # Add category filter if specified
        if request.category:
            viator_category = self._map_category_to_viator(request.category)
            if viator_category:
                params["category_id"] = viator_category

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/products/search", headers=headers, params=params
                )

                if response.status_code == 200:
                    data = response.json()
                    products_data = data.get("products", [])

                    products = []
                    for product_data in products_data:
                        try:
                            product = ViatorProduct(**product_data)
                            products.append(product)
                        except Exception as e:
                            self.logger.debug(f"Failed to parse Viator product: {e}")
                            continue

                    return products

                elif response.status_code == 429:
                    await self._handle_rate_limit(response)
                    return []

                response.raise_for_status()

        except Exception as e:
            self.logger.warning(f"Viator product search failed: {e}")

        return []

    async def _convert_to_activity(
        self, product: ViatorProduct, location: str
    ) -> ActivityOption | None:
        """Convert Viator product to our internal ActivityOption model.

        Args:
            product: Viator product data
            location: Original location search string

        Returns:
            ActivityOption model or None if conversion fails
        """
        try:
            # Estimate location coordinates (Viator API might not provide exact coordinates)
            location_coords = await self._estimate_location_coordinates(location)

            location_obj = ActivityLocation(
                latitude=location_coords[0],
                longitude=location_coords[1],
                address=None,  # Viator typically doesn't provide detailed address
                city=location,
                country=None,
                postal_code=None,
            )

            # Parse pricing
            price = Decimal("0.00")
            currency = "USD"

            if product.price:
                # Viator pricing can be complex, extract the base price
                if "retail" in product.price:
                    price_data = product.price["retail"]
                    if "value" in price_data:
                        price = Decimal(str(price_data["value"]))
                    if "currency" in price_data:
                        currency = price_data["currency"]

            # Parse duration
            duration_minutes = None
            if product.duration:
                duration_minutes = self._parse_duration(product.duration)

            # Map category
            category = self._map_viator_category_to_internal(product)

            # Extract images
            images = []
            for image_info in product.images:
                if "url" in image_info:
                    images.append(image_info["url"])

            activity = ActivityOption(
                external_id=product.code,
                name=product.title,
                description=product.description,
                category=category,
                location=location_obj,
                duration_minutes=duration_minutes,
                price=price,
                currency=currency,
                rating=product.rating,
                review_count=product.review_count,
                images=images,
                booking_url=product.booking_url,
                provider="viator",
            )

            return activity

        except Exception as e:
            self.logger.warning(f"Failed to convert Viator product {product.title}: {e}")
            return None

    async def _estimate_location_coordinates(self, location: str) -> tuple[float, float]:
        """Estimate coordinates for a location.

        Args:
            location: Location name

        Returns:
            Tuple of (latitude, longitude)
        """
        # This is a simplified approach. In a real implementation,
        # you might use a geocoding service or maintain a location database
        location_coords = {
            "new york": (40.7128, -74.0060),
            "london": (51.5074, -0.1278),
            "paris": (48.8566, 2.3522),
            "tokyo": (35.6762, 139.6503),
            "rome": (41.9028, 12.4964),
            "barcelona": (41.3851, 2.1734),
            "amsterdam": (52.3676, 4.9041),
            "berlin": (52.5200, 13.4050),
            "sydney": (-33.8688, 151.2093),
            "bangkok": (13.7563, 100.5018),
        }

        location_lower = location.lower()
        for city, coords in location_coords.items():
            if city in location_lower:
                return coords

        # Default to NYC if no match
        return (40.7128, -74.0060)

    def _parse_duration(self, duration_str: str) -> int | None:
        """Parse duration string into minutes.

        Args:
            duration_str: Duration string from Viator API

        Returns:
            Duration in minutes or None if parsing fails
        """
        try:
            duration_lower = duration_str.lower()

            # Handle common patterns
            if "hour" in duration_lower:
                hours = 0
                if duration_lower.startswith("full day"):
                    hours = 8
                elif duration_lower.startswith("half day"):
                    hours = 4
                else:
                    # Extract number before "hour"
                    import re

                    match = re.search(r"(\d+(?:\.\d+)?)\s*hour", duration_lower)
                    if match:
                        hours = float(match.group(1))

                return int(hours * 60)

            elif "day" in duration_lower:
                days = 1
                import re

                match = re.search(r"(\d+)\s*day", duration_lower)
                if match:
                    days = int(match.group(1))

                return days * 8 * 60  # Assume 8 hours per day

            elif "minute" in duration_lower:
                import re

                match = re.search(r"(\d+)\s*minute", duration_lower)
                if match:
                    return int(match.group(1))

        except Exception as e:
            self.logger.debug(f"Failed to parse duration '{duration_str}': {e}")

        return None

    def _map_category_to_viator(self, category: ActivityCategory) -> str | None:
        """Map our internal category to Viator category ID.

        Args:
            category: Internal activity category

        Returns:
            Viator category ID string or None
        """
        # These would be actual Viator category IDs in a real implementation
        category_mapping = {
            ActivityCategory.CULTURAL: "26",  # Tours & Sightseeing
            ActivityCategory.ADVENTURE: "57",  # Outdoor Activities
            ActivityCategory.ENTERTAINMENT: "49",  # Shows & Performances
            ActivityCategory.NATURE: "57",  # Outdoor Activities
            ActivityCategory.SHOPPING: "56",  # Shopping
            ActivityCategory.NIGHTLIFE: "49",  # Shows & Performances
            ActivityCategory.FOOD: "136",  # Food & Drink
            ActivityCategory.RELAXATION: "61",  # Spa & Wellness
        }

        return category_mapping.get(category)

    def _map_viator_category_to_internal(self, product: ViatorProduct) -> ActivityCategory:
        """Map Viator product category to our internal category.

        Args:
            product: Viator product data

        Returns:
            Internal activity category
        """
        # Extract category names
        category_names = []
        for cat in product.categories:
            if "name" in cat:
                category_names.append(cat["name"].lower())

        combined_categories = " ".join(category_names)
        title_lower = product.title.lower()
        description_lower = (product.description or "").lower()
        combined_text = f"{combined_categories} {title_lower} {description_lower}"

        # Map based on keywords
        if any(
            keyword in combined_text
            for keyword in ["museum", "historic", "cultural", "heritage", "tour", "sightseeing"]
        ):
            return ActivityCategory.CULTURAL
        elif any(
            keyword in combined_text
            for keyword in ["adventure", "outdoor", "hiking", "climbing", "extreme"]
        ):
            return ActivityCategory.ADVENTURE
        elif any(
            keyword in combined_text
            for keyword in ["food", "dining", "cooking", "culinary", "taste", "wine"]
        ):
            return ActivityCategory.FOOD
        elif any(
            keyword in combined_text
            for keyword in ["show", "theater", "performance", "entertainment", "concert"]
        ):
            return ActivityCategory.ENTERTAINMENT
        elif any(
            keyword in combined_text
            for keyword in ["nature", "park", "wildlife", "safari", "beach"]
        ):
            return ActivityCategory.NATURE
        elif any(keyword in combined_text for keyword in ["shopping", "market", "souvenir"]):
            return ActivityCategory.SHOPPING
        elif any(
            keyword in combined_text for keyword in ["spa", "wellness", "relaxation", "massage"]
        ):
            return ActivityCategory.RELAXATION
        elif any(
            keyword in combined_text for keyword in ["nightlife", "bar", "club", "evening", "night"]
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
            self.logger.info("Viator circuit breaker reset")

        return self.circuit_open

    async def _handle_api_failure(self) -> None:
        """Handle API failure for circuit breaker."""
        import time

        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= 3:
            self.circuit_open = True
            self.logger.warning("Viator circuit breaker opened due to repeated failures")

    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker on successful request."""
        if self.failure_count > 0:
            self.failure_count = 0
            self.logger.debug("Viator circuit breaker failure count reset")

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limits."""
        import time

        current_time = time.time()

        # Reset counter every hour
        if current_time > self.rate_limit_reset_time:
            self.request_count = 0
            self.rate_limit_reset_time = current_time + 3600  # 1 hour

        # Conservative rate limiting: 30 requests/hour
        if self.request_count >= 30:
            self.logger.warning("Viator rate limit reached, waiting...")
            await asyncio.sleep(10)  # Wait 10 seconds

        self.request_count += 1

    async def _handle_rate_limit(self, response: httpx.Response) -> None:
        """Handle rate limit response from API.

        Args:
            response: HTTP response with rate limit headers
        """
        retry_after = response.headers.get("Retry-After", "60")
        wait_time = min(int(retry_after), 300)  # Max 5 minutes

        self.logger.warning(f"Viator rate limited, waiting {wait_time} seconds")
        await asyncio.sleep(wait_time)

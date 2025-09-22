"""Geoapify API client for restaurant and place discovery."""

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from travel_companion.core.config import get_settings
from travel_companion.models.external import (
    RestaurantLocation,
    RestaurantOption,
    RestaurantSearchRequest,
    RestaurantSearchResponse,
)

# Note: Caching would use CacheManager when properly integrated
from travel_companion.utils.errors import ExternalAPIError


class GeoapifyClient:
    """Client for interacting with Geoapify Places and Place Details APIs."""

    BASE_URL = "https://api.geoapify.com/v2"
    PLACES_ENDPOINT = f"{BASE_URL}/places"
    PLACE_DETAILS_ENDPOINT = f"{BASE_URL}/place-details"

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
                # Use bias for location name search
                params["bias"] = f"proximity:{request.location}"
                params["filter"] = f"circle:{request.location},{request.radius_meters}"

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

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

"""Google Places API client for restaurant search."""

import asyncio
import logging
from decimal import Decimal
from typing import Any

import httpx

from travel_companion.models.external import (
    CuisineType,
    PriceRange,
    RestaurantContact,
    RestaurantHours,
    RestaurantLocation,
    RestaurantOption,
    RestaurantSearchRequest,
)
from travel_companion.utils.errors import ExternalAPIError


class GooglePlacesClient:
    """Google Places API client for restaurant search."""

    def __init__(self, api_key: str):
        """Initialize Google Places client with API key."""
        if not api_key:
            raise ValueError("Google Places API key is required")

        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/place"
        self.logger = logging.getLogger("travel_companion.services.google_places")

        # Rate limiting tracking
        self._requests_count = 0

    async def search_restaurants(self, request: RestaurantSearchRequest) -> list[RestaurantOption]:
        """Search for restaurants using Google Places API.

        Args:
            request: Restaurant search request parameters

        Returns:
            List of RestaurantOption objects from Google Places results
        """
        try:
            self.logger.info(f"Searching Google Places for restaurants in {request.location}")

            # Build search parameters for Places Nearby Search
            params = self._build_search_params(request)

            # Make API request with timeout
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/nearbysearch/json", params=params)

                self._requests_count += 1
                response.raise_for_status()

                data = response.json()

            # Check for API errors
            if data.get("status") != "OK" and data.get("status") != "ZERO_RESULTS":
                error_message = data.get("error_message", f"API status: {data.get('status')}")
                self.logger.error(f"Google Places API error: {error_message}")
                if data.get("status") == "REQUEST_DENIED":
                    raise ExternalAPIError(f"Google Places API access denied: {error_message}")
                elif data.get("status") == "OVER_QUERY_LIMIT":
                    self.logger.warning("Google Places API quota exceeded")
                    return []
                else:
                    raise ExternalAPIError(f"Google Places API error: {error_message}")

            # Parse and convert results
            restaurants = []
            places = data.get("results", [])

            # Get detailed information for top results
            detailed_places = await self._get_detailed_places(places[: request.max_results])

            for place in detailed_places:
                try:
                    restaurant = self._parse_place(place, request)
                    if restaurant:
                        restaurants.append(restaurant)
                except Exception as e:
                    self.logger.warning(f"Failed to parse Google Places result: {e}")

            self.logger.info(f"Found {len(restaurants)} restaurants from Google Places")
            return restaurants

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                self.logger.error("Google Places API access forbidden - check API key and billing")
                raise ExternalAPIError("Google Places API access denied") from e
            else:
                self.logger.error(f"Google Places API HTTP error {e.response.status_code}")
                raise ExternalAPIError(f"Google Places API error: {e.response.status_code}") from e

        except httpx.TimeoutException:
            self.logger.warning("Google Places API request timeout")
            raise ExternalAPIError("Google Places API timeout") from None

        except Exception as e:
            self.logger.error(f"Google Places API request failed: {e}")
            raise ExternalAPIError(f"Google Places API request failed: {e}") from e

    def _build_search_params(self, request: RestaurantSearchRequest) -> dict[str, Any]:
        """Build Google Places API search parameters from request."""
        params = {"key": self.api_key, "type": "restaurant", "rankby": "prominence"}

        # Location parameters
        if request.latitude and request.longitude:
            params["location"] = f"{request.latitude},{request.longitude}"
        else:
            # If no coordinates, we need to geocode the location first
            # For simplicity, using text search instead
            params = {
                "key": self.api_key,
                "query": f"restaurants in {request.location}",
                "type": "restaurant",
            }
            return params  # Return early for text search

        # Radius in meters (max 50000 for rankby=prominence)
        if request.radius_km:
            radius_meters = min(int(request.radius_km * 1000), 50000)
            params["radius"] = str(radius_meters)
        else:
            params["radius"] = "5000"  # Default 5km

        # Note: Google Places doesn't directly support price filtering in nearby search
        # Price filtering would need to be applied post-search if needed

        # Open now filter
        if request.open_now:
            params["opennow"] = "true"

        return params

    async def _get_detailed_places(self, places: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Get detailed information for a list of places."""
        detailed_places = []

        # Batch requests with rate limiting
        semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

        async def get_place_details(place: dict[str, Any]) -> dict[str, Any]:
            async with semaphore:
                try:
                    place_id = place.get("place_id")
                    if not place_id:
                        return place

                    fields = [
                        "name",
                        "rating",
                        "user_ratings_total",
                        "price_level",
                        "formatted_address",
                        "geometry",
                        "formatted_phone_number",
                        "website",
                        "opening_hours",
                        "photos",
                        "types",
                        "reviews",
                    ]

                    params = {"key": self.api_key, "place_id": place_id, "fields": ",".join(fields)}

                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(f"{self.base_url}/details/json", params=params)

                        self._requests_count += 1
                        response.raise_for_status()

                        data = response.json()

                    if data.get("status") == "OK":
                        # Merge detailed data with original place data
                        detailed_place = {**place, **data.get("result", {})}
                        return detailed_place
                    else:
                        self.logger.warning(
                            f"Failed to get details for place {place_id}: {data.get('status')}"
                        )
                        return place

                except Exception as e:
                    self.logger.warning(f"Failed to get place details: {e}")
                    return place

        # Execute all detail requests concurrently
        tasks = [get_place_details(place) for place in places]
        detailed_places = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return valid places
        valid_places: list[dict[str, Any]] = []
        for place in detailed_places:
            if not isinstance(place, Exception):
                valid_places.append(place)

        return valid_places

    def _parse_place(
        self, place: dict[str, Any], request: RestaurantSearchRequest
    ) -> RestaurantOption | None:
        """Parse Google Places data into RestaurantOption model."""
        try:
            # Extract location data
            geometry = place.get("geometry", {})
            location_data = geometry.get("location", {})

            location = RestaurantLocation(
                latitude=location_data.get("lat", 0.0),
                longitude=location_data.get("lng", 0.0),
                address=place.get("formatted_address", place.get("vicinity")),
                # Google doesn't always provide structured address components
                city=None,
                state=None,
                country=None,
                postal_code=None,
                neighborhood=None,
            )

            # Map price level from Google (0-4) to our price range
            google_price = place.get("price_level", 2)
            price_range_map = {
                0: PriceRange.BUDGET,
                1: PriceRange.BUDGET,
                2: PriceRange.MODERATE,
                3: PriceRange.EXPENSIVE,
                4: PriceRange.VERY_EXPENSIVE,
            }
            price_range = price_range_map.get(google_price, PriceRange.MODERATE)

            # Determine cuisine type from place types
            place_types = place.get("types", [])
            cuisine_type = self._determine_cuisine_type(place_types)

            # Extract hours if available
            hours = None
            opening_hours = place.get("opening_hours")
            if opening_hours:
                hours = self._parse_hours(opening_hours)

            # Extract contact info
            contact = RestaurantContact(
                phone=place.get("formatted_phone_number"),
                email=None,
                website=place.get("website"),
                reservation_url=None,
            )

            # Extract photos
            photos = []
            if place.get("photos"):
                for photo in place["photos"][:3]:  # Limit to first 3 photos
                    photo_reference = photo.get("photo_reference")
                    if photo_reference:
                        photo_url = (
                            f"{self.base_url}/photo?"
                            f"maxwidth=800&photoreference={photo_reference}&key={self.api_key}"
                        )
                        photos.append(photo_url)

            # Estimate average cost per person based on price range
            avg_cost_map = {
                PriceRange.BUDGET: Decimal("10.00"),
                PriceRange.MODERATE: Decimal("25.00"),
                PriceRange.EXPENSIVE: Decimal("50.00"),
                PriceRange.VERY_EXPENSIVE: Decimal("80.00"),
            }
            avg_cost = avg_cost_map.get(price_range)

            return RestaurantOption(
                external_id=place.get("place_id", place.get("id", "")),
                name=place["name"],
                cuisine_type=cuisine_type,
                location=location,
                rating=float(place.get("rating", 0)),
                review_count=place.get("user_ratings_total", 0),
                price_range=price_range,
                average_cost_per_person=avg_cost,
                currency=request.currency,
                hours=hours,
                contact=contact,
                photos=photos,
                booking_url=place.get("website"),
                provider="google_places",
                trip_id=None,  # Will be set when associated with a trip
                distance_km=None,  # Would need to calculate from request location
            )

        except Exception as e:
            self.logger.error(
                f"Failed to parse Google Places result {place.get('place_id', 'unknown')}: {e}"
            )
            return None

    def _determine_cuisine_type(self, place_types: list[str]) -> CuisineType:
        """Determine primary cuisine type from Google Places types."""
        # Google Places doesn't provide detailed cuisine categorization
        # We can only determine basic categories from place types
        type_map = {
            "meal_takeaway": CuisineType.FAST_FOOD,
            "meal_delivery": CuisineType.FAST_FOOD,
            "bakery": CuisineType.OTHER,
            "cafe": CuisineType.OTHER,
            "bar": CuisineType.OTHER,
        }

        for place_type in place_types:
            if place_type in type_map:
                return type_map[place_type]

        # Default to American for general restaurants
        return CuisineType.AMERICAN

    def _parse_hours(self, opening_hours: dict[str, Any]) -> RestaurantHours:
        """Parse Google Places hours data into RestaurantHours model."""
        weekday_text = opening_hours.get("weekday_text", [])
        is_open_now = opening_hours.get("open_now", False)

        # Initialize hours dict
        hours_dict = {
            "monday": None,
            "tuesday": None,
            "wednesday": None,
            "thursday": None,
            "friday": None,
            "saturday": None,
            "sunday": None,
            "is_open_now": is_open_now,
        }

        # Parse weekday text (format: "Monday: 11:00 AM – 10:00 PM")
        day_mapping = {
            "Monday": "monday",
            "Tuesday": "tuesday",
            "Wednesday": "wednesday",
            "Thursday": "thursday",
            "Friday": "friday",
            "Saturday": "saturday",
            "Sunday": "sunday",
        }

        for day_text in weekday_text:
            try:
                if ":" in day_text:
                    day_name, hours_text = day_text.split(":", 1)
                    day_key = day_mapping.get(day_name.strip())
                    if day_key:
                        hours_dict[day_key] = hours_text.strip()
            except Exception as e:
                self.logger.warning(f"Failed to parse hours text '{day_text}': {e}")

        return RestaurantHours(**hours_dict)

    async def search_text(self, query: str, location: str | None = None) -> list[dict[str, Any]]:
        """Perform text-based search for restaurants.

        Args:
            query: Search query
            location: Optional location to bias results

        Returns:
            List of place results
        """
        try:
            params = {"key": self.api_key, "query": query, "type": "restaurant"}

            if location:
                params["location"] = location
                params["radius"] = "50000"  # 50km radius

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/textsearch/json", params=params)

                self._requests_count += 1
                response.raise_for_status()

                data = response.json()

            if data.get("status") == "OK":
                results = data.get("results", [])
                return results  # type: ignore[return-value]
            else:
                self.logger.error(f"Google Places text search error: {data.get('status')}")
                return []

        except Exception as e:
            self.logger.error(f"Google Places text search failed: {e}")
            raise ExternalAPIError(f"Google Places text search failed: {e}") from e

    @property
    def requests_count(self) -> int:
        """Get current request count."""
        return self._requests_count

    def reset_request_counter(self) -> None:
        """Reset request counter."""
        self._requests_count = 0
        self.logger.info("Google Places API request counter reset")

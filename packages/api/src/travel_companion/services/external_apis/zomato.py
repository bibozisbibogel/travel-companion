"""Zomato API client for restaurant search."""

import logging
from decimal import Decimal
from typing import Any

import httpx

from travel_companion.models.external import (
    CuisineType,
    DietaryRestriction,
    PriceRange,
    RestaurantContact,
    RestaurantHours,
    RestaurantLocation,
    RestaurantOption,
    RestaurantSearchRequest,
)
from travel_companion.utils.errors import ExternalAPIError


class ZomatoClient:
    """Zomato API client for restaurant search and data."""

    def __init__(self, api_key: str):
        """Initialize Zomato client with API key."""
        if not api_key:
            raise ValueError("Zomato API key is required")

        self.api_key = api_key
        self.base_url = "https://developers.zomato.com/api/v2.1"
        self.logger = logging.getLogger("travel_companion.services.zomato")

        # Rate limiting tracking
        self._requests_count = 0
        self._daily_limit = 1000  # Zomato API limit

    async def search_restaurants(self, request: RestaurantSearchRequest) -> list[RestaurantOption]:
        """Search for restaurants using Zomato API.

        Args:
            request: Restaurant search request parameters

        Returns:
            List of RestaurantOption objects from Zomato results
        """
        try:
            self.logger.info(f"Searching Zomato for restaurants in {request.location}")

            # Check rate limits
            if self._requests_count >= self._daily_limit:
                self.logger.warning("Zomato API daily limit reached")
                return []

            # First, get location details if we don't have coordinates
            location_id = None
            if request.latitude and request.longitude:
                location_id = await self._get_location_by_coordinates(
                    request.latitude, request.longitude
                )
            else:
                location_id = await self._get_location_by_name(request.location)

            if not location_id:
                self.logger.warning(f"Could not resolve location: {request.location}")
                return []

            # Build search parameters
            params = self._build_search_params(request, location_id)

            # Make API request with timeout
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"user-key": self.api_key, "Content-Type": "application/json"}

                response = await client.get(
                    f"{self.base_url}/search", params=params, headers=headers
                )

                self._requests_count += 1
                response.raise_for_status()

                data = response.json()

            # Parse and convert results
            restaurants = []
            restaurant_list = data.get("restaurants", [])

            for restaurant_data in restaurant_list:
                try:
                    restaurant_info = restaurant_data.get("restaurant", {})
                    restaurant = self._parse_restaurant(restaurant_info, request)
                    if restaurant:
                        restaurants.append(restaurant)
                except Exception as e:
                    self.logger.warning(f"Failed to parse Zomato restaurant: {e}")

            self.logger.info(f"Found {len(restaurants)} restaurants from Zomato")
            return restaurants

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                self.logger.error("Zomato API access forbidden - check API key")
                raise ExternalAPIError("Zomato API access denied") from e
            elif e.response.status_code == 429:
                self.logger.warning("Zomato API rate limit exceeded")
                return []
            else:
                self.logger.error(f"Zomato API HTTP error {e.response.status_code}")
                raise ExternalAPIError(f"Zomato API error: {e.response.status_code}") from e

        except httpx.TimeoutException:
            self.logger.warning("Zomato API request timeout")
            raise ExternalAPIError("Zomato API timeout") from None

        except Exception as e:
            self.logger.error(f"Zomato API request failed: {e}")
            raise ExternalAPIError(f"Zomato API request failed: {e}") from e

    async def _get_location_by_coordinates(self, latitude: float, longitude: float) -> int | None:
        """Get Zomato location ID by coordinates."""
        try:
            params = {"lat": latitude, "lon": longitude}

            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"user-key": self.api_key}

                response = await client.get(
                    f"{self.base_url}/locations", params=params, headers=headers
                )

                self._requests_count += 1
                response.raise_for_status()

                data = response.json()

            location_suggestions = data.get("location_suggestions", [])
            if location_suggestions:
                return location_suggestions[0].get("entity_id")

            return None

        except Exception as e:
            self.logger.error(f"Failed to get Zomato location by coordinates: {e}")
            return None

    async def _get_location_by_name(self, location_name: str) -> int | None:
        """Get Zomato location ID by name."""
        try:
            params = {"query": location_name, "count": 1}

            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"user-key": self.api_key}

                response = await client.get(
                    f"{self.base_url}/locations", params=params, headers=headers
                )

                self._requests_count += 1
                response.raise_for_status()

                data = response.json()

            location_suggestions = data.get("location_suggestions", [])
            if location_suggestions:
                return location_suggestions[0].get("entity_id")

            return None

        except Exception as e:
            self.logger.error(f"Failed to get Zomato location by name: {e}")
            return None

    def _build_search_params(
        self, request: RestaurantSearchRequest, location_id: int
    ) -> dict[str, Any]:
        """Build Zomato API search parameters from request."""
        params = {
            "entity_id": location_id,
            "entity_type": "subzone",  # or "city"
            "count": min(request.max_results, 20),  # Zomato max is 20 per request
            "sort": "rating",
            "order": "desc",
        }

        # Radius in meters (Zomato uses radius)
        if request.radius_km:
            radius_meters = min(int(request.radius_km * 1000), 30000)  # Max 30km
            params["radius"] = radius_meters

        # Cuisine filtering
        if request.cuisine_type:
            cuisine_id = self._map_cuisine_to_zomato_id(request.cuisine_type)
            if cuisine_id:
                params["cuisines"] = cuisine_id

        # Category (establishment type)
        params["category"] = "1,2,3"  # Delivery, Dine-out, Takeaway

        return params

    def _map_cuisine_to_zomato_id(self, cuisine: CuisineType) -> str | None:
        """Map our cuisine types to Zomato cuisine IDs."""
        # Common Zomato cuisine IDs (these may vary by location)
        mapping = {
            CuisineType.AMERICAN: "1",
            CuisineType.ITALIAN: "55",
            CuisineType.CHINESE: "25",
            CuisineType.JAPANESE: "60",
            CuisineType.INDIAN: "148",
            CuisineType.MEXICAN: "73",
            CuisineType.FRENCH: "45",
            CuisineType.THAI: "95",
            CuisineType.MEDITERRANEAN: "70",
            CuisineType.SEAFOOD: "83",
            CuisineType.VEGETARIAN: "308",
            CuisineType.PIZZA: "82",
            CuisineType.BBQ: "193",
            CuisineType.FAST_FOOD: "40",
        }
        return mapping.get(cuisine)

    def _parse_restaurant(
        self, restaurant_data: dict[str, Any], request: RestaurantSearchRequest
    ) -> RestaurantOption | None:
        """Parse Zomato restaurant data into RestaurantOption model."""
        try:
            # Extract location data
            location_data = restaurant_data.get("location", {})

            location = RestaurantLocation(
                latitude=float(location_data.get("latitude", 0)),
                longitude=float(location_data.get("longitude", 0)),
                address=location_data.get("address"),
                city=location_data.get("city"),
                country=location_data.get("country_name"),
                postal_code=location_data.get("zipcode"),
            )

            # Map price range from Zomato price range (1-4)
            zomato_price = restaurant_data.get("price_range", 2)
            price_range_map = {
                1: PriceRange.BUDGET,
                2: PriceRange.MODERATE,
                3: PriceRange.EXPENSIVE,
                4: PriceRange.VERY_EXPENSIVE,
            }
            price_range = price_range_map.get(zomato_price, PriceRange.MODERATE)

            # Determine cuisine type from cuisines
            cuisines = restaurant_data.get("cuisines", "")
            cuisine_type = self._determine_cuisine_type(cuisines)

            # Extract hours if available - Zomato has limited hours data
            hours = None
            timings = restaurant_data.get("timings")
            if timings:
                hours = RestaurantHours(
                    monday=timings if timings != "Closed" else "Closed",
                    is_open_now=restaurant_data.get("is_delivering_now", False),
                )

            # Extract contact info
            contact = RestaurantContact(
                phone=restaurant_data.get("phone_numbers"), website=restaurant_data.get("menu_url")
            )

            # Extract photos
            photos = []
            photo_data = restaurant_data.get("photos", [])
            for photo in photo_data[:3]:  # Limit to first 3
                if isinstance(photo, dict) and "photo" in photo:
                    thumb_url = photo["photo"].get("thumb_url")
                    if thumb_url:
                        photos.append(thumb_url)

            # Get average cost
            avg_cost = restaurant_data.get("average_cost_for_two")
            if avg_cost:
                # Divide by 2 to get per person cost
                avg_cost_per_person = Decimal(str(avg_cost)) / 2
            else:
                # Estimate based on price range
                cost_estimates = {
                    PriceRange.BUDGET: Decimal("8.00"),
                    PriceRange.MODERATE: Decimal("20.00"),
                    PriceRange.EXPENSIVE: Decimal("40.00"),
                    PriceRange.VERY_EXPENSIVE: Decimal("70.00"),
                }
                avg_cost_per_person = cost_estimates[price_range]

            # Extract highlights for amenities
            highlights = restaurant_data.get("highlights", [])
            amenities = []
            for highlight in highlights:
                if isinstance(highlight, str):
                    amenities.append(highlight.lower())

            # Determine dietary accommodations from highlights and cuisines
            dietary_accommodations = self._extract_dietary_accommodations(highlights, cuisines)

            return RestaurantOption(
                external_id=str(restaurant_data.get("id", "")),
                name=restaurant_data["name"],
                cuisine_type=cuisine_type,
                location=location,
                rating=float(restaurant_data.get("user_rating", {}).get("aggregate_rating", 0)),
                review_count=restaurant_data.get("user_rating", {}).get("votes", 0),
                price_range=price_range,
                average_cost_per_person=avg_cost_per_person,
                currency=restaurant_data.get("currency", request.currency),
                hours=hours,
                contact=contact,
                amenities=amenities,
                dietary_accommodations=dietary_accommodations,
                photos=photos,
                booking_url=restaurant_data.get("url"),
                provider="zomato",
            )

        except Exception as e:
            self.logger.error(
                f"Failed to parse Zomato restaurant {restaurant_data.get('id', 'unknown')}: {e}"
            )
            return None

    def _determine_cuisine_type(self, cuisines_str: str) -> CuisineType:
        """Determine primary cuisine type from Zomato cuisines string."""
        if not cuisines_str:
            return CuisineType.OTHER

        cuisines_lower = cuisines_str.lower()

        # Map common cuisine strings
        cuisine_mappings = {
            "american": CuisineType.AMERICAN,
            "italian": CuisineType.ITALIAN,
            "chinese": CuisineType.CHINESE,
            "japanese": CuisineType.JAPANESE,
            "indian": CuisineType.INDIAN,
            "mexican": CuisineType.MEXICAN,
            "french": CuisineType.FRENCH,
            "thai": CuisineType.THAI,
            "mediterranean": CuisineType.MEDITERRANEAN,
            "seafood": CuisineType.SEAFOOD,
            "vegetarian": CuisineType.VEGETARIAN,
            "vegan": CuisineType.VEGAN,
            "bbq": CuisineType.BBQ,
            "pizza": CuisineType.PIZZA,
            "sushi": CuisineType.SUSHI,
            "steakhouse": CuisineType.STEAKHOUSE,
            "fast food": CuisineType.FAST_FOOD,
        }

        # Find best matching cuisine type
        for cuisine_key, cuisine_type in cuisine_mappings.items():
            if cuisine_key in cuisines_lower:
                return cuisine_type

        return CuisineType.OTHER

    def _extract_dietary_accommodations(
        self, highlights: list, cuisines: str
    ) -> list[DietaryRestriction]:
        """Extract dietary accommodations from restaurant highlights and cuisines."""
        accommodations = []

        # Check highlights for dietary info
        highlight_text = " ".join(highlights).lower() if highlights else ""
        cuisine_text = cuisines.lower() if cuisines else ""
        combined_text = f"{highlight_text} {cuisine_text}"

        # Map text indicators to dietary restrictions
        if any(term in combined_text for term in ["vegetarian", "veg only"]):
            accommodations.append(DietaryRestriction.VEGETARIAN)

        if "vegan" in combined_text:
            accommodations.append(DietaryRestriction.VEGAN)

        if any(term in combined_text for term in ["gluten free", "gluten-free"]):
            accommodations.append(DietaryRestriction.GLUTEN_FREE)

        if "halal" in combined_text:
            accommodations.append(DietaryRestriction.HALAL)

        if "kosher" in combined_text:
            accommodations.append(DietaryRestriction.KOSHER)

        return accommodations

    async def get_restaurant_details(self, restaurant_id: str) -> dict[str, Any]:
        """Get detailed restaurant information from Zomato.

        Args:
            restaurant_id: Zomato restaurant ID

        Returns:
            Detailed restaurant information
        """
        try:
            params = {"res_id": restaurant_id}

            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"user-key": self.api_key}

                response = await client.get(
                    f"{self.base_url}/restaurant", params=params, headers=headers
                )

                self._requests_count += 1
                response.raise_for_status()

                return response.json()

        except Exception as e:
            self.logger.error(f"Failed to get Zomato restaurant details for {restaurant_id}: {e}")
            raise ExternalAPIError(f"Failed to get restaurant details: {e}") from e

    async def get_reviews(self, restaurant_id: str, count: int = 5) -> list[dict]:
        """Get restaurant reviews from Zomato.

        Args:
            restaurant_id: Zomato restaurant ID
            count: Number of reviews to fetch

        Returns:
            List of restaurant reviews
        """
        try:
            params = {
                "res_id": restaurant_id,
                "start": 0,
                "count": min(count, 10),  # Max 10 reviews per call
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"user-key": self.api_key}

                response = await client.get(
                    f"{self.base_url}/reviews", params=params, headers=headers
                )

                self._requests_count += 1
                response.raise_for_status()

                data = response.json()
                return data.get("user_reviews", [])

        except Exception as e:
            self.logger.error(f"Failed to get Zomato reviews for {restaurant_id}: {e}")
            return []

    @property
    def requests_remaining(self) -> int:
        """Get remaining requests for today."""
        return max(0, self._daily_limit - self._requests_count)

    def reset_daily_counter(self) -> None:
        """Reset daily request counter."""
        self._requests_count = 0
        self.logger.info("Zomato API daily request counter reset")

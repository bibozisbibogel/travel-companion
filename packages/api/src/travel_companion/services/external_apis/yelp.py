"""Yelp Fusion API client for restaurant search."""

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


class YelpClient:
    """Yelp Fusion API client with rate limiting and error handling."""

    def __init__(self, api_key: str):
        """Initialize Yelp client with API key."""
        if not api_key:
            raise ValueError("Yelp API key is required")

        self.api_key = api_key
        self.base_url = "https://api.yelp.com/v3"
        self.logger = logging.getLogger("travel_companion.services.yelp")

        # Rate limiting: 5000 requests per day (Yelp free tier)
        self._requests_today = 0
        self._daily_limit = 5000

    async def search_restaurants(self, request: RestaurantSearchRequest) -> list[RestaurantOption]:
        """Search for restaurants using Yelp Fusion API.

        Args:
            request: Restaurant search request parameters

        Returns:
            List of RestaurantOption objects from Yelp results
        """
        try:
            self.logger.info(f"Searching Yelp for restaurants in {request.location}")

            # Check rate limits
            if self._requests_today >= self._daily_limit:
                self.logger.warning("Yelp API daily limit reached")
                return []

            # Build search parameters
            params = self._build_search_params(request)

            # Make API request with timeout
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Authorization": f"Bearer {self.api_key}"}

                response = await client.get(
                    f"{self.base_url}/businesses/search", params=params, headers=headers
                )

                self._requests_today += 1
                response.raise_for_status()

                data = response.json()

            # Parse and convert results
            restaurants = []
            for business in data.get("businesses", []):
                try:
                    restaurant = self._parse_business(business, request)
                    if restaurant:
                        restaurants.append(restaurant)
                except Exception as e:
                    self.logger.warning(f"Failed to parse Yelp business: {e}")

            self.logger.info(f"Found {len(restaurants)} restaurants from Yelp")
            return restaurants

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                self.logger.warning("Yelp API rate limit exceeded")
                return []
            elif e.response.status_code == 400:
                self.logger.error(f"Yelp API bad request: {e.response.text}")
                raise ExternalAPIError(f"Invalid Yelp search parameters: {e.response.text}") from e
            else:
                self.logger.error(f"Yelp API error {e.response.status_code}: {e.response.text}")
                raise ExternalAPIError(f"Yelp API error: {e.response.status_code}") from e

        except httpx.TimeoutException:
            self.logger.warning("Yelp API request timeout")
            raise ExternalAPIError("Yelp API timeout") from None

        except Exception as e:
            self.logger.error(f"Yelp API request failed: {e}")
            raise ExternalAPIError(f"Yelp API request failed: {e}") from e

    def _build_search_params(self, request: RestaurantSearchRequest) -> dict[str, Any]:
        """Build Yelp API search parameters from request."""
        params = {
            "categories": "restaurants",
            "limit": min(request.max_results, 50),  # Yelp max is 50 per request
            "sort_by": "best_match",
        }

        # Location parameters
        if request.latitude and request.longitude:
            params["latitude"] = request.latitude
            params["longitude"] = request.longitude
        else:
            params["location"] = request.location

        if request.radius_km:
            # Convert km to meters (Yelp uses meters, max 40000)
            radius_meters = min(int(request.radius_km * 1000), 40000)
            params["radius"] = radius_meters

        # Price filter (Yelp uses 1-4 scale)
        if request.price_range:
            price_map = {
                PriceRange.BUDGET: "1",
                PriceRange.MODERATE: "2",
                PriceRange.EXPENSIVE: "3",
                PriceRange.VERY_EXPENSIVE: "4",
            }
            params["price"] = price_map.get(request.price_range, "1,2,3,4")

        # Cuisine type mapping to Yelp categories
        if request.cuisine_type:
            cuisine_category = self._map_cuisine_to_yelp_category(request.cuisine_type)
            if cuisine_category:
                params["categories"] = f"restaurants,{cuisine_category}"

        # Open now filter
        if request.open_now:
            params["open_now"] = True

        return params

    def _map_cuisine_to_yelp_category(self, cuisine: CuisineType) -> str | None:
        """Map our cuisine types to Yelp category aliases."""
        mapping = {
            CuisineType.AMERICAN: "newamerican",
            CuisineType.ITALIAN: "italian",
            CuisineType.CHINESE: "chinese",
            CuisineType.JAPANESE: "japanese",
            CuisineType.INDIAN: "indpak",
            CuisineType.MEXICAN: "mexican",
            CuisineType.FRENCH: "french",
            CuisineType.THAI: "thai",
            CuisineType.MEDITERRANEAN: "mediterranean",
            CuisineType.SEAFOOD: "seafood",
            CuisineType.VEGETARIAN: "vegetarian",
            CuisineType.VEGAN: "vegan",
            CuisineType.BBQ: "bbq",
            CuisineType.PIZZA: "pizza",
            CuisineType.SUSHI: "sushi",
            CuisineType.STEAKHOUSE: "steakhouses",
            CuisineType.FAST_FOOD: "hotdogs,burgers,sandwiches",
            CuisineType.FINE_DINING: "fine_dining",
        }
        return mapping.get(cuisine)

    def _parse_business(
        self, business: dict[str, Any], request: RestaurantSearchRequest
    ) -> RestaurantOption | None:
        """Parse Yelp business data into RestaurantOption model."""
        try:
            # Extract location data
            location_data = business.get("location", {})
            coordinates = business.get("coordinates", {})

            location = RestaurantLocation(
                latitude=coordinates.get("latitude", 0.0),
                longitude=coordinates.get("longitude", 0.0),
                address=location_data.get("address1"),
                city=location_data.get("city"),
                state=location_data.get("state"),
                country=location_data.get("country"),
                postal_code=location_data.get("zip_code"),
                neighborhood=location_data.get("neighborhood"),
            )

            # Map price range from Yelp $ system
            yelp_price = business.get("price", "$")
            price_range_map = {
                "$": PriceRange.BUDGET,
                "$$": PriceRange.MODERATE,
                "$$$": PriceRange.EXPENSIVE,
                "$$$$": PriceRange.VERY_EXPENSIVE,
            }
            price_range = price_range_map.get(yelp_price, PriceRange.MODERATE)

            # Determine cuisine type from categories
            categories = business.get("categories", [])
            cuisine_type = self._determine_cuisine_type(categories)

            # Extract hours if available
            hours = None
            if "hours" in business and business["hours"]:
                hours_data = business["hours"][0].get("open", [])
                hours = self._parse_hours(
                    hours_data, business.get("hours", [{}])[0].get("is_open_now", False)
                )

            # Extract contact info
            contact = RestaurantContact(
                phone=business.get("display_phone"),
                email=None,
                website=business.get("url"),
                reservation_url=None,
            )

            # Calculate distance if coordinates provided
            distance_km = None
            if business.get("distance"):
                distance_km = round(business["distance"] / 1000, 2)  # Convert meters to km

            # Estimate average cost per person based on price range
            avg_cost_map = {
                PriceRange.BUDGET: Decimal("12.50"),
                PriceRange.MODERATE: Decimal("22.50"),
                PriceRange.EXPENSIVE: Decimal("45.00"),
                PriceRange.VERY_EXPENSIVE: Decimal("75.00"),
            }
            avg_cost = avg_cost_map.get(price_range)

            return RestaurantOption(
                external_id=business["id"],
                name=business["name"],
                cuisine_type=cuisine_type,
                location=location,
                rating=float(business.get("rating", 0)),
                review_count=business.get("review_count", 0),
                price_range=price_range,
                average_cost_per_person=avg_cost,
                currency=request.currency,
                hours=hours,
                contact=contact,
                photos=[business["image_url"]] if business.get("image_url") else [],
                booking_url=business.get("url"),
                provider="yelp",
                trip_id=None,  # Will be set by the workflow orchestrator
                distance_km=distance_km,
            )

        except Exception as e:
            self.logger.error(f"Failed to parse Yelp business {business.get('id', 'unknown')}: {e}")
            return None

    def _determine_cuisine_type(self, categories: list[dict[str, str]]) -> CuisineType:
        """Determine primary cuisine type from Yelp categories."""
        # Map Yelp category aliases back to our cuisine types
        category_map = {
            "newamerican": CuisineType.AMERICAN,
            "italian": CuisineType.ITALIAN,
            "chinese": CuisineType.CHINESE,
            "japanese": CuisineType.JAPANESE,
            "indpak": CuisineType.INDIAN,
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
            "steakhouses": CuisineType.STEAKHOUSE,
            "burgers": CuisineType.AMERICAN,
            "sandwiches": CuisineType.AMERICAN,
            "hotdogs": CuisineType.AMERICAN,
        }

        # Find best matching cuisine type
        for category in categories:
            alias = category.get("alias", "")
            if alias in category_map:
                return category_map[alias]

        # Default to OTHER if no specific match
        return CuisineType.OTHER

    def _parse_hours(self, hours_data: list[dict[str, str]], is_open_now: bool) -> RestaurantHours:
        """Parse Yelp hours data into RestaurantHours model."""
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        hours_dict: dict[str, str | None] = {}

        # Initialize all days
        for day in days:
            hours_dict[day] = None

        # Parse hours data
        for hour_entry in hours_data:
            day_index = int(hour_entry.get("day", 0))  # 0=Monday, 1=Tuesday, etc.
            if 0 <= day_index < 7:
                day_name = days[day_index]
                start_time = hour_entry.get("start", "")
                end_time = hour_entry.get("end", "")

                if start_time and end_time:
                    # Convert 24hr format to readable format
                    start_formatted = f"{start_time[:2]}:{start_time[2:]}"
                    end_formatted = f"{end_time[:2]}:{end_time[2:]}"
                    hours_dict[day_name] = f"{start_formatted} - {end_formatted}"

        return RestaurantHours(**hours_dict, is_open_now=is_open_now)

    async def get_business_details(self, business_id: str) -> dict[str, Any]:
        """Get detailed business information from Yelp.

        Args:
            business_id: Yelp business ID

        Returns:
            Detailed business information including reviews and photos
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Authorization": f"Bearer {self.api_key}"}

                response = await client.get(
                    f"{self.base_url}/businesses/{business_id}", headers=headers
                )

                self._requests_today += 1
                response.raise_for_status()

                data = response.json()
                return dict(data) if data else {}

        except Exception as e:
            self.logger.error(f"Failed to get Yelp business details for {business_id}: {e}")
            raise ExternalAPIError(f"Failed to get business details: {e}") from e

    def reset_daily_counter(self) -> None:
        """Reset daily request counter (should be called daily)."""
        self._requests_today = 0
        self.logger.info("Yelp API daily request counter reset")

    @property
    def requests_remaining(self) -> int:
        """Get remaining requests for today."""
        return max(0, self._daily_limit - self._requests_today)

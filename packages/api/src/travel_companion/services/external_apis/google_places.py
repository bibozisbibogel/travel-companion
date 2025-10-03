"""Google Places API (New) integration for place search and details."""

import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field

from travel_companion.core.config import get_settings

logger = logging.getLogger(__name__)


class PlaceLocation(BaseModel):
    """Location coordinates."""

    latitude: float
    longitude: float


class PlaceOpeningHours(BaseModel):
    """Opening hours information."""

    open_now: bool | None = None
    periods: list[dict[str, Any]] = Field(default_factory=list)
    weekday_text: list[str] = Field(default_factory=list)


class PlaceReview(BaseModel):
    """User review information."""

    author_name: str
    author_url: str | None = None
    rating: float
    relative_time_description: str
    text: str
    time: int


class PlacePhoto(BaseModel):
    """Place photo information."""

    name: str
    width_px: int
    height_px: int
    author_attributions: list[dict[str, Any]] = Field(default_factory=list)


class Place(BaseModel):
    """Google Places (New) API place model."""

    id: str
    display_name: dict[str, str]
    formatted_address: str | None = None
    location: PlaceLocation | None = None
    types: list[str] = Field(default_factory=list)
    primary_type: str | None = None
    rating: float | None = None
    user_rating_count: int | None = None
    price_level: str | None = None  # PRICE_LEVEL_INEXPENSIVE, PRICE_LEVEL_MODERATE, etc.
    current_opening_hours: PlaceOpeningHours | None = None
    website_uri: str | None = None
    international_phone_number: str | None = None
    photos: list[PlacePhoto] = Field(default_factory=list)
    reviews: list[PlaceReview] = Field(default_factory=list)
    google_maps_uri: str | None = None


class GooglePlacesNewAPI:
    """Google Places API (New) client for searching places and getting details."""

    def __init__(self, api_key: str | None = None):
        """Initialize Google Places API (New) client."""
        self.api_key = api_key or get_settings().google_places_api_key
        if not self.api_key:
            raise ValueError("Google Places API key is required")

        # New API endpoint
        self.base_url = "https://places.googleapis.com/v1/places"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "*",  # Default to all fields
            },
        )

    async def __aenter__(self) -> "GooglePlacesNewAPI":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

    async def text_search(
        self,
        text_query: str,
        location_bias: tuple[float, float] | None = None,
        radius: int | None = None,
        min_rating: float | None = None,
        price_levels: list[str] | None = None,
        open_now: bool | None = None,
        max_result_count: int = 20,
        field_mask: str | None = None,
    ) -> list[Place]:
        """
        Search for places using text query (New API).

        Args:
            text_query: Text query for place search
            location_bias: Optional (latitude, longitude) for location bias
            radius: Search radius in meters
            min_rating: Minimum rating filter (1.0-5.0)
            price_levels: List of price levels (e.g., ["PRICE_LEVEL_INEXPENSIVE"])
            open_now: Filter for places open now
            max_result_count: Maximum number of results (1-20)
            field_mask: Fields to return (comma-separated)

        Returns:
            List of places matching the search
        """
        try:
            url = f"{self.base_url}:searchText"

            # Build request body
            body = {
                "textQuery": text_query,
                "maxResultCount": min(max_result_count, 20),
            }

            # Add location bias if provided
            if location_bias and radius:
                body["locationBias"] = {
                    "circle": {
                        "center": {
                            "latitude": location_bias[0],
                            "longitude": location_bias[1],
                        },
                        "radius": radius,
                    }
                }

            # Add filters
            if min_rating:
                body["minRating"] = min_rating

            if price_levels:
                body["priceLevels"] = price_levels

            if open_now is not None:
                body["openNow"] = open_now

            # Update headers if custom field mask provided
            headers = {}
            if field_mask:
                headers["X-Goog-FieldMask"] = field_mask
            else:
                # Default fields for search
                headers["X-Goog-FieldMask"] = (
                    "places.id,"
                    "places.displayName,"
                    "places.formattedAddress,"
                    "places.location,"
                    "places.types,"
                    "places.primaryType,"
                    "places.rating,"
                    "places.userRatingCount,"
                    "places.priceLevel,"
                    "places.currentOpeningHours,"
                    "places.photos,"
                    "places.googleMapsUri"
                )

            response = await self.client.post(url, json=body, headers=headers)
            response.raise_for_status()

            data = response.json()

            places = []
            for place_data in data.get("places", []):
                place = self._parse_place(place_data)
                places.append(place)

            return places

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error searching places: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error searching places: {e}")
            raise

    async def nearby_search(
        self,
        location: tuple[float, float],
        radius: int = 1000,
        included_types: list[str] | None = None,
        excluded_types: list[str] | None = None,
        min_rating: float | None = None,
        price_levels: list[str] | None = None,
        open_now: bool | None = None,
        max_result_count: int = 20,
        field_mask: str | None = None,
    ) -> list[Place]:
        """
        Search for places near a location (New API).

        Args:
            location: (latitude, longitude) tuple
            radius: Search radius in meters (max 50000)
            included_types: Types to include (e.g., ["restaurant", "cafe"])
            excluded_types: Types to exclude
            min_rating: Minimum rating filter
            price_levels: Price level filters
            open_now: Filter for open places
            max_result_count: Maximum results (1-20)
            field_mask: Fields to return

        Returns:
            List of nearby places
        """
        try:
            url = f"{self.base_url}:searchNearby"

            body = {
                "locationRestriction": {
                    "circle": {
                        "center": {
                            "latitude": location[0],
                            "longitude": location[1],
                        },
                        "radius": min(radius, 50000),
                    }
                },
                "maxResultCount": min(max_result_count, 20),
            }

            if included_types:
                body["includedTypes"] = included_types

            if excluded_types:
                body["excludedTypes"] = excluded_types

            if min_rating:
                body["minRating"] = min_rating

            if price_levels:
                body["priceLevels"] = price_levels

            if open_now is not None:
                body["openNow"] = open_now

            headers = {}
            if field_mask:
                headers["X-Goog-FieldMask"] = field_mask
            else:
                headers["X-Goog-FieldMask"] = (
                    "places.id,"
                    "places.displayName,"
                    "places.formattedAddress,"
                    "places.location,"
                    "places.types,"
                    "places.primaryType,"
                    "places.rating,"
                    "places.userRatingCount,"
                    "places.priceLevel,"
                    "places.currentOpeningHours,"
                    "places.photos,"
                    "places.googleMapsUri"
                )

            response = await self.client.post(url, json=body, headers=headers)
            response.raise_for_status()

            data = response.json()

            places = []
            for place_data in data.get("places", []):
                place = self._parse_place(place_data)
                places.append(place)

            return places

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in nearby search: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error in nearby search: {e}")
            raise

    async def get_place(
        self,
        place_id: str,
        field_mask: str | None = None,
    ) -> Place:
        """
        Get detailed information about a place.

        Args:
            place_id: Google Place ID
            field_mask: Specific fields to retrieve

        Returns:
            Detailed place information
        """
        try:
            url = f"{self.base_url}/{place_id}"

            headers = {}
            if field_mask:
                headers["X-Goog-FieldMask"] = field_mask
            else:
                # Get comprehensive details
                headers["X-Goog-FieldMask"] = (
                    "id,"
                    "displayName,"
                    "formattedAddress,"
                    "location,"
                    "types,"
                    "primaryType,"
                    "rating,"
                    "userRatingCount,"
                    "priceLevel,"
                    "currentOpeningHours,"
                    "websiteUri,"
                    "internationalPhoneNumber,"
                    "photos,"
                    "reviews,"
                    "googleMapsUri"
                )

            response = await self.client.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            return self._parse_place(data)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting place details: {e.response.text}")
            raise ValueError(f"Failed to get place details: {e.response.text}") from e
        except Exception as e:
            logger.error(f"Error getting place details: {e}")
            raise

    def _parse_place(self, data: dict[str, Any]) -> Place:
        """Parse place data from API response."""
        # Parse location
        location = None
        if "location" in data:
            location = PlaceLocation(
                latitude=data["location"]["latitude"],
                longitude=data["location"]["longitude"],
            )

        # Parse opening hours
        opening_hours = None
        if "currentOpeningHours" in data:
            hours_data = data["currentOpeningHours"]
            opening_hours = PlaceOpeningHours(
                open_now=hours_data.get("openNow"),
                periods=hours_data.get("periods", []),
                weekday_text=hours_data.get("weekdayText", []),
            )

        # Parse photos
        photos = []
        for photo_data in data.get("photos", []):
            photos.append(
                PlacePhoto(
                    name=photo_data.get("name", ""),
                    width_px=photo_data.get("widthPx", 0),
                    height_px=photo_data.get("heightPx", 0),
                    author_attributions=photo_data.get("authorAttributions", []),
                )
            )

        # Parse reviews
        reviews = []
        for review_data in data.get("reviews", []):
            # Handle text field which may be a dict with 'text' and 'languageCode'
            text_data = review_data.get("text", "")
            if isinstance(text_data, dict):
                text = text_data.get("text", "")
            else:
                text = text_data

            reviews.append(
                PlaceReview(
                    author_name=review_data.get("authorName", ""),
                    author_url=review_data.get("authorUrl"),
                    rating=review_data.get("rating", 0),
                    relative_time_description=review_data.get("relativeTimeDescription", ""),
                    text=text,
                    time=review_data.get("time", 0),
                )
            )

        return Place(
            id=data.get("id", ""),
            display_name=data.get("displayName", {"text": ""}),
            formatted_address=data.get("formattedAddress"),
            location=location,
            types=data.get("types", []),
            primary_type=data.get("primaryType"),
            rating=data.get("rating"),
            user_rating_count=data.get("userRatingCount"),
            price_level=data.get("priceLevel"),
            current_opening_hours=opening_hours,
            website_uri=data.get("websiteUri"),
            international_phone_number=data.get("internationalPhoneNumber"),
            photos=photos,
            reviews=reviews,
            google_maps_uri=data.get("googleMapsUri"),
        )

    def get_photo_url(self, photo_name: str, max_width: int = 400, max_height: int = 400) -> str:
        """
        Get URL for a place photo using the new API.

        Args:
            photo_name: Photo resource name from API
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels

        Returns:
            Photo URL
        """
        base = "https://places.googleapis.com/v1"
        return (
            f"{base}/{photo_name}/media"
            f"?maxHeightPx={max_height}&maxWidthPx={max_width}"
            f"&key={self.api_key}"
        )

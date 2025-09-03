"""
Airbnb API client for alternative accommodation search integration.

Handles REST API authentication, rate limiting, and accommodation search operations.
"""

import asyncio
import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field

from travel_companion.core.config import get_settings
from travel_companion.utils.circuit_breaker import CircuitBreaker
from travel_companion.utils.errors import ExternalAPIError, RateLimitError

logger = logging.getLogger(__name__)


class AirbnbCredentials(BaseModel):
    """Airbnb API credentials model."""

    api_key: str = Field(..., description="Airbnb API key")


class AirbnbSearchParams(BaseModel):
    """Accommodation search parameters for Airbnb API."""

    location: str = Field(..., description="Search location (city, address, etc.)")
    check_in: str = Field(..., description="Check-in date (YYYY-MM-DD)")
    check_out: str = Field(..., description="Check-out date (YYYY-MM-DD)")
    guest_count: int = Field(..., ge=1, le=16, description="Number of guests")
    max_results: int = Field(default=50, ge=1, le=100, description="Maximum results")
    currency: str = Field(default="USD", description="Currency code")
    language: str = Field(default="en", description="Language code")
    property_type: str | None = Field(None, description="Property type filter")
    min_price: float | None = Field(None, ge=0, description="Minimum price per night")
    max_price: float | None = Field(None, ge=0, description="Maximum price per night")


class AirbnbListingResult(BaseModel):
    """Accommodation listing result model from Airbnb API."""

    listing_id: str = Field(..., description="Airbnb listing ID")
    name: str = Field(..., description="Listing name/title")
    property_type: str | None = Field(None, description="Property type")
    address: str | None = Field(None, description="Property address")
    latitude: float | None = Field(None, description="Property latitude")
    longitude: float | None = Field(None, description="Property longitude")
    rating: float | None = Field(None, ge=1, le=5, description="Guest rating")
    review_count: int = Field(default=0, ge=0, description="Number of reviews")
    price_per_night: float | None = Field(None, ge=0, description="Price per night")
    currency: str = Field(default="USD", description="Currency code")
    amenities: list[str] = Field(default_factory=list, description="Listing amenities")
    photos: list[str] = Field(default_factory=list, description="Property photo URLs")
    booking_url: str | None = Field(None, description="Direct booking URL")
    description: str | None = Field(None, description="Property description")
    bedrooms: int | None = Field(None, ge=0, description="Number of bedrooms")
    bathrooms: float | None = Field(None, ge=0, description="Number of bathrooms")
    max_guests: int | None = Field(None, ge=1, description="Maximum guest capacity")
    host_name: str | None = Field(None, description="Host name")
    instant_book: bool = Field(default=False, description="Instant booking available")


class AirbnbClient:
    """
    Airbnb API client for accommodation search operations.
    
    Implements rate limiting, circuit breaker pattern, and comprehensive error handling.
    """

    def __init__(self, credentials: AirbnbCredentials | None = None):
        """
        Initialize Airbnb API client.

        Args:
            credentials: API credentials (will use settings if not provided)
        """
        self.settings = get_settings()
        self.credentials = credentials or self._get_default_credentials()

        # Base URLs for Airbnb API endpoints
        self.base_url = "https://api.airbnb.com/v2"
        self.search_url = f"{self.base_url}/search_results"
        self.listing_url = f"{self.base_url}/listings"

        # Rate limiting: 60 requests per minute (conservative)
        self.rate_limiter = asyncio.Semaphore(60)
        self.last_request_time: float = 0.0
        self.min_request_interval = 1.0  # 60 seconds / 60 requests

        # Circuit breaker for API resilience
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,  # More sensitive for Airbnb
            recovery_timeout=300,  # 5 minutes
            expected_exception=(httpx.HTTPError, ExternalAPIError),
            name="AirbnbAPI",
        )

        # HTTP client with timeout configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(25.0),  # Slightly shorter timeout for Airbnb
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    def _get_default_credentials(self) -> AirbnbCredentials:
        """Get default credentials from settings."""
        return AirbnbCredentials(
            api_key=self.settings.airbnb_api_key,
        )

    async def _make_request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make rate-limited HTTP request with circuit breaker protection.

        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            headers: Request headers
            json_data: JSON request body

        Returns:
            API response as dictionary

        Raises:
            RateLimitError: When rate limit is exceeded
            ExternalAPIError: When API returns error response
        """
        async with self.rate_limiter:
            # Enforce minimum time between requests
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - time_since_last)

            self.last_request_time = asyncio.get_event_loop().time()

            # Prepare headers with authentication
            request_headers = {
                "X-Airbnb-API-Key": self.credentials.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "TravelCompanion/1.0",
            }
            if headers:
                request_headers.update(headers)

            try:
                async def make_api_call() -> dict[str, Any]:
                    """Make the actual API call."""
                    response = await self.client.request(
                        method=method,
                        url=url,
                        params=params,
                        headers=request_headers,
                        json=json_data,
                    )

                    # Handle rate limiting
                    if response.status_code == 429:
                        logger.warning("Airbnb API rate limit exceeded")
                        raise RateLimitError("Airbnb API rate limit exceeded")

                    # Handle authentication errors
                    if response.status_code == 401:
                        logger.error("Airbnb API authentication failed")
                        raise ExternalAPIError("Airbnb API authentication failed")

                    # Handle other HTTP errors
                    if response.status_code >= 400:
                        error_detail = f"HTTP {response.status_code}"
                        try:
                            error_data = response.json()
                            if isinstance(error_data, dict):
                                error_detail = error_data.get("error_message",
                                                              error_data.get("message", error_detail))
                        except Exception:
                            error_detail = response.text[:200] if response.text else error_detail

                        logger.error(
                            "Airbnb API error",
                            extra={
                                "status_code": response.status_code,
                                "error": error_detail,
                                "url": url,
                            },
                        )
                        raise ExternalAPIError(f"Airbnb API error: {error_detail}")

                    return response.json()

                return await self.circuit_breaker.call(make_api_call)

            except httpx.TimeoutException as e:
                logger.error("Airbnb API timeout", extra={"url": url, "error": str(e)})
                raise ExternalAPIError(f"Airbnb API timeout: {e}") from e
            except httpx.RequestError as e:
                logger.error("Airbnb API request error", extra={"url": url, "error": str(e)})
                raise ExternalAPIError(f"Airbnb API request error: {e}") from e

    async def search_listings(self, params: AirbnbSearchParams) -> list[AirbnbListingResult]:
        """
        Search for accommodation listings using Airbnb API.

        Args:
            params: Search parameters

        Returns:
            List of accommodation search results

        Raises:
            ExternalAPIError: When API request fails
            ValidationError: When response data is invalid
        """
        logger.info(
            "Starting Airbnb listing search",
            extra={
                "location": params.location,
                "check_in": params.check_in,
                "check_out": params.check_out,
                "guests": params.guest_count,
            },
        )

        # Build search parameters
        search_params = {
            "location": params.location,
            "checkin": params.check_in,
            "checkout": params.check_out,
            "guests": params.guest_count,
            "items_per_grid": min(params.max_results, 100),  # Airbnb max limit
            "currency": params.currency,
            "locale": f"{params.language}_{params.currency}",
        }

        # Add optional filters
        if params.property_type:
            search_params["property_type_id"] = params.property_type

        if params.min_price is not None:
            search_params["price_min"] = int(params.min_price)

        if params.max_price is not None:
            search_params["price_max"] = int(params.max_price)

        try:
            # Make search request
            response_data = await self._make_request(
                method="GET",
                url=self.search_url,
                params=search_params,
            )

            # Parse response
            listings = []
            if "search_results" in response_data:
                for listing_data in response_data["search_results"][:params.max_results]:
                    try:
                        listing = self._parse_listing_result(listing_data)
                        listings.append(listing)
                    except Exception as e:
                        logger.warning(
                            "Failed to parse Airbnb listing result",
                            extra={"listing_data": listing_data, "error": str(e)},
                        )
                        continue

            logger.info(
                "Airbnb listing search completed",
                extra={
                    "listings_found": len(listings),
                    "location": params.location,
                },
            )

            return listings

        except Exception as e:
            logger.error(
                "Airbnb listing search failed",
                extra={
                    "location": params.location,
                    "error": str(e),
                },
            )
            raise ExternalAPIError(f"Airbnb listing search failed: {e}") from e

    def _parse_listing_result(self, listing_data: dict[str, Any]) -> AirbnbListingResult:
        """
        Parse accommodation listing data from Airbnb API response.

        Args:
            listing_data: Raw listing data from API

        Returns:
            Parsed listing result

        Raises:
            ValidationError: When listing data is invalid
        """
        # Extract basic information
        listing_id = str(listing_data.get("listing", {}).get("id", ""))
        name = listing_data.get("listing", {}).get("name", "")
        property_type = listing_data.get("listing", {}).get("property_type", "")

        # Extract location information
        address = None
        latitude = None
        longitude = None
        if "listing" in listing_data and "lat" in listing_data["listing"]:
            latitude = listing_data["listing"].get("lat")
            longitude = listing_data["listing"].get("lng")
            address = listing_data["listing"].get("public_address", "")

        # Extract rating and reviews
        rating = None
        review_count = 0
        if "listing" in listing_data:
            rating = listing_data["listing"].get("star_rating")
            review_count = listing_data["listing"].get("reviews_count", 0)

        # Extract pricing
        price_per_night = None
        currency = "USD"
        if "pricing_quote" in listing_data:
            price_data = listing_data["pricing_quote"]
            price_per_night = price_data.get("rate", {}).get("amount")
            currency = price_data.get("rate", {}).get("currency", "USD")

        # Extract amenities
        amenities = []
        if "listing" in listing_data and "amenities" in listing_data["listing"]:
            amenities = [
                amenity.get("name", "")
                for amenity in listing_data["listing"]["amenities"]
            ]

        # Extract photos
        photos = []
        if "listing" in listing_data and "pictures" in listing_data["listing"]:
            photos = [
                pic.get("large", pic.get("medium", pic.get("small", "")))
                for pic in listing_data["listing"]["pictures"][:8]  # Limit to 8 photos
            ]

        # Extract additional details
        bedrooms = listing_data.get("listing", {}).get("bedrooms")
        bathrooms = listing_data.get("listing", {}).get("bathrooms")
        max_guests = listing_data.get("listing", {}).get("person_capacity")
        host_name = listing_data.get("listing", {}).get("user", {}).get("first_name")
        instant_book = listing_data.get("listing", {}).get("instant_book", False)

        # Extract description
        description = listing_data.get("listing", {}).get("description")

        # Generate booking URL
        booking_url = f"https://www.airbnb.com/rooms/{listing_id}" if listing_id else None

        return AirbnbListingResult(
            listing_id=listing_id,
            name=name,
            property_type=property_type,
            address=address,
            latitude=latitude,
            longitude=longitude,
            rating=rating,
            review_count=review_count,
            price_per_night=price_per_night,
            currency=currency,
            amenities=amenities,
            photos=photos,
            booking_url=booking_url,
            description=description,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            max_guests=max_guests,
            host_name=host_name,
            instant_book=instant_book,
        )

    async def get_listing_details(self, listing_id: str) -> AirbnbListingResult | None:
        """
        Get detailed information for a specific listing.

        Args:
            listing_id: Airbnb listing ID

        Returns:
            Detailed listing information or None if not found

        Raises:
            ExternalAPIError: When API request fails
        """
        logger.info("Getting Airbnb listing details", extra={"listing_id": listing_id})

        try:
            response_data = await self._make_request(
                method="GET",
                url=f"{self.listing_url}/{listing_id}",
            )

            if "listing" in response_data:
                return self._parse_listing_result({"listing": response_data["listing"]})

            return None

        except Exception as e:
            logger.error(
                "Failed to get Airbnb listing details",
                extra={"listing_id": listing_id, "error": str(e)},
            )
            raise ExternalAPIError(f"Failed to get Airbnb listing details: {e}") from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


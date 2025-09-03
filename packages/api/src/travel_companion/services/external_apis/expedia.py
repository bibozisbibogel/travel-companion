"""
Expedia API client for hotel accommodation search integration.

Handles REST API authentication, rate limiting, and hotel search operations.
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


class ExpediaCredentials(BaseModel):
    """Expedia API credentials model."""

    api_key: str = Field(..., description="Expedia API key")
    secret_key: str = Field(..., description="Expedia secret key")


class ExpediaSearchParams(BaseModel):
    """Hotel search parameters for Expedia API."""

    location: str = Field(..., description="Hotel search location")
    check_in: str = Field(..., description="Check-in date (YYYY-MM-DD)")
    check_out: str = Field(..., description="Check-out date (YYYY-MM-DD)")
    guest_count: int = Field(..., ge=1, le=20, description="Number of guests")
    room_count: int = Field(default=1, ge=1, le=10, description="Number of rooms")
    max_results: int = Field(default=50, ge=1, le=250, description="Maximum results")
    currency: str = Field(default="USD", description="Currency code")
    language: str = Field(default="en", description="Language code")


class ExpediaHotelResult(BaseModel):
    """Hotel result model from Expedia API."""

    hotel_id: str = Field(..., description="Expedia hotel ID")
    name: str = Field(..., description="Hotel name")
    address: str | None = Field(None, description="Hotel address")
    latitude: float | None = Field(None, description="Hotel latitude")
    longitude: float | None = Field(None, description="Hotel longitude")
    rating: float | None = Field(None, ge=1, le=5, description="Hotel rating")
    price_per_night: float | None = Field(None, ge=0, description="Price per night")
    currency: str = Field(default="USD", description="Currency code")
    amenities: list[str] = Field(default_factory=list, description="Hotel amenities")
    photos: list[str] = Field(default_factory=list, description="Hotel photo URLs")
    booking_url: str | None = Field(None, description="Direct booking URL")
    description: str | None = Field(None, description="Hotel description")


class ExpediaClient:
    """
    Expedia API client for hotel search operations.
    
    Implements rate limiting, circuit breaker pattern, and comprehensive error handling.
    """

    def __init__(self, credentials: ExpediaCredentials | None = None):
        """
        Initialize Expedia API client.

        Args:
            credentials: API credentials (will use settings if not provided)
        """
        self.settings = get_settings()
        self.credentials = credentials or self._get_default_credentials()

        # Base URLs for different Expedia API endpoints
        self.base_url = "https://api.expediagroup.com"
        self.search_url = f"{self.base_url}/v1/lodging/search"
        self.details_url = f"{self.base_url}/v1/lodging/details"

        # Rate limiting: 100 requests per minute
        self.rate_limiter = asyncio.Semaphore(100)
        self.last_request_time: float = 0.0
        self.min_request_interval = 0.6  # 60 seconds / 100 requests

        # Circuit breaker for API resilience
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=300,  # 5 minutes
            expected_exception=(httpx.HTTPError, ExternalAPIError),
            name="ExpediaAPI",
        )

        # HTTP client with timeout configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )

    def _get_default_credentials(self) -> ExpediaCredentials:
        """Get default credentials from settings."""
        return ExpediaCredentials(
            api_key=self.settings.expedia_api_key,
            secret_key=self.settings.expedia_secret_key,
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
                "Authorization": f"Bearer {self.credentials.api_key}",
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
                        logger.warning("Expedia API rate limit exceeded")
                        raise RateLimitError("Expedia API rate limit exceeded")

                    # Handle other HTTP errors
                    if response.status_code >= 400:
                        error_detail = f"HTTP {response.status_code}"
                        try:
                            error_data = response.json()
                            if isinstance(error_data, dict) and "message" in error_data:
                                error_detail = error_data["message"]
                        except Exception:
                            error_detail = response.text[:200] if response.text else error_detail

                        logger.error(
                            "Expedia API error",
                            extra={
                                "status_code": response.status_code,
                                "error": error_detail,
                                "url": url,
                            },
                        )
                        raise ExternalAPIError(f"Expedia API error: {error_detail}")

                    return response.json()

                return await self.circuit_breaker.call(make_api_call)

            except httpx.TimeoutException as e:
                logger.error("Expedia API timeout", extra={"url": url, "error": str(e)})
                raise ExternalAPIError(f"Expedia API timeout: {e}") from e
            except httpx.RequestError as e:
                logger.error("Expedia API request error", extra={"url": url, "error": str(e)})
                raise ExternalAPIError(f"Expedia API request error: {e}") from e

    async def search_hotels(self, params: ExpediaSearchParams) -> list[ExpediaHotelResult]:
        """
        Search for hotels using Expedia API.

        Args:
            params: Search parameters

        Returns:
            List of hotel search results

        Raises:
            ExternalAPIError: When API request fails
            ValidationError: When response data is invalid
        """
        logger.info(
            "Starting Expedia hotel search",
            extra={
                "location": params.location,
                "check_in": params.check_in,
                "check_out": params.check_out,
                "guests": params.guest_count,
                "rooms": params.room_count,
            },
        )

        # Build search parameters
        search_params = {
            "location": params.location,
            "checkin": params.check_in,
            "checkout": params.check_out,
            "adults": params.guest_count,
            "rooms": params.room_count,
            "limit": min(params.max_results, 100),  # Expedia max limit
            "currency": params.currency,
            "locale": f"{params.language}_{params.currency}",
        }

        try:
            # Make search request
            response_data = await self._make_request(
                method="GET",
                url=self.search_url,
                params=search_params,
            )

            # Parse response
            hotels = []
            if "properties" in response_data:
                for property_data in response_data["properties"][:params.max_results]:
                    try:
                        hotel = self._parse_hotel_result(property_data)
                        hotels.append(hotel)
                    except Exception as e:
                        logger.warning(
                            "Failed to parse Expedia hotel result",
                            extra={"hotel_data": property_data, "error": str(e)},
                        )
                        continue

            logger.info(
                "Expedia hotel search completed",
                extra={
                    "hotels_found": len(hotels),
                    "location": params.location,
                },
            )

            return hotels

        except Exception as e:
            logger.error(
                "Expedia hotel search failed",
                extra={
                    "location": params.location,
                    "error": str(e),
                },
            )
            raise ExternalAPIError(f"Expedia hotel search failed: {e}") from e

    def _parse_hotel_result(self, property_data: dict[str, Any]) -> ExpediaHotelResult:
        """
        Parse hotel property data from Expedia API response.

        Args:
            property_data: Raw property data from API

        Returns:
            Parsed hotel result

        Raises:
            ValidationError: When property data is invalid
        """
        # Extract basic information
        hotel_id = str(property_data.get("id", ""))
        name = property_data.get("name", "")

        # Extract location
        address = None
        latitude = None
        longitude = None
        if "address" in property_data:
            addr_data = property_data["address"]
            address = addr_data.get("line1", "")
            if "coordinates" in addr_data:
                coordinates = addr_data["coordinates"]
                latitude = coordinates.get("latitude")
                longitude = coordinates.get("longitude")

        # Extract rating
        rating = None
        if "rating" in property_data and "overall" in property_data["rating"]:
            rating = property_data["rating"]["overall"]

        # Extract pricing
        price_per_night = None
        currency = "USD"
        if "rates" in property_data and property_data["rates"]:
            rate_data = property_data["rates"][0]
            if "price" in rate_data:
                price_data = rate_data["price"]
                price_per_night = price_data.get("total")
                currency = price_data.get("currency", "USD")

        # Extract amenities
        amenities = []
        if "amenities" in property_data:
            amenities = [amenity.get("name", "") for amenity in property_data["amenities"]]

        # Extract photos
        photos = []
        if "images" in property_data:
            photos = [img.get("url", "") for img in property_data["images"][:5]]  # Limit to 5 photos

        # Extract booking URL
        booking_url = property_data.get("booking_url")

        # Extract description
        description = property_data.get("description")

        return ExpediaHotelResult(
            hotel_id=hotel_id,
            name=name,
            address=address,
            latitude=latitude,
            longitude=longitude,
            rating=rating,
            price_per_night=price_per_night,
            currency=currency,
            amenities=amenities,
            photos=photos,
            booking_url=booking_url,
            description=description,
        )

    async def get_hotel_details(self, hotel_id: str) -> ExpediaHotelResult | None:
        """
        Get detailed information for a specific hotel.

        Args:
            hotel_id: Expedia hotel ID

        Returns:
            Detailed hotel information or None if not found

        Raises:
            ExternalAPIError: When API request fails
        """
        logger.info("Getting Expedia hotel details", extra={"hotel_id": hotel_id})

        try:
            response_data = await self._make_request(
                method="GET",
                url=f"{self.details_url}/{hotel_id}",
            )

            if "property" in response_data:
                return self._parse_hotel_result(response_data["property"])

            return None

        except Exception as e:
            logger.error(
                "Failed to get Expedia hotel details",
                extra={"hotel_id": hotel_id, "error": str(e)},
            )
            raise ExternalAPIError(f"Failed to get Expedia hotel details: {e}") from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


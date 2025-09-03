"""
Booking.com API client for hotel accommodation search integration.

Handles XML API authentication, rate limiting, and hotel search operations.
"""

import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from travel_companion.core.config import get_settings
from travel_companion.utils.circuit_breaker import CircuitBreaker
from travel_companion.utils.errors import ExternalAPIError, RateLimitError

logger = logging.getLogger(__name__)


class BookingCredentials(BaseModel):
    """Booking.com API credentials model."""

    username: str = Field(..., description="Booking.com API username")
    password: str = Field(..., description="Booking.com API password")


class HotelSearchParams(BaseModel):
    """Hotel search parameters for Booking.com API."""

    location: str = Field(..., description="Hotel search location")
    check_in: str = Field(..., description="Check-in date (YYYY-MM-DD)")
    check_out: str = Field(..., description="Check-out date (YYYY-MM-DD)")
    guest_count: int = Field(..., ge=1, le=20, description="Number of guests")
    room_count: int = Field(default=1, ge=1, le=10, description="Number of rooms")
    max_results: int = Field(default=50, ge=1, le=250, description="Maximum results")
    currency: str = Field(default="USD", description="Currency code")
    language: str = Field(default="en", description="Language code")


class BookingHotelResult(BaseModel):
    """Hotel result model from Booking.com API."""

    hotel_id: str = Field(..., description="Booking.com hotel ID")
    name: str = Field(..., description="Hotel name")
    address: str | None = Field(None, description="Hotel address")
    latitude: float | None = Field(None, description="Hotel latitude")
    longitude: float | None = Field(None, description="Hotel longitude")
    price_per_night: float = Field(..., description="Price per night")
    currency: str = Field(..., description="Price currency")
    rating: float | None = Field(None, description="Hotel rating")
    review_score: float | None = Field(None, description="Review score")
    amenities: list[str] = Field(default_factory=list, description="Hotel amenities")
    photos: list[str] = Field(default_factory=list, description="Hotel photos")
    description: str | None = Field(None, description="Hotel description")
    booking_url: str | None = Field(None, description="Booking URL")


class BookingApiResponse(BaseModel):
    """Booking.com API response model."""

    hotels: list[BookingHotelResult] = Field(default_factory=list)
    total_results: int = Field(default=0)
    search_time_ms: int = Field(default=0)
    api_response_time_ms: int = Field(default=0)


class BookingClient:
    """
    Booking.com API client with XML API integration.

    Handles hotel search operations with proper rate limiting and error handling.
    Rate limit: 100 requests/minute per property type as per Booking.com requirements.
    """

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        base_url: str = "https://distribution-xml.booking.com",
        timeout: float = 30.0,
        max_retries: int = 3,
        rate_limit_per_minute: int = 100,
    ):
        """
        Initialize Booking.com API client.

        Args:
            username: Booking.com API username
            password: Booking.com API password
            base_url: Base URL for Booking.com API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            rate_limit_per_minute: Maximum requests per minute
        """
        settings = get_settings()
        self.username = username or getattr(settings, "booking_username", None)
        self.password = password or getattr(settings, "booking_password", None)
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_per_minute = rate_limit_per_minute

        # Initialize HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

        # Rate limiting with asyncio semaphore (100 requests per minute = ~1.67 per second)
        self._rate_limiter = asyncio.Semaphore(10)  # Burst of 10, controlled by sleep
        self._last_request_time = 0.0

        # Circuit breaker for API resilience
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=300,  # 5 minutes
            expected_exception=(ExternalAPIError, httpx.RequestError),
            name="BookingAPI",
        )

        if not self.username or not self.password:
            logger.warning("Booking.com API credentials not configured")

        logger.info("Booking.com API client initialized")

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _rate_limit(self) -> None:
        """Apply rate limiting (100 requests/minute)."""
        async with self._rate_limiter:
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self._last_request_time

            # Ensure minimum 0.6 seconds between requests (100/minute = 1.67/second)
            min_interval = 0.6
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                await asyncio.sleep(sleep_time)

            self._last_request_time = asyncio.get_event_loop().time()

    def _create_hotel_search_xml(self, params: HotelSearchParams) -> str:
        """
        Create XML payload for hotel availability search.

        Args:
            params: Hotel search parameters

        Returns:
            XML payload string
        """
        xml_payload = f"""<?xml version="1.0" encoding="UTF-8"?>
<request>
    <username>{self.username}</username>
    <password>{self.password}</password>
    <hotel_availability>
        <location>{params.location}</location>
        <checkin>{params.check_in}</checkin>
        <checkout>{params.check_out}</checkout>
        <num_rooms>{params.room_count}</num_rooms>
        <guests>{params.guest_count}</guests>
        <currency>{params.currency}</currency>
        <language>{params.language}</language>
        <max_rows>{params.max_results}</max_rows>
    </hotel_availability>
</request>"""
        return xml_payload

    def _parse_hotel_response(self, xml_response: str) -> BookingApiResponse:
        """
        Parse XML response from Booking.com hotel search.

        Args:
            xml_response: XML response string

        Returns:
            Parsed BookingApiResponse
        """
        start_time = datetime.now(UTC)

        try:
            root = ET.fromstring(xml_response)
            hotels = []

            # Parse hotel results from XML
            for hotel_element in root.findall(".//hotel"):
                try:
                    hotel_data = {
                        "hotel_id": hotel_element.get("hotel_id", ""),
                        "name": hotel_element.findtext("name", ""),
                        "address": hotel_element.findtext("address"),
                        "price_per_night": float(hotel_element.findtext("price", "0")),
                        "currency": hotel_element.findtext("currency", "USD"),
                    }

                    # Parse coordinates if available
                    location_elem = hotel_element.find("location")
                    if location_elem is not None:
                        hotel_data["latitude"] = float(
                            location_elem.findtext("latitude", "0") or "0"
                        )
                        hotel_data["longitude"] = float(
                            location_elem.findtext("longitude", "0") or "0"
                        )

                    # Parse rating if available
                    rating_text = hotel_element.findtext("rating")
                    if rating_text:
                        hotel_data["rating"] = float(rating_text)

                    # Parse review score if available
                    review_score_text = hotel_element.findtext("review_score")
                    if review_score_text:
                        hotel_data["review_score"] = float(review_score_text)

                    # Parse amenities
                    amenities_elem = hotel_element.find("amenities")
                    if amenities_elem is not None:
                        hotel_data["amenities"] = [
                            amenity.text
                            for amenity in amenities_elem.findall("amenity")
                            if amenity.text
                        ]

                    # Parse photos
                    photos_elem = hotel_element.find("photos")
                    if photos_elem is not None:
                        hotel_data["photos"] = [
                            photo.text for photo in photos_elem.findall("photo") if photo.text
                        ]

                    # Additional fields
                    hotel_data["description"] = hotel_element.findtext("description")
                    hotel_data["booking_url"] = hotel_element.findtext("booking_url")

                    hotels.append(BookingHotelResult(**hotel_data))

                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse hotel element: {e}")
                    continue

            # Calculate parsing time
            end_time = datetime.now(UTC)
            parse_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Get total results from response
            total_results = len(hotels)
            total_elem = root.find(".//total_results")
            if total_elem is not None and total_elem.text:
                total_results = int(total_elem.text)

            return BookingApiResponse(
                hotels=hotels,
                total_results=total_results,
                search_time_ms=parse_time_ms,
            )

        except ET.ParseError as e:
            logger.error(f"Failed to parse XML response: {e}")
            raise ExternalAPIError(
                f"Failed to parse Booking.com response: {e}",
                service="booking",
                details={"xml_response": xml_response[:500]},  # First 500 chars for debugging
            ) from e

    async def search_hotels(self, params: HotelSearchParams) -> BookingApiResponse:
        """
        Search for hotel availability using Booking.com API.

        Args:
            params: Hotel search parameters

        Returns:
            BookingApiResponse with hotel results

        Raises:
            ExternalAPIError: For API errors
            RateLimitError: For rate limit exceeded
            ValueError: For invalid parameters
        """
        if not self.username or not self.password:
            raise ExternalAPIError(
                "Booking.com API credentials not configured",
                service="booking",
                error_code="CREDENTIALS_MISSING",
            )

        # Validate search parameters
        try:
            datetime.strptime(params.check_in, "%Y-%m-%d")
            datetime.strptime(params.check_out, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid date format: {e}") from e

        logger.info(
            f"Searching hotels: location={params.location}, "
            f"check_in={params.check_in}, check_out={params.check_out}, "
            f"guests={params.guest_count}"
        )

        # Apply rate limiting
        await self._rate_limit()

        # Create XML payload
        xml_payload = self._create_hotel_search_xml(params)

        # Make API request through circuit breaker
        try:
            response = await self._circuit_breaker.call(
                self._make_api_request, "/json/bookings.getHotelAvailabilityV2", xml_payload
            )

            # Parse and return response
            return self._parse_hotel_response(response)

        except Exception as e:
            logger.error(f"Hotel search failed for location {params.location}: {e}")
            raise

    async def _make_api_request(self, endpoint: str, xml_payload: str) -> str:
        """
        Make HTTP request to Booking.com API.

        Args:
            endpoint: API endpoint
            xml_payload: XML payload

        Returns:
            Response text

        Raises:
            ExternalAPIError: For API errors
            RateLimitError: For rate limit exceeded
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/xml",
            "User-Agent": "TravelCompanion/1.0",
        }

        start_time = datetime.now(UTC)

        try:
            response = await self.client.post(url, content=xml_payload, headers=headers)

            # Calculate API response time
            end_time = datetime.now(UTC)
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Booking.com rate limit exceeded, retry after {retry_after}s")
                raise RateLimitError(
                    "Booking.com API rate limit exceeded",
                    service="booking",
                    retry_after=retry_after,
                )

            # Handle other HTTP errors
            if response.status_code >= 400:
                error_msg = f"Booking.com API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise ExternalAPIError(
                    error_msg,
                    service="booking",
                    status_code=response.status_code,
                    details={"response_text": response.text},
                )

            logger.info(f"Booking.com API request completed in {response_time_ms}ms")
            return response.text

        except httpx.RequestError as e:
            logger.error(f"HTTP request failed to Booking.com: {e}")
            raise ExternalAPIError(
                f"Failed to connect to Booking.com API: {e}",
                service="booking",
                details={"endpoint": endpoint, "error": str(e)},
            ) from e

    async def get_hotel_details(self, hotel_id: str) -> BookingHotelResult | None:
        """
        Get detailed information for a specific hotel.

        Args:
            hotel_id: Booking.com hotel ID

        Returns:
            Detailed hotel information or None if not found
        """
        # Apply rate limiting
        await self._rate_limit()

        # Create XML payload for hotel details
        xml_payload = f"""<?xml version="1.0" encoding="UTF-8"?>
<request>
    <username>{self.username}</username>
    <password>{self.password}</password>
    <hotel_description_photos>
        <hotel_ids>{hotel_id}</hotel_ids>
        <language>en</language>
    </hotel_description_photos>
</request>"""

        try:
            response = await self._circuit_breaker.call(
                self._make_api_request, "/json/bookings.getHotelDescriptionPhotosV2", xml_payload
            )

            # Parse hotel details response
            parsed_response = self._parse_hotel_response(response)
            return parsed_response.hotels[0] if parsed_response.hotels else None

        except Exception as e:
            logger.error(f"Failed to get hotel details for ID {hotel_id}: {e}")
            return None

    def get_health_status(self) -> dict[str, Any]:
        """
        Get health status of the Booking.com API client.

        Returns:
            Health status dictionary
        """
        return {
            "service": "booking",
            "status": "healthy" if self.username and self.password else "degraded",
            "credentials_configured": bool(self.username and self.password),
            "circuit_breaker": self._circuit_breaker.get_status(),
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "timeout": self.timeout,
        }

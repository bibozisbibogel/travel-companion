"""
RapidAPI Booking.com client for hotel accommodation search integration.

Handles RapidAPI authentication, rate limiting, and hotel search operations
using the Booking.com RapidAPI service.
"""

import asyncio
import http.client
import json
import logging
import urllib.parse
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from travel_companion.core.config import get_settings
from travel_companion.utils.circuit_breaker import CircuitBreaker
from travel_companion.utils.errors import ExternalAPIError, RateLimitError

logger = logging.getLogger(__name__)


class RapidAPIBookingCredentials(BaseModel):
    """RapidAPI Booking.com credentials model."""

    api_key: str = Field(..., description="RapidAPI key")
    host: str = Field(default="booking-com15.p.rapidapi.com", description="RapidAPI host")


class RapidAPIDestinationSearchParams(BaseModel):
    """Destination search parameters for RapidAPI Booking.com."""

    query: str = Field(..., description="Search query for destination")


class RapidAPIHotelSearchParams(BaseModel):
    """Hotel search parameters for RapidAPI Booking.com API."""

    dest_id: str = Field(..., description="Destination ID from searchDestination")
    search_type: str = Field(default="CITY", description="Search type (CITY, REGION, etc.)")
    arrival_date: str = Field(..., description="Arrival date (YYYY-MM-DD)")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    adults: int = Field(..., ge=1, le=20, description="Number of adults")
    children_age: str = Field(default="", description="Children ages (comma-separated)")
    room_qty: int = Field(default=1, ge=1, le=10, description="Number of rooms")
    page_number: int = Field(default=1, ge=1, description="Page number for pagination")
    units: str = Field(default="metric", description="Unit system (metric/imperial)")
    temperature_unit: str = Field(default="c", description="Temperature unit (c/f)")
    languagecode: str = Field(default="en-us", description="Language code")
    currency_code: str = Field(default="USD", description="Currency code")
    location: str = Field(default="US", description="Location code")


class RapidAPIDestinationResult(BaseModel):
    """Destination search result from RapidAPI Booking.com."""

    dest_id: str = Field(..., description="Destination ID")
    dest_type: str = Field(..., description="Destination type")
    label: str = Field(..., description="Destination label")
    name: str = Field(..., description="Destination name")
    region: str | None = Field(None, description="Region name")
    country: str | None = Field(None, description="Country name")
    latitude: float | None = Field(None, description="Latitude")
    longitude: float | None = Field(None, description="Longitude")


class RapidAPIHotelResult(BaseModel):
    """Hotel result model from RapidAPI Booking.com API."""

    hotel_id: str = Field(..., description="Hotel ID")
    name: str = Field(..., description="Hotel name")
    address: str | None = Field(None, description="Hotel address")
    latitude: float | None = Field(None, description="Hotel latitude")
    longitude: float | None = Field(None, description="Hotel longitude")
    price_per_night: float | None = Field(None, description="Price per night")
    currency: str = Field(default="USD", description="Currency code")
    rating: float | None = Field(None, ge=0, le=5, description="Hotel rating (0-5)")
    review_score: float | None = Field(None, description="Review score")
    review_count: int | None = Field(None, description="Number of reviews")
    amenities: list[str] = Field(default_factory=list, description="Hotel amenities")
    photos: list[str] = Field(default_factory=list, description="Hotel photo URLs")
    booking_url: str | None = Field(None, description="Booking URL")
    description: str | None = Field(None, description="Hotel description")


class RapidAPIDestinationResponse(BaseModel):
    """Response model for destination search."""

    destinations: list[RapidAPIDestinationResult] = Field(default_factory=list)
    total_results: int = Field(default=0, description="Total number of destinations found")
    api_response_time_ms: int = Field(default=0, description="API response time")


class RapidAPIHotelResponse(BaseModel):
    """Response model for hotel search."""

    hotels: list[RapidAPIHotelResult] = Field(default_factory=list)
    total_results: int = Field(default=0, description="Total number of hotels found")
    page_number: int = Field(default=1, description="Current page number")
    total_pages: int = Field(default=1, description="Total number of pages")
    api_response_time_ms: int = Field(default=0, description="API response time")


class RapidAPIBookingClient:
    """RapidAPI Booking.com client for hotel search operations."""

    def __init__(self, api_key: str | None = None, timeout: int = 30) -> None:
        """Initialize RapidAPI Booking client.

        Args:
            api_key: RapidAPI key (if None, will try to get from settings)
            timeout: Request timeout in seconds
        """
        self.settings = get_settings()
        
        # Get API key from parameter or settings
        self.api_key = api_key or self.settings.rapidapi_booking_api_key
        if not self.api_key:
            logger.warning("RapidAPI Booking API key not configured")
            
        self.host = "booking-com15.p.rapidapi.com"
        self.timeout = timeout
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=ExternalAPIError
        )
        
        # Initialize HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        logger.info(f"RapidAPI Booking client initialized with timeout={timeout}s")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        return {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': self.host
        }

    async def _make_request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make authenticated request to RapidAPI Booking.com.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Parsed JSON response

        Raises:
            ExternalAPIError: For API errors
            RateLimitError: For rate limiting
        """
        if not self.api_key:
            raise ExternalAPIError("RapidAPI key not configured")

        url = f"https://{self.host}{endpoint}"
        headers = self._get_headers()
        
        logger.debug(f"Making RapidAPI Booking request to: {url}")
        
        start_time = datetime.now(UTC)
        
        try:
            response = await self.client.get(url, headers=headers, params=params or {})
            
            # Calculate response time
            response_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            
            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("RapidAPI Booking rate limit exceeded")
                raise RateLimitError("RapidAPI Booking rate limit exceeded")
            
            # Handle authentication errors
            if response.status_code == 401:
                logger.error("RapidAPI Booking authentication failed")
                raise ExternalAPIError("RapidAPI Booking authentication failed")
            
            # Handle other HTTP errors
            if response.status_code >= 400:
                error_msg = f"RapidAPI Booking API error: {response.status_code}"
                logger.error(f"{error_msg}: {response.text}")
                raise ExternalAPIError(error_msg)
            
            # Parse JSON response
            try:
                data = response.json()
                logger.debug(f"RapidAPI Booking response received in {response_time_ms}ms")
                return {"data": data, "response_time_ms": response_time_ms}
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse RapidAPI Booking response: {e}")
                raise ExternalAPIError(f"Invalid JSON response: {e}")
                
        except httpx.TimeoutException:
            logger.error("RapidAPI Booking request timeout")
            raise ExternalAPIError("RapidAPI Booking request timeout")
        except httpx.RequestError as e:
            logger.error(f"RapidAPI Booking request error: {e}")
            raise ExternalAPIError(f"RapidAPI Booking request error: {e}")

    async def search_destination(self, params: RapidAPIDestinationSearchParams) -> RapidAPIDestinationResponse:
        """Search for destinations using RapidAPI Booking.com.

        Args:
            params: Destination search parameters

        Returns:
            RapidAPIDestinationResponse with found destinations

        Raises:
            ExternalAPIError: For API errors
            RateLimitError: For rate limiting
        """
        logger.info(f"Searching destinations for query: {params.query}")
        
        # Use circuit breaker to handle failures
        async def _search():
            query_params = {
                "query": params.query
            }
            
            response = await self._make_request("/api/v1/hotels/searchDestination", query_params)
            return response
        
        try:
            result = await self.circuit_breaker.call(_search)
            response_data = result["data"]
            response_time_ms = result["response_time_ms"]
            
            # Parse destinations from response
            destinations = []
            if isinstance(response_data, dict) and "data" in response_data:
                for dest_data in response_data.get("data", []):
                    try:
                        destination = RapidAPIDestinationResult(
                            dest_id=str(dest_data.get("dest_id", "")),
                            dest_type=dest_data.get("dest_type", ""),
                            label=dest_data.get("label", ""),
                            name=dest_data.get("name", ""),
                            region=dest_data.get("region"),
                            country=dest_data.get("country"),
                            latitude=dest_data.get("latitude"),
                            longitude=dest_data.get("longitude")
                        )
                        destinations.append(destination)
                    except Exception as e:
                        logger.warning(f"Failed to parse destination result: {e}")
                        continue
            
            logger.info(f"Found {len(destinations)} destinations for query: {params.query}")
            
            return RapidAPIDestinationResponse(
                destinations=destinations,
                total_results=len(destinations),
                api_response_time_ms=response_time_ms
            )
            
        except Exception as e:
            logger.error(f"Destination search failed: {e}")
            raise

    async def search_hotels(self, params: RapidAPIHotelSearchParams) -> RapidAPIHotelResponse:
        """Search for hotels using RapidAPI Booking.com.

        Args:
            params: Hotel search parameters

        Returns:
            RapidAPIHotelResponse with found hotels

        Raises:
            ExternalAPIError: For API errors
            RateLimitError: For rate limiting
        """
        logger.info(f"Searching hotels for dest_id: {params.dest_id}")
        
        # Use circuit breaker to handle failures
        async def _search():
            query_params = {
                "dest_id": params.dest_id,
                "search_type": params.search_type,
                "arrival_date": params.arrival_date,
                "departure_date": params.departure_date,
                "adults": params.adults,
                "children_age": params.children_age,
                "room_qty": params.room_qty,
                "page_number": params.page_number,
                "units": params.units,
                "temperature_unit": params.temperature_unit,
                "languagecode": params.languagecode,
                "currency_code": params.currency_code,
                "location": params.location
            }
            
            response = await self._make_request("/api/v1/hotels/searchHotels", query_params)
            return response
        
        try:
            result = await self.circuit_breaker.call(_search)
            response_data = result["data"]
            response_time_ms = result["response_time_ms"]
            
            # Parse hotels from response
            hotels = []
            total_results = 0
            total_pages = 1
            
            if isinstance(response_data, dict) and "data" in response_data:
                data = response_data["data"]
                # Get metadata if available
                meta = data.get("meta", {}) if isinstance(data, dict) else {}
                total_results = meta.get("total", 0) if isinstance(meta, dict) else 0
                total_pages = meta.get("pages", 1) if isinstance(meta, dict) else 1
                
                for hotel_data in data.get("hotels", []):
                    try:
                        # The actual hotel data is nested in "property"
                        property_data = hotel_data.get("property", {})
                        
                        # Extract hotel ID from top level or property
                        hotel_id = str(hotel_data.get("hotel_id", property_data.get("id", "")))
                        
                        # Extract name
                        name = property_data.get("name", "Unknown Hotel")
                        
                        # Extract location information
                        latitude = property_data.get("latitude")
                        longitude = property_data.get("longitude")
                        
                        # Build address from available location data
                        address_parts = []
                        if property_data.get("wishlistName"):
                            address_parts.append(property_data["wishlistName"])
                        if property_data.get("countryCode"):
                            address_parts.append(property_data["countryCode"].upper())
                        address = ", ".join(address_parts) if address_parts else None
                        
                        # Extract price information from priceBreakdown
                        price_per_night = None
                        currency = property_data.get("currency", params.currency_code)
                        
                        price_breakdown = property_data.get("priceBreakdown", {})
                        if price_breakdown:
                            gross_price = price_breakdown.get("grossPrice", {})
                            if gross_price:
                                total_price = gross_price.get("value")
                                currency = gross_price.get("currency", currency)
                                # Calculate per night price (total / number of nights)
                                if total_price:
                                    # Calculate nights between arrival and departure
                                    from datetime import datetime
                                    arrival = datetime.strptime(params.arrival_date, "%Y-%m-%d")
                                    departure = datetime.strptime(params.departure_date, "%Y-%m-%d")
                                    nights = (departure - arrival).days
                                    if nights > 0:
                                        price_per_night = float(total_price) / nights
                        
                        # Extract rating information
                        rating = property_data.get("reviewScore")
                        if rating:
                            # Convert to 0-5 scale if needed (API uses 0-10)
                            rating = float(rating) / 2.0 if float(rating) > 5 else float(rating)
                        
                        # Extract review information
                        review_count = property_data.get("reviewCount")
                        review_score_word = property_data.get("reviewScoreWord", "")
                        
                        # Extract photos
                        photos = property_data.get("photoUrls", [])
                        if not photos and property_data.get("mainPhotoId"):
                            # Construct photo URL if only ID is provided
                            photo_id = property_data["mainPhotoId"]
                            photos = [f"https://cf.bstatic.com/xdata/images/hotel/square500/{photo_id}.jpg"]
                        
                        # Note: Amenities not directly available in this response format
                        # Could parse from accessibilityLabel if needed
                        amenities = []
                        
                        # Construct booking URL (not directly provided in response)
                        booking_url = f"https://www.booking.com/hotel/{property_data.get('countryCode', '')}/h{hotel_id}.html" if hotel_id else None
                        
                        hotel = RapidAPIHotelResult(
                            hotel_id=hotel_id,
                            name=name,
                            address=address,
                            latitude=latitude,
                            longitude=longitude,
                            price_per_night=price_per_night,
                            currency=currency,
                            rating=rating,
                            review_score=rating,  # Use same value
                            review_count=review_count,
                            amenities=amenities,
                            photos=photos[:3] if photos else [],  # Limit to 3 photos
                            booking_url=booking_url,
                            description=review_score_word
                        )
                        hotels.append(hotel)
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse hotel result: {e}")
                        continue
            
            logger.info(f"Found {len(hotels)} hotels for dest_id: {params.dest_id}")
            
            return RapidAPIHotelResponse(
                hotels=hotels,
                total_results=total_results,
                page_number=params.page_number,
                total_pages=total_pages,
                api_response_time_ms=response_time_ms
            )
            
        except Exception as e:
            logger.error(f"Hotel search failed: {e}")
            raise

    async def get_destination_id(self, location: str) -> str | None:
        """Get destination ID for a location string.

        Args:
            location: Location query string

        Returns:
            Destination ID if found, None otherwise
        """
        try:
            params = RapidAPIDestinationSearchParams(query=location)
            response = await self.search_destination(params)
            
            if response.destinations:
                # Return the first destination ID
                return response.destinations[0].dest_id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get destination ID for '{location}': {e}")
            return None
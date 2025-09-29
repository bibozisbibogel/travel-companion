"""LiteAPI client for hotel rates and availability via Nuitée."""

import logging
from datetime import datetime
from typing import Any, cast

import httpx
from pydantic import BaseModel, Field

from travel_companion.core.config import get_settings
from travel_companion.utils.circuit_breaker import CircuitBreaker
from travel_companion.utils.errors import ExternalAPIError


class LiteAPIStay(BaseModel):
    """Stay information for liteAPI requests."""

    check_in: str = Field(..., description="Check-in date (YYYY-MM-DD)")
    check_out: str = Field(..., description="Check-out date (YYYY-MM-DD)")


class LiteAPIOccupancy(BaseModel):
    """Room occupancy information for liteAPI requests."""

    rooms: int = Field(default=1, ge=1, le=10, description="Number of rooms")
    adults: int = Field(..., ge=1, le=20, description="Number of adults")
    children: int = Field(default=0, ge=0, le=10, description="Number of children")


class LiteAPIHotelSearchRequest(BaseModel):
    """Hotel search request for liteAPI geo-based search."""

    latitude: float = Field(..., ge=-90, le=90, description="Search center latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Search center longitude")
    radius: int = Field(default=5000, ge=100, le=50000, description="Search radius in meters")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum number of hotels to return")


class LiteAPIRatesRequest(BaseModel):
    """Hotel rates request for liteAPI."""

    stay: LiteAPIStay = Field(..., description="Stay information")
    occupancies: list[LiteAPIOccupancy] = Field(..., min_length=1, description="Room occupancies")
    hotel_ids: list[str] = Field(..., min_length=1, description="LiteAPI hotel IDs")
    currency: str = Field(default="USD", description="Currency code")


class LiteAPIMinRatesRequest(BaseModel):
    """Hotel minimum rates request for liteAPI."""

    stay: LiteAPIStay = Field(..., description="Stay information")
    occupancies: list[LiteAPIOccupancy] = Field(..., min_length=1, description="Room occupancies")
    hotel_ids: list[str] = Field(..., min_length=1, description="LiteAPI hotel IDs")


class LiteAPIClient:
    """Client for interacting with LiteAPI (Nuitée) for hotel bookings."""

    BASE_URL = "https://api.liteapi.travel/v3.0"
    SEARCH_ENDPOINT = f"{BASE_URL}/hotels"
    MIN_RATES_ENDPOINT = f"{BASE_URL}/hotels/min-rates"
    RATES_ENDPOINT = f"{BASE_URL}/hotels/rates"

    def __init__(self, timeout: float = 30.0) -> None:
        """Initialize LiteAPI client with API credentials."""
        settings = get_settings()
        self.api_key = settings.liteapi_key
        if not self.api_key:
            raise ValueError("LITEAPI_KEY not configured")

        self.client = httpx.AsyncClient(timeout=timeout)
        self.logger = logging.getLogger(__name__)
        self._request_count = 0
        self._rate_limit = 1000  # Adjust based on your plan
        self._last_reset = datetime.now()

        # Initialize circuit breakers for different API endpoints
        self._search_circuit = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=(ExternalAPIError, httpx.HTTPError, httpx.TimeoutException),
            name="liteapi_search",
        )
        self._rates_circuit = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=120,  # Longer recovery for rates endpoint
            expected_exception=(ExternalAPIError, httpx.HTTPError, httpx.TimeoutException),
            name="liteapi_rates",
        )

    async def __aenter__(self) -> "LiteAPIClient":
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
            raise ExternalAPIError(f"LiteAPI rate limit exceeded ({self._rate_limit} requests/day)")

    def _get_headers(self) -> dict[str, str]:
        """Get headers for LiteAPI requests."""
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

    async def search_hotels_by_geo(
        self, request: LiteAPIHotelSearchRequest
    ) -> list[dict[str, Any]]:
        """
        Search for hotels by geographic location using LiteAPI.

        Args:
            request: Geographic search request parameters

        Returns:
            List of hotel dictionaries with liteAPI hotel IDs

        Raises:
            ExternalAPIError: If API request fails
        """
        return cast(
            list[dict[str, Any]],
            await self._search_circuit.call(self._search_hotels_by_geo_impl, request),
        )

    async def _search_hotels_by_geo_impl(
        self, request: LiteAPIHotelSearchRequest
    ) -> list[dict[str, Any]]:
        """Implementation of geo search with circuit breaker protection."""
        try:
            # Check rate limit
            self._check_rate_limit()

            # Build query parameters
            params = {
                "latitude": request.latitude,
                "longitude": request.longitude,
                "radius": request.radius,
                "limit": request.limit,
            }

            # Make API request
            start_time = datetime.now()
            response = await self.client.get(
                self.SEARCH_ENDPOINT,
                params=params,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            self._request_count += 1

            # Parse response
            data = response.json()
            search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Transform response
            hotels = cast(list[dict[str, Any]], data.get("data", []))

            self.logger.info(
                f"Found {len(hotels)} hotels via LiteAPI geo search in {search_time_ms}ms"
            )
            return hotels

        except httpx.HTTPStatusError as e:
            self.logger.error(f"LiteAPI search HTTP error: {e.response.status_code}")
            raise ExternalAPIError(f"LiteAPI search error: {e.response.text}") from e
        except httpx.TimeoutException:
            self.logger.error("LiteAPI search request timeout")
            raise ExternalAPIError("LiteAPI search timeout") from None
        except Exception as e:
            self.logger.error(f"Unexpected error in LiteAPI search: {str(e)}")
            raise ExternalAPIError(f"Failed to search hotels: {str(e)}") from e

    async def get_min_rates(self, request: LiteAPIMinRatesRequest) -> dict[str, Any]:
        """
        Get minimum rates for hotels using LiteAPI.

        Args:
            request: Minimum rates request parameters

        Returns:
            Dictionary with hotel rates data

        Raises:
            ExternalAPIError: If API request fails
        """
        return cast(
            dict[str, Any],
            await self._rates_circuit.call(self._get_min_rates_impl, request),
        )

    async def _get_min_rates_impl(self, request: LiteAPIMinRatesRequest) -> dict[str, Any]:
        """Implementation of min rates with circuit breaker protection."""
        try:
            # Check rate limit
            self._check_rate_limit()

            # Convert request to dict for JSON serialization
            request_data = request.model_dump()

            # Make API request
            start_time = datetime.now()
            response = await self.client.post(
                self.MIN_RATES_ENDPOINT,
                json=request_data,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            self._request_count += 1

            # Parse response
            data = response.json()
            search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            self.logger.info(
                f"Retrieved min rates for {len(request.hotel_ids)} hotels in {search_time_ms}ms"
            )
            return cast(dict[str, Any], data)

        except httpx.HTTPStatusError as e:
            self.logger.error(f"LiteAPI min rates HTTP error: {e.response.status_code}")
            raise ExternalAPIError(f"LiteAPI min rates error: {e.response.text}") from e
        except httpx.TimeoutException:
            self.logger.error("LiteAPI min rates request timeout")
            raise ExternalAPIError("LiteAPI min rates timeout") from None
        except Exception as e:
            self.logger.error(f"Unexpected error in LiteAPI min rates: {str(e)}")
            raise ExternalAPIError(f"Failed to get min rates: {str(e)}") from e

    async def get_full_rates(self, request: LiteAPIRatesRequest) -> dict[str, Any]:
        """
        Get full rates and availability for hotels using LiteAPI.

        Args:
            request: Full rates request parameters

        Returns:
            Dictionary with detailed hotel rates and availability

        Raises:
            ExternalAPIError: If API request fails
        """
        return cast(
            dict[str, Any],
            await self._rates_circuit.call(self._get_full_rates_impl, request),
        )

    async def _get_full_rates_impl(self, request: LiteAPIRatesRequest) -> dict[str, Any]:
        """Implementation of full rates with circuit breaker protection."""
        try:
            # Check rate limit
            self._check_rate_limit()

            # Convert request to dict for JSON serialization
            request_data = request.model_dump()

            # Make API request
            start_time = datetime.now()
            response = await self.client.post(
                self.RATES_ENDPOINT,
                json=request_data,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            self._request_count += 1

            # Parse response
            data = response.json()
            search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            self.logger.info(
                f"Retrieved full rates for {len(request.hotel_ids)} hotels in {search_time_ms}ms"
            )
            return cast(dict[str, Any], data)

        except httpx.HTTPStatusError as e:
            self.logger.error(f"LiteAPI full rates HTTP error: {e.response.status_code}")
            raise ExternalAPIError(f"LiteAPI full rates error: {e.response.text}") from e
        except httpx.TimeoutException:
            self.logger.error("LiteAPI full rates request timeout")
            raise ExternalAPIError("LiteAPI full rates timeout") from None
        except Exception as e:
            self.logger.error(f"Unexpected error in LiteAPI full rates: {str(e)}")
            raise ExternalAPIError(f"Failed to get full rates: {str(e)}") from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

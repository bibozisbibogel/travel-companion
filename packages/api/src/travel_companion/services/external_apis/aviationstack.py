"""
AviationStack API client for flight data integration.

Handles API key authentication, rate limiting, and flight search operations.
"""

import asyncio
import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field

from travel_companion.core.config import get_settings
from travel_companion.utils.errors import ExternalAPIError, RateLimitError

logger = logging.getLogger(__name__)


class AviationStackFlight(BaseModel):
    """AviationStack flight data model."""

    flight_date: str
    flight_status: str
    departure: dict[str, Any]
    arrival: dict[str, Any]
    airline: dict[str, Any]
    flight: dict[str, Any]
    aircraft: dict[str, Any] | None = None
    live: dict[str, Any] | None = None


class FlightSearchParams(BaseModel):
    """Flight search parameters for AviationStack API."""

    origin: str = Field(..., description="Origin airport code", min_length=3, max_length=3)
    destination: str = Field(
        ..., description="Destination airport code", min_length=3, max_length=3
    )
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    return_date: str | None = Field(None, description="Return date (YYYY-MM-DD)")
    adults: int = Field(1, ge=1, le=9, description="Number of adult passengers")
    children: int = Field(0, ge=0, le=9, description="Number of child passengers")
    infants: int = Field(0, ge=0, le=9, description="Number of infant passengers")
    max_results: int = Field(100, ge=1, le=250, description="Maximum number of results")
    currency: str = Field("USD", description="Currency code")


class AviationStackRoute(BaseModel):
    """AviationStack route response model."""

    airline_name: str
    airline_iata: str
    airline_icao: str
    departure_airport: str
    departure_iata: str
    departure_icao: str
    arrival_airport: str
    arrival_iata: str
    arrival_icao: str


class AviationStackClient:
    """
    AviationStack API client with API key authentication.

    Handles flight search operations with proper rate limiting and error handling.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "http://api.aviationstack.com/v1",
        timeout: float = 30.0,
        max_retries: int = 3,
        rate_limit_per_second: int = 10,
    ):
        """
        Initialize AviationStack API client.

        Args:
            api_key: AviationStack API key
            base_url: Base URL for AviationStack API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            rate_limit_per_second: Maximum requests per second
        """
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.aviationstack_api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_per_second = rate_limit_per_second

        # Rate limiting
        self._rate_limit_semaphore = asyncio.Semaphore(rate_limit_per_second)
        self._last_request_time = 0.0

        # HTTP client
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AviationStackClient":
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object
    ) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
            )

    async def _rate_limit(self) -> None:
        """Implement rate limiting."""
        async with self._rate_limit_semaphore:
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self._last_request_time
            min_interval = 1.0 / self.rate_limit_per_second

            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)

            self._last_request_time = asyncio.get_event_loop().time()

    def _get_auth_params(self) -> dict[str, str]:
        """
        Get authentication parameters for AviationStack API.

        Returns:
            Dictionary with API key parameter

        Raises:
            ExternalAPIError: If API key is not configured
        """
        if not self.api_key:
            raise ExternalAPIError("AviationStack API key not configured")

        return {"access_key": self.api_key}

    async def _make_authenticated_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> dict[str, Any]:
        """
        Make authenticated request to AviationStack API with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            json: JSON body
            max_retries: Maximum retry attempts (overrides default)

        Returns:
            Response JSON data

        Raises:
            RateLimitError: If rate limit is exceeded
            ExternalAPIError: If request fails
        """
        await self._ensure_client()
        max_retries = max_retries or self.max_retries

        # Ensure client is available
        assert self._client is not None

        # Add API key to parameters
        if params is None:
            params = {}
        params.update(self._get_auth_params())

        for attempt in range(max_retries + 1):
            try:
                await self._rate_limit()

                response = await self._client.request(
                    method=method,
                    url=f"{self.base_url}/{endpoint.lstrip('/')}",
                    params=params,
                    json=json,
                )

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limit exceeded, retrying after {retry_after}s")

                    if attempt == max_retries:
                        raise RateLimitError(f"Rate limit exceeded after {max_retries} retries")

                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                json_response: dict[str, Any] = response.json()
                return json_response

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"AviationStack API request failed: {e.response.status_code} {e.response.text}"
                )

                if attempt == max_retries:
                    raise ExternalAPIError(f"API request failed: {e.response.status_code}") from e

                # Exponential backoff
                await asyncio.sleep(2**attempt)

            except Exception as e:
                logger.error(f"AviationStack API request error: {str(e)}")

                if attempt == max_retries:
                    raise ExternalAPIError(f"API request error: {str(e)}") from e

                await asyncio.sleep(2**attempt)

        raise ExternalAPIError("Maximum retry attempts exceeded")

    async def search_flights(self, search_params: FlightSearchParams) -> list[AviationStackFlight]:
        """
        Search for flights using AviationStack real-time flights API.

        Args:
            search_params: Flight search parameters

        Returns:
            List of flights

        Raises:
            ExternalAPIError: If search fails
        """
        logger.info(f"Searching flights from {search_params.origin} to {search_params.destination}")

        # Convert search parameters to API format
        params = {
            "dep_iata": search_params.origin.upper(),
            "arr_iata": search_params.destination.upper(),
            "flight_date": search_params.departure_date,
            "limit": min(search_params.max_results, 100),  # AviationStack API limit
        }

        try:
            response_data = await self._make_authenticated_request(
                method="GET",
                endpoint="/flights",
                params=params,
            )

            flights = []
            for flight_data in response_data.get("data", []):
                flights.append(AviationStackFlight(**flight_data))

            logger.info(f"Found {len(flights)} flights")
            return flights

        except Exception as e:
            logger.error(f"Flight search failed: {str(e)}")
            raise ExternalAPIError(f"Flight search failed: {str(e)}") from e

    async def get_routes(self, origin: str, destination: str) -> list[AviationStackRoute]:
        """
        Get flight routes between airports using AviationStack routes API.

        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code

        Returns:
            List of routes

        Raises:
            ExternalAPIError: If request fails
        """
        logger.info(f"Getting routes from {origin} to {destination}")

        params = {
            "dep_iata": origin.upper(),
            "arr_iata": destination.upper(),
        }

        try:
            response_data = await self._make_authenticated_request(
                method="GET",
                endpoint="/routes",
                params=params,
            )

            routes = []
            for route_data in response_data.get("data", []):
                routes.append(AviationStackRoute(**route_data))

            logger.info(f"Found {len(routes)} routes")
            return routes

        except Exception as e:
            logger.error(f"Route search failed: {str(e)}")
            raise ExternalAPIError(f"Route search failed: {str(e)}") from e

    async def get_airport_info(self, location_code: str) -> dict[str, Any]:
        """
        Get airport information by IATA code using AviationStack airports API.

        Args:
            location_code: Airport IATA code

        Returns:
            Airport information

        Raises:
            ExternalAPIError: If request fails
        """
        params = {"iata_code": location_code.upper()}

        try:
            response_data = await self._make_authenticated_request(
                method="GET",
                endpoint="/airports",
                params=params,
            )

            airports = response_data.get("data", [])
            if not airports:
                raise ExternalAPIError(f"Airport not found: {location_code}")

            airport_info: dict[str, Any] = airports[0]
            return airport_info

        except Exception as e:
            logger.error(f"Airport info request failed: {str(e)}")
            raise ExternalAPIError(f"Airport info request failed: {str(e)}") from e

    async def health_check(self) -> bool:
        """
        Perform health check by testing API access.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Test API access with a simple airports request
            await self._make_authenticated_request(
                method="GET",
                endpoint="/airports",
                params={"limit": 1},
            )
            return True
        except Exception as e:
            logger.error(f"AviationStack API health check failed: {str(e)}")
            return False

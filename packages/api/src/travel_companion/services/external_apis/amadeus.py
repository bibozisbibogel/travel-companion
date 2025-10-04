"""
Amadeus API client for flight data integration.

Handles OAuth 2.0 authentication, rate limiting, and flight search operations.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from pydantic import BaseModel, Field

from travel_companion.core.config import get_settings
from travel_companion.utils.errors import ExternalAPIError, RateLimitError

logger = logging.getLogger(__name__)


class AmadeusAuthToken(BaseModel):
    """Amadeus OAuth 2.0 token model."""

    access_token: str
    token_type: str
    expires_in: int
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        """Set expiration time after initialization."""
        if self.expires_at is None:
            self.expires_at = datetime.now(UTC) + timedelta(seconds=self.expires_in - 60)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return self.expires_at is not None and datetime.now(UTC) >= self.expires_at


class FlightSearchParams(BaseModel):
    """Flight search parameters for Amadeus API."""

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


class AmadeusFlightOffer(BaseModel):
    """Flight offer response model from Amadeus API."""

    id: str
    source: str
    instant_ticketing_required: bool = False
    non_homogeneous: bool = False
    one_way: bool = True
    last_ticketing_date: str | None = None
    price: dict[str, Any]
    itineraries: list[dict[str, Any]]
    pricing_options: dict[str, Any] = {}
    validating_airline_codes: list[str] = []
    traveler_pricings: list[dict[str, Any]] = []


class AmadeusClient:
    """
    Amadeus Travel API client with OAuth 2.0 authentication.

    Handles flight search operations with proper rate limiting and error handling.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        rate_limit_per_second: int = 10,
    ):
        """
        Initialize Amadeus API client.

        Args:
            client_id: Amadeus API client ID
            client_secret: Amadeus API client secret
            base_url: Base URL for Amadeus API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            rate_limit_per_second: Maximum requests per second
        """
        settings = get_settings()
        self.client_id = client_id or settings.amadeus_api_key
        self.client_secret = client_secret or settings.amadeus_api_secret
        self.base_url = (base_url or settings.amadeus_base_url).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_per_second = rate_limit_per_second

        # Rate limiting
        self._rate_limit_semaphore = asyncio.Semaphore(rate_limit_per_second)
        self._last_request_time = 0.0

        # Authentication
        self._auth_token: AmadeusAuthToken | None = None
        self._auth_lock = asyncio.Lock()

        # HTTP client
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AmadeusClient":
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

    async def _get_access_token(self) -> str:
        """
        Authenticate with Amadeus API using OAuth 2.0 client credentials flow.

        Returns:
            Access token string

        Raises:
            ExternalAPIError: If authentication fails
        """
        async with self._auth_lock:
            if self._auth_token and not self._auth_token.is_expired:
                return self._auth_token.access_token

            await self._ensure_client()
            await self._rate_limit()

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            # Ensure client is available after _ensure_client call
            assert self._client is not None

            try:
                response = await self._client.post(
                    f"{self.base_url}/v1/security/oauth2/token",
                    headers=headers,
                    data=data,
                )
                response.raise_for_status()

                token_data = response.json()
                self._auth_token = AmadeusAuthToken(**token_data)
                self._auth_token.__post_init__()

                logger.info("Successfully authenticated with Amadeus API")
                return self._auth_token.access_token

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Amadeus authentication failed: {e.response.status_code} {e.response.text}"
                )
                raise ExternalAPIError(f"Authentication failed: {e.response.status_code}") from e
            except Exception as e:
                logger.error(f"Amadeus authentication error: {str(e)}")
                raise ExternalAPIError(f"Authentication error: {str(e)}") from e

    async def _make_authenticated_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> dict[str, Any]:
        """
        Make authenticated request to Amadeus API with retry logic.

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

        for attempt in range(max_retries + 1):
            try:
                await self._rate_limit()

                # Only use OAuth authentication for non-test URLs
                headers = {}
                if self.base_url == "https://test.api.amadeus.com":
                    access_token = await self._get_access_token()
                    headers = {"Authorization": f"Bearer {access_token}"}

                response = await self._client.request(
                    method=method,
                    url=f"{self.base_url}/{endpoint.lstrip('/')}",
                    headers=headers,
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
                if e.response.status_code == 401:
                    # Token expired, force re-authentication
                    self._auth_token = None
                    if attempt < max_retries:
                        logger.info("Access token expired, re-authenticating")
                        continue

                logger.error(
                    f"Amadeus API request failed: {e.response.status_code} {e.response.text}"
                )

                if attempt == max_retries:
                    raise ExternalAPIError(f"API request failed: {e.response.status_code}") from e

                # Exponential backoff
                await asyncio.sleep(2**attempt)

            except Exception as e:
                logger.error(f"Amadeus API request error: {str(e)}")

                if attempt == max_retries:
                    raise ExternalAPIError(f"API request error: {str(e)}") from e

                await asyncio.sleep(2**attempt)

        raise ExternalAPIError("Maximum retry attempts exceeded")

    async def search_flights(self, search_params: FlightSearchParams) -> list[AmadeusFlightOffer]:
        """
        Search for flight offers using Amadeus Flight Offers Search API.

        Args:
            search_params: Flight search parameters

        Returns:
            List of flight offers

        Raises:
            ExternalAPIError: If search fails
        """
        logger.info(f"Searching flights from {search_params.origin} to {search_params.destination}")

        # Convert search parameters to API format
        params = {
            "originLocationCode": search_params.origin.upper(),
            "destinationLocationCode": search_params.destination.upper(),
            "departureDate": search_params.departure_date,
            "adults": search_params.adults,
            "max": search_params.max_results,
            "currencyCode": search_params.currency,
        }

        if search_params.return_date:
            params["returnDate"] = search_params.return_date

        if search_params.children > 0:
            params["children"] = search_params.children

        if search_params.infants > 0:
            params["infants"] = search_params.infants

        try:
            response_data = await self._make_authenticated_request(
                method="GET",
                endpoint="/v2/shopping/flight-offers",
                params=params,
            )

            flight_offers = []
            for offer_data in response_data.get("data", []):
                flight_offers.append(AmadeusFlightOffer(**offer_data))

            logger.info(f"Found {len(flight_offers)} flight offers")
            return flight_offers

        except Exception as e:
            logger.error(f"Flight search failed: {str(e)}")
            raise ExternalAPIError(f"Flight search failed: {str(e)}") from e

    async def get_airport_info(self, location_code: str) -> dict[str, Any]:
        """
        Get airport information by IATA code.

        Args:
            location_code: Airport IATA code

        Returns:
            Airport information

        Raises:
            ExternalAPIError: If request fails
        """
        params = {"keyword": location_code.upper(), "subType": "AIRPORT"}

        try:
            response_data = await self._make_authenticated_request(
                method="GET",
                endpoint="/v1/reference-data/locations",
                params=params,
            )

            locations = response_data.get("data", [])
            if not locations:
                raise ExternalAPIError(f"Airport not found: {location_code}")

            location_info: dict[str, Any] = locations[0]
            return location_info

        except Exception as e:
            logger.error(f"Airport info request failed: {str(e)}")
            raise ExternalAPIError(f"Airport info request failed: {str(e)}") from e

    async def health_check(self) -> bool:
        """
        Perform health check by testing authentication.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            await self._get_access_token()
            return True
        except Exception as e:
            logger.error(f"Amadeus API health check failed: {str(e)}")
            return False

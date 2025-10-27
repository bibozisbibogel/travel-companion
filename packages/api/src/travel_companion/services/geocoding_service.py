"""Geocoding service for converting location strings to coordinates."""

import asyncio
import hashlib
import logging
from functools import lru_cache
from typing import Literal

import googlemaps  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, field_validator

from travel_companion.core.config import get_settings

logger = logging.getLogger(__name__)


class GeocodeResult(BaseModel):
    """Result of a geocoding operation."""

    status: Literal["success", "failed", "pending"] = Field(
        description="Status of the geocoding operation"
    )
    latitude: float | None = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: float | None = Field(None, ge=-180, le=180, description="Longitude coordinate")
    formatted_address: str | None = Field(None, description="Formatted address from geocoding API")
    error_message: str | None = Field(None, description="Error message if geocoding failed")

    @field_validator("latitude", "longitude")
    @classmethod
    def validate_coordinates(cls, v: float | None) -> float | None:
        """Validate coordinate ranges."""
        if v is None:
            return v
        return round(v, 8)  # Round to 8 decimal places for precision


class GeocodingService:
    """Service for geocoding location strings to lat/lng coordinates."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize geocoding service.

        Args:
            api_key: Google Maps Platform API key. If None, loads from settings.

        Raises:
            ValueError: If API key is not provided and not in settings
        """
        settings = get_settings()
        self.api_key = api_key or settings.google_places_api_key

        if not self.api_key:
            raise ValueError(
                "Google Maps Platform API key not provided. "
                "Set GOOGLE_PLACES_API_KEY environment variable."
            )

        # Initialize Google Maps client with timeout
        self.client = googlemaps.Client(
            key=self.api_key, timeout=settings.geocoding_timeout_seconds
        )

        # Configuration from settings
        self.max_retries = settings.geocoding_retry_attempts
        self.timeout = settings.geocoding_timeout_seconds
        self.rate_limit = settings.geocoding_rate_limit_per_second

        # In-memory cache for geocoded locations (LRU cache)
        self._cache: dict[str, GeocodeResult] = {}
        self._cache_size = 1000

        logger.info(
            "GeocodingService initialized",
            extra={
                "max_retries": self.max_retries,
                "timeout": self.timeout,
                "rate_limit": self.rate_limit,
            },
        )

    def _normalize_address(self, address: str) -> str:
        """
        Normalize address for consistent caching.

        Args:
            address: Raw address string

        Returns:
            Normalized address string (lowercase, stripped)
        """
        return address.strip().lower()

    def _get_cache_key(self, address: str) -> str:
        """
        Generate cache key for an address.

        Args:
            address: Normalized address string

        Returns:
            SHA256 hash of the address
        """
        return hashlib.sha256(address.encode()).hexdigest()

    def _get_from_cache(self, address: str) -> GeocodeResult | None:
        """
        Retrieve geocoding result from cache.

        Args:
            address: Normalized address string

        Returns:
            Cached GeocodeResult or None if not found
        """
        cache_key = self._get_cache_key(address)
        cached_result = self._cache.get(cache_key)

        if cached_result:
            logger.debug(
                "Geocoding cache hit",
                extra={"address": address[:50], "cache_key": cache_key[:16]},
            )
            return cached_result

        logger.debug(
            "Geocoding cache miss", extra={"address": address[:50], "cache_key": cache_key[:16]}
        )
        return None

    def _add_to_cache(self, address: str, result: GeocodeResult) -> None:
        """
        Add geocoding result to cache.

        Args:
            address: Normalized address string
            result: GeocodeResult to cache
        """
        cache_key = self._get_cache_key(address)

        # Simple LRU eviction: remove oldest entry if cache is full
        if len(self._cache) >= self._cache_size:
            # Remove first (oldest) entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug("Evicted oldest cache entry", extra={"cache_key": oldest_key[:16]})

        self._cache[cache_key] = result
        logger.debug("Added to geocoding cache", extra={"cache_key": cache_key[:16]})

    async def geocode_location(self, address: str, retry_count: int = 0) -> GeocodeResult:
        """
        Geocode a location string to latitude/longitude coordinates.

        Implements retry logic with exponential backoff for transient failures.

        Args:
            address: Location string to geocode (e.g., "Trevi Fountain, Rome, Italy")
            retry_count: Current retry attempt (internal use)

        Returns:
            GeocodeResult with status, coordinates, and error information

        Example:
            >>> service = GeocodingService(api_key="your-api-key")
            >>> result = await service.geocode_location("Eiffel Tower, Paris")
            >>> print(result.latitude, result.longitude)
            48.8583701 2.2944813
        """
        # Normalize address for caching
        normalized_address = self._normalize_address(address)

        # Check cache first
        cached_result = self._get_from_cache(normalized_address)
        if cached_result:
            return cached_result

        try:
            # Execute geocoding in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            geocode_result = await loop.run_in_executor(
                None,
                lambda: self.client.geocode(address=address),
            )

            # Handle API response
            if not geocode_result:
                # ZERO_RESULTS - no results found
                result = GeocodeResult(
                    status="failed",
                    latitude=None,
                    longitude=None,
                    formatted_address=None,
                    error_message=f"No geocoding results found for address: {address[:100]}",
                )
                logger.warning(
                    "Geocoding returned zero results",
                    extra={"address": address[:100], "retry_count": retry_count},
                )
                self._add_to_cache(normalized_address, result)
                return result

            # Extract coordinates from first result
            first_result = geocode_result[0]
            geometry = first_result.get("geometry", {})
            location = geometry.get("location", {})

            latitude = location.get("lat")
            longitude = location.get("lng")
            formatted_address = first_result.get("formatted_address")

            # Validate coordinates
            if latitude is None or longitude is None:
                result = GeocodeResult(
                    status="failed",
                    latitude=None,
                    longitude=None,
                    formatted_address=None,
                    error_message=f"Invalid coordinates in geocoding response: {address[:100]}",
                )
                logger.error(
                    "Invalid coordinates in geocoding response",
                    extra={
                        "address": address[:100],
                        "response": str(first_result)[:200],
                    },
                )
                self._add_to_cache(normalized_address, result)
                return result

            # Success!
            result = GeocodeResult(
                status="success",
                latitude=latitude,
                longitude=longitude,
                formatted_address=formatted_address,
                error_message=None,
            )

            logger.info(
                "Geocoding successful",
                extra={
                    "address": address[:100],
                    "latitude": latitude,
                    "longitude": longitude,
                    "formatted_address": formatted_address[:100] if formatted_address else None,
                },
            )

            # Cache successful result
            self._add_to_cache(normalized_address, result)
            return result

        except googlemaps.exceptions.ApiError as e:
            # API errors (REQUEST_DENIED, INVALID_REQUEST, etc.)
            error_message = str(e)
            logger.error(
                "Google Geocoding API error",
                extra={
                    "address": address[:100],
                    "error": error_message,
                    "retry_count": retry_count,
                },
            )

            # Check if this is a transient error that should be retried
            if "OVER_QUERY_LIMIT" in error_message and retry_count < self.max_retries:
                # Exponential backoff: 1s, 2s, 4s
                backoff_seconds = 2**retry_count
                logger.warning(
                    "Rate limit exceeded, retrying with backoff",
                    extra={"backoff_seconds": backoff_seconds, "retry_count": retry_count},
                )
                await asyncio.sleep(backoff_seconds)
                return await self.geocode_location(address, retry_count + 1)

            # Permanent error or max retries reached
            result = GeocodeResult(
                status="failed",
                latitude=None,
                longitude=None,
                formatted_address=None,
                error_message=error_message,
            )
            self._add_to_cache(normalized_address, result)
            return result

        except googlemaps.exceptions.Timeout:
            # Timeout error
            logger.warning(
                "Geocoding request timeout",
                extra={
                    "address": address[:100],
                    "timeout": self.timeout,
                    "retry_count": retry_count,
                },
            )

            # Retry once on timeout
            if retry_count < 1:
                await asyncio.sleep(1)
                return await self.geocode_location(address, retry_count + 1)

            result = GeocodeResult(
                status="failed",
                latitude=None,
                longitude=None,
                formatted_address=None,
                error_message=f"Geocoding request timed out after {self.timeout}s",
            )
            self._add_to_cache(normalized_address, result)
            return result

        except Exception as e:
            # Unexpected errors
            error_message = f"Unexpected geocoding error: {type(e).__name__}: {str(e)}"
            logger.exception(
                "Unexpected geocoding error",
                extra={"address": address[:100], "retry_count": retry_count},
            )

            result = GeocodeResult(
                status="failed",
                latitude=None,
                longitude=None,
                formatted_address=None,
                error_message=error_message,
            )
            # Don't cache unexpected errors (might be transient)
            return result

    async def geocode_locations_batch(
        self, addresses: list[str], max_concurrent: int = 10
    ) -> list[GeocodeResult]:
        """
        Geocode multiple locations concurrently.

        Args:
            addresses: List of location strings to geocode
            max_concurrent: Maximum number of concurrent requests (default: 10)

        Returns:
            List of GeocodeResults in the same order as input addresses

        Example:
            >>> service = GeocodingService(api_key="your-api-key")
            >>> addresses = ["Eiffel Tower, Paris", "Big Ben, London", "Colosseum, Rome"]
            >>> results = await service.geocode_locations_batch(addresses)
            >>> for addr, result in zip(addresses, results):
            ...     print(f"{addr}: {result.status}")
        """
        # Create tasks for all addresses
        tasks = [self.geocode_location(address) for address in addresses]

        # Execute with concurrency limit
        results = []
        for i in range(0, len(tasks), max_concurrent):
            batch = tasks[i : i + max_concurrent]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)

            # Handle any exceptions in the batch
            for idx, result in enumerate(batch_results):
                if isinstance(result, BaseException):
                    logger.error(
                        "Batch geocoding error",
                        extra={
                            "address": addresses[i + idx][:100],
                            "error": str(result),
                        },
                    )
                    results.append(
                        GeocodeResult(
                            status="failed",
                            latitude=None,
                            longitude=None,
                            formatted_address=None,
                            error_message=f"Batch processing error: {str(result)}",
                        )
                    )
                else:
                    results.append(result)

        logger.info(
            "Batch geocoding completed",
            extra={
                "total_addresses": len(addresses),
                "successful": sum(1 for r in results if r.status == "success"),
                "failed": sum(1 for r in results if r.status == "failed"),
            },
        )

        return results


@lru_cache
def get_geocoding_service() -> GeocodingService:
    """
    Get singleton geocoding service instance.

    Returns:
        Cached GeocodingService instance
    """
    return GeocodingService()

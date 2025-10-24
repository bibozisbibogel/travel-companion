"""Flight agent for searching and comparing flight options."""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from travel_companion.agents.base import BaseAgent
from travel_companion.models.external import (
    FlightComparisonResult,
    FlightOption,
    FlightSearchRequest,
    FlightSearchResponse,
)
from travel_companion.services.external_apis.amadeus import (
    AmadeusClient,
    AmadeusFlightOffer,
    FlightSearchParams,
)
from travel_companion.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from travel_companion.utils.errors import ExternalAPIError


class FlightAgent(BaseAgent[FlightSearchResponse]):
    """Agent responsible for flight search and comparison operations."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize FlightAgent with Amadeus client and circuit breaker."""
        super().__init__(**kwargs)
        self._amadeus_client: AmadeusClient | None = None

        # Circuit breaker for Amadeus API calls
        self._amadeus_circuit_breaker = CircuitBreaker(
            failure_threshold=3,  # Open after 3 failures
            recovery_timeout=30,  # Wait 30s before retry
            expected_exception=ExternalAPIError,
            name="AmadeusAPI",
        )

    @property
    def agent_name(self) -> str:
        """Name of the flight agent."""
        return "FlightAgent"

    @property
    def agent_version(self) -> str:
        """Version of the flight agent."""
        return "1.0.0"

    async def _get_amadeus_client(self) -> AmadeusClient:
        """Get or create Amadeus client."""
        if self._amadeus_client is None:
            self._amadeus_client = AmadeusClient()
        return self._amadeus_client

    async def process(self, request_data: dict[str, Any]) -> FlightSearchResponse:
        """Process flight search request.

        Args:
            request_data: Flight search parameters

        Returns:
            Flight search response with options
        """
        # Validate and parse request
        try:
            search_request = FlightSearchRequest(**request_data)
        except Exception as e:
            self.logger.error(f"Invalid flight search request: {e}")
            raise ValueError(f"Invalid flight search request: {e}") from e

        self.logger.info(
            f"Processing flight search: {search_request.origin} → {search_request.destination}"
        )

        # Generate cache key
        cache_key = await self._cache_key(request_data)

        # Check cache first
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            return FlightSearchResponse.model_validate(cached_result)

        # Start timing
        start_time = datetime.now()

        try:
            # Search for flights
            flights = await self.search_flights(search_request)

            # Compare and rank flights
            compared_flights = await self.compare_flights(flights)

            # Calculate search time
            search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Create response
            response = FlightSearchResponse(
                flights=[result.flight for result in compared_flights],
                search_metadata={
                    "search_request": search_request.model_dump(),
                    "ranking_applied": True,
                    "comparison_scores": [
                        {
                            "flight_id": str(result.flight.flight_id),
                            "score": result.score,
                            "price_rank": result.price_rank,
                            "duration_rank": result.duration_rank,
                        }
                        for result in compared_flights
                    ],
                },
                total_results=len(compared_flights),
                search_time_ms=search_time_ms,
                cached=False,
                cache_expires_at=datetime.now() + timedelta(minutes=5),
            )

            # Cache the result
            await self._set_cached_result(cache_key, response.model_dump(), expire_seconds=300)

            self.logger.info(
                f"Flight search completed: {len(compared_flights)} results in {search_time_ms}ms"
            )

            return response

        except Exception as e:
            self.logger.error(f"Flight search failed: {e}")
            # Return empty response on failure
            search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return FlightSearchResponse(
                flights=[],
                search_metadata={
                    "search_request": search_request.model_dump(),
                    "error": str(e),
                },
                total_results=0,
                search_time_ms=search_time_ms,
                cached=False,
                cache_expires_at=datetime.now() + timedelta(minutes=15),
            )

    async def search_flights(self, request: FlightSearchRequest) -> list[FlightOption]:
        """Search for flights using external API.

        Args:
            request: Flight search request parameters

        Returns:
            List of flight options
        """
        self.logger.debug(f"Searching flights for request: {request}")

        try:
            # Try to use Amadeus API first with circuit breaker and timeout
            flights = await self._search_flights_with_resilience(request)
            self.logger.debug(f"Found {len(flights)} flight options from Amadeus API")
            return flights

        except CircuitBreakerOpenError as e:
            self.logger.warning(f"Amadeus circuit breaker is open: {e}. Using mock data.")
            mock_flights = await self._get_mock_flight_data(request)
            return mock_flights
        except TimeoutError:
            self.logger.warning("Amadeus API timeout. Falling back to mock data.")
            mock_flights = await self._get_mock_flight_data(request)
            return mock_flights
        except ExternalAPIError as e:
            self.logger.warning(f"Amadeus API failed: {e}. Falling back to mock data.")
            mock_flights = await self._get_mock_flight_data(request)
            return mock_flights
        except Exception as e:
            self.logger.error(f"Unexpected error in flight search: {e}. Using mock data.")
            mock_flights = await self._get_mock_flight_data(request)
            return mock_flights

    async def compare_flights(self, flights: list[FlightOption]) -> list[FlightComparisonResult]:
        """Compare and rank flight options.

        Args:
            flights: List of flight options to compare

        Returns:
            List of comparison results sorted by score
        """
        if not flights:
            return []

        self.logger.debug(f"Comparing {len(flights)} flight options")

        # Sort flights for ranking
        sorted_by_price = sorted(flights, key=lambda f: f.price)
        sorted_by_duration = sorted(flights, key=lambda f: f.duration_minutes)

        comparison_results = []

        for flight in flights:
            # Calculate rankings
            price_rank = sorted_by_price.index(flight) + 1
            duration_rank = sorted_by_duration.index(flight) + 1

            # Calculate departure preference score (prefer morning/afternoon flights)
            departure_hour = flight.departure_time.hour
            if 6 <= departure_hour <= 10:  # Morning flights
                departure_preference_score = 1.0
            elif 11 <= departure_hour <= 17:  # Afternoon flights
                departure_preference_score = 0.8
            elif 18 <= departure_hour <= 22:  # Evening flights
                departure_preference_score = 0.6
            else:  # Late night/early morning
                departure_preference_score = 0.3

            # Calculate overall score (higher is better)
            price_score = max(0, 100 - (price_rank - 1) * 10)
            duration_score = max(0, 100 - (duration_rank - 1) * 10)
            departure_score = departure_preference_score * 100

            # Weighted average (price: 40%, duration: 30%, departure time: 20%, stops: 10%)
            overall_score = (
                price_score * 0.4
                + duration_score * 0.3
                + departure_score * 0.2
                + (100 - flight.stops * 20) * 0.1  # Fewer stops is better
            )

            # Generate reasons
            reasons = []
            if price_rank <= 3:
                reasons.append(f"Top {price_rank} cheapest option")
            if duration_rank <= 3:
                reasons.append(f"Top {duration_rank} fastest option")
            if flight.stops == 0:
                reasons.append("Direct flight")
            if departure_preference_score >= 0.8:
                reasons.append("Convenient departure time")

            comparison_results.append(
                FlightComparisonResult(
                    flight=flight,
                    score=min(100, max(0, overall_score)),
                    price_rank=price_rank,
                    duration_rank=duration_rank,
                    departure_preference_score=departure_preference_score,
                    reasons=reasons,
                )
            )

        # Sort by score (highest first)
        comparison_results.sort(key=lambda r: r.score, reverse=True)

        self.logger.debug(
            f"Flight comparison completed, best score: {comparison_results[0].score:.1f}"
        )

        return comparison_results

    async def _search_flights_with_resilience(
        self, request: FlightSearchRequest
    ) -> list[FlightOption]:
        """Search flights using Amadeus API with circuit breaker and timeout.

        Args:
            request: Flight search request parameters

        Returns:
            List of flight options from Amadeus API

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
            asyncio.TimeoutError: If request times out
            ExternalAPIError: If API request fails
        """

        async def _api_call() -> list[FlightOption]:
            amadeus_client = await self._get_amadeus_client()

            # Convert request to Amadeus format
            search_params = FlightSearchParams(
                origin=request.origin,
                destination=request.destination,
                departure_date=request.departure_date.strftime("%Y-%m-%d"),
                return_date=request.return_date.strftime("%Y-%m-%d")
                if request.return_date
                else None,
                adults=request.passengers,
                children=0,  # Default to 0 children
                infants=0,  # Default to 0 infants
                max_results=min(request.max_results, 100),
                currency=request.currency,
            )

            async with amadeus_client:
                amadeus_flights = await amadeus_client.search_flights(search_params)
                return self._convert_amadeus_flights_to_flights(amadeus_flights, request)

        # Use circuit breaker with 30-second timeout
        try:

            async def _wrapped_call() -> list[FlightOption]:
                return await asyncio.wait_for(_api_call(), timeout=30.0)

            result: list[FlightOption] = await self._amadeus_circuit_breaker.call(_wrapped_call)
            return result
        except TimeoutError:
            self.logger.warning("Flight search timed out after 30 seconds")
            raise
        except CircuitBreakerOpenError:
            self.logger.warning("Circuit breaker is open for Amadeus API")
            raise
        except Exception as e:
            self.logger.error(f"Flight search failed: {e}")
            if isinstance(e, ExternalAPIError):
                raise
            raise ExternalAPIError(f"Flight search failed: {str(e)}") from e

    def _convert_amadeus_flights_to_flights(
        self, amadeus_flights: list[AmadeusFlightOffer], request: FlightSearchRequest
    ) -> list[FlightOption]:
        """Convert Amadeus flight offers to FlightOption models.

        Args:
            amadeus_flights: List of Amadeus flight offers
            request: Original search request for context

        Returns:
            List of FlightOption models
        """
        flights = []

        for offer in amadeus_flights:
            try:
                # Get first itinerary (outbound flight)
                itinerary = offer.itineraries[0]
                segments = itinerary.get("segments", [])

                if not segments:
                    continue

                # Extract first and last segment for departure/arrival info
                first_segment = segments[0]
                last_segment = segments[-1]

                # Parse departure time
                departure_time = datetime.fromisoformat(
                    first_segment.get("departure", {}).get("at", "").replace("Z", "+00:00")
                )

                # Parse arrival time
                arrival_time = datetime.fromisoformat(
                    last_segment.get("arrival", {}).get("at", "").replace("Z", "+00:00")
                )

                # Calculate duration from ISO 8601 duration string (e.g., "PT6H15M")
                duration_str = itinerary.get("duration", "")
                duration_minutes = self._parse_iso8601_duration(duration_str)

                # Extract airline info
                carrier_code = first_segment.get("carrierCode", "Unknown")
                flight_number = f"{carrier_code}{first_segment.get('number', '')}"

                # Get price
                price = Decimal(str(offer.price.get("grandTotal", "0")))
                currency = offer.price.get("currency", request.currency)

                # Count stops (segments - 1)
                stops = len(segments) - 1

                flight = FlightOption(
                    flight_id=uuid4(),
                    trip_id=None,
                    external_id=f"amadeus_{offer.id}",
                    airline=carrier_code,
                    flight_number=flight_number,
                    origin=first_segment.get("departure", {}).get("iataCode", request.origin),
                    destination=last_segment.get("arrival", {}).get(
                        "iataCode", request.destination
                    ),
                    departure_time=departure_time,
                    arrival_time=arrival_time,
                    duration_minutes=duration_minutes,
                    stops=stops,
                    price=price,
                    currency=currency,
                    travel_class=request.travel_class,
                    flight_status="scheduled",
                    booking_url=None,
                )

                flights.append(flight)

            except Exception as e:
                self.logger.warning(f"Failed to convert Amadeus flight offer {offer.id}: {e}")
                continue

        return flights

    def _parse_iso8601_duration(self, duration: str) -> int:
        """Parse ISO 8601 duration string to minutes.

        Args:
            duration: ISO 8601 duration string (e.g., "PT6H15M")

        Returns:
            Duration in minutes
        """
        hours = 0
        minutes = 0

        if "H" in duration:
            hours = int(duration.split("T")[1].split("H")[0].replace("PT", ""))

        if "M" in duration:
            part = duration.split("H")[-1] if "H" in duration else duration.split("T")[1]
            minutes = int(part.split("M")[0].replace("PT", ""))

        return hours * 60 + minutes

    async def _get_mock_flight_data(self, request: FlightSearchRequest) -> list[FlightOption]:
        """Generate mock flight data for development/testing.

        Args:
            request: Flight search request

        Returns:
            List of mock flight options
        """
        import random
        from decimal import Decimal
        from uuid import uuid4

        mock_airlines = ["American Airlines", "Delta", "United", "Southwest", "JetBlue"]
        base_price = Decimal("300.00")

        flights = []

        for i in range(min(request.max_results, 20)):  # Generate up to 20 mock flights
            airline = random.choice(mock_airlines)
            flight_number = f"{airline[:2].upper()}{random.randint(100, 9999)}"

            # Random departure time within the day
            departure_time = request.departure_date.replace(
                hour=random.randint(6, 22),
                minute=random.choice([0, 15, 30, 45]),
                second=0,
                microsecond=0,
            )

            # Random flight duration (2-8 hours)
            duration_minutes = random.randint(120, 480)
            arrival_time = departure_time + timedelta(minutes=duration_minutes)

            # Random price variation
            price_multiplier = Decimal(str(random.uniform(0.8, 2.0)))
            price = (base_price * price_multiplier).quantize(Decimal("0.01"))

            # Random stops
            stops = random.choices([0, 1, 2], weights=[60, 30, 10])[0]

            flight = FlightOption(
                flight_id=uuid4(),
                trip_id=None,
                external_id=f"mock_{i}_{flight_number}",
                airline=airline,
                flight_number=flight_number,
                origin=request.origin,
                destination=request.destination,
                departure_time=departure_time,
                arrival_time=arrival_time,
                duration_minutes=duration_minutes,
                stops=stops,
                price=price,
                currency=request.currency,
                travel_class=request.travel_class,
                flight_status="scheduled",
                booking_url=None,
            )

            flights.append(flight)

        return flights

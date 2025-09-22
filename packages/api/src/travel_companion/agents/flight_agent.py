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
from travel_companion.services.external_apis.aviationstack import (
    AviationStackClient,
    AviationStackFlight,
    FlightSearchParams,
)
from travel_companion.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from travel_companion.utils.errors import ExternalAPIError


class FlightAgent(BaseAgent[FlightSearchResponse]):
    """Agent responsible for flight search and comparison operations."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize FlightAgent with AviationStack client and circuit breaker."""
        super().__init__(**kwargs)
        self._aviationstack_client: AviationStackClient | None = None

        # Circuit breaker for AviationStack API calls
        self._aviationstack_circuit_breaker = CircuitBreaker(
            failure_threshold=3,  # Open after 3 failures
            recovery_timeout=30,  # Wait 30s before retry
            expected_exception=ExternalAPIError,
            name="AviationStackAPI",
        )

    @property
    def agent_name(self) -> str:
        """Name of the flight agent."""
        return "FlightAgent"

    @property
    def agent_version(self) -> str:
        """Version of the flight agent."""
        return "1.0.0"

    async def _get_aviationstack_client(self) -> AviationStackClient:
        """Get or create AviationStack client."""
        if self._aviationstack_client is None:
            self._aviationstack_client = AviationStackClient()
        return self._aviationstack_client

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
            # Try to use AviationStack API first with circuit breaker and timeout
            flights = await self._search_flights_with_resilience(request)
            self.logger.debug(f"Found {len(flights)} flight options from AviationStack API")
            return flights

        except CircuitBreakerOpenError as e:
            self.logger.warning(f"AviationStack circuit breaker is open: {e}. Using mock data.")
            mock_flights = await self._get_mock_flight_data(request)
            return mock_flights
        except TimeoutError:
            self.logger.warning("AviationStack API timeout. Falling back to mock data.")
            mock_flights = await self._get_mock_flight_data(request)
            return mock_flights
        except ExternalAPIError as e:
            self.logger.warning(f"AviationStack API failed: {e}. Falling back to mock data.")
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
        """Search flights using AviationStack API with circuit breaker and timeout.

        Args:
            request: Flight search request parameters

        Returns:
            List of flight options from AviationStack API

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
            asyncio.TimeoutError: If request times out
            ExternalAPIError: If API request fails
        """

        async def _api_call() -> list[FlightOption]:
            aviationstack_client = await self._get_aviationstack_client()

            # Convert request to AviationStack format
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
                max_results=min(request.max_results, 100),  # AviationStack limit
                currency=request.currency,
            )

            async with aviationstack_client:
                aviationstack_flights = await aviationstack_client.search_flights(search_params)
                return self._convert_aviationstack_flights_to_flights(
                    aviationstack_flights, request
                )

        # Use circuit breaker with 30-second timeout
        try:

            async def _wrapped_call() -> list[FlightOption]:
                return await asyncio.wait_for(_api_call(), timeout=30.0)

            result: list[FlightOption] = await self._aviationstack_circuit_breaker.call(
                _wrapped_call
            )
            return result
        except TimeoutError:
            self.logger.warning("Flight search timed out after 30 seconds")
            raise
        except CircuitBreakerOpenError:
            self.logger.warning("Circuit breaker is open for AviationStack API")
            raise
        except Exception as e:
            self.logger.error(f"Flight search failed: {e}")
            if isinstance(e, ExternalAPIError):
                raise
            raise ExternalAPIError(f"Flight search failed: {str(e)}") from e

    def _convert_aviationstack_flights_to_flights(
        self, aviationstack_flights: list[AviationStackFlight], request: FlightSearchRequest
    ) -> list[FlightOption]:
        """Convert AviationStack flight data to FlightOption models.

        Args:
            aviationstack_flights: List of AviationStack flight data
            request: Original search request for context

        Returns:
            List of FlightOption models
        """
        flights = []

        for flight_data in aviationstack_flights:
            try:
                # Extract departure info
                departure_info = flight_data.departure
                departure_time = datetime.fromisoformat(
                    departure_info.get(
                        "scheduled",
                        departure_info.get("estimated", departure_info.get("actual", "")),
                    )
                )

                # Extract arrival info
                arrival_info = flight_data.arrival
                arrival_time = datetime.fromisoformat(
                    arrival_info.get(
                        "scheduled", arrival_info.get("estimated", arrival_info.get("actual", ""))
                    )
                )

                # Calculate duration
                duration_minutes = int((arrival_time - departure_time).total_seconds() / 60)

                # Extract airline info
                airline_name = flight_data.airline.get("name", "Unknown Airline")
                flight_number = flight_data.flight.get("number", "Unknown")

                # Generate a mock price since AviationStack doesn't provide pricing
                import random

                base_price = Decimal("400.00")
                price_multiplier = Decimal(str(random.uniform(0.7, 2.5)))
                price = (base_price * price_multiplier).quantize(Decimal("0.01"))

                # Assume direct flights for now (AviationStack doesn't provide segment info)
                stops = 0

                flight = FlightOption(
                    flight_id=uuid4(),
                    trip_id=None,
                    external_id=f"aviationstack_{flight_data.flight.get('iata', flight_number)}",
                    airline=airline_name,
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
                    flight_status=flight_data.flight_status,
                    booking_url=None,
                )

                flights.append(flight)

            except Exception as e:
                self.logger.warning(
                    f"Failed to convert AviationStack flight {flight_data.flight.get('number', 'unknown')}: {e}"
                )
                continue

        return flights

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

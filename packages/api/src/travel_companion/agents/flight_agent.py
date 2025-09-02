"""Flight agent for searching and comparing flight options."""

from datetime import datetime, timedelta
from typing import Any

from travel_companion.agents.base import BaseAgent
from travel_companion.models.external import (
    FlightComparisonResult,
    FlightOption,
    FlightSearchRequest,
    FlightSearchResponse,
)


class FlightAgent(BaseAgent[FlightSearchResponse]):
    """Agent responsible for flight search and comparison operations."""

    @property
    def agent_name(self) -> str:
        """Name of the flight agent."""
        return "FlightAgent"

    @property
    def agent_version(self) -> str:
        """Version of the flight agent."""
        return "1.0.0"

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
            return FlightSearchResponse(**cached_result)

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
            await self._set_cached_result(
                cache_key, response.model_dump(), expire_seconds=300
            )

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
            )

    async def search_flights(self, request: FlightSearchRequest) -> list[FlightOption]:
        """Search for flights using external API.

        Args:
            request: Flight search request parameters

        Returns:
            List of flight options
        """
        self.logger.debug(f"Searching flights for request: {request}")

        # For now, return mock data - will be replaced with actual API integration
        mock_flights = await self._get_mock_flight_data(request)

        self.logger.debug(f"Found {len(mock_flights)} flight options")
        return mock_flights

    async def compare_flights(
        self, flights: list[FlightOption]
    ) -> list[FlightComparisonResult]:
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
                price_score * 0.4 +
                duration_score * 0.3 +
                departure_score * 0.2 +
                (100 - flight.stops * 20) * 0.1  # Fewer stops is better
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

        self.logger.debug(f"Flight comparison completed, best score: {comparison_results[0].score:.1f}")

        return comparison_results

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
            price = (base_price * price_multiplier).quantize(Decimal('0.01'))

            # Random stops
            stops = random.choices([0, 1, 2], weights=[60, 30, 10])[0]

            flight = FlightOption(
                flight_id=uuid4(),
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
            )

            flights.append(flight)

        return flights


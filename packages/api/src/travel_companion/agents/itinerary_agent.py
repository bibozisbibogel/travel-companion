"""Itinerary agent for coordinating and integrating all travel components."""

import asyncio
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from travel_companion.agents.activity_agent import ActivityAgent
from travel_companion.agents.base import BaseAgent
from travel_companion.agents.flight_agent import FlightAgent
from travel_companion.agents.food_agent import FoodAgent
from travel_companion.agents.hotel_agent import HotelAgent
from travel_companion.agents.weather_agent import WeatherAgent
from travel_companion.models.external import (
    ActivityCategory,
    ActivityLocation,
    ActivityOption,
    ActivitySearchRequest,
    ActivitySearchResponse,
    FlightOption,
    FlightSearchRequest,
    FlightSearchResponse,
    GeoapifyCateringCategory,  # New Geoapify categories
    HotelLocation,
    HotelOption,
    HotelSearchRequest,
    HotelSearchResponse,
    RestaurantLocation,
    RestaurantOption,
    RestaurantSearchRequest,
    RestaurantSearchResponse,
    WeatherSearchRequest,
)
from travel_companion.models.trip import (
    DailyItinerary,
    ItineraryItem,
    TripItinerary,
    TripPlanRequest,
    TripSummary,
)
from travel_companion.utils.circuit_breaker import CircuitBreaker
from travel_companion.utils.errors import ExternalAPIError


class ItineraryAgentResponse(BaseModel):
    """Response model for itinerary agent processing."""

    trip_id: str
    itinerary: TripItinerary
    total_cost: Decimal
    currency: str
    budget_status: str
    conflicts: list[dict[str, Any]]
    optimization_score: float
    generated_at: datetime
    cached: bool = False


class ItineraryAgent(BaseAgent[ItineraryAgentResponse]):
    """Itinerary agent that coordinates all travel planning agents."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize itinerary agent with multi-agent coordination capabilities."""
        super().__init__(**kwargs)

        # Initialize all travel agents with same dependencies
        self.flight_agent = FlightAgent(
            settings=self.settings, database=self.database, redis=self.redis
        )
        self.hotel_agent = HotelAgent(
            settings=self.settings, database=self.database, redis=self.redis
        )
        self.activity_agent = ActivityAgent(
            settings=self.settings, database=self.database, redis=self.redis
        )
        self.weather_agent = WeatherAgent(
            settings=self.settings, database=self.database, redis=self.redis
        )
        self.food_agent = FoodAgent(
            settings=self.settings, database=self.database, redis=self.redis
        )

        # Circuit breakers for agent coordination
        self.flight_circuit = CircuitBreaker(
            name="flight_agent", failure_threshold=3, recovery_timeout=60
        )
        self.hotel_circuit = CircuitBreaker(
            name="hotel_agent", failure_threshold=3, recovery_timeout=60
        )
        self.activity_circuit = CircuitBreaker(
            name="activity_agent", failure_threshold=3, recovery_timeout=60
        )
        self.weather_circuit = CircuitBreaker(
            name="weather_agent", failure_threshold=3, recovery_timeout=60
        )
        self.food_circuit = CircuitBreaker(
            name="food_agent", failure_threshold=3, recovery_timeout=60
        )

        # Agent coordination configuration
        self.agent_timeout = 30  # seconds
        self.max_retries = 2
        self.cache_ttl = 1800  # 30 minutes

        self.logger.info("ItineraryAgent initialized with multi-agent coordination")

    @property
    def agent_name(self) -> str:
        """Name of the agent for logging and identification."""
        return "itinerary_agent"

    @property
    def agent_version(self) -> str:
        """Version of the agent for compatibility and debugging."""
        return "1.0.0"

    async def process(self, request_data: dict[str, Any]) -> ItineraryAgentResponse:
        """Process trip planning request with multi-agent coordination.

        Supports two modes:
        1. Standalone mode: Receives TripPlanRequest, coordinates all agents internally
        2. Workflow mode: Receives pre-fetched agent results from workflow state

        Args:
            request_data: Trip planning request data or workflow state with pre-fetched results

        Returns:
            Complete itinerary with all travel components integrated
        """
        try:
            # Check if this is workflow mode (pre-fetched data) or standalone mode
            has_prefetched_data = self._has_prefetched_agent_results(request_data)

            if has_prefetched_data:
                # Workflow mode - use pre-fetched data
                trip_request, agent_results = await self._extract_workflow_data(request_data)
                self.logger.info(
                    f"Processing itinerary for {trip_request.destination.city} "
                    f"(workflow mode with pre-fetched data)"
                )
            else:
                # Standalone mode - validate and parse request
                trip_request = TripPlanRequest(**request_data)
                self.logger.info(
                    f"Processing itinerary for {trip_request.destination.city} "
                    f"(standalone mode)"
                )

                # Generate cache key and check cache
                cache_key = await self._cache_key(request_data)
                cached_result = await self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result

                # Coordinate with all agents concurrently
                start_time = asyncio.get_event_loop().time()
                agent_results = await self._coordinate_agents(trip_request)

            # Common processing for both modes
            start_time = asyncio.get_event_loop().time()

            # Generate daily schedule and optimize
            daily_itinerary = await self._generate_daily_schedule(trip_request, agent_results)

            # Calculate total costs and validate budget allocation
            total_cost, currency = await self._calculate_total_cost(agent_results)

            # Create detailed cost breakdown for budget analysis
            cost_breakdown = await self._create_cost_breakdown(agent_results)

            # Check budget status
            budget_status = await self._check_budget_status(
                total_cost, trip_request.requirements.budget
            )

            # Validate budget allocation across categories
            budget_analysis = await self._validate_budget_allocation(
                cost_breakdown, trip_request.requirements.budget
            )

            # Detect conflicts
            conflicts = await self._detect_conflicts(daily_itinerary, agent_results)

            # Calculate optimization score
            optimization_score = await self._calculate_optimization_score(
                daily_itinerary, agent_results
            )

            # Log budget analysis for monitoring and recommendations
            if budget_analysis["warnings"]:
                self.logger.warning(
                    f"Budget allocation concerns: {', '.join(budget_analysis['warnings'])}"
                )

            self.logger.info(
                f"Budget utilization: {budget_analysis['budget_utilization']:.1%}, "
                f"status: {budget_status}"
            )

            # Create response
            response = ItineraryAgentResponse(
                trip_id=str(uuid4()),
                itinerary=daily_itinerary,
                total_cost=total_cost,
                currency=currency,
                budget_status=budget_status,
                conflicts=conflicts,
                optimization_score=optimization_score,
                generated_at=datetime.now(),
                cached=False,
            )

            # Cache the result (convert to dict for JSON serialization)
            try:
                cache_data = response.model_dump(mode="json")
                await self.redis.set(cache_key, json.dumps(cache_data), expire=self.cache_ttl)
            except Exception as cache_error:
                self.logger.warning(f"Failed to cache itinerary result: {cache_error}")

            search_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            self.logger.info(f"Itinerary generated in {search_time_ms}ms")

            return response

        except Exception as e:
            self.logger.error(f"Itinerary generation failed: {e}")
            raise ExternalAPIError(f"Itinerary generation failed: {e}") from e

    async def _coordinate_agents(
        self, trip_request: TripPlanRequest, agents_to_fetch: list[str] | None = None
    ) -> dict[str, Any]:
        """Enhanced agent coordination with fallback strategies and improved error handling.

        Args:
            trip_request: Trip planning request
            agents_to_fetch: Optional list of specific agents to fetch. If None, fetches all agents.

        Returns:
            Dictionary containing results from requested agents with graceful degradation
        """
        agent_results: dict[str, Any] = {}

        # Prepare requests only for requested agents (or all if not specified)
        all_agent_preparers = {
            "flights": self._prepare_flight_request,
            "hotels": self._prepare_hotel_request,
            "activities": self._prepare_activity_request,
            "weather": self._prepare_weather_request,
            "restaurants": self._prepare_food_request,
        }

        # If specific agents requested, only prepare those
        if agents_to_fetch is not None:
            agent_requests = {
                name: preparer(trip_request)
                for name, preparer in all_agent_preparers.items()
                if name in agents_to_fetch
            }
        else:
            # Prepare all agents (standalone mode)
            agent_requests = {
                name: preparer(trip_request) for name, preparer in all_agent_preparers.items()
            }

        # Try to get cached results first
        cached_results = await self._get_cached_agent_results(agent_requests)

        # Identify which agents need fresh calls
        agents_to_call = {
            name: request for name, request in agent_requests.items() if name not in cached_results
        }

        if cached_results:
            self.logger.info(f"Using cached results for {len(cached_results)} agents")
            agent_results.update(cached_results)

        if agents_to_call:
            # Execute remaining agent calls with enhanced coordination
            fresh_results = await self._execute_agent_calls_with_fallback(agents_to_call)
            agent_results.update(fresh_results)

            # Cache fresh results
            await self._cache_agent_results(fresh_results)

        # Apply graceful degradation for failed agents
        degraded_results = await self._apply_graceful_degradation(agent_results, trip_request)
        agent_results.update(degraded_results)

        # Log coordination summary
        success_count = sum(1 for r in agent_results.values() if r.get("status") == "success")
        fallback_count = sum(1 for r in agent_results.values() if r.get("fallback_used", False))

        self.logger.info(
            f"Agent coordination complete: {success_count}/5 successful, "
            f"{fallback_count} using fallbacks"
        )

        return agent_results

    async def _get_cached_agent_results(self, agent_requests: dict[str, Any]) -> dict[str, Any]:
        """Get cached results for agents that don't need fresh data."""
        cached_results: dict[str, Any] = {}

        for agent_name, request in agent_requests.items():
            # Generate cache key for each agent
            cache_key = f"agent_{agent_name}:{await self._agent_cache_key(request)}"

            try:
                cached_data_raw = await self.redis.get(cache_key)
                if cached_data_raw:
                    cached_data = json.loads(cached_data_raw)
                    # Check if cached data is still valid
                    cached_at = datetime.fromisoformat(cached_data.get("cached_at", "2000-01-01"))
                    cache_age_hours = (datetime.now() - cached_at).total_seconds() / 3600

                    # Weather data expires quickly (2 hours), others last longer (24 hours)
                    max_age = 2 if agent_name == "weather" else 24

                    if cache_age_hours < max_age:
                        cached_results[agent_name] = {
                            "status": "success",
                            "data": cached_data["data"],
                            "cached": True,
                            "cache_age_hours": cache_age_hours,
                        }
                        self.logger.debug(
                            f"Using cached data for {agent_name} ({cache_age_hours:.1f}h old)"
                        )

            except Exception as e:
                self.logger.warning(f"Failed to retrieve cached data for {agent_name}: {e}")

        return cached_results

    async def _execute_agent_calls_with_fallback(
        self, agents_to_call: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute agent calls with retry logic and fallback strategies."""
        agent_results: dict[str, Any] = {}

        # Primary attempt with all agents
        tasks = []
        agent_names = []

        for agent_name, request in agents_to_call.items():
            if agent_name == "flights":
                tasks.append(self._call_flight_agent_with_retry(request))
            elif agent_name == "hotels":
                tasks.append(self._call_hotel_agent_with_retry(request))
            elif agent_name == "activities":
                tasks.append(self._call_activity_agent_with_retry(request))
            elif agent_name == "weather":
                tasks.append(self._call_weather_agent_with_retry(request))
            elif agent_name == "restaurants":
                tasks.append(self._call_food_agent_with_retry(request))

            agent_names.append(agent_name)

        # Execute with timeout and error collection
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results with detailed error handling
        for i, result in enumerate(results):
            agent_name = agent_names[i]

            if isinstance(result, Exception):
                self.logger.error(f"{agent_name} agent failed after retries: {result}")
                agent_results[agent_name] = {
                    "status": "failed",
                    "error": str(result),
                    "error_type": type(result).__name__,
                }
            else:
                # Normalize data format to match pre-fetched data structure
                # Wrap response objects in dict format expected by downstream methods
                normalized_data = self._normalize_agent_response(agent_name, result)

                agent_results[agent_name] = {
                    "status": "success",
                    "data": normalized_data,
                    "cached": False,
                }
                self.logger.debug(f"{agent_name} agent completed successfully")

        return agent_results

    async def _call_flight_agent_with_retry(
        self, request: FlightSearchRequest, retries: int = 2
    ) -> Any:
        """Call flight agent with retry logic and fallback."""
        last_exception: Exception | None = None

        for attempt in range(retries + 1):
            try:
                async with self.flight_circuit:
                    result = await asyncio.wait_for(
                        self.flight_agent.process(request.model_dump()), timeout=self.agent_timeout
                    )
                    return result

            except Exception as e:
                last_exception = e
                self.logger.warning(f"Flight agent attempt {attempt + 1} failed: {e}")

                if attempt < retries:
                    # Exponential backoff
                    await asyncio.sleep(2**attempt)
                    continue

        # All retries failed
        raise ExternalAPIError(
            f"Flight agent failed after {retries + 1} attempts"
        ) from last_exception

    async def _call_hotel_agent_with_retry(
        self, request: HotelSearchRequest, retries: int = 2
    ) -> Any:
        """Call hotel agent with retry logic and fallback."""
        last_exception: Exception | None = None

        for attempt in range(retries + 1):
            try:
                async with self.hotel_circuit:
                    result = await asyncio.wait_for(
                        self.hotel_agent.process(request.model_dump()), timeout=self.agent_timeout
                    )
                    return result

            except Exception as e:
                last_exception = e
                self.logger.warning(f"Hotel agent attempt {attempt + 1} failed: {e}")

                if attempt < retries:
                    await asyncio.sleep(2**attempt)
                    continue

        raise ExternalAPIError(
            f"Hotel agent failed after {retries + 1} attempts"
        ) from last_exception

    async def _call_activity_agent_with_retry(
        self, request: ActivitySearchRequest, retries: int = 2
    ) -> Any:
        """Call activity agent with retry logic and fallback."""
        last_exception: Exception | None = None

        for attempt in range(retries + 1):
            try:
                async with self.activity_circuit:
                    result = await asyncio.wait_for(
                        self.activity_agent.process(request.model_dump()),
                        timeout=self.agent_timeout,
                    )
                    return result

            except Exception as e:
                last_exception = e
                self.logger.warning(f"Activity agent attempt {attempt + 1} failed: {e}")

                if attempt < retries:
                    await asyncio.sleep(2**attempt)
                    continue

        raise ExternalAPIError(
            f"Activity agent failed after {retries + 1} attempts"
        ) from last_exception

    async def _call_weather_agent_with_retry(
        self, request: WeatherSearchRequest, retries: int = 2
    ) -> Any:
        """Call weather agent with retry logic and fallback."""
        last_exception: Exception | None = None

        for attempt in range(retries + 1):
            try:
                async with self.weather_circuit:
                    result = await asyncio.wait_for(
                        self.weather_agent.process(request.model_dump()), timeout=self.agent_timeout
                    )
                    return result

            except Exception as e:
                last_exception = e
                self.logger.warning(f"Weather agent attempt {attempt + 1} failed: {e}")

                if attempt < retries:
                    await asyncio.sleep(2**attempt)
                    continue

        raise ExternalAPIError(
            f"Weather agent failed after {retries + 1} attempts"
        ) from last_exception

    async def _call_food_agent_with_retry(
        self, request: RestaurantSearchRequest, retries: int = 2
    ) -> Any:
        """Call food agent with retry logic and fallback."""
        last_exception: Exception | None = None

        for attempt in range(retries + 1):
            try:
                async with self.food_circuit:
                    result = await asyncio.wait_for(
                        self.food_agent.process(request.model_dump()), timeout=self.agent_timeout
                    )
                    return result

            except Exception as e:
                last_exception = e
                self.logger.warning(f"Food agent attempt {attempt + 1} failed: {e}")

                if attempt < retries:
                    await asyncio.sleep(2**attempt)
                    continue

        raise ExternalAPIError(
            f"Food agent failed after {retries + 1} attempts"
        ) from last_exception

    async def _apply_graceful_degradation(
        self, agent_results: dict[str, Any], trip_request: TripPlanRequest
    ) -> dict[str, Any]:
        """Apply graceful degradation for failed agents using fallback strategies."""
        degraded_results: dict[str, Any] = {}

        for agent_name, result in agent_results.items():
            if result.get("status") == "failed":
                fallback_data = await self._get_fallback_data(agent_name, trip_request)
                if fallback_data:
                    degraded_results[agent_name] = {
                        "status": "success",
                        "data": fallback_data,
                        "fallback_used": True,
                        "original_error": result.get("error"),
                    }
                    self.logger.info(f"Applied fallback for {agent_name} agent")

        return degraded_results

    async def _get_fallback_data(self, agent_name: str, trip_request: TripPlanRequest) -> Any:
        """Generate fallback data when agents fail."""
        try:
            if agent_name == "flights":
                return self._create_fallback_flight_data(trip_request)
            elif agent_name == "hotels":
                return self._create_fallback_hotel_data(trip_request)
            elif agent_name == "activities":
                return self._create_fallback_activity_data(trip_request)
            elif agent_name == "weather":
                return self._create_fallback_weather_data(trip_request)
            elif agent_name == "restaurants":
                return self._create_fallback_restaurant_data(trip_request)
        except Exception as e:
            self.logger.error(f"Failed to create fallback data for {agent_name}: {e}")

        return None

    def _create_fallback_flight_data(self, trip_request: TripPlanRequest) -> FlightSearchResponse:
        """Create basic flight data when flight agent fails."""
        # Create placeholder flight options
        departure_flight = FlightOption(
            external_id="fallback_departure",
            airline="TBD",
            flight_number="PLACEHOLDER",
            origin="TBD",
            destination=trip_request.destination.airport_code or "TBD",
            departure_time=datetime.combine(
                trip_request.requirements.start_date, datetime.min.time().replace(hour=9)
            ),
            arrival_time=datetime.combine(
                trip_request.requirements.start_date, datetime.min.time().replace(hour=12)
            ),
            duration_minutes=180,
            price=Decimal("300.00"),
            currency=trip_request.requirements.currency,
            travel_class=trip_request.requirements.travel_class,
            flight_status="scheduled",
            stops=0,
            trip_id=None,
            booking_url=None,
        )

        return_flight = FlightOption(
            external_id="fallback_return",
            airline="TBD",
            flight_number="PLACEHOLDER_RETURN",
            origin=trip_request.destination.airport_code or "TBD",
            destination="TBD",
            departure_time=datetime.combine(
                trip_request.requirements.end_date, datetime.min.time().replace(hour=15)
            ),
            arrival_time=datetime.combine(
                trip_request.requirements.end_date, datetime.min.time().replace(hour=18)
            ),
            duration_minutes=180,
            price=Decimal("300.00"),
            currency=trip_request.requirements.currency,
            travel_class=trip_request.requirements.travel_class,
            flight_status="scheduled",
            stops=0,
            trip_id=None,
            booking_url=None,
        )

        return FlightSearchResponse(
            flights=[departure_flight, return_flight],
            search_metadata={
                "fallback": True,
                "note": "Placeholder flights - manual booking required",
            },
            cache_expires_at=None,
        )

    def _create_fallback_hotel_data(self, trip_request: TripPlanRequest) -> HotelSearchResponse:
        """Create basic hotel data when hotel agent fails."""
        nights = (trip_request.requirements.end_date - trip_request.requirements.start_date).days
        budget_per_night = (
            trip_request.requirements.budget / max(nights, 1) / 3
        )  # 1/3 of budget for accommodation

        fallback_hotel = HotelOption(
            external_id="fallback_hotel",
            name=f"Hotel in {trip_request.destination.city}",
            location=HotelLocation(
                latitude=trip_request.destination.latitude or 0.0,
                longitude=trip_request.destination.longitude or 0.0,
                address=f"City Center, {trip_request.destination.city}",
                city=trip_request.destination.city,
                country=trip_request.destination.country,
                postal_code=None,
            ),
            price_per_night=Decimal(budget_per_night),
            currency=trip_request.requirements.currency,
            rating=3.5,
            amenities=["WiFi", "Breakfast", "Reception"],
            trip_id=None,
            booking_url=None,
        )

        return HotelSearchResponse(
            hotels=[fallback_hotel],
            search_metadata={
                "fallback": True,
                "note": "Generic hotel option - manual selection required",
            },
            cache_expires_at=None,
        )

    def _create_fallback_activity_data(
        self, trip_request: TripPlanRequest
    ) -> ActivitySearchResponse:
        """Create basic activity data when activity agent fails."""
        generic_activities = [
            ActivityOption(
                external_id="fallback_city_tour",
                name=f"Explore {trip_request.destination.city} City Center",
                description="Walking tour of the main attractions and landmarks",
                category=ActivityCategory.CULTURAL,
                duration_minutes=180,
                price=Decimal("25.00"),
                currency=trip_request.requirements.currency,
                location=ActivityLocation(
                    latitude=trip_request.destination.latitude or 0.0,
                    longitude=trip_request.destination.longitude or 0.0,
                    address=f"{trip_request.destination.city} City Center",
                    city=trip_request.destination.city,
                    country=trip_request.destination.country,
                    postal_code=None,
                ),
                rating=4.0,
                provider="fallback",
                trip_id=None,
                review_count=None,
                booking_url=None,
            ),
            ActivityOption(
                external_id="fallback_museum",
                name="Local Museum Visit",
                description="Visit to a popular local museum or cultural site",
                category=ActivityCategory.CULTURAL,
                duration_minutes=120,
                price=Decimal("15.00"),
                currency=trip_request.requirements.currency,
                location=ActivityLocation(
                    latitude=trip_request.destination.latitude or 0.0,
                    longitude=trip_request.destination.longitude or 0.0,
                    address=f"{trip_request.destination.city}",
                    city=trip_request.destination.city,
                    country=trip_request.destination.country,
                    postal_code=None,
                ),
                rating=3.8,
                provider="fallback",
                trip_id=None,
                review_count=None,
                booking_url=None,
            ),
        ]

        return ActivitySearchResponse(
            activities=generic_activities,
            search_metadata={
                "fallback": True,
                "note": "Generic activities - research specific options",
            },
            cache_expires_at=None,
        )

    def _create_fallback_weather_data(self, trip_request: TripPlanRequest) -> dict[str, Any]:
        """Create basic weather data when weather agent fails."""
        return {
            "location": trip_request.destination.city,
            "forecast": "Weather information unavailable - check local forecast",
            "temperature_range": "15-25°C (estimated)",
            "conditions": "Variable",
            "recommendations": ["Pack layers", "Check weather before departure"],
            "fallback": True,
        }

    def _create_fallback_restaurant_data(
        self, trip_request: TripPlanRequest
    ) -> RestaurantSearchResponse:
        """Create basic restaurant data when food agent fails."""
        generic_restaurants = [
            RestaurantOption(
                trip_id=None,  # Will be set later
                external_id="fallback_restaurant",
                name=f"Local Restaurant in {trip_request.destination.city}",
                categories=[GeoapifyCateringCategory.RESTAURANT_REGIONAL.value],
                formatted_address=f"{trip_request.destination.city}, {trip_request.destination.country}",
                location=RestaurantLocation(
                    latitude=trip_request.destination.latitude or 0.0,
                    longitude=trip_request.destination.longitude or 0.0,
                    address=f"City Center, {trip_request.destination.city}",
                    address_line2=None,
                    city=trip_request.destination.city,
                    state=None,
                    country=trip_request.destination.country,
                    postal_code=None,
                    neighborhood=None,
                ),
                distance_meters=1000,  # 1km from city center
                provider="fallback",
            )
        ]

        return RestaurantSearchResponse(
            restaurants=generic_restaurants,
            search_metadata={
                "fallback": True,
                "note": "Generic restaurant - research local options",
            },
            cache_expires_at=None,
        )

    def _make_serializable(self, data: Any) -> Any:
        """Convert Pydantic models and other objects to JSON-serializable format."""
        from pydantic import BaseModel

        if isinstance(data, BaseModel):
            return data.model_dump(mode="json")
        elif isinstance(data, dict):
            return {key: self._make_serializable(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._make_serializable(item) for item in data]
        elif isinstance(data, (datetime, date)):
            return data.isoformat()
        elif isinstance(data, Decimal):
            return str(data)
        else:
            return data

    async def _cache_agent_results(self, agent_results: dict[str, Any]) -> None:
        """Cache successful agent results for future use."""
        for agent_name, result in agent_results.items():
            if result.get("status") == "success" and not result.get("cached", False):
                try:
                    # Convert Pydantic models to dicts for JSON serialization
                    data = result["data"]
                    serializable_data = self._make_serializable(data)

                    cache_data = {
                        "data": serializable_data,
                        "cached_at": datetime.now().isoformat(),
                        "agent_name": agent_name,
                    }

                    # Generate cache key (simplified)
                    cache_key = f"agent_{agent_name}:recent"

                    # Set expiration based on agent type
                    expire_seconds = (
                        7200 if agent_name == "weather" else 86400
                    )  # 2h for weather, 24h for others

                    await self.redis.set(cache_key, json.dumps(cache_data), expire=expire_seconds)
                    self.logger.debug(f"Cached {agent_name} result for {expire_seconds / 3600}h")

                except Exception as e:
                    self.logger.warning(f"Failed to cache {agent_name} results: {e}")

    async def _agent_cache_key(self, request: Any) -> str:
        """Generate cache key for agent request."""
        import hashlib
        import json
        from datetime import date, datetime
        from decimal import Decimal

        def json_serializer(obj: Any) -> str:
            """Custom JSON serializer for datetime, date and Decimal objects."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, date):
                return obj.isoformat()
            elif isinstance(obj, Decimal):
                return str(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        # Create a simple hash of the request
        request_data = request.model_dump() if hasattr(request, "model_dump") else str(request)
        request_str = json.dumps(request_data, sort_keys=True, default=json_serializer)
        return hashlib.md5(request_str.encode()).hexdigest()[:16]

    async def _call_flight_agent(self, request: FlightSearchRequest) -> Any:
        """Call flight agent with circuit breaker protection."""
        async with self.flight_circuit:
            return await asyncio.wait_for(
                self.flight_agent.process(request.model_dump()), timeout=self.agent_timeout
            )

    async def _call_hotel_agent(self, request: HotelSearchRequest) -> Any:
        """Call hotel agent with circuit breaker protection."""
        async with self.hotel_circuit:
            return await asyncio.wait_for(
                self.hotel_agent.process(request.model_dump()), timeout=self.agent_timeout
            )

    async def _call_activity_agent(self, request: ActivitySearchRequest) -> Any:
        """Call activity agent with circuit breaker protection."""
        async with self.activity_circuit:
            return await asyncio.wait_for(
                self.activity_agent.process(request.model_dump()), timeout=self.agent_timeout
            )

    async def _call_weather_agent(self, request: WeatherSearchRequest) -> Any:
        """Call weather agent with circuit breaker protection."""
        async with self.weather_circuit:
            return await asyncio.wait_for(
                self.weather_agent.process(request.model_dump()), timeout=self.agent_timeout
            )

    async def _call_food_agent(self, request: RestaurantSearchRequest) -> Any:
        """Call food agent with circuit breaker protection."""
        async with self.food_circuit:
            return await asyncio.wait_for(
                self.food_agent.process(request.model_dump()), timeout=self.agent_timeout
            )

    def _prepare_flight_request(self, trip_request: TripPlanRequest) -> FlightSearchRequest:
        """Prepare flight search request from trip request."""
        return FlightSearchRequest(
            origin="NYC",  # This should come from user location or be derived
            destination=trip_request.destination.airport_code or "JFK",
            departure_date=datetime.combine(
                trip_request.requirements.start_date, datetime.min.time()
            ),
            return_date=datetime.combine(trip_request.requirements.end_date, datetime.min.time()),
            passengers=trip_request.requirements.travelers,
            travel_class=trip_request.requirements.travel_class,
            currency="USD",
        )

    def _prepare_hotel_request(self, trip_request: TripPlanRequest) -> HotelSearchRequest:
        """Prepare hotel search request from trip request."""
        return HotelSearchRequest(
            location=trip_request.destination.city,
            check_in_date=datetime.combine(
                trip_request.requirements.start_date, datetime.min.time()
            ),
            check_out_date=datetime.combine(
                trip_request.requirements.end_date, datetime.min.time()
            ),
            guest_count=trip_request.requirements.travelers,
            room_count=1,  # Default, could be derived from guest count
            budget_per_night=Decimal(
                trip_request.requirements.budget
                / (
                    (trip_request.requirements.end_date - trip_request.requirements.start_date).days
                    or 1
                )
                / 2
            ),
        )

    def _normalize_agent_response(self, agent_name: str, response: Any) -> dict[str, Any]:
        """Normalize agent response to match pre-fetched data format.

        Args:
            agent_name: Name of the agent (flights, hotels, activities, etc.)
            response: Raw agent response object

        Returns:
            Normalized dict with data wrapped in expected format
        """
        # Handle response objects - extract data and wrap in dict
        if agent_name == "flights":
            if hasattr(response, "flights"):
                return {"flights": response.flights}
            return {"flights": []}
        elif agent_name == "hotels":
            if hasattr(response, "hotels"):
                return {"hotels": response.hotels}
            return {"hotels": []}
        elif agent_name == "activities":
            if hasattr(response, "activities"):
                return {"activities": response.activities}
            return {"activities": []}
        elif agent_name == "restaurants":
            if hasattr(response, "restaurants"):
                return {"restaurants": response.restaurants}
            return {"restaurants": []}
        elif agent_name == "weather":
            # Weather is already a dict, return as-is
            if isinstance(response, dict):
                return response
            # If it's a response object, try to extract data
            if hasattr(response, "model_dump"):
                return response.model_dump()
            return {}
        else:
            # Unknown agent, return as-is
            return response

    def _has_prefetched_agent_results(self, request_data: dict[str, Any]) -> bool:
        """Check if request_data contains pre-fetched agent results from workflow.

        Args:
            request_data: Request data dictionary

        Returns:
            True if this appears to be workflow mode with pre-fetched data
        """
        # Workflow mode has these keys that standalone mode doesn't
        workflow_indicators = [
            "flight_options",
            "hotel_options",
            "activity_options",
            "restaurant_options",
            "weather_forecast",
        ]

        # If any of these workflow-specific keys exist, we're in workflow mode
        return any(key in request_data for key in workflow_indicators)

    async def _extract_workflow_data(
        self, request_data: dict[str, Any]
    ) -> tuple[TripPlanRequest, dict[str, Any]]:
        """Extract TripPlanRequest and agent results from workflow state.

        Args:
            request_data: Workflow state with pre-fetched agent results

        Returns:
            Tuple of (TripPlanRequest, agent_results dict)
        """
        # Reconstruct TripPlanRequest from workflow data
        # The workflow sends individual fields, we need to reconstruct the proper structure
        from ..models.trip import TripDestination, TripRequirements

        # Build TripDestination
        destination = TripDestination(
            city=request_data.get("destination", "Unknown"),
            country=request_data.get("country", "Unknown"),
            country_code=request_data.get("country_code", "XX"),
            airport_code=request_data.get("airport_code"),
            latitude=request_data.get("latitude", 0.0),
            longitude=request_data.get("longitude", 0.0),
        )

        # Build TripRequirements
        from datetime import date

        start_date_str = request_data.get("start_date", "")
        end_date_str = request_data.get("end_date", "")

        requirements = TripRequirements(
            budget=Decimal(str(request_data.get("budget", 1000.0))),
            currency=request_data.get("currency", "USD"),
            start_date=date.fromisoformat(start_date_str) if start_date_str else date.today(),
            end_date=date.fromisoformat(end_date_str)
            if end_date_str
            else date.today(),
            travelers=request_data.get("traveler_count", 1),
            travel_class=request_data.get("travel_class", "economy"),
            accommodation_type=request_data.get("accommodation_type", "hotel"),
        )

        # Create TripPlanRequest
        trip_request = TripPlanRequest(
            destination=destination,
            requirements=requirements,
            preferences=request_data.get("user_preferences", {}),
        )

        # Extract pre-fetched agent results and convert to expected format
        # Note: Some agents might have failed in workflow, so check if data is present
        agent_results = {}

        # Flight data - wrap in dict format expected by _add_flight_items
        flight_data = request_data.get("flight_options", [])
        if flight_data:  # Has data
            agent_results["flights"] = {
                "status": "success",
                "data": {"flights": flight_data},  # Wrap in dict with "flights" key
                "cached": False,
                "prefetched": True,
            }

        # Hotel data - wrap in dict format expected by _add_hotel_items
        hotel_data = request_data.get("hotel_options", [])
        if hotel_data:  # Has data
            agent_results["hotels"] = {
                "status": "success",
                "data": {"hotels": hotel_data},  # Wrap in dict with "hotels" key
                "cached": False,
                "prefetched": True,
            }

        # Activity data - wrap in dict format expected by _add_activity_items
        activity_data = request_data.get("activity_options", [])
        if activity_data:  # Has data
            agent_results["activities"] = {
                "status": "success",
                "data": {"activities": activity_data},  # Wrap in dict with "activities" key
                "cached": False,
                "prefetched": True,
            }

        # Restaurant data - wrap in dict format expected by _add_meal_items
        restaurant_data = request_data.get("restaurant_options", [])
        if restaurant_data:  # Has data
            agent_results["restaurants"] = {
                "status": "success",
                "data": {"restaurants": restaurant_data},  # Wrap in dict with "restaurants" key
                "cached": False,
                "prefetched": True,
            }

        # Weather data - already in correct format (dict with forecasts)
        weather_data = request_data.get("weather_forecast", {})
        if weather_data:  # Has data
            agent_results["weather"] = {
                "status": "success",
                "data": weather_data,  # Weather data is already a dict
                "cached": False,
                "prefetched": True,
            }

        # Check for missing agents and call them if needed
        missing_agents = []
        if "flights" not in agent_results:
            missing_agents.append("flights")
        if "hotels" not in agent_results:
            missing_agents.append("hotels")
        if "activities" not in agent_results:
            missing_agents.append("activities")
        if "restaurants" not in agent_results:
            missing_agents.append("restaurants")
        if "weather" not in agent_results:
            missing_agents.append("weather")

        if missing_agents:
            self.logger.warning(
                f"Workflow mode: Missing data for {missing_agents}. "
                f"Will call agents to fetch missing data."
            )

            # Call _coordinate_agents ONLY for missing agents (with caching and fallback)
            missing_results = await self._coordinate_agents(trip_request, agents_to_fetch=missing_agents)

            # Merge missing results with pre-fetched results
            for agent_name in missing_agents:
                if agent_name in missing_results:
                    agent_results[agent_name] = missing_results[agent_name]

        # Helper to safely get count of items
        def get_item_count(agent_name: str) -> int:
            if agent_name not in agent_results:
                return 0
            data = agent_results[agent_name].get("data")
            if data is None:
                return 0
            # Handle dict with wrapped lists (workflow mode)
            if isinstance(data, dict):
                if "flights" in data:
                    return len(data["flights"])
                if "hotels" in data:
                    return len(data["hotels"])
                if "activities" in data:
                    return len(data["activities"])
                if "restaurants" in data:
                    return len(data["restaurants"])
            # Handle response objects (from agent calls)
            if hasattr(data, "flights"):
                return len(data.flights)
            if hasattr(data, "hotels"):
                return len(data.hotels)
            if hasattr(data, "activities"):
                return len(data.activities)
            if hasattr(data, "restaurants"):
                return len(data.restaurants)
            return 0

        self.logger.info(
            f"Extracted workflow data: "
            f"{get_item_count('flights')} flights, "
            f"{get_item_count('hotels')} hotels, "
            f"{get_item_count('activities')} activities, "
            f"{get_item_count('restaurants')} restaurants"
        )

        return trip_request, agent_results

    def _prepare_activity_request(self, trip_request: TripPlanRequest) -> ActivitySearchRequest:
        """Prepare activity search request from trip request."""
        budget_per_person = Decimal(
            trip_request.requirements.budget / trip_request.requirements.travelers / 4
        )

        request = ActivitySearchRequest(
            location=trip_request.destination.city,
            guest_count=trip_request.requirements.travelers,
            budget_per_person=budget_per_person,
            max_results=10,
            check_in_date=datetime.combine(
                trip_request.requirements.start_date, datetime.min.time()
            ),
            check_out_date=datetime.combine(
                trip_request.requirements.end_date, datetime.min.time()
            ),
            category=ActivityCategory.CULTURAL,
            duration_hours=4,
            currency="USD",
        )

        return request

    def _prepare_weather_request(self, trip_request: TripPlanRequest) -> WeatherSearchRequest:
        """Prepare weather request from trip request."""
        return WeatherSearchRequest(
            location=trip_request.destination.city,
            start_date=datetime.combine(trip_request.requirements.start_date, datetime.min.time()),
            end_date=datetime.combine(trip_request.requirements.end_date, datetime.min.time()),
            latitude=trip_request.destination.latitude,
            longitude=trip_request.destination.longitude,
            include_historical=True,
        )

    def _prepare_food_request(self, trip_request: TripPlanRequest) -> RestaurantSearchRequest:
        """Prepare restaurant search request from trip request."""
        return RestaurantSearchRequest(
            location=trip_request.destination.city,
            max_results=15,
            latitude=trip_request.destination.latitude,
            longitude=trip_request.destination.longitude,
            categories=[GeoapifyCateringCategory.RESTAURANT_ITALIAN.value],
            radius_meters=5000,
        )

    async def health_check(self) -> dict[str, Any]:
        """Enhanced health check including all coordinated agents."""
        status = await super().health_check()

        # Add agent health checks
        agent_health = {}
        agents: dict[str, BaseAgent[Any]] = {
            "flight": self.flight_agent,
            "hotel": self.hotel_agent,
            "activity": self.activity_agent,
            "weather": self.weather_agent,
            "food": self.food_agent,
        }

        for agent_name, agent in agents.items():
            try:
                agent_status = await agent.health_check()
                agent_health[agent_name] = agent_status["status"]
            except Exception:
                agent_health[agent_name] = "unhealthy"

        status["dependencies"]["agents"] = agent_health

        # Overall status degraded if any agent is unhealthy
        if any(health != "healthy" for health in agent_health.values()):
            status["status"] = "degraded"

        return status

    # Daily schedule generation and optimization methods
    async def _generate_daily_schedule(
        self, trip_request: TripPlanRequest, agent_results: dict[str, Any]
    ) -> "TripItinerary":
        """Generate daily schedule with time-based activity sequencing."""
        start_date = trip_request.requirements.start_date
        end_date = trip_request.requirements.end_date
        trip_duration = (end_date - start_date).days

        if trip_duration <= 0:
            trip_duration = 1
            end_date = start_date + timedelta(days=1)

        daily_itineraries: list[DailyItinerary] = []

        # Generate daily schedules
        for day_num in range(trip_duration):
            current_date = start_date + timedelta(days=day_num)

            daily_items = await self._generate_daily_items(
                current_date, day_num + 1, trip_request, agent_results
            )

            # Sort items by time
            daily_items.sort(key=lambda x: x.start_time)

            # Calculate daily cost and metrics
            daily_cost = sum(item.cost for item in daily_items if item.cost is not None)

            # Get weather summary if available
            weather_summary = self._extract_weather_for_date(current_date, agent_results)

            daily_itinerary = DailyItinerary(
                date=current_date,
                day_number=day_num + 1,
                items=daily_items,
                daily_cost=Decimal(daily_cost),
                weather_summary=weather_summary,
                meal_plan=await self._generate_meal_plan(daily_items),
                notes=None,
            )

            daily_itineraries.append(daily_itinerary)

        # Calculate trip totals
        total_cost = sum(day.daily_cost for day in daily_itineraries if day.daily_cost is not None)
        average_daily_cost = (
            total_cost / len(daily_itineraries) if daily_itineraries else Decimal("0.00")
        )

        return TripItinerary(
            trip_id=str(uuid4()),
            days=daily_itineraries,
            total_days=trip_duration,
            total_cost=Decimal(total_cost),
            average_daily_cost=Decimal(average_daily_cost),
            currency="USD",
            optimization_score=0.0,  # Will be calculated by optimization engine
            budget_status="calculating",  # Will be updated by budget calculation
            last_updated=datetime.now(),
        )

    async def _generate_daily_items(
        self,
        date: date,
        day_number: int,
        trip_request: TripPlanRequest,
        agent_results: dict[str, Any],
    ) -> list["ItineraryItem"]:
        """Generate itinerary items for a specific day."""

        items: list[ItineraryItem] = []

        # Add flight items (arrival/departure days)
        items.extend(await self._add_flight_items(date, day_number, trip_request, agent_results))

        # Add hotel check-in/check-out
        items.extend(await self._add_hotel_items(date, day_number, trip_request, agent_results))

        # Add activities (avoid first/last day if flights present)
        if not self._is_travel_day(date, day_number, trip_request):
            items.extend(
                await self._add_activity_items(date, day_number, trip_request, agent_results)
            )

        # Add meals
        items.extend(await self._add_meal_items(date, day_number, trip_request, agent_results))

        return items

    async def _add_flight_items(
        self,
        date: date,
        day_number: int,
        trip_request: TripPlanRequest,
        agent_results: dict[str, Any],
    ) -> list["ItineraryItem"]:
        """Add flight items for arrival and departure days."""
        items: list[ItineraryItem] = []

        if "flights" not in agent_results or agent_results["flights"]["status"] != "success":
            return items

        flight_data = agent_results["flights"]["data"]

        try:
            # Handle both dict and Pydantic model and Mock objects
            flights_list = None
            if hasattr(flight_data, "flights"):  # Pydantic model
                flights_list = flight_data.flights
            elif isinstance(flight_data, dict) and "flights" in flight_data:  # Dict
                flights_list = flight_data["flights"]
            else:
                # Handle Mock or other objects
                return items

            # First day - arrival flight
            if day_number == 1 and flights_list:
                # Find arrival flight (usually first one)
                arrival_flights = [
                    f
                    for f in flights_list
                    if (
                        hasattr(f, "destination")
                        and f.destination == trip_request.destination.airport_code
                    )
                    or (
                        isinstance(f, dict)
                        and f.get("destination") == trip_request.destination.airport_code
                    )
                ]

                if arrival_flights:
                    flight = arrival_flights[0]
                    # Get flight data safely
                    flight_number = (
                        flight.flight_number
                        if hasattr(flight, "flight_number")
                        else flight["flight_number"]
                    )
                    flight_origin = flight.origin if hasattr(flight, "origin") else flight["origin"]
                    flight_destination = (
                        flight.destination
                        if hasattr(flight, "destination")
                        else flight["destination"]
                    )
                    flight_arrival_time = (
                        flight.arrival_time
                        if hasattr(flight, "arrival_time")
                        else flight["arrival_time"]
                    )
                    flight_price = flight.price if hasattr(flight, "price") else flight["price"]

                    items.append(
                        ItineraryItem(
                            item_id=f"flight_arrival_{flight_number}",
                            item_type="flight",
                            name=f"Flight {flight_number} Arrival",
                            description=f"Arrive from {flight_origin} to {flight_destination}",
                            start_time=flight_arrival_time
                            if isinstance(flight_arrival_time, datetime)
                            else datetime.combine(
                                date, datetime.fromisoformat(str(flight_arrival_time)).time()
                            ),
                            end_time=(
                                flight_arrival_time
                                if isinstance(flight_arrival_time, datetime)
                                else datetime.combine(
                                    date, datetime.fromisoformat(str(flight_arrival_time)).time()
                                )
                            )
                            + timedelta(minutes=30),
                            duration_minutes=30,
                            cost=Decimal(str(flight_price)),
                            booking_reference=flight_number,
                            latitude=None,
                            longitude=None,
                            address=None,
                            booking_url=None,
                            cancellation_policy=None,
                            special_instructions=None,
                        )
                    )

            # Last day - departure flight
            total_days = (
                trip_request.requirements.end_date - trip_request.requirements.start_date
            ).days + 1
            if day_number == total_days and flights_list:
                # Find departure flight (usually second one or one departing from destination)
                departure_flights = [
                    f
                    for f in flights_list
                    if (hasattr(f, "origin") and f.origin == trip_request.destination.airport_code)
                    or (
                        isinstance(f, dict)
                        and f.get("origin") == trip_request.destination.airport_code
                    )
                ]

                if departure_flights:
                    flight = departure_flights[0]
                    # Get flight data safely
                    dep_flight_number = (
                        flight.flight_number
                        if hasattr(flight, "flight_number")
                        else flight["flight_number"]
                    )
                    dep_flight_origin = (
                        flight.origin if hasattr(flight, "origin") else flight["origin"]
                    )
                    dep_flight_destination = (
                        flight.destination
                        if hasattr(flight, "destination")
                        else flight["destination"]
                    )
                    dep_flight_departure_time = (
                        flight.departure_time
                        if hasattr(flight, "departure_time")
                        else flight["departure_time"]
                    )

                    items.append(
                        ItineraryItem(
                            item_id=f"flight_departure_{dep_flight_number}",
                            item_type="flight",
                            name=f"Flight {dep_flight_number} Departure",
                            description=f"Depart from {dep_flight_origin} to {dep_flight_destination}",
                            start_time=(
                                dep_flight_departure_time
                                if isinstance(dep_flight_departure_time, datetime)
                                else datetime.combine(
                                    date,
                                    datetime.fromisoformat(str(dep_flight_departure_time)).time(),
                                )
                            )
                            - timedelta(hours=2),
                            end_time=dep_flight_departure_time
                            if isinstance(dep_flight_departure_time, datetime)
                            else datetime.combine(
                                date, datetime.fromisoformat(str(dep_flight_departure_time)).time()
                            ),
                            duration_minutes=120,
                            cost=Decimal("0.00"),  # Cost already counted in arrival
                            latitude=None,
                            longitude=None,
                            address=None,
                            booking_reference=None,
                            booking_url=None,
                            cancellation_policy=None,
                            special_instructions=None,
                        )
                    )

        except (TypeError, AttributeError):
            # Handle Mock objects or other non-iterable data
            return items

        return items

    async def _add_hotel_items(
        self,
        date: date,
        day_number: int,
        trip_request: TripPlanRequest,
        agent_results: dict[str, Any],
    ) -> list["ItineraryItem"]:
        """Add hotel check-in/check-out items."""
        items: list[ItineraryItem] = []

        if "hotels" not in agent_results or agent_results["hotels"]["status"] != "success":
            return items

        hotel_data = agent_results["hotels"]["data"]

        try:
            # Handle both dict and Pydantic model and Mock objects
            hotels_list = None
            if hasattr(hotel_data, "hotels"):  # Pydantic model
                hotels_list = hotel_data.hotels
            elif isinstance(hotel_data, dict) and "hotels" in hotel_data:  # Dict
                hotels_list = hotel_data["hotels"]
            else:
                # Handle Mock or other objects
                return items

            if hotels_list:
                hotel = hotels_list[0]  # Take first hotel

                # Check-in on first non-travel day (usually day 1, or day 2 if day 1 has late arrival)
                # Check in on day 1 or 2, but not on last day
                total_days = (
                    trip_request.requirements.end_date - trip_request.requirements.start_date
                ).days + 1
                is_checkin_day = (
                    (day_number == 1 and not self._is_travel_day(date, day_number, trip_request))
                    or (day_number == 2 and day_number < total_days)
                )

                if is_checkin_day:
                    # Get hotel data safely
                    hotel_external_id = (
                        hotel.external_id if hasattr(hotel, "external_id") else hotel["external_id"]
                    )
                    hotel_name = hotel.name if hasattr(hotel, "name") else hotel["name"]
                    hotel_price_per_night = (
                        hotel.price_per_night
                        if hasattr(hotel, "price_per_night")
                        else hotel["price_per_night"]
                    )

                    if hasattr(hotel, "location"):
                        hotel_address = hotel.location.address
                        hotel_latitude = hotel.location.latitude
                        hotel_longitude = hotel.location.longitude
                    else:
                        hotel_location = hotel["location"]
                        hotel_address = hotel_location["address"]
                        hotel_latitude = hotel_location["latitude"]
                        hotel_longitude = hotel_location["longitude"]

                    items.append(
                        ItineraryItem(
                            item_id=f"hotel_checkin_{hotel_external_id}",
                            item_type="hotel",
                            name=f"Check-in at {hotel_name}",
                            description=f"Hotel check-in at {hotel_address}",
                            start_time=datetime.combine(
                                date, datetime.min.time().replace(hour=15)
                            ),  # 3 PM
                            end_time=datetime.combine(
                                date, datetime.min.time().replace(hour=15, minute=30)
                            ),
                            duration_minutes=30,
                            cost=Decimal(str(hotel_price_per_night)),
                            address=hotel_address,
                            latitude=hotel_latitude,
                            longitude=hotel_longitude,
                            booking_reference=f"hotel_{hotel_external_id}",
                            booking_url=None,
                            cancellation_policy=None,
                            special_instructions=None,
                        )
                    )

                # Check-out on last day
                elif date == trip_request.requirements.end_date:
                    items.append(
                        ItineraryItem(
                            item_id=f"hotel_checkout_{hotel_external_id}",
                            item_type="hotel",
                            name=f"Check-out from {hotel_name}",
                            description="Hotel check-out",
                            start_time=datetime.combine(
                                date, datetime.min.time().replace(hour=11)
                            ),  # 11 AM
                            end_time=datetime.combine(
                                date, datetime.min.time().replace(hour=11, minute=30)
                            ),
                            duration_minutes=30,
                            cost=Decimal("0.00"),  # Cost already counted in check-in
                            latitude=None,
                            longitude=None,
                            address=None,
                            booking_reference=None,
                            booking_url=None,
                            cancellation_policy=None,
                            special_instructions=None,
                        )
                    )

        except (TypeError, IndexError, AttributeError):
            # Handle Mock objects or empty lists
            return items

        return items

    async def _add_activity_items(
        self,
        date: date,
        day_number: int,
        trip_request: TripPlanRequest,
        agent_results: dict[str, Any],
    ) -> list["ItineraryItem"]:
        """Add activity items for the day."""
        items: list[ItineraryItem] = []

        if "activities" not in agent_results or agent_results["activities"]["status"] != "success":
            return items

        activity_data = agent_results["activities"]["data"]

        try:
            # Handle both dict and Pydantic model and Mock objects
            activities_list = None
            if hasattr(activity_data, "activities"):  # Pydantic model
                activities_list = activity_data.activities
            elif isinstance(activity_data, dict) and "activities" in activity_data:  # Dict
                activities_list = activity_data["activities"]
            else:
                # Handle Mock or other objects
                return items

            if activities_list:
                # Distribute activities across non-travel days
                # Calculate how many non-travel days we have
                trip_duration = (
                    trip_request.requirements.end_date - trip_request.requirements.start_date
                ).days + 1

                # Estimate non-travel days (usually trip_duration - 2 for arrival/departure)
                # Schedule activities in morning (09:00) and afternoon (15:30) slots
                # to avoid conflicts with lunch (14:00) and dinner (19:00)

                activity_index = (day_number - 2) % len(activities_list)  # Start from day 2

                # Take up to 4 activities per day (2 morning, 2 afternoon)
                day_activities = []
                for i in range(4):
                    idx = (activity_index + i) % len(activities_list)
                    day_activities.append(activities_list[idx])
                    if len(day_activities) >= min(4, len(activities_list)):
                        break

                # Define time slots with 2-hour gaps for 90-min activities + 30min travel buffer
                # Morning: 09:00, 11:00 | Afternoon: 15:30, 17:30
                time_slots = [9, 11, 15.5, 17.5]  # Hours as decimals

                for i, activity in enumerate(day_activities):
                    if i >= len(time_slots):
                        break

                    start_hour_decimal = time_slots[i]
                    start_hour = int(start_hour_decimal)
                    start_minute = int((start_hour_decimal - start_hour) * 60)

                    # Get activity data safely
                    activity_external_id = (
                        activity.external_id
                        if hasattr(activity, "external_id")
                        else activity["external_id"]
                    )
                    activity_name = activity.name if hasattr(activity, "name") else activity["name"]
                    activity_description = (
                        activity.description
                        if hasattr(activity, "description")
                        else activity["description"]
                    )
                    activity_duration = (
                        activity.duration_minutes
                        if hasattr(activity, "duration_minutes")
                        else activity.get("duration_minutes", 90)
                    )
                    # Cap duration at 90 minutes to avoid overlaps
                    activity_duration = min(activity_duration or 90, 90)
                    activity_price = (
                        activity.price if hasattr(activity, "price") else activity["price"]
                    )

                    if hasattr(activity, "location"):
                        activity_latitude = activity.location.latitude
                        activity_longitude = activity.location.longitude
                    else:
                        activity_location = activity["location"]
                        activity_latitude = activity_location["latitude"]
                        activity_longitude = activity_location["longitude"]

                    start_time = datetime.combine(
                        date, datetime.min.time().replace(hour=start_hour, minute=start_minute)
                    )
                    end_time = start_time + timedelta(minutes=activity_duration)

                    items.append(
                        ItineraryItem(
                            item_id=f"activity_{activity_external_id}_{date}",
                            item_type="activity",
                            name=activity_name,
                            description=activity_description,
                            start_time=start_time,
                            end_time=end_time,
                            duration_minutes=activity_duration,
                            cost=Decimal(str(activity_price)),
                            latitude=activity_latitude,
                            longitude=activity_longitude,
                            booking_url=getattr(activity, "booking_url", None)
                            if hasattr(activity, "booking_url")
                            else activity.get("booking_url"),
                            address=None,
                            booking_reference=None,
                            cancellation_policy=None,
                            special_instructions=None,
                        )
                    )

        except (TypeError, AttributeError):
            # Handle Mock objects or other non-iterable data
            return items

        return items

    async def _add_meal_items(
        self,
        date: date,
        day_number: int,
        trip_request: TripPlanRequest,
        agent_results: dict[str, Any],
    ) -> list["ItineraryItem"]:
        """Add meal items (restaurants) for the day."""
        items: list[ItineraryItem] = []

        if (
            "restaurants" not in agent_results
            or agent_results["restaurants"]["status"] != "success"
        ):
            return items

        restaurant_data = agent_results["restaurants"]["data"]

        try:
            # Handle both dict and Pydantic model and Mock objects
            restaurants_list = None
            if hasattr(restaurant_data, "restaurants"):  # Pydantic model
                restaurants_list = restaurant_data.restaurants
            elif isinstance(restaurant_data, dict) and "restaurants" in restaurant_data:  # Dict
                restaurants_list = restaurant_data["restaurants"]
            else:
                # Handle Mock or other objects
                return items

            if restaurants_list:
                # Select 2 restaurants per day (lunch and dinner)
                restaurants_per_day = min(2, len(restaurants_list))

                start_index = (day_number - 1) * restaurants_per_day
                day_restaurants = restaurants_list[start_index : start_index + restaurants_per_day]

                meal_times = [
                    (14, 60, "Lunch"),  # 2 PM, 1 hour (after morning activities)
                    (19, 90, "Dinner"),  # 7 PM, 1.5 hours
                ]

                for i, restaurant in enumerate(day_restaurants):
                    if i >= len(meal_times):
                        break

                    hour, duration, meal_type = meal_times[i]

                    # Get restaurant data safely
                    restaurant_external_id = (
                        restaurant.external_id
                        if hasattr(restaurant, "external_id")
                        else restaurant["external_id"]
                    )
                    restaurant_name = (
                        restaurant.name if hasattr(restaurant, "name") else restaurant["name"]
                    )

                    # RestaurantOption doesn't have cuisine_type or price_range
                    # Use categories field instead
                    categories = (
                        restaurant.categories
                        if hasattr(restaurant, "categories")
                        else restaurant.get("categories", [])
                    )
                    # Extract cuisine type from categories (e.g., "catering.restaurant.italian" -> "Italian")
                    cuisine_str = (
                        categories[0].split('.')[-1].title() if categories
                        else "Restaurant"
                    )

                    # RestaurantOption doesn't have average_cost_per_person, use default
                    cost_per_person = Decimal("30.00")  # Default $30 per person for meals
                    total_cost = Decimal(str(cost_per_person)) * trip_request.requirements.travelers

                    items.append(
                        ItineraryItem(
                            item_id=f"meal_{restaurant_external_id}_{date}_{meal_type.lower()}",
                            item_type="restaurant",
                            name=f"{meal_type} at {restaurant_name}",
                            description=f"{meal_type} - {cuisine_str} cuisine",
                            start_time=datetime.combine(
                                date, datetime.min.time().replace(hour=hour)
                            ),
                            end_time=datetime.combine(date, datetime.min.time().replace(hour=hour))
                            + timedelta(minutes=duration),
                            duration_minutes=duration,
                            cost=total_cost,
                            latitude=restaurant.location.latitude
                            if hasattr(restaurant, "location")
                            else restaurant["location"]["latitude"],
                            longitude=restaurant.location.longitude
                            if hasattr(restaurant, "location")
                            else restaurant["location"]["longitude"],
                            booking_url=None,  # RestaurantOption doesn't have booking_url
                            address=restaurant.formatted_address if hasattr(restaurant, "formatted_address") else None,
                            booking_reference=None,
                            cancellation_policy=None,
                            special_instructions=None,
                        )
                    )

        except (TypeError, AttributeError):
            # Handle Mock objects or other non-iterable data
            return items

        return items

    def _is_travel_day(self, date: date, day_number: int, trip_request: TripPlanRequest) -> bool:
        """Check if this is primarily a travel day."""
        return day_number == 1 or date == trip_request.requirements.end_date

    def _extract_weather_for_date(self, date: date, agent_results: dict[str, Any]) -> str | None:
        """Extract weather summary for specific date."""
        if "weather" not in agent_results or agent_results["weather"]["status"] != "success":
            return None

        weather_data = agent_results["weather"]["data"]

        try:
            # Handle both dict and Pydantic model and Mock objects
            daily_forecast = None
            if isinstance(weather_data, dict):
                # Try different key names for forecast data
                if "daily_forecast" in weather_data:
                    daily_forecast = weather_data["daily_forecast"]
                elif "forecasts" in weather_data:
                    daily_forecast = weather_data["forecasts"]

            if not daily_forecast:
                return "Weather information unavailable"

            if daily_forecast:
                for forecast in daily_forecast:
                    if "date" in forecast:
                        # Handle both string and date comparison
                        forecast_date_str = forecast["date"]
                        if isinstance(forecast_date_str, str):
                            forecast_date = datetime.fromisoformat(forecast_date_str).date()
                        else:
                            forecast_date = forecast_date_str

                        if forecast_date == date:
                            # Handle different temperature field names
                            high_temp = forecast.get("high_temp") or forecast.get("temperature_high")
                            low_temp = forecast.get("low_temp") or forecast.get("temperature_low")
                            condition = forecast.get("condition", "Unknown")

                            return f"{condition.replace('_', ' ').title()} - High: {high_temp}°, Low: {low_temp}°"

        except (TypeError, AttributeError, ValueError):
            # Handle Mock objects or other non-iterable data
            return None

        return None

    async def _generate_meal_plan(self, daily_items: list["ItineraryItem"]) -> dict[str, str]:
        """Generate meal plan summary for the day."""
        meal_plan: dict[str, str] = {}

        for item in daily_items:
            if item.item_type == "restaurant":
                if "lunch" in item.name.lower():
                    meal_plan["lunch"] = item.name
                elif "dinner" in item.name.lower():
                    meal_plan["dinner"] = item.name
                elif "breakfast" in item.name.lower():
                    meal_plan["breakfast"] = item.name

        return meal_plan

    async def _calculate_total_cost(self, agent_results: dict[str, Any]) -> tuple[Decimal, str]:
        """Calculate total cost from all agent results with detailed breakdown."""
        total_cost = Decimal("0.00")
        currency = "USD"  # Default currency
        cost_breakdown: dict[str, Decimal] = {
            "flights": Decimal("0.00"),
            "hotels": Decimal("0.00"),
            "activities": Decimal("0.00"),
            "restaurants": Decimal("0.00"),
        }

        try:
            # Calculate flight costs
            if "flights" in agent_results and agent_results["flights"]["status"] == "success":
                flight_data = agent_results["flights"]["data"]

                # Handle both dict and Pydantic model
                flights_list = None
                if hasattr(flight_data, "flights"):  # Pydantic model
                    flights_list = flight_data.flights
                elif "flights" in flight_data:  # Dict
                    flights_list = flight_data["flights"]

                if flights_list:
                    for flight in flights_list:
                        price = (
                            flight.price
                            if hasattr(flight, "price")
                            else flight.get("price") if isinstance(flight, dict)
                            else Decimal("450.00")
                        )
                        flight_currency = (
                            getattr(flight, "currency", "USD")
                            if hasattr(flight, "currency")
                            else flight.get("currency", "USD") if isinstance(flight, dict)
                            else "USD"
                        )

                        cost_breakdown["flights"] += Decimal(str(price))
                        currency = flight_currency  # Use flight currency as primary

            # Calculate hotel costs
            if "hotels" in agent_results and agent_results["hotels"]["status"] == "success":
                hotel_data = agent_results["hotels"]["data"]

                # Handle both dict and Pydantic model
                hotels_list = None
                if hasattr(hotel_data, "hotels"):  # Pydantic model
                    hotels_list = hotel_data.hotels
                elif "hotels" in hotel_data:  # Dict
                    hotels_list = hotel_data["hotels"]

                if hotels_list:
                    for hotel in hotels_list:
                        # Calculate total hotel cost based on nights
                        nights = 1  # Default
                        price_per_night = (
                            hotel.price_per_night
                            if hasattr(hotel, "price_per_night")
                            else hotel.get("price_per_night") if isinstance(hotel, dict)
                            else Decimal("100.00")
                        )
                        hotel_currency = (
                            getattr(hotel, "currency", "USD")
                            if hasattr(hotel, "currency")
                            else hotel.get("currency", "USD") if isinstance(hotel, dict)
                            else "USD"
                        )

                        cost_breakdown["hotels"] += Decimal(str(price_per_night)) * nights
                        if not currency or currency == "USD":  # Update currency if needed
                            currency = hotel_currency

            # Calculate activity costs
            if "activities" in agent_results and agent_results["activities"]["status"] == "success":
                activity_data = agent_results["activities"]["data"]

                # Handle both dict and Pydantic model
                activities_list = None
                if hasattr(activity_data, "activities"):  # Pydantic model
                    activities_list = activity_data.activities
                elif "activities" in activity_data:  # Dict
                    activities_list = activity_data["activities"]

                if activities_list:
                    for activity in activities_list:
                        price = (
                            activity.price
                            if hasattr(activity, "price")
                            else activity.get("price") if isinstance(activity, dict)
                            else Decimal("25.00")
                        )
                        if price:
                            activity_currency = (
                                getattr(activity, "currency", "USD")
                                if hasattr(activity, "currency")
                                else activity.get("currency", "USD") if isinstance(activity, dict)
                                else "USD"
                            )
                            cost_breakdown["activities"] += Decimal(str(price))
                            if not currency or currency == "USD":
                                currency = activity_currency

            # Calculate restaurant costs (estimated from food agent)
            if (
                "restaurants" in agent_results
                and agent_results["restaurants"]["status"] == "success"
            ):
                restaurant_data = agent_results["restaurants"]["data"]

                # Handle both dict and Pydantic model
                restaurants_list = None
                if hasattr(restaurant_data, "restaurants"):  # Pydantic model
                    restaurants_list = restaurant_data.restaurants
                elif "restaurants" in restaurant_data:  # Dict
                    restaurants_list = restaurant_data["restaurants"]

                if restaurants_list:
                    for restaurant in restaurants_list:
                        # RestaurantOption doesn't have price_range, use default estimate
                        # In the future, could extract from categories or add field to model
                        estimated_cost_per_meal = Decimal("30.00")  # Default $30 per meal
                        cost_breakdown["restaurants"] += estimated_cost_per_meal

            # Sum total cost
            total_cost = Decimal(str(sum(cost_breakdown.values())))

            self.logger.info(
                f"Calculated trip cost breakdown: {cost_breakdown}, total: {total_cost} {currency}"
            )

        except Exception as e:
            self.logger.error(f"Error calculating total cost: {e}")
            # Return conservative estimate
            total_cost = Decimal("1000.00")  # Default estimate

        return total_cost, currency

    def _estimate_meal_cost(self, price_range: Any) -> Decimal:
        """Estimate meal cost based on price range."""
        # Handle both enum and string values
        if hasattr(price_range, "value"):
            price_str = price_range.value
        else:
            price_str = str(price_range)

        # Note: Price ranges not available in Geoapify, using general budget estimates
        cost_mapping = {
            "$": Decimal("15.00"),  # Budget
            "$$": Decimal("30.00"),  # Moderate
            "$$$": Decimal("60.00"),  # Expensive
            "$$$$": Decimal("100.00"),  # Very expensive
        }
        return cost_mapping.get(price_str, Decimal("30.00"))  # Default moderate

    async def _create_cost_breakdown(self, agent_results: dict[str, Any]) -> dict[str, Decimal]:
        """Create detailed cost breakdown from agent results."""
        cost_breakdown: dict[str, Decimal] = {
            "flights": Decimal("0.00"),
            "hotels": Decimal("0.00"),
            "activities": Decimal("0.00"),
            "restaurants": Decimal("0.00"),
        }

        try:
            # Extract flight costs
            if "flights" in agent_results and agent_results["flights"]["status"] == "success":
                flight_data = agent_results["flights"]["data"]
                if "flights" in flight_data:
                    for flight in flight_data["flights"]:
                        cost_breakdown["flights"] += Decimal(flight["price"])

            # Extract hotel costs
            if "hotels" in agent_results and agent_results["hotels"]["status"] == "success":
                hotel_data = agent_results["hotels"]["data"]
                if "hotels" in hotel_data:
                    for hotel in hotel_data["hotels"]:
                        # Calculate total hotel cost based on nights
                        nights = 1  # This should be calculated from stay duration
                        price_per_night = (
                            hotel.price_per_night
                            if hasattr(hotel, "price_per_night")
                            else hotel.get("price_per_night") if isinstance(hotel, dict)
                            else Decimal("100.00")
                        )
                        cost_breakdown["hotels"] += Decimal(str(price_per_night)) * nights

            # Extract activity costs
            if "activities" in agent_results and agent_results["activities"]["status"] == "success":
                activity_data = agent_results["activities"]["data"]
                if "activities" in activity_data:
                    for activity in activity_data["activities"]:
                        price = (
                            activity.price
                            if hasattr(activity, "price")
                            else activity.get("price") if isinstance(activity, dict)
                            else Decimal("25.00")
                        )
                        if price:
                            cost_breakdown["activities"] += Decimal(str(price))

            # Extract restaurant costs
            if (
                "restaurants" in agent_results
                and agent_results["restaurants"]["status"] == "success"
            ):
                restaurant_data = agent_results["restaurants"]["data"]
                if "restaurants" in restaurant_data:
                    for restaurant in restaurant_data["restaurants"]:
                        # RestaurantOption doesn't have price_range, use default
                        estimated_cost_per_meal = Decimal("30.00")
                        cost_breakdown["restaurants"] += estimated_cost_per_meal

        except Exception as e:
            self.logger.error(f"Error creating cost breakdown: {e}")

        return cost_breakdown

    async def _check_budget_status(self, total_cost: Decimal, budget: Decimal) -> str:
        """Check budget status with detailed analysis."""
        if total_cost <= budget * Decimal("0.9"):  # Within 90% of budget
            return "well_within_budget"
        elif total_cost <= budget:  # Within budget but close
            return "within_budget"
        elif total_cost <= budget * Decimal("1.1"):  # Up to 10% over
            return "slightly_over_budget"
        elif total_cost <= budget * Decimal("1.25"):  # Up to 25% over
            return "over_budget"
        else:  # More than 25% over
            return "significantly_over_budget"

    async def _validate_budget_allocation(
        self, cost_breakdown: dict[str, Decimal], budget: Decimal
    ) -> dict[str, Any]:
        """Validate budget allocation across categories with recommendations."""
        # Recommended budget allocation percentages
        recommended_allocation = {
            "flights": 0.35,  # 35% for flights
            "hotels": 0.30,  # 30% for accommodation
            "activities": 0.25,  # 25% for activities
            "restaurants": 0.10,  # 10% for dining
        }

        total_cost = sum(cost_breakdown.values())
        allocation_analysis: dict[str, Any] = {}
        warnings: list[str] = []

        for category, recommended_pct in recommended_allocation.items():
            category_cost = cost_breakdown.get(category, Decimal("0.00"))
            actual_pct = float(category_cost / total_cost) if total_cost > 0 else 0.0
            recommended_amount = budget * Decimal(str(recommended_pct))

            allocation_analysis[category] = {
                "actual_cost": category_cost,
                "actual_percentage": actual_pct,
                "recommended_percentage": recommended_pct,
                "recommended_amount": recommended_amount,
                "variance": category_cost - recommended_amount,
            }

            # Generate warnings for significant variances
            if abs(actual_pct - recommended_pct) > 0.15:  # More than 15% variance
                if actual_pct > recommended_pct:
                    warnings.append(
                        f"{category} allocation is {actual_pct:.1%} (recommended {recommended_pct:.1%}) - consider reducing costs"
                    )
                else:
                    warnings.append(
                        f"{category} allocation is only {actual_pct:.1%} (recommended {recommended_pct:.1%}) - consider increasing budget"
                    )

        return {
            "allocation_analysis": allocation_analysis,
            "warnings": warnings,
            "total_cost": total_cost,
            "budget_utilization": float(total_cost / budget) if budget > 0 else 0.0,
        }

    async def _detect_conflicts(
        self, itinerary: "TripItinerary", agent_results: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect timeline conflicts, booking conflicts, and impossible schedules."""
        conflicts: list[dict[str, Any]] = []

        try:
            # Check for timeline conflicts within each day
            for day in itinerary.days:
                daily_conflicts = await self._detect_daily_timeline_conflicts(day)
                conflicts.extend(daily_conflicts)

            # Check for inter-day conflicts (flight/hotel timing)
            flight_conflicts = await self._detect_flight_hotel_conflicts(itinerary, agent_results)
            conflicts.extend(flight_conflicts)

            # Check for impossible travel distances
            travel_conflicts = await self._detect_impossible_travel_conflicts(itinerary)
            conflicts.extend(travel_conflicts)

            # Check for availability conflicts
            availability_conflicts = await self._detect_availability_conflicts(
                itinerary, agent_results
            )
            conflicts.extend(availability_conflicts)

            # Check for budget conflicts
            budget_conflicts = await self._detect_budget_conflicts(itinerary, agent_results)
            conflicts.extend(budget_conflicts)

            if conflicts:
                self.logger.warning(f"Detected {len(conflicts)} conflicts in itinerary")
            else:
                self.logger.info("No conflicts detected in itinerary")

        except Exception as e:
            self.logger.error(f"Error detecting conflicts: {e}")
            conflicts.append(
                {
                    "type": "system_error",
                    "severity": "medium",
                    "description": f"Error during conflict detection: {e}",
                    "recommendation": "Manual review recommended",
                }
            )

        return conflicts

    async def _detect_daily_timeline_conflicts(self, day: "DailyItinerary") -> list[dict[str, Any]]:
        """Detect overlapping activities within a single day."""
        conflicts: list[dict[str, Any]] = []

        if len(day.items) < 2:
            return conflicts

        # Sort items by start time
        sorted_items = sorted(day.items, key=lambda x: x.start_time)

        for i in range(len(sorted_items) - 1):
            current_item = sorted_items[i]
            next_item = sorted_items[i + 1]

            # Check for overlapping times
            if current_item.end_time > next_item.start_time:
                overlap_minutes = int(
                    (current_item.end_time - next_item.start_time).total_seconds() / 60
                )
                conflicts.append(
                    {
                        "type": "timeline_overlap",
                        "severity": "high",
                        "date": day.date.isoformat(),
                        "description": f"{current_item.name} ends after {next_item.name} starts",
                        "items": [current_item.item_id, next_item.item_id],
                        "overlap_minutes": overlap_minutes,
                        "recommendation": f"Adjust timing or reduce duration by {overlap_minutes} minutes",
                    }
                )

            # Check for insufficient travel time between locations
            if (
                hasattr(current_item, "latitude")
                and hasattr(next_item, "latitude")
                and current_item.latitude is not None
                and current_item.longitude is not None
                and next_item.latitude is not None
                and next_item.longitude is not None
            ):
                travel_distance = self._calculate_distance(
                    current_item.latitude,
                    current_item.longitude,
                    next_item.latitude,
                    next_item.longitude,
                )

                # Assume average travel speed of 30 km/h in cities
                estimated_travel_minutes = int((travel_distance / 30) * 60)
                buffer_time = 15  # 15-minute buffer for transitions
                required_time = estimated_travel_minutes + buffer_time

                available_time = int(
                    (next_item.start_time - current_item.end_time).total_seconds() / 60
                )

                if available_time < required_time:
                    conflicts.append(
                        {
                            "type": "insufficient_travel_time",
                            "severity": "medium",
                            "date": day.date.isoformat(),
                            "description": f"Insufficient time to travel from {current_item.name} to {next_item.name}",
                            "items": [current_item.item_id, next_item.item_id],
                            "required_minutes": required_time,
                            "available_minutes": available_time,
                            "travel_distance_km": travel_distance,
                            "recommendation": f"Add {required_time - available_time} minutes between activities",
                        }
                    )

        return conflicts

    async def _detect_flight_hotel_conflicts(
        self, itinerary: "TripItinerary", agent_results: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect conflicts between flight times and hotel check-in/check-out."""
        conflicts: list[dict[str, Any]] = []

        if not itinerary.days:
            return conflicts

        first_day = itinerary.days[0]
        last_day = itinerary.days[-1]

        # Find flight and hotel items
        arrival_flights = [
            item
            for item in first_day.items
            if item.item_type == "flight" and "arrival" in item.name.lower()
        ]
        departure_flights = [
            item
            for item in last_day.items
            if item.item_type == "flight" and "departure" in item.name.lower()
        ]
        hotel_checkins = [
            item
            for item in first_day.items
            if item.item_type == "hotel" and "check-in" in item.name.lower()
        ]
        hotel_checkouts = [
            item
            for item in last_day.items
            if item.item_type == "hotel" and "check-out" in item.name.lower()
        ]

        # Check arrival flight vs hotel check-in
        for flight in arrival_flights:
            for checkin in hotel_checkins:
                # Standard hotel check-in is 3 PM (15:00)
                if flight.end_time.hour > 15:  # Late arrival
                    conflicts.append(
                        {
                            "type": "late_arrival_checkin",
                            "severity": "low",
                            "description": "Late flight arrival may affect hotel check-in",
                            "items": [flight.item_id, checkin.item_id],
                            "flight_arrival": flight.end_time.strftime("%H:%M"),
                            "checkin_time": checkin.start_time.strftime("%H:%M"),
                            "recommendation": "Confirm late check-in availability with hotel",
                        }
                    )

        # Check hotel checkout vs departure flight
        for checkout in hotel_checkouts:
            for flight in departure_flights:
                # Need at least 2 hours before domestic flights, 3 hours before international
                time_difference = (
                    flight.start_time - checkout.end_time
                ).total_seconds() / 3600  # hours
                if time_difference < 2:
                    conflicts.append(
                        {
                            "type": "tight_checkout_departure",
                            "severity": "high" if time_difference < 1 else "medium",
                            "description": "Insufficient time between hotel checkout and flight departure",
                            "items": [checkout.item_id, flight.item_id],
                            "available_hours": time_difference,
                            "recommendation": "Consider earlier checkout or later flight",
                        }
                    )

        return conflicts

    async def _detect_impossible_travel_conflicts(
        self, itinerary: "TripItinerary"
    ) -> list[dict[str, Any]]:
        """Detect travel times that are physically impossible."""
        conflicts: list[dict[str, Any]] = []

        for day in itinerary.days:
            items = sorted(day.items, key=lambda x: x.start_time)

            for i in range(len(items) - 1):
                current = items[i]
                next_item = items[i + 1]

                if not (
                    hasattr(current, "latitude")
                    and hasattr(next_item, "latitude")
                    and current.latitude is not None
                    and current.longitude is not None
                    and next_item.latitude is not None
                    and next_item.longitude is not None
                ):
                    continue

                distance = self._calculate_distance(
                    current.latitude, current.longitude, next_item.latitude, next_item.longitude
                )

                available_time_hours = (
                    next_item.start_time - current.end_time
                ).total_seconds() / 3600

                # Maximum reasonable speeds: 50 km/h average (including traffic, stops)
                max_reasonable_distance = available_time_hours * 50

                if distance > max_reasonable_distance:
                    conflicts.append(
                        {
                            "type": "impossible_travel_distance",
                            "severity": "critical",
                            "date": day.date.isoformat(),
                            "description": f"Cannot travel {distance:.1f}km in {available_time_hours:.1f} hours",
                            "items": [current.item_id, next_item.item_id],
                            "distance_km": distance,
                            "available_hours": available_time_hours,
                            "required_hours": distance / 30,  # Conservative 30 km/h
                            "recommendation": "Reschedule activities or choose closer alternatives",
                        }
                    )

        return conflicts

    async def _detect_availability_conflicts(
        self, itinerary: "TripItinerary", agent_results: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect conflicts with business hours and availability."""
        conflicts: list[dict[str, Any]] = []

        for day in itinerary.days:
            for item in day.items:
                # Check if activity is scheduled outside business hours
                if item.item_type in ["activity", "restaurant"]:
                    if item.start_time.hour < 8:  # Before 8 AM
                        conflicts.append(
                            {
                                "type": "early_schedule",
                                "severity": "medium",
                                "date": day.date.isoformat(),
                                "description": f"{item.name} scheduled before typical opening hours",
                                "item": item.item_id,
                                "scheduled_time": item.start_time.strftime("%H:%M"),
                                "recommendation": "Verify opening hours or reschedule",
                            }
                        )
                    elif item.start_time.hour > 22:  # After 10 PM
                        conflicts.append(
                            {
                                "type": "late_schedule",
                                "severity": "medium",
                                "date": day.date.isoformat(),
                                "description": f"{item.name} scheduled after typical closing hours",
                                "item": item.item_id,
                                "scheduled_time": item.start_time.strftime("%H:%M"),
                                "recommendation": "Verify availability or reschedule",
                            }
                        )

                # Check for unrealistic meal times
                if item.item_type == "restaurant":
                    hour = item.start_time.hour
                    if "breakfast" in item.name.lower() and (hour < 6 or hour > 11):
                        conflicts.append(
                            {
                                "type": "unrealistic_meal_time",
                                "severity": "low",
                                "date": day.date.isoformat(),
                                "description": f"Breakfast scheduled at {item.start_time.strftime('%H:%M')}",
                                "item": item.item_id,
                                "recommendation": "Adjust meal timing to typical hours",
                            }
                        )
                    elif "lunch" in item.name.lower() and (hour < 11 or hour > 15):
                        conflicts.append(
                            {
                                "type": "unrealistic_meal_time",
                                "severity": "low",
                                "date": day.date.isoformat(),
                                "description": f"Lunch scheduled at {item.start_time.strftime('%H:%M')}",
                                "item": item.item_id,
                                "recommendation": "Adjust meal timing to typical hours",
                            }
                        )
                    elif "dinner" in item.name.lower() and (hour < 17 or hour > 23):
                        conflicts.append(
                            {
                                "type": "unrealistic_meal_time",
                                "severity": "low",
                                "date": day.date.isoformat(),
                                "description": f"Dinner scheduled at {item.start_time.strftime('%H:%M')}",
                                "item": item.item_id,
                                "recommendation": "Adjust meal timing to typical hours",
                            }
                        )

        return conflicts

    async def _detect_budget_conflicts(
        self, itinerary: "TripItinerary", agent_results: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect budget-related conflicts and warnings."""
        conflicts: list[dict[str, Any]] = []

        # Check if total cost significantly exceeds budget
        if itinerary.budget_status in ["over_budget", "significantly_over_budget"]:
            conflicts.append(
                {
                    "type": "budget_exceeded",
                    "severity": "high"
                    if itinerary.budget_status == "significantly_over_budget"
                    else "medium",
                    "description": f"Trip cost exceeds budget - status: {itinerary.budget_status}",
                    "total_cost": float(itinerary.total_cost),
                    "currency": itinerary.currency,
                    "recommendation": "Consider reducing costs or increasing budget",
                }
            )

        # Check for days with disproportionate costs
        if itinerary.days:
            average_daily = itinerary.average_daily_cost

            for day in itinerary.days:
                if day.daily_cost > average_daily * Decimal("2.0"):  # More than 2x average
                    conflicts.append(
                        {
                            "type": "uneven_daily_budget",
                            "severity": "low",
                            "date": day.date.isoformat(),
                            "description": "Daily cost significantly higher than average",
                            "daily_cost": float(day.daily_cost),
                            "average_cost": float(average_daily),
                            "recommendation": "Consider redistributing activities across days",
                        }
                    )

        return conflicts

    async def _calculate_optimization_score(
        self, itinerary: "TripItinerary", agent_results: dict[str, Any]
    ) -> float:
        """Calculate optimization score based on travel distances, time efficiency, and cost."""
        if not itinerary.days:
            return 0.0

        total_score = 0.0
        total_days = len(itinerary.days)

        for day in itinerary.days:
            daily_score = await self._calculate_daily_optimization_score(day)
            total_score += daily_score

        # Average optimization score across all days
        return total_score / total_days if total_days > 0 else 0.0

    async def _calculate_daily_optimization_score(self, daily_itinerary: "DailyItinerary") -> float:
        """Calculate optimization score for a single day."""
        if not daily_itinerary.items:
            return 1.0  # Empty day is perfectly optimized

        # Get items with locations
        location_items = [
            item
            for item in daily_itinerary.items
            if item.latitude is not None and item.longitude is not None
        ]

        if len(location_items) < 2:
            return 1.0  # Single location or no locations is optimal

        # Calculate geographic optimization
        geo_score = await self._calculate_geographic_optimization(location_items)

        # Calculate time optimization (minimal gaps, logical sequencing)
        time_score = self._calculate_time_optimization(daily_itinerary.items)

        # Calculate cost efficiency (activities within reasonable budget)
        cost_score = self._calculate_cost_optimization(daily_itinerary)

        # Weighted average (geography 40%, time 40%, cost 20%)
        return (geo_score * 0.4) + (time_score * 0.4) + (cost_score * 0.2)

    async def _calculate_geographic_optimization(
        self, location_items: list["ItineraryItem"]
    ) -> float:
        """Calculate geographic optimization score based on travel distances."""
        if len(location_items) < 2:
            return 1.0

        total_distance = 0.0
        min_possible_distance = 0.0

        # Calculate actual travel distance (in order of schedule)
        sorted_items = sorted(location_items, key=lambda x: x.start_time)

        for i in range(len(sorted_items) - 1):
            current_item = sorted_items[i]
            next_item = sorted_items[i + 1]

            if (
                current_item.latitude is not None
                and current_item.longitude is not None
                and next_item.latitude is not None
                and next_item.longitude is not None
            ):
                distance = self._calculate_haversine_distance(
                    current_item.latitude,
                    current_item.longitude,
                    next_item.latitude,
                    next_item.longitude,
                )
                total_distance += distance

        # Calculate minimum possible distance (optimal order)
        optimal_distance = await self._calculate_optimal_route_distance(location_items)
        min_possible_distance = max(optimal_distance, 0.1)  # Avoid division by zero

        # Score is inverse of distance ratio (lower distance = higher score)
        if total_distance <= min_possible_distance:
            return 1.0

        return min(1.0, min_possible_distance / total_distance)

    async def _calculate_optimal_route_distance(
        self, location_items: list["ItineraryItem"]
    ) -> float:
        """Calculate optimal route distance using nearest neighbor approximation."""
        if len(location_items) < 2:
            return 0.0

        # Simple nearest neighbor algorithm for small numbers of locations
        items = location_items.copy()
        start_item = items.pop(0)
        current_item = start_item
        total_distance = 0.0

        while items:
            # Find nearest unvisited location
            nearest_item: ItineraryItem | None = None
            nearest_distance = float("inf")

            for item in items:
                if (
                    current_item.latitude is not None
                    and current_item.longitude is not None
                    and item.latitude is not None
                    and item.longitude is not None
                ):
                    distance = self._calculate_haversine_distance(
                        current_item.latitude, current_item.longitude, item.latitude, item.longitude
                    )
                    if distance < nearest_distance:
                        nearest_distance = distance
                        nearest_item = item

            if nearest_item:
                total_distance += nearest_distance
                current_item = nearest_item
                items.remove(nearest_item)

        return total_distance

    def _calculate_haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points using Haversine formula."""
        import math

        # Convert to radians
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # Earth's radius in kilometers
        r = 6371

        return c * r

    def _calculate_time_optimization(self, items: list["ItineraryItem"]) -> float:
        """Calculate time optimization score based on scheduling efficiency."""
        if not items:
            return 1.0

        sorted_items = sorted(items, key=lambda x: x.start_time)

        # Check for reasonable gaps between activities
        gap_penalty = 0.0
        overlap_penalty = 0.0

        for i in range(len(sorted_items) - 1):
            current_item = sorted_items[i]
            next_item = sorted_items[i + 1]

            gap_minutes = (next_item.start_time - current_item.end_time).total_seconds() / 60

            if gap_minutes < 0:
                # Overlapping activities - major penalty
                overlap_penalty += abs(gap_minutes) / 60  # Convert to hours
            elif gap_minutes > 180:  # More than 3 hours gap
                # Long gap - minor penalty
                gap_penalty += (gap_minutes - 180) / 1440  # Normalize by day length

        # Calculate score (1.0 is perfect, penalties reduce score)
        total_penalty = overlap_penalty + gap_penalty
        return max(0.0, 1.0 - (total_penalty * 0.1))

    def _calculate_cost_optimization(self, daily_itinerary: "DailyItinerary") -> float:
        """Calculate cost optimization score based on budget efficiency."""
        if daily_itinerary.daily_cost <= 0:
            return 1.0

        # Assume reasonable daily budget based on trip type
        # This is a simplified calculation - in real implementation,
        # this would use the actual budget allocation
        reasonable_daily_budget = Decimal("200.00")  # $200 per day baseline

        if daily_itinerary.daily_cost <= reasonable_daily_budget:
            return 1.0

        # Penalty for exceeding reasonable budget
        overage_ratio = float(daily_itinerary.daily_cost / reasonable_daily_budget)
        return max(0.0, 2.0 - overage_ratio)  # Score decreases as cost increases

    async def _optimize_daily_route(self, daily_itinerary: "DailyItinerary") -> "DailyItinerary":
        """Optimize the route for a daily itinerary to minimize travel time."""
        location_items = [
            item
            for item in daily_itinerary.items
            if item.latitude is not None
            and item.longitude is not None
            and item.item_type in ["activity", "restaurant"]
        ]

        if len(location_items) < 2:
            return daily_itinerary  # Nothing to optimize

        # Keep fixed items (flights, hotels) in their original positions
        fixed_items = [
            item
            for item in daily_itinerary.items
            if item.item_type in ["flight", "hotel"] or item.latitude is None
        ]

        # Optimize order of location-based items
        optimized_items = await self._optimize_item_order(location_items)

        # Reassign times to optimized items
        optimized_items = self._reassign_optimal_times(optimized_items)

        # Combine fixed and optimized items
        all_items = fixed_items + optimized_items
        all_items.sort(key=lambda x: x.start_time)

        # Update travel distances and times
        self._calculate_total_travel_distance(optimized_items)

        # Create new daily itinerary with optimized data
        return DailyItinerary(
            date=daily_itinerary.date,
            day_number=daily_itinerary.day_number,
            items=all_items,
            daily_cost=daily_itinerary.daily_cost,
            weather_summary=daily_itinerary.weather_summary,
            notes=daily_itinerary.notes,
            meal_plan=daily_itinerary.meal_plan,
        )

    async def _optimize_item_order(self, items: list["ItineraryItem"]) -> list["ItineraryItem"]:
        """Optimize order of items to minimize travel distance."""
        if len(items) <= 2:
            return items

        # Use nearest neighbor algorithm for route optimization
        optimized_items: list[ItineraryItem] = []
        remaining_items = items.copy()

        # Start with first item (could be improved by finding best starting point)
        current_item = remaining_items.pop(0)
        optimized_items.append(current_item)

        while remaining_items:
            # Find nearest unvisited location
            nearest_item: ItineraryItem | None = None
            nearest_distance = float("inf")

            for item in remaining_items:
                if (
                    current_item.latitude is not None
                    and current_item.longitude is not None
                    and item.latitude is not None
                    and item.longitude is not None
                ):
                    distance = self._calculate_haversine_distance(
                        current_item.latitude, current_item.longitude, item.latitude, item.longitude
                    )
                    if distance < nearest_distance:
                        nearest_distance = distance
                        nearest_item = item

            if nearest_item:
                optimized_items.append(nearest_item)
                remaining_items.remove(nearest_item)
                current_item = nearest_item

        return optimized_items

    def _reassign_optimal_times(self, items: list["ItineraryItem"]) -> list["ItineraryItem"]:
        """Reassign times to items based on optimal order."""
        if not items:
            return items

        # Start at 9 AM for activities
        current_time = datetime.combine(
            items[0].start_time.date(), datetime.min.time().replace(hour=9)
        )

        for item in items:
            travel_time = 30 if item != items[0] else 0  # 30 minutes travel between locations

            item.start_time = current_time + timedelta(minutes=travel_time)
            if item.duration_minutes:
                item.end_time = item.start_time + timedelta(minutes=item.duration_minutes)
                current_time = item.end_time

        return items

    def _calculate_total_travel_distance(self, items: list["ItineraryItem"]) -> float:
        """Calculate total travel distance for ordered items."""
        if len(items) < 2:
            return 0.0

        total_distance = 0.0

        for i in range(len(items) - 1):
            current_item = items[i]
            next_item = items[i + 1]

            if (
                current_item.latitude is not None
                and current_item.longitude is not None
                and next_item.latitude is not None
                and next_item.longitude is not None
            ):
                distance = self._calculate_haversine_distance(
                    current_item.latitude,
                    current_item.longitude,
                    next_item.latitude,
                    next_item.longitude,
                )
                total_distance += distance

        return total_distance

    # Export Functionality Methods (Task 7)

    async def export_itinerary(
        self,
        itinerary: "TripItinerary",
        format_type: str = "json",
        trip_request: TripPlanRequest | None = None,
    ) -> dict[str, Any]:
        """Export itinerary in specified format (JSON, PDF, iCalendar)."""
        try:
            # Create comprehensive trip summary
            trip_summary = await self._create_trip_summary(itinerary, trip_request)

            if format_type.lower() == "json":
                return await self._export_json(trip_summary)
            elif format_type.lower() == "pdf":
                return await self._export_pdf(trip_summary)
            elif format_type.lower() in ["icalendar", "ical", "ics"]:
                return await self._export_icalendar(trip_summary)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")

        except Exception as e:
            self.logger.error(f"Export failed for format {format_type}: {e}")
            raise ExternalAPIError(f"Export failed: {e}") from e

    async def _create_trip_summary(
        self, itinerary: "TripItinerary", trip_request: TripPlanRequest | None = None
    ) -> "TripSummary":
        """Create comprehensive trip summary for export."""
        # Extract basic trip information
        trip_name = "My Trip"
        destination = "Unknown"
        travelers = 1
        start_date = itinerary.days[0].date if itinerary.days else date.today()
        end_date = itinerary.days[-1].date if itinerary.days else date.today()

        if trip_request:
            trip_name = f"Trip to {trip_request.destination.city}"
            destination = f"{trip_request.destination.city}, {trip_request.destination.country}"
            travelers = trip_request.requirements.travelers
            start_date = trip_request.requirements.start_date
            end_date = trip_request.requirements.end_date

        # Generate cost breakdown
        cost_breakdown = self._generate_cost_breakdown_for_export(itinerary)

        # Extract confirmation numbers
        confirmations = self._extract_confirmation_numbers(itinerary)

        # Create emergency contacts placeholder
        emergency_contacts = [
            {"type": "local_police", "number": "911", "description": "Emergency services"},
            {
                "type": "embassy",
                "number": "Contact local embassy",
                "description": "For passport/visa issues",
            },
        ]

        return TripSummary(
            trip_id=itinerary.trip_id,
            trip_name=trip_name,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            total_days=itinerary.total_days,
            travelers=travelers,
            itinerary=itinerary,
            cost_breakdown=cost_breakdown,
            total_cost=itinerary.total_cost,
            currency=itinerary.currency,
            budget_original=trip_request.requirements.budget if trip_request else None,
            budget_remaining=None,
            flight_confirmations=confirmations["flights"],
            hotel_confirmations=confirmations["hotels"],
            activity_bookings=confirmations["activities"],
            emergency_contacts=emergency_contacts,
            generated_at=datetime.now(),
            export_format="multiple",
            qr_code_data=None,
        )

    def _generate_cost_breakdown_for_export(self, itinerary: "TripItinerary") -> dict[str, Decimal]:
        """Generate cost breakdown by category for export."""
        breakdown: dict[str, Decimal] = {
            "flights": Decimal("0.00"),
            "hotels": Decimal("0.00"),
            "activities": Decimal("0.00"),
            "restaurants": Decimal("0.00"),
            "other": Decimal("0.00"),
        }

        for day in itinerary.days:
            for item in day.items:
                category = item.item_type.lower()
                if category == "restaurant":
                    category = "restaurants"
                elif category == "activity":
                    category = "activities"
                elif category not in breakdown:
                    category = "other"

                if item.cost:
                    breakdown[category] += item.cost

        return breakdown

    def _extract_confirmation_numbers(self, itinerary: "TripItinerary") -> dict[str, list[str]]:
        """Extract booking confirmation numbers from itinerary items."""
        confirmations: dict[str, list[str]] = {"flights": [], "hotels": [], "activities": []}

        for day in itinerary.days:
            for item in day.items:
                if item.booking_reference:
                    category = item.item_type.lower()
                    if category == "flight":
                        confirmations["flights"].append(item.booking_reference)
                    elif category == "hotel":
                        confirmations["hotels"].append(item.booking_reference)
                    elif category in ["activity", "restaurant"]:
                        confirmations["activities"].append(item.booking_reference)

        return confirmations

    async def _export_json(self, trip_summary: "TripSummary") -> dict[str, Any]:
        """Export trip summary as JSON."""
        # Update export format
        trip_summary.export_format = "json"

        # Convert to dictionary with proper serialization
        json_data = trip_summary.model_dump(mode="json")

        # Add metadata
        export_result = {
            "format": "json",
            "generated_at": datetime.now().isoformat(),
            "version": "1.0",
            "data": json_data,
        }

        self.logger.info(f"Exported itinerary as JSON: {len(str(json_data))} characters")
        return export_result

    async def _export_pdf(self, trip_summary: "TripSummary") -> dict[str, Any]:
        """Export trip summary as PDF (placeholder implementation)."""
        # Update export format
        trip_summary.export_format = "pdf"

        # This would typically use a PDF library like reportlab or weasyprint
        # For now, return a structured representation that could be converted to PDF
        pdf_structure = {
            "title": f"{trip_summary.trip_name}",
            "subtitle": f"{trip_summary.destination} • {trip_summary.start_date} to {trip_summary.end_date}",
            "sections": [
                {
                    "name": "Trip Overview",
                    "content": {
                        "travelers": trip_summary.travelers,
                        "duration": f"{trip_summary.total_days} days",
                        "total_cost": f"{trip_summary.total_cost} {trip_summary.currency}",
                        "generated": trip_summary.generated_at.strftime("%Y-%m-%d %H:%M"),
                    },
                },
                {
                    "name": "Daily Itinerary",
                    "content": [
                        {
                            "date": day.date.strftime("%A, %B %d, %Y"),
                            "day_number": day.day_number,
                            "activities": [
                                {
                                    "time": f"{item.start_time.strftime('%H:%M')} - {item.end_time.strftime('%H:%M')}",
                                    "name": item.name,
                                    "type": item.item_type.title(),
                                    "cost": f"{item.cost} {trip_summary.currency}",
                                    "description": item.description or "",
                                    "address": item.address or "",
                                    "booking_ref": item.booking_reference or "",
                                }
                                for item in day.items
                            ],
                            "daily_cost": f"{day.daily_cost} {trip_summary.currency}",
                        }
                        for day in trip_summary.itinerary.days
                    ],
                },
                {
                    "name": "Cost Breakdown",
                    "content": {
                        category: f"{cost} {trip_summary.currency}"
                        for category, cost in trip_summary.cost_breakdown.items()
                    },
                },
                {
                    "name": "Booking References",
                    "content": {
                        "flights": trip_summary.flight_confirmations,
                        "hotels": trip_summary.hotel_confirmations,
                        "activities": trip_summary.activity_bookings,
                    },
                },
                {"name": "Emergency Contacts", "content": trip_summary.emergency_contacts},
            ],
        }

        export_result = {
            "format": "pdf",
            "generated_at": datetime.now().isoformat(),
            "version": "1.0",
            "pdf_structure": pdf_structure,
            "note": "PDF structure ready for conversion using PDF library (reportlab/weasyprint)",
        }

        self.logger.info(
            f"Exported itinerary as PDF structure with {len(pdf_structure['sections'])} sections"
        )
        return export_result

    async def _export_icalendar(self, trip_summary: "TripSummary") -> dict[str, Any]:
        """Export trip summary as iCalendar format."""
        # Update export format
        trip_summary.export_format = "icalendar"

        # Generate iCalendar content (RFC 5545 format)
        icalendar_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Travel Companion//Itinerary Agent//EN",
            f"X-WR-CALNAME:{trip_summary.trip_name}",
            f"X-WR-CALDESC:Complete itinerary for {trip_summary.destination}",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
        ]

        # Add events for each itinerary item
        for day in trip_summary.itinerary.days:
            for item in day.items:
                event_uid = f"{item.item_id}@travelcompanion.com"

                # Format dates for iCalendar (YYYYMMDDTHHMMSSZ format)
                start_time = item.start_time.strftime("%Y%m%dT%H%M%S")
                end_time = item.end_time.strftime("%Y%m%dT%H%M%S")
                created_time = datetime.now().strftime("%Y%m%dT%H%M%SZ")

                event_lines = [
                    "BEGIN:VEVENT",
                    f"UID:{event_uid}",
                    f"DTSTART:{start_time}",
                    f"DTEND:{end_time}",
                    f"DTSTAMP:{created_time}",
                    f"SUMMARY:{item.name}",
                    f"DESCRIPTION:{item.description or item.item_type.title()} - {item.cost} {trip_summary.currency}",
                    f"LOCATION:{item.address or 'Location TBD'}",
                    f"CATEGORIES:{item.item_type.upper()}",
                    "STATUS:CONFIRMED",
                ]

                # Add booking reference if available
                if item.booking_reference:
                    event_lines.append(f"X-BOOKING-REF:{item.booking_reference}")

                # Add cost information
                if item.cost:
                    event_lines.append(f"X-COST:{item.cost} {trip_summary.currency}")

                event_lines.append("END:VEVENT")
                icalendar_lines.extend(event_lines)

        icalendar_lines.append("END:VCALENDAR")

        # Join all lines with CRLF as per iCalendar spec
        icalendar_content = "\r\n".join(icalendar_lines)

        export_result = {
            "format": "icalendar",
            "generated_at": datetime.now().isoformat(),
            "version": "1.0",
            "icalendar_content": icalendar_content,
            "filename": f"{trip_summary.trip_name.replace(' ', '_').lower()}_itinerary.ics",
            "mime_type": "text/calendar",
        }

        self.logger.info(f"Exported itinerary as iCalendar: {len(icalendar_content)} characters")
        return export_result

    async def generate_qr_code_data(self, itinerary: "TripItinerary") -> str:
        """Generate QR code data for quick itinerary access."""
        # Create a simplified itinerary summary for QR code
        qr_data = {
            "trip_id": itinerary.trip_id,
            "destination": "Trip Itinerary",
            "days": len(itinerary.days),
            "total_cost": float(itinerary.total_cost),
            "currency": itinerary.currency,
            "generated": datetime.now().isoformat(),
        }

        import json

        return json.dumps(qr_data, separators=(",", ":"))  # Compact JSON

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula."""
        return self._calculate_haversine_distance(lat1, lon1, lat2, lon2)

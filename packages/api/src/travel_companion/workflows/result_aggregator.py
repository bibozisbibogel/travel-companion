"""Agent result aggregation and correlation for comprehensive trip planning."""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

from ..models.external import ActivityOption, FlightOption, HotelOption, RestaurantOption
from ..utils.logging import workflow_logger
from .orchestrator import TripPlanningWorkflowState


class CorrelationStrength(str, Enum):
    """Strength of correlation between agent results."""

    STRONG = "strong"  # Direct dependency or high relevance
    MODERATE = "moderate"  # Indirect relationship or medium relevance
    WEAK = "weak"  # Low relevance or optional relationship
    NONE = "none"  # No meaningful relationship


class CorrelationType(str, Enum):
    """Type of correlation between results."""

    TEMPORAL = "temporal"  # Time-based relationships
    SPATIAL = "spatial"  # Location-based relationships
    BUDGET = "budget"  # Cost-based relationships
    PREFERENCE = "preference"  # User preference-based relationships
    LOGICAL = "logical"  # Logical dependencies (e.g., weather -> activities)


@dataclass
class ResultCorrelation:
    """Represents a correlation between agent results."""

    from_agent: str
    to_agent: str
    correlation_type: CorrelationType
    strength: CorrelationStrength
    score: float  # 0.0 to 1.0
    explanation: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedTripPlan:
    """Comprehensive aggregated trip plan with correlations."""

    trip_id: str
    destination: str
    start_date: datetime
    end_date: datetime
    total_travelers: int

    # Agent results
    flights: list[FlightOption] = field(default_factory=list)
    hotels: list[HotelOption] = field(default_factory=list)
    activities: list[ActivityOption] = field(default_factory=list)
    restaurants: list[RestaurantOption] = field(default_factory=list)
    weather_forecast: dict[str, Any] = field(default_factory=dict)

    # Aggregated insights
    total_estimated_cost: Decimal = Decimal("0.00")
    cost_breakdown: dict[str, Decimal] = field(default_factory=dict)
    daily_schedule: dict[str, dict[str, Any]] = field(default_factory=dict)
    correlations: list[ResultCorrelation] = field(default_factory=list)

    # Optimization metrics
    budget_utilization: float = 0.0
    schedule_density: float = 0.0
    preference_alignment: float = 0.0
    weather_consideration: float = 0.0

    # Quality scores
    overall_quality_score: float = 0.0
    completeness_score: float = 0.0
    coherence_score: float = 0.0

    @property
    def duration_days(self) -> int:
        """Calculate trip duration in days."""
        return (self.end_date - self.start_date).days + 1

    @property
    def average_daily_cost(self) -> Decimal:
        """Calculate average daily cost."""
        if self.duration_days == 0:
            return Decimal("0.00")
        return self.total_estimated_cost / self.duration_days


class AgentResultAggregator:
    """
    Aggregates and correlates results from multiple travel agents.

    Provides intelligent correlation analysis, cost optimization,
    temporal coordination, and quality scoring for trip planning results.
    """

    def __init__(self, state: TripPlanningWorkflowState):
        """
        Initialize result aggregator.

        Args:
            state: Current workflow state with agent results
        """
        self.state = state
        self.workflow_id = state["workflow_id"]
        self.request_id = state["request_id"]

        # Extract trip details
        self.trip_request = state["trip_request"]
        self.user_preferences = state.get("user_preferences", {})
        self.budget_tracking = state.get("budget_tracking", {})

        # Initialize aggregation data
        self.correlations: list[ResultCorrelation] = []
        self.quality_metrics: dict[str, float] = {}

    def aggregate_all_results(self) -> AggregatedTripPlan:
        """
        Aggregate all agent results into a comprehensive trip plan.

        Returns:
            Complete aggregated trip plan with correlations and insights
        """
        start_time = time.time()

        workflow_logger.log_coordination_started(
            workflow_id=self.workflow_id, request_id=self.request_id, total_agents=6
        )

        try:
            # Create base aggregated plan
            aggregated_plan = self._create_base_plan()

            # Extract and validate agent results
            self._extract_agent_results(aggregated_plan)

            # Calculate correlations between agent results
            self._calculate_result_correlations(aggregated_plan)

            # Perform cost analysis and optimization
            self._analyze_costs(aggregated_plan)

            # Create temporal coordination (daily schedules)
            self._create_temporal_coordination(aggregated_plan)

            # Calculate quality and optimization metrics
            self._calculate_quality_metrics(aggregated_plan)

            # Validate plan coherence
            self._validate_plan_coherence(aggregated_plan)

            aggregation_time_ms = (time.time() - start_time) * 1000

            workflow_logger.log_coordination_completed(
                workflow_id=self.workflow_id,
                request_id=self.request_id,
                execution_summary={
                    "aggregation_time_ms": aggregation_time_ms,
                    "total_correlations": len(aggregated_plan.correlations),
                    "quality_score": aggregated_plan.overall_quality_score,
                },
            )

            return aggregated_plan

        except Exception as e:
            aggregation_time_ms = (time.time() - start_time) * 1000

            workflow_logger.log_coordination_failed(
                workflow_id=self.workflow_id,
                request_id=self.request_id,
                error=str(e),
                execution_summary={"aggregation_failed": True, "error": str(e)},
            )

            raise

    def _create_base_plan(self) -> AggregatedTripPlan:
        """Create base aggregated trip plan structure."""
        trip_destination = self.trip_request.destination
        trip_requirements = self.trip_request.requirements

        trip_id = self.state.get("trip_id")
        if not trip_id:
            trip_id = f"trip_{self.workflow_id[:8]}"

        return AggregatedTripPlan(
            trip_id=trip_id,
            destination=trip_destination.city,
            start_date=datetime.combine(trip_requirements.start_date, datetime.min.time()),
            end_date=datetime.combine(trip_requirements.end_date, datetime.min.time()),
            total_travelers=trip_requirements.travelers,
        )

    def _extract_agent_results(self, plan: AggregatedTripPlan) -> None:
        """Extract and validate results from all agents."""
        # Extract flight results
        flight_results = self.state.get("flight_results", [])
        if flight_results:
            plan.flights = flight_results[:5]  # Top 5 flight options

        # Extract hotel results
        hotel_results = self.state.get("hotel_results", [])
        if hotel_results:
            plan.hotels = hotel_results[:5]  # Top 5 hotel options

        # Extract activity results
        activity_results = self.state.get("activity_results", [])
        if activity_results:
            plan.activities = activity_results[:10]  # Top 10 activities

        # Extract restaurant results
        food_results = self.state.get("food_recommendations", [])
        if food_results:
            # Convert food recommendations to RestaurantOption format
            plan.restaurants = [
                self._convert_food_to_restaurant(food_item)
                for food_item in food_results[:8]  # Top 8 restaurants
            ]

        # Extract weather data
        plan.weather_forecast = self.state.get("weather_data", {})

    def _convert_food_to_restaurant(self, food_item: dict[str, Any]) -> RestaurantOption:
        """Convert food recommendation to RestaurantOption."""
        from travel_companion.models.external import RestaurantLocation

        # Parse location data
        location_data = food_item.get("location", {})
        if isinstance(location_data, str):
            # If location is a string, create basic location
            location = RestaurantLocation(
                latitude=0.0,
                longitude=0.0,
                address=location_data,
                address_line2=None,
                city=None,
                state=None,
                country=None,
                postal_code=None,
                neighborhood=None,
            )
        elif isinstance(location_data, dict):
            location = RestaurantLocation(
                latitude=location_data.get("latitude", 0.0),
                longitude=location_data.get("longitude", 0.0),
                address=location_data.get("address"),
                address_line2=location_data.get("address_line2"),
                city=location_data.get("city"),
                state=location_data.get("state"),
                country=location_data.get("country"),
                postal_code=location_data.get("postal_code"),
                neighborhood=location_data.get("neighborhood"),
            )
        else:
            location = RestaurantLocation(
                latitude=0.0,
                longitude=0.0,
                address=None,
                address_line2=None,
                city=None,
                state=None,
                country=None,
                postal_code=None,
                neighborhood=None,
            )

        # Parse cuisine type as string category
        cuisine_str = food_item.get("cuisine", "International")
        categories = [cuisine_str.lower().replace(" ", "_")]

        return RestaurantOption(
            trip_id=None,  # Will be set later if needed
            external_id=food_item.get("id", "unknown"),
            name=food_item.get("name", "Restaurant"),
            categories=categories,
            location=location,
            formatted_address=food_item.get("address"),
            distance_meters=int(food_item.get("distance_km", 0) * 1000)
            if food_item.get("distance_km")
            else None,
            provider=food_item.get("provider", "legacy_conversion"),
        )

    def _calculate_result_correlations(self, plan: AggregatedTripPlan) -> None:
        """Calculate correlations between different agent results."""
        correlations = []

        # Flight-Hotel temporal correlations
        correlations.extend(self._correlate_flights_hotels(plan))

        # Weather-Activity correlations
        correlations.extend(self._correlate_weather_activities(plan))

        # Hotel-Activity spatial correlations
        correlations.extend(self._correlate_hotels_activities(plan))

        # Budget correlations across all agents
        correlations.extend(self._correlate_budget_options(plan))

        # Preference-based correlations
        correlations.extend(self._correlate_user_preferences(plan))

        plan.correlations = correlations

    def _correlate_flights_hotels(self, plan: AggregatedTripPlan) -> list[ResultCorrelation]:
        """Calculate temporal correlations between flights and hotels."""
        correlations = []

        for flight in plan.flights:
            for hotel in plan.hotels:
                # Check temporal alignment
                arrival_date = flight.arrival_time.date()
                checkin_date = plan.start_date.date()

                if arrival_date == checkin_date:
                    # Strong temporal correlation for same-day arrival
                    correlations.append(
                        ResultCorrelation(
                            from_agent="flight_agent",
                            to_agent="hotel_agent",
                            correlation_type=CorrelationType.TEMPORAL,
                            strength=CorrelationStrength.STRONG,
                            score=0.9,
                            explanation=f"Flight {flight.flight_number} arrives on hotel check-in date",
                            metadata={
                                "flight_id": str(flight.flight_id),
                                "hotel_name": hotel.name,
                                "arrival_time": flight.arrival_time.isoformat(),
                            },
                        )
                    )

        return correlations

    def _correlate_weather_activities(self, plan: AggregatedTripPlan) -> list[ResultCorrelation]:
        """Calculate correlations between weather forecast and activities."""
        correlations = []

        weather_forecast = plan.weather_forecast.get("forecast", {})
        daily_forecasts = weather_forecast.get("daily_forecasts", [])

        for activity in plan.activities:
            for i, daily_weather in enumerate(daily_forecasts[: plan.duration_days]):
                condition = daily_weather.get("condition", "unknown")

                # Determine correlation strength based on activity type and weather
                outdoor_activities = {"sightseeing", "tours", "outdoor", "adventure", "sports"}
                indoor_activities = {"museums", "galleries", "shopping", "dining", "cultural"}

                activity_category = getattr(activity, "category", "").lower()

                if any(outdoor in activity_category for outdoor in outdoor_activities):
                    if condition in ["clear", "sunny", "partly_cloudy"]:
                        strength = CorrelationStrength.STRONG
                        score = 0.9
                        explanation = f"Perfect weather for outdoor activity: {activity.name}"
                    elif condition in ["cloudy", "overcast"]:
                        strength = CorrelationStrength.MODERATE
                        score = 0.6
                        explanation = f"Acceptable weather for outdoor activity: {activity.name}"
                    else:
                        strength = CorrelationStrength.WEAK
                        score = 0.3
                        explanation = f"Poor weather for outdoor activity: {activity.name}"
                elif any(indoor in activity_category for indoor in indoor_activities):
                    if condition in ["rainy", "stormy", "heavy_rain"]:
                        strength = CorrelationStrength.STRONG
                        score = 0.8
                        explanation = f"Great indoor option for rainy weather: {activity.name}"
                    else:
                        strength = CorrelationStrength.MODERATE
                        score = 0.5
                        explanation = f"Good indoor activity option: {activity.name}"
                else:
                    strength = CorrelationStrength.WEAK
                    score = 0.4
                    explanation = f"Weather-neutral activity: {activity.name}"

                correlations.append(
                    ResultCorrelation(
                        from_agent="weather_agent",
                        to_agent="activity_agent",
                        correlation_type=CorrelationType.LOGICAL,
                        strength=strength,
                        score=score,
                        explanation=explanation,
                        metadata={
                            "activity_id": getattr(activity, "activity_id", "unknown"),
                            "day": i + 1,
                            "weather_condition": condition,
                            "activity_category": activity_category,
                        },
                    )
                )

        return correlations

    def _correlate_hotels_activities(self, plan: AggregatedTripPlan) -> list[ResultCorrelation]:
        """Calculate spatial correlations between hotels and activities."""
        correlations = []

        for hotel in plan.hotels:
            for activity in plan.activities:
                # Calculate spatial correlation based on location proximity
                hotel_location = hotel.address if hasattr(hotel, "address") else hotel.name
                activity_location = getattr(activity, "location", "unknown")

                # Simple text-based proximity check (in real implementation, use geocoding)
                if hotel_location and activity_location:
                    if (
                        hotel_location.lower() in activity_location.lower()
                        or activity_location.lower() in hotel_location.lower()
                    ):
                        strength = CorrelationStrength.STRONG
                        score = 0.8
                        explanation = f"Hotel {hotel.name} is near activity {activity.name}"
                    else:
                        # Check for common location terms
                        hotel_terms = set(hotel_location.lower().split())
                        activity_terms = set(activity_location.lower().split())
                        common_terms = hotel_terms.intersection(activity_terms)

                        if common_terms:
                            strength = CorrelationStrength.MODERATE
                            score = 0.6
                            explanation = f"Hotel and activity share location terms: {', '.join(common_terms)}"
                        else:
                            strength = CorrelationStrength.WEAK
                            score = 0.3
                            explanation = "Hotel and activity in same destination"

                    correlations.append(
                        ResultCorrelation(
                            from_agent="hotel_agent",
                            to_agent="activity_agent",
                            correlation_type=CorrelationType.SPATIAL,
                            strength=strength,
                            score=score,
                            explanation=explanation,
                            metadata={
                                "hotel_name": hotel.name,
                                "activity_name": activity.name,
                                "hotel_location": hotel_location,
                                "activity_location": activity_location,
                            },
                        )
                    )

        return correlations

    def _correlate_budget_options(self, plan: AggregatedTripPlan) -> list[ResultCorrelation]:
        """Calculate budget-based correlations across all options."""
        correlations = []

        budget_allocation = self.budget_tracking.get("allocations", {})
        flight_budget = budget_allocation.get("flights", 0)
        budget_allocation.get("hotels", 0)

        # Flight budget correlations
        if plan.flights and flight_budget > 0:
            for flight in plan.flights:
                budget_ratio = float(flight.price) / flight_budget

                if budget_ratio <= 0.8:
                    strength = CorrelationStrength.STRONG
                    score = 0.9
                    explanation = f"Flight within budget ({budget_ratio:.1%} of allocation)"
                elif budget_ratio <= 1.0:
                    strength = CorrelationStrength.MODERATE
                    score = 0.7
                    explanation = f"Flight at budget limit ({budget_ratio:.1%} of allocation)"
                else:
                    strength = CorrelationStrength.WEAK
                    score = 0.3
                    explanation = f"Flight over budget ({budget_ratio:.1%} of allocation)"

                correlations.append(
                    ResultCorrelation(
                        from_agent="flight_agent",
                        to_agent="budget_tracker",
                        correlation_type=CorrelationType.BUDGET,
                        strength=strength,
                        score=score,
                        explanation=explanation,
                        metadata={
                            "flight_price": float(flight.price),
                            "budget_allocation": flight_budget,
                            "budget_ratio": budget_ratio,
                        },
                    )
                )

        return correlations

    def _correlate_user_preferences(self, plan: AggregatedTripPlan) -> list[ResultCorrelation]:
        """Calculate preference-based correlations."""
        correlations = []

        preferences = self.trip_request.preferences or {}

        # Activity preferences
        preferred_activities = preferences.get("activity_types", [])
        if preferred_activities and isinstance(preferred_activities, list | tuple):
            for activity in plan.activities:
                activity_category = getattr(activity, "category", "").lower()

                preference_match = any(
                    pref.lower() in activity_category or activity_category in pref.lower()
                    for pref in preferred_activities
                    if isinstance(pref, str)
                )

                if preference_match:
                    correlations.append(
                        ResultCorrelation(
                            from_agent="activity_agent",
                            to_agent="user_preferences",
                            correlation_type=CorrelationType.PREFERENCE,
                            strength=CorrelationStrength.STRONG,
                            score=0.9,
                            explanation=f"Activity matches user preferences: {activity.name}",
                            metadata={
                                "activity_category": activity_category,
                                "preferred_types": preferred_activities,
                                "match": True,
                            },
                        )
                    )

        # Cuisine preferences
        preferred_cuisines = preferences.get("cuisine_types", [])
        if preferred_cuisines and isinstance(preferred_cuisines, list | tuple):
            for restaurant in plan.restaurants:
                cuisine_match = any(
                    any(cuisine.lower() in cat.lower() for cat in restaurant.categories)
                    or any(cat.lower() in cuisine.lower() for cat in restaurant.categories)
                    for cuisine in preferred_cuisines
                    if isinstance(cuisine, str)
                )

                if cuisine_match:
                    correlations.append(
                        ResultCorrelation(
                            from_agent="food_agent",
                            to_agent="user_preferences",
                            correlation_type=CorrelationType.PREFERENCE,
                            strength=CorrelationStrength.STRONG,
                            score=0.85,
                            explanation=f"Restaurant matches cuisine preferences: {restaurant.name}",
                            metadata={
                                "restaurant_cuisine": ", ".join(restaurant.categories),
                                "preferred_cuisines": preferred_cuisines,
                                "match": True,
                            },
                        )
                    )

        return correlations

    def _analyze_costs(self, plan: AggregatedTripPlan) -> None:
        """Analyze and optimize costs across all options."""
        cost_breakdown = {}

        # Flight costs
        if plan.flights:
            cheapest_flight = min(plan.flights, key=lambda f: f.price)
            cost_breakdown["flights"] = cheapest_flight.price

        # Hotel costs (per night * duration)
        if plan.hotels:
            cheapest_hotel = min(plan.hotels, key=lambda h: h.price_per_night)
            cost_breakdown["hotels"] = cheapest_hotel.price_per_night * plan.duration_days

        # Activity costs (estimated)
        activity_costs = []
        for activity in plan.activities:
            if hasattr(activity, "price") and activity.price:
                activity_costs.append(activity.price)
            else:
                # Estimate based on category
                estimated_cost = self._estimate_activity_cost(activity)
                activity_costs.append(estimated_cost)

        if activity_costs:
            # Select top 3-4 activities within budget
            cost_breakdown["activities"] = Decimal(str(sum(sorted(activity_costs)[:4])))

        # Restaurant costs (estimated per day)
        if plan.restaurants:
            daily_food_cost = (
                Decimal("50.00") * plan.total_travelers
            )  # Estimate $50 per person per day
            cost_breakdown["food"] = daily_food_cost * plan.duration_days

        # Calculate totals
        plan.cost_breakdown = cost_breakdown
        plan.total_estimated_cost = Decimal(str(sum(cost_breakdown.values())))

        # Calculate budget utilization
        original_budget = float(self.trip_request.requirements.budget)
        if original_budget > 0:
            plan.budget_utilization = float(plan.total_estimated_cost) / original_budget

    def _create_temporal_coordination(self, plan: AggregatedTripPlan) -> None:
        """Create coordinated daily schedules."""
        daily_schedule = {}

        # Create schedule for each day
        current_date = plan.start_date.date()
        for day in range(plan.duration_days):
            day_key = f"day_{day + 1}"
            day_date = current_date + timedelta(days=day)

            day_activities = []

            # Add flight information for arrival/departure days
            if day == 0 and plan.flights:  # Arrival day
                arrival_flight = min(plan.flights, key=lambda f: f.arrival_time)
                day_activities.append(
                    {
                        "type": "transport",
                        "activity": "Flight Arrival",
                        "time": arrival_flight.arrival_time.strftime("%H:%M"),
                        "details": f"{arrival_flight.airline} {arrival_flight.flight_number}",
                        "duration_hours": 0.5,
                    }
                )

            if day == plan.duration_days - 1 and plan.flights:  # Departure day
                departure_flight = min(plan.flights, key=lambda f: f.departure_time)
                day_activities.append(
                    {
                        "type": "transport",
                        "activity": "Flight Departure",
                        "time": departure_flight.departure_time.strftime("%H:%M"),
                        "details": f"{departure_flight.airline} {departure_flight.flight_number}",
                        "duration_hours": 0.5,
                    }
                )

            # Add weather-appropriate activities
            weather_forecast = plan.weather_forecast.get("forecast", {})
            daily_forecasts = weather_forecast.get("daily_forecasts", [])

            if day < len(daily_forecasts):
                day_weather = daily_forecasts[day]
                weather_condition = day_weather.get("condition", "unknown")

                # Filter activities based on weather
                suitable_activities = self._get_weather_suitable_activities(
                    plan.activities, weather_condition
                )

                # Add 2-3 activities per day
                for i, activity in enumerate(suitable_activities[:3]):
                    activity_time = f"{9 + i * 3:02d}:00"  # Space activities 3 hours apart
                    day_activities.append(
                        {
                            "type": "activity",
                            "activity": activity.name,
                            "time": activity_time,
                            "details": activity.description
                            if hasattr(activity, "description")
                            else "",
                            "duration_hours": getattr(activity, "duration_hours", 2.0),
                            "category": getattr(activity, "category", "general"),
                        }
                    )

            # Add meal recommendations
            if plan.restaurants:
                # Add lunch and dinner
                lunch_restaurant = plan.restaurants[day % len(plan.restaurants)]
                dinner_restaurant = plan.restaurants[(day + 1) % len(plan.restaurants)]

                day_activities.extend(
                    [
                        {
                            "type": "dining",
                            "activity": f"Lunch at {lunch_restaurant.name}",
                            "time": "12:30",
                            "details": f"{', '.join(lunch_restaurant.categories)} cuisine",
                            "duration_hours": 1.5,
                            "price_range": "varies",  # Price range not available in current model
                        },
                        {
                            "type": "dining",
                            "activity": f"Dinner at {dinner_restaurant.name}",
                            "time": "19:00",
                            "details": f"{', '.join(dinner_restaurant.categories)} cuisine",
                            "duration_hours": 2.0,
                            "price_range": "varies",  # Price range not available in current model
                        },
                    ]
                )

            # Sort activities by time
            day_activities.sort(key=lambda x: str(x.get("time", "00:00")))
            daily_schedule[day_key] = {
                "date": day_date.isoformat(),
                "weather": daily_forecasts[day] if day < len(daily_forecasts) else {},
                "activities": day_activities,
                "total_activities": len(day_activities),
            }

        plan.daily_schedule = daily_schedule

    def _calculate_quality_metrics(self, plan: AggregatedTripPlan) -> None:
        """Calculate comprehensive quality metrics for the trip plan."""
        # Completeness score (all agents have results)
        agent_results = {
            "flights": len(plan.flights) > 0,
            "hotels": len(plan.hotels) > 0,
            "activities": len(plan.activities) > 0,
            "restaurants": len(plan.restaurants) > 0,
            "weather": bool(plan.weather_forecast),
        }

        plan.completeness_score = sum(agent_results.values()) / len(agent_results)

        # Coherence score (correlation strength average)
        if plan.correlations:
            correlation_scores = [corr.score for corr in plan.correlations]
            plan.coherence_score = sum(correlation_scores) / len(correlation_scores)
        else:
            plan.coherence_score = 0.0

        # Preference alignment score
        preference_correlations = [
            corr
            for corr in plan.correlations
            if corr.correlation_type == CorrelationType.PREFERENCE
        ]

        if preference_correlations:
            preference_scores = [corr.score for corr in preference_correlations]
            plan.preference_alignment = sum(preference_scores) / len(preference_scores)
        else:
            plan.preference_alignment = 0.5  # Neutral if no preferences

        # Weather consideration score
        weather_correlations = [
            corr
            for corr in plan.correlations
            if corr.correlation_type == CorrelationType.LOGICAL
            and corr.from_agent == "weather_agent"
        ]

        if weather_correlations:
            weather_scores = [corr.score for corr in weather_correlations]
            plan.weather_consideration = sum(weather_scores) / len(weather_scores)
        else:
            plan.weather_consideration = 0.5  # Neutral if no weather data

        # Schedule density (activities per day)
        if plan.daily_schedule:
            daily_activity_counts = [
                day_data["total_activities"] for day_data in plan.daily_schedule.values()
            ]
            average_activities_per_day = sum(daily_activity_counts) / len(daily_activity_counts)
            plan.schedule_density = min(
                average_activities_per_day / 6.0, 1.0
            )  # Max 6 activities per day

        # Overall quality score (weighted average)
        weights = {
            "completeness": 0.3,
            "coherence": 0.25,
            "preference_alignment": 0.2,
            "weather_consideration": 0.15,
            "schedule_density": 0.1,
        }

        plan.overall_quality_score = (
            plan.completeness_score * weights["completeness"]
            + plan.coherence_score * weights["coherence"]
            + plan.preference_alignment * weights["preference_alignment"]
            + plan.weather_consideration * weights["weather_consideration"]
            + plan.schedule_density * weights["schedule_density"]
        )

    def _validate_plan_coherence(self, plan: AggregatedTripPlan) -> None:
        """Validate overall plan coherence and flag potential issues."""
        issues = []

        # Check budget coherence
        if plan.budget_utilization > 1.2:
            issues.append("Plan significantly exceeds budget")
        elif plan.budget_utilization < 0.5:
            issues.append("Plan underutilizes budget - consider upgrades")

        # Check temporal coherence
        if not plan.daily_schedule:
            issues.append("No daily schedule created")

        # Check correlation coherence
        weak_correlations = [
            corr
            for corr in plan.correlations
            if corr.strength == CorrelationStrength.WEAK and corr.score < 0.3
        ]

        if len(weak_correlations) > len(plan.correlations) * 0.5:
            issues.append("Many weak correlations - plan may lack coherence")

        # Log issues if any
        if issues:
            workflow_logger.log_plan_coherence_issues(
                workflow_id=self.workflow_id,
                issues=issues,
                severity="warning" if plan.overall_quality_score < 0.5 else "info",
            )

    def _get_weather_suitable_activities(
        self, activities: list[ActivityOption], weather_condition: str
    ) -> list[ActivityOption]:
        """Filter activities based on weather suitability."""
        outdoor_friendly = ["clear", "sunny", "partly_cloudy", "cloudy"]
        indoor_preferred = ["rainy", "stormy", "heavy_rain", "snow", "heavy_snow"]

        if weather_condition in outdoor_friendly:
            # Prioritize outdoor activities
            return sorted(activities, key=lambda a: self._get_outdoor_score(a), reverse=True)
        elif weather_condition in indoor_preferred:
            # Prioritize indoor activities
            return sorted(activities, key=lambda a: self._get_indoor_score(a), reverse=True)
        else:
            # Neutral weather - return as is
            return activities

    def _get_outdoor_score(self, activity: ActivityOption) -> float:
        """Get outdoor suitability score for an activity."""
        outdoor_keywords = {"outdoor", "tour", "sightseeing", "walk", "park", "garden", "monument"}
        activity_text = (
            f"{getattr(activity, 'name', '')} {getattr(activity, 'category', '')}".lower()
        )

        return sum(1 for keyword in outdoor_keywords if keyword in activity_text)

    def _get_indoor_score(self, activity: ActivityOption) -> float:
        """Get indoor suitability score for an activity."""
        indoor_keywords = {
            "museum",
            "gallery",
            "shopping",
            "theater",
            "cinema",
            "indoor",
            "cultural",
        }
        activity_text = (
            f"{getattr(activity, 'name', '')} {getattr(activity, 'category', '')}".lower()
        )

        return sum(1 for keyword in indoor_keywords if keyword in activity_text)

    def _estimate_activity_cost(self, activity: ActivityOption) -> Decimal:
        """Estimate cost for an activity based on category."""
        category = getattr(activity, "category", "general").lower()

        cost_estimates = {
            "museum": Decimal("15.00"),
            "tour": Decimal("40.00"),
            "cultural": Decimal("20.00"),
            "entertainment": Decimal("35.00"),
            "outdoor": Decimal("10.00"),
            "adventure": Decimal("60.00"),
            "shopping": Decimal("25.00"),
            "general": Decimal("20.00"),
        }

        for cat_key, cost in cost_estimates.items():
            if cat_key in category:
                return cost * self.trip_request.requirements.travelers

        return cost_estimates["general"] * self.trip_request.requirements.travelers

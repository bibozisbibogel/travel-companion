"""Comprehensive tests for trip planning workflow nodes."""

import asyncio
import time
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from travel_companion.models.external import (
    ActivityOption,
    ActivitySearchResponse,
    FlightOption,
    FlightSearchResponse,
    HotelOption,
    HotelSearchResponse,
    RestaurantSearchResponse,
    WeatherCondition,
    WeatherData,
    WeatherForecast,
    WeatherLocation,
    WeatherSearchResponse,
)
from travel_companion.models.trip import (
    TravelClass,
    TripDestination,
    TripPlanRequest,
    TripRequirements,
)
from travel_companion.utils.errors import ExternalAPIError, TravelCompanionError
from travel_companion.workflows.nodes import (
    execute_activity_agent,
    execute_flight_agent,
    execute_food_agent,
    execute_hotel_agent,
    execute_itinerary_agent,
    execute_weather_agent,
    finalize_trip_plan,
    initialize_trip_context,
    route_based_on_preferences,
    should_proceed_to_itinerary,
)
from travel_companion.workflows.orchestrator import TripPlanningWorkflowState


class TestTripPlanningNodes:
    """Test suite for trip planning workflow nodes."""

    @pytest.fixture
    def sample_trip_request(self) -> TripPlanRequest:
        """Create sample trip request for testing."""
        return TripPlanRequest(
            destination=TripDestination(
                city="Paris", country="France", country_code="FR", airport_code="CDG"
            ),
            requirements=TripRequirements(
                budget=Decimal("3000.00"),
                currency="USD",
                start_date=datetime(2024, 6, 15).date(),
                end_date=datetime(2024, 6, 22).date(),
                travelers=2,
            ),
            preferences={
                "cabin_class": "business",
                "cuisine_types": ["french", "italian"],
                "activity_types": ["cultural", "museums"],
            },
        )

    @pytest.fixture
    def sample_workflow_state(self, sample_trip_request) -> TripPlanningWorkflowState:
        """Create sample trip planning workflow state for testing."""
        return {
            "request_id": "req123",
            "workflow_id": "wf123",
            "user_id": "user123",
            "status": "running",
            "error": None,
            "start_time": time.time(),
            "end_time": None,
            "current_node": "init",
            "input_data": sample_trip_request.model_dump(),
            "output_data": {},
            "intermediate_results": {},
            # Trip planning specific fields
            "trip_request": sample_trip_request,
            "trip_id": None,
            # Agent execution tracking
            "agents_completed": [],
            "agents_failed": [],
            "agent_dependencies": {
                "activity_agent": ["weather_agent"],
                "itinerary_agent": ["flight_agent", "hotel_agent", "activity_agent", "food_agent"],
            },
            # Agent results (initialized empty)
            "flight_results": [],
            "hotel_results": [],
            "activity_results": [],
            "weather_data": {},
            "food_recommendations": [],
            "itinerary_data": {},
            # Workflow context
            "user_preferences": {},
            "budget_tracking": {},
            "optimization_metrics": {
                "start_time": time.time(),
                "nodes_executed": 0,
                "parallel_executions": 0,
                "total_api_calls": 0,
            },
        }

    @patch("travel_companion.workflows.nodes.workflow_logger")
    def test_initialize_trip_context_success(self, mock_logger, sample_workflow_state):
        """Test successful trip context initialization."""
        result = initialize_trip_context(sample_workflow_state)

        assert result["current_node"] == "initialize_trip"
        assert result["status"] == "initializing"
        assert result["error"] is None

        # Check budget tracking initialization
        budget_tracking = result["budget_tracking"]
        assert budget_tracking["total_budget"] == 3000.0
        assert budget_tracking["allocated"] == 3000.0
        assert budget_tracking["spent"] == 0.0
        assert budget_tracking["remaining"] == 3000.0

        # Check budget allocations
        allocations = budget_tracking["allocations"]
        assert allocations["flights"] == 1200.0  # 40%
        assert allocations["hotels"] == 900.0  # 30%
        assert allocations["activities"] == 600.0  # 20%
        assert allocations["food"] == 300.0  # 10%

        # Check user preferences
        user_prefs = result["user_preferences"]
        assert user_prefs["destination"] == "Paris"
        assert user_prefs["traveler_count"] == 2

        # Check optimization metrics
        metrics = result["optimization_metrics"]
        assert metrics["nodes_executed"] == 1
        assert metrics["parallel_executions"] == 0
        assert metrics["total_api_calls"] == 0

        mock_logger.log_node_entered.assert_called_once()
        mock_logger.log_node_completed.assert_called_once()

    @patch("travel_companion.workflows.nodes.workflow_logger")
    def test_initialize_trip_context_missing_request(self, mock_logger, sample_workflow_state):
        """Test trip context initialization with missing trip request."""
        sample_workflow_state["trip_request"] = None

        with pytest.raises(TravelCompanionError, match="Missing trip request data"):
            initialize_trip_context(sample_workflow_state)

        assert sample_workflow_state["status"] == "failed"
        assert sample_workflow_state["error"] == "Missing trip request data"
        assert "initialize_trip" in sample_workflow_state["agents_failed"]

    @pytest.mark.asyncio
    @patch("travel_companion.workflows.nodes.WeatherAgent")
    @patch("travel_companion.workflows.nodes.workflow_logger")
    async def test_execute_weather_agent_success(
        self, mock_logger, mock_weather_agent_class, sample_workflow_state
    ):
        """Test successful weather agent execution."""
        # Mock weather response
        mock_weather_location = WeatherLocation(
            name="Paris", latitude=48.8566, longitude=2.3522, country="France"
        )

        mock_forecast = WeatherForecast(
            location=mock_weather_location,
            current_weather=WeatherData(
                timestamp=datetime.now(),
                temperature=22.0,
                feels_like=24.0,
                humidity=65.0,
                pressure=1013.25,
                visibility=10.0,
                wind_speed=5.0,
                wind_direction=180.0,
                precipitation=0.0,
                precipitation_probability=0.1,
                condition=WeatherCondition.CLEAR,
                condition_description="Sunny and clear",
            ),
            daily_forecasts=[],
        )

        mock_response = WeatherSearchResponse(
            forecast=mock_forecast,
            historical_data=[],
            search_time_ms=250,
            search_metadata={},
            data_source="openweather",
        )

        mock_weather_agent = AsyncMock()
        mock_weather_agent.process.return_value = mock_response
        mock_weather_agent_class.return_value = mock_weather_agent

        result = await execute_weather_agent(sample_workflow_state)

        assert result["current_node"] == "weather_agent"
        assert "weather_agent" in result["agents_completed"]
        assert "weather_data" in result
        assert result["optimization_metrics"]["total_api_calls"] == 1

        weather_data = result["weather_data"]
        assert "forecast" in weather_data
        assert "historical_data" in weather_data
        assert "search_metadata" in weather_data

    @pytest.mark.asyncio
    @patch("travel_companion.workflows.nodes.WeatherAgent")
    @patch("travel_companion.workflows.nodes.workflow_logger")
    async def test_execute_weather_agent_api_error(
        self, mock_logger, mock_weather_agent_class, sample_workflow_state
    ):
        """Test weather agent execution with API error (graceful degradation)."""
        mock_weather_agent = AsyncMock()
        mock_weather_agent.process.side_effect = ExternalAPIError("Weather API unavailable")
        mock_weather_agent_class.return_value = mock_weather_agent

        result = await execute_weather_agent(sample_workflow_state)

        # Should not raise exception but handle gracefully
        assert "weather_agent" in result["agents_failed"]
        assert result["weather_data"]["error"] == "Weather API unavailable"
        assert result["weather_data"]["degraded"] is True

    @pytest.mark.asyncio
    @patch("travel_companion.workflows.nodes.FlightAgent")
    @patch("travel_companion.workflows.nodes.workflow_logger")
    async def test_execute_flight_agent_success(
        self, mock_logger, mock_flight_agent_class, sample_workflow_state
    ):
        """Test successful flight agent execution."""
        # Initialize budget tracking
        sample_workflow_state["budget_tracking"] = {
            "allocations": {"flights": 1200.0},
            "spent": 0.0,
            "remaining": 3000.0,
        }

        # Mock flight response
        mock_flight = FlightOption(
            external_id="FL123",
            airline="Air France",
            flight_number="AF1234",
            origin="JFK",
            destination="CDG",
            departure_time=datetime(2024, 6, 15, 8, 0),
            arrival_time=datetime(2024, 6, 15, 14, 30),
            duration_minutes=450,
            stops=0,
            price=Decimal("800.00"),
            currency="USD",
            travel_class=TravelClass.BUSINESS,
            booking_url="https://example.com/book",
        )

        mock_response = FlightSearchResponse(
            flights=[mock_flight], search_time_ms=500, search_metadata={}
        )

        mock_flight_agent = AsyncMock()
        mock_flight_agent.process.return_value = mock_response
        mock_flight_agent_class.return_value = mock_flight_agent

        result = await execute_flight_agent(sample_workflow_state)

        assert result["current_node"] == "flight_agent"
        assert "flight_agent" in result["agents_completed"]
        assert len(result["flight_results"]) == 1
        assert result["budget_tracking"]["spent"] == 800.0
        assert result["budget_tracking"]["remaining"] == 2200.0
        assert result["optimization_metrics"]["parallel_executions"] == 1

    @pytest.mark.asyncio
    @patch("travel_companion.workflows.nodes.HotelAgent")
    @patch("travel_companion.workflows.nodes.workflow_logger")
    async def test_execute_hotel_agent_success(
        self, mock_logger, mock_hotel_agent_class, sample_workflow_state
    ):
        """Test successful hotel agent execution."""
        # Initialize budget tracking
        sample_workflow_state["budget_tracking"] = {
            "allocations": {"hotels": 900.0},
            "spent": 0.0,
            "remaining": 3000.0,
        }

        # Mock hotel response
        from uuid import uuid4

        from travel_companion.models.external import HotelLocation

        mock_hotel = HotelOption(
            hotel_id=uuid4(),
            external_id="HTL123",
            name="Hotel Paris",
            location=HotelLocation(
                latitude=48.8566,
                longitude=2.3522,
                address="Central Paris",
                city="Paris",
                country="France",
            ),
            price_per_night=Decimal("150.00"),
            rating=4.0,
            amenities=["wifi", "pool"],
        )

        mock_response = HotelSearchResponse(
            hotels=[mock_hotel], search_time_ms=400, search_metadata={}
        )

        mock_hotel_agent = AsyncMock()
        mock_hotel_agent.process.return_value = mock_response
        mock_hotel_agent_class.return_value = mock_hotel_agent

        result = await execute_hotel_agent(sample_workflow_state)

        assert result["current_node"] == "hotel_agent"
        assert "hotel_agent" in result["agents_completed"]
        assert len(result["hotel_results"]) == 1

        # Check budget calculation (7 nights * $150)
        assert result["budget_tracking"]["spent"] == 1050.0
        assert result["budget_tracking"]["remaining"] == 1950.0

    @pytest.mark.asyncio
    @patch("travel_companion.workflows.nodes.ActivityAgent")
    @patch("travel_companion.workflows.nodes.workflow_logger")
    async def test_execute_activity_agent_with_weather_dependency(
        self, mock_logger, mock_activity_agent_class, sample_workflow_state
    ):
        """Test activity agent execution using weather data for filtering."""
        # Initialize budget tracking and weather data
        sample_workflow_state["budget_tracking"] = {
            "allocations": {"activities": 600.0},
            "spent": 0.0,
            "remaining": 3000.0,
        }
        sample_workflow_state["weather_data"] = {
            "forecast": {
                "daily_forecasts": [
                    {"condition": "sunny"},
                    {"condition": "partly_cloudy"},
                    {"condition": "rainy"},
                ]
            }
        }

        # Mock activity response
        from uuid import uuid4

        from travel_companion.models.external import ActivityCategory, ActivityLocation

        mock_activity = ActivityOption(
            activity_id=uuid4(),
            external_id="ACT123",
            name="Louvre Museum",
            description="World famous art museum",
            category=ActivityCategory.CULTURAL,
            duration_minutes=180,  # 3 hours
            price=Decimal("25.00"),
            location=ActivityLocation(
                latitude=48.8606,
                longitude=2.3376,
                address="Rue de Rivoli",
                city="Paris",
                country="France",
            ),
            provider="tripadvisor",
        )

        mock_response = ActivitySearchResponse(
            activities=[mock_activity], search_time_ms=300, search_metadata={}
        )

        mock_activity_agent = AsyncMock()
        mock_activity_agent.process.return_value = mock_response
        mock_activity_agent_class.return_value = mock_activity_agent

        result = await execute_activity_agent(sample_workflow_state)

        assert result["current_node"] == "activity_agent"
        assert "activity_agent" in result["agents_completed"]
        assert len(result["activity_results"]) == 1

        # Verify agent was called with proper arguments
        mock_activity_agent.process.assert_called_once()

    @pytest.mark.asyncio
    @patch("travel_companion.workflows.nodes.FoodAgent")
    @patch("travel_companion.workflows.nodes.workflow_logger")
    async def test_execute_food_agent_success(
        self, mock_logger, mock_food_agent_class, sample_workflow_state
    ):
        """Test successful food agent execution."""
        # Initialize budget tracking
        sample_workflow_state["budget_tracking"] = {
            "allocations": {"food": 300.0},
            "spent": 0.0,
            "remaining": 3000.0,
        }

        # Mock food response using RestaurantSearchResponse
        mock_response = RestaurantSearchResponse(
            restaurants=[],  # Simplified for test - no need to create full restaurant objects
            search_time_ms=200,
            search_metadata={},
            total_results=0,
        )

        mock_food_agent = AsyncMock()
        mock_food_agent.process.return_value = mock_response
        mock_food_agent_class.return_value = mock_food_agent

        result = await execute_food_agent(sample_workflow_state)

        assert result["current_node"] == "food_agent"
        assert "food_agent" in result["agents_completed"]
        assert len(result["food_recommendations"]) == 1

        # Check budget calculation (2 meals/day * 7 days * 2 people * $45)
        expected_cost = 45.0 * 2 * 7 * 2
        assert result["budget_tracking"]["spent"] == expected_cost

    @pytest.mark.asyncio
    @patch("travel_companion.workflows.nodes.ItineraryAgent")
    @patch("travel_companion.workflows.nodes.workflow_logger")
    async def test_execute_itinerary_agent_success(
        self, mock_logger, mock_itinerary_agent_class, sample_workflow_state
    ):
        """Test successful itinerary agent execution with all dependencies."""
        # Setup completed agents and their results
        sample_workflow_state["agents_completed"] = [
            "flight_agent",
            "hotel_agent",
            "activity_agent",
            "food_agent",
        ]
        sample_workflow_state["flight_results"] = [{"flight_id": "FL123"}]
        sample_workflow_state["hotel_results"] = [{"hotel_id": "HTL123"}]
        sample_workflow_state["activity_results"] = [{"activity_id": "ACT123"}]
        sample_workflow_state["food_recommendations"] = [{"restaurant_id": "REST123"}]
        sample_workflow_state["weather_data"] = {"forecast": "sunny"}
        sample_workflow_state["budget_tracking"] = {"total_budget": 3000.0}

        # Mock itinerary response with simple structure
        mock_response = MagicMock()
        mock_response.optimized_itinerary.model_dump.return_value = {
            "trip_id": "trip_123",
            "optimization_score": 8.5,
        }
        mock_response.daily_schedules = [MagicMock()]
        mock_response.daily_schedules[0].model_dump.return_value = {
            "date": "2024-06-15",
            "estimated_cost": 200.0,
        }
        mock_response.budget_summary.model_dump.return_value = {
            "total_estimated_cost": {"amount": 2800.0, "currency": "USD"}
        }
        mock_response.optimization_score = 8.5
        mock_response.recommendations = []

        mock_itinerary_agent = AsyncMock()
        mock_itinerary_agent.process.return_value = mock_response
        mock_itinerary_agent_class.return_value = mock_itinerary_agent

        result = await execute_itinerary_agent(sample_workflow_state)

        assert result["current_node"] == "itinerary_agent"
        assert "itinerary_agent" in result["agents_completed"]
        assert "itinerary_data" in result

        itinerary_data = result["itinerary_data"]
        assert "optimized_itinerary" in itinerary_data
        assert "daily_schedules" in itinerary_data
        assert "budget_summary" in itinerary_data
        assert itinerary_data["optimization_score"] == 8.5

    @pytest.mark.asyncio
    @patch("travel_companion.workflows.nodes.workflow_logger")
    async def test_execute_itinerary_agent_missing_critical_agents(
        self, mock_logger, sample_workflow_state
    ):
        """Test itinerary agent execution when critical agents failed."""
        # No critical agents completed
        sample_workflow_state["agents_completed"] = ["weather_agent"]
        sample_workflow_state["agents_failed"] = ["flight_agent", "hotel_agent"]

        with pytest.raises(TravelCompanionError, match="Critical travel agents"):
            await execute_itinerary_agent(sample_workflow_state)

    @patch("travel_companion.workflows.nodes.workflow_logger")
    def test_finalize_trip_plan_success(self, mock_logger, sample_workflow_state):
        """Test successful trip plan finalization."""
        # Setup completed workflow state
        sample_workflow_state["agents_completed"] = ["weather_agent", "flight_agent", "hotel_agent"]
        sample_workflow_state["agents_failed"] = ["activity_agent"]
        sample_workflow_state["start_time"] = time.time() - 10  # 10 seconds ago
        sample_workflow_state["optimization_metrics"] = {
            "parallel_executions": 3,
            "total_api_calls": 4,
        }
        sample_workflow_state["flight_results"] = [{"flight_id": "FL123"}]
        sample_workflow_state["hotel_results"] = [{"hotel_id": "HTL123"}]
        sample_workflow_state["weather_data"] = {"forecast": "sunny"}

        result = finalize_trip_plan(sample_workflow_state)

        assert result["current_node"] == "finalize_plan"
        assert result["status"] == "completed"
        assert result["end_time"] is not None
        assert "output_data" in result

        output = result["output_data"]
        assert "trip_plan_id" in output
        assert "workflow_id" in output
        assert "execution_summary" in output
        assert "flight_options" in output
        assert "hotel_options" in output

        execution_summary = output["execution_summary"]
        assert execution_summary["status"] == "completed"
        assert execution_summary["agents_completed"] == [
            "weather_agent",
            "flight_agent",
            "hotel_agent",
        ]
        assert execution_summary["agents_failed"] == ["activity_agent"]
        assert execution_summary["parallel_optimizations"] == 3

    def test_should_proceed_to_itinerary_with_critical_agents(self, sample_workflow_state):
        """Test conditional routing when critical agents completed."""
        sample_workflow_state["agents_completed"] = ["flight_agent", "weather_agent"]
        sample_workflow_state["agents_failed"] = []

        next_node = should_proceed_to_itinerary(sample_workflow_state)
        assert next_node == "itinerary_agent"

    def test_should_proceed_to_itinerary_critical_failure(self, sample_workflow_state):
        """Test conditional routing when all critical agents failed."""
        sample_workflow_state["agents_completed"] = ["weather_agent"]
        sample_workflow_state["agents_failed"] = ["flight_agent", "hotel_agent"]

        next_node = should_proceed_to_itinerary(sample_workflow_state)
        assert next_node == "finalize_plan"

    def test_route_based_on_preferences_budget_exceeded(self, sample_workflow_state):
        """Test preference-based routing when budget is exceeded."""
        sample_workflow_state["budget_tracking"] = {"remaining": -100.0}

        routing = route_based_on_preferences(sample_workflow_state)
        assert routing == {"budget_exceeded": "finalize_plan"}

    def test_route_based_on_preferences_critical_failure(self, sample_workflow_state):
        """Test preference-based routing with critical agent failures."""
        sample_workflow_state["agents_failed"] = ["flight_agent", "hotel_agent"]
        sample_workflow_state["budget_tracking"] = {"remaining": 1000.0}

        routing = route_based_on_preferences(sample_workflow_state)
        assert routing == {"critical_failure": "finalize_plan"}

    def test_route_based_on_preferences_normal(self, sample_workflow_state):
        """Test preference-based routing under normal conditions."""
        sample_workflow_state["agents_failed"] = []
        sample_workflow_state["budget_tracking"] = {"remaining": 1000.0}

        routing = route_based_on_preferences(sample_workflow_state)
        assert "default" in routing
        assert routing["default"] == "itinerary_agent"

    @pytest.mark.asyncio
    async def test_parallel_agent_execution_simulation(self, sample_workflow_state):
        """Test that parallel agents can be executed concurrently."""
        # Initialize budget tracking
        sample_workflow_state["budget_tracking"] = {
            "allocations": {"flights": 1200.0, "hotels": 900.0, "activities": 600.0, "food": 300.0},
            "spent": 0.0,
            "remaining": 3000.0,
        }

        # Mock all agents to return empty but successful responses
        with (
            patch("travel_companion.workflows.nodes.FlightAgent") as mock_flight,
            patch("travel_companion.workflows.nodes.HotelAgent") as mock_hotel,
            patch("travel_companion.workflows.nodes.ActivityAgent") as mock_activity,
            patch("travel_companion.workflows.nodes.FoodAgent") as mock_food,
        ):
            # Setup mocks
            for mock_agent_class in [mock_flight, mock_hotel, mock_activity, mock_food]:
                mock_agent = AsyncMock()
                mock_agent.process.return_value = MagicMock(
                    flights=[], hotels=[], activities=[], restaurants=[]
                )
                mock_agent_class.return_value = mock_agent

            # Simulate parallel execution
            start_time = time.time()

            tasks = [
                execute_flight_agent(sample_workflow_state.copy()),
                execute_hotel_agent(sample_workflow_state.copy()),
                execute_activity_agent(sample_workflow_state.copy()),
                execute_food_agent(sample_workflow_state.copy()),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.time()
            execution_time = end_time - start_time

            # Verify all completed successfully
            for result in results:
                assert not isinstance(result, Exception)
                assert result["optimization_metrics"]["parallel_executions"] == 1

            # Parallel execution should be faster than sequential
            # (This is a simulation - in real scenarios, the speedup would be more significant)
            assert execution_time < 2.0  # Should complete quickly

    @pytest.mark.asyncio
    @patch("travel_companion.workflows.nodes.workflow_logger")
    async def test_error_recovery_and_graceful_degradation(
        self, mock_logger, sample_workflow_state
    ):
        """Test error recovery and graceful degradation across multiple agents."""
        # Initialize budget tracking
        sample_workflow_state["budget_tracking"] = {
            "allocations": {"activities": 600.0},
            "spent": 0.0,
            "remaining": 3000.0,
        }

        # Mock activity agent to fail with API error
        with patch("travel_companion.workflows.nodes.ActivityAgent") as mock_activity_agent_class:
            mock_activity_agent = AsyncMock()
            mock_activity_agent.process.side_effect = ExternalAPIError("Service unavailable")
            mock_activity_agent_class.return_value = mock_activity_agent

            result = await execute_activity_agent(sample_workflow_state)

            # Should handle gracefully without crashing workflow
            assert "activity_agent" in result["agents_failed"]
            assert result["activity_results"] == []
            assert result["current_node"] == "activity_agent"

    def test_budget_allocation_logic(self, sample_workflow_state):
        """Test budget allocation percentages and calculations."""
        result = initialize_trip_context(sample_workflow_state)

        budget_tracking = result["budget_tracking"]
        total_budget = budget_tracking["total_budget"]
        allocations = budget_tracking["allocations"]

        # Verify percentages add up to 100%
        total_allocation = sum(allocations.values())
        assert abs(total_allocation - total_budget) < 0.01  # Allow for floating point precision

        # Verify individual percentages
        assert allocations["flights"] / total_budget == 0.4  # 40%
        assert allocations["hotels"] / total_budget == 0.3  # 30%
        assert allocations["activities"] / total_budget == 0.2  # 20%
        assert allocations["food"] / total_budget == 0.1  # 10%

    @pytest.mark.asyncio
    async def test_dependency_management_weather_to_activities(self, sample_workflow_state):
        """Test that activity agent correctly uses weather data as dependency."""
        # Setup weather data first
        sample_workflow_state["weather_data"] = {
            "forecast": {
                "daily_forecasts": [
                    {"condition": "sunny", "temperature": 25},
                    {"condition": "rainy", "temperature": 18},
                ]
            }
        }
        sample_workflow_state["budget_tracking"] = {
            "allocations": {"activities": 600.0},
            "spent": 0.0,
            "remaining": 3000.0,
        }

        with patch("travel_companion.workflows.nodes.ActivityAgent") as mock_activity_agent_class:
            mock_activity_agent = AsyncMock()
            mock_response = ActivitySearchResponse(
                activities=[], search_time_ms=300, search_metadata={}
            )
            mock_activity_agent.process.return_value = mock_response
            mock_activity_agent_class.return_value = mock_activity_agent

            await execute_activity_agent(sample_workflow_state)

            # Verify activity agent was called
            mock_activity_agent.process.assert_called_once()

    def test_optimization_metrics_tracking(self, sample_workflow_state):
        """Test that optimization metrics are properly tracked across nodes."""
        # Initialize context
        result = initialize_trip_context(sample_workflow_state)

        initial_metrics = result["optimization_metrics"]
        assert initial_metrics["nodes_executed"] == 1
        assert initial_metrics["parallel_executions"] == 0
        assert initial_metrics["total_api_calls"] == 0

        # Simulate completing multiple nodes with API calls
        result["agents_completed"] = ["weather_agent", "flight_agent", "hotel_agent"]
        result["optimization_metrics"]["total_api_calls"] = 3
        result["optimization_metrics"]["parallel_executions"] = 2

        # Finalize and check final metrics
        final_result = finalize_trip_plan(result)

        final_metrics = final_result["optimization_metrics"]
        assert final_metrics["nodes_executed"] == 5  # init + 3 agents + finalize
        assert final_metrics["total_api_calls"] == 3
        assert final_metrics["parallel_executions"] == 2
        assert final_metrics["success_rate"] == 1.0  # All agents completed successfully

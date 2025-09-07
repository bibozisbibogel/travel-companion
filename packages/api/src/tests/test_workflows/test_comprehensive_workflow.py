"""
Comprehensive workflow integration tests for complete user scenarios.

This test suite covers end-to-end workflow testing with complete user scenarios,
including complex multi-agent coordination, state transitions, and edge cases.
"""

import asyncio
import time
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from travel_companion.models.external import (
    ActivityCategory,
    ActivityLocation,
    ActivityOption,
    ActivitySearchResponse,
    FlightOption,
    FlightSearchResponse,
    HotelLocation,
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
    AccommodationType,
    TravelClass,
    TripDestination,
    TripPlanRequest,
    TripRequirements,
)
from travel_companion.utils.errors import ExternalAPIError, TravelCompanionError
from travel_companion.workflows.orchestrator import TripPlanningWorkflow


class TestComprehensiveWorkflowScenarios:
    """End-to-end workflow tests with complete user scenarios."""

    @pytest.fixture
    def sample_trip_request_short(self) -> TripPlanRequest:
        """Sample short weekend trip request."""
        return TripPlanRequest(
            destination=TripDestination(
                city="Amsterdam",
                country="Netherlands",
                country_code="NL",
                airport_code="AMS",
                latitude=52.3676,
                longitude=4.9041,
            ),
            requirements=TripRequirements(
                budget=Decimal("1500.00"),
                currency="USD",
                start_date=date(2024, 3, 15),
                end_date=date(2024, 3, 17),
                travelers=2,
                travel_class=TravelClass.ECONOMY,
                accommodation_type=AccommodationType.HOTEL,
            ),
            preferences={
                "activities": "museums,canals",
                "dietary_restrictions": "none",
                "accommodation_style": "boutique",
            },
        )

    @pytest.fixture
    def sample_trip_request_long(self) -> TripPlanRequest:
        """Sample long family vacation request."""
        return TripPlanRequest(
            destination=TripDestination(
                city="Tokyo",
                country="Japan",
                country_code="JP",
                airport_code="NRT",
                latitude=35.6762,
                longitude=139.6503,
            ),
            requirements=TripRequirements(
                budget=Decimal("8000.00"),
                currency="USD",
                start_date=date(2024, 7, 1),
                end_date=date(2024, 7, 14),
                travelers=4,
                travel_class=TravelClass.PREMIUM_ECONOMY,
                accommodation_type=AccommodationType.HOTEL,
            ),
            preferences={
                "activities": "cultural,temples,food_tours",
                "dietary_restrictions": "vegetarian",
                "accommodation_style": "family_friendly",
                "language_preference": "english_speaking_staff",
            },
        )

    @pytest.fixture
    def mock_successful_agents(self):
        """Mock all travel agents with successful responses."""
        mocks = {}

        # Mock Weather Agent
        weather_location = WeatherLocation(
            name="Amsterdam", latitude=52.3676, longitude=4.9041, country="Netherlands"
        )
        weather_forecast = WeatherForecast(
            location=weather_location,
            current_weather=WeatherData(
                timestamp=datetime.now(),
                temperature=18.0,
                feels_like=20.0,
                humidity=70.0,
                pressure=1015.0,
                visibility=10.0,
                wind_speed=12.0,
                wind_direction=250,
                precipitation=0.2,
                precipitation_probability=0.3,
                condition=WeatherCondition.PARTLY_CLOUDY,
                condition_description="Partly cloudy with light breeze",
            ),
            daily_forecasts=[],
        )
        mocks["weather"] = WeatherSearchResponse(
            forecast=weather_forecast,
            historical_data=[],
            search_time_ms=200,
            search_metadata={},
            data_source="openweather",
        )

        # Mock Flight Agent
        flight_option = FlightOption(
            external_id="KL1234",
            airline="KLM",
            flight_number="KL1234",
            origin="JFK",
            destination="AMS",
            departure_time=datetime(2024, 3, 15, 14, 30),
            arrival_time=datetime(2024, 3, 16, 2, 45),
            duration_minutes=495,
            stops=0,
            price=Decimal("650.00"),
            currency="USD",
            travel_class=TravelClass.ECONOMY,
            booking_url="https://klm.com/book/KL1234",
        )
        mocks["flight"] = FlightSearchResponse(
            flights=[flight_option], search_time_ms=800, search_metadata={}
        )

        # Mock Hotel Agent
        from uuid import uuid4

        hotel_option = HotelOption(
            hotel_id=uuid4(),
            external_id="AMS_HOTEL_123",
            name="Canal House Boutique Hotel",
            location=HotelLocation(
                latitude=52.3676,
                longitude=4.9041,
                address="Keizersgracht 148",
                city="Amsterdam",
                country="Netherlands",
            ),
            price_per_night=Decimal("180.00"),
            rating=4.5,
            amenities=["wifi", "breakfast", "canal_view", "historic_building"],
        )
        mocks["hotel"] = HotelSearchResponse(
            hotels=[hotel_option], search_time_ms=600, search_metadata={}
        )

        # Mock Activity Agent
        activity_option = ActivityOption(
            activity_id=uuid4(),
            external_id="AMS_ACT_VAN_GOGH",
            name="Van Gogh Museum",
            description="World-renowned collection of Van Gogh masterpieces",
            category=ActivityCategory.CULTURAL,
            duration_minutes=120,
            price=Decimal("22.00"),
            location=ActivityLocation(
                latitude=52.3579,
                longitude=4.8794,
                address="Museumplein 6",
                city="Amsterdam",
                country="Netherlands",
            ),
            provider="viator",
        )
        mocks["activity"] = ActivitySearchResponse(
            activities=[activity_option], search_time_ms=400, search_metadata={}
        )

        # Mock Food Agent
        mocks["food"] = RestaurantSearchResponse(
            restaurants=[], search_time_ms=300, search_metadata={}, total_results=5
        )

        # Mock Itinerary Agent
        itinerary_mock = MagicMock()
        itinerary_mock.optimized_itinerary.model_dump.return_value = {
            "trip_id": "amsterdam_weekend_2024",
            "optimization_score": 9.2,
            "total_duration_hours": 48,
        }
        itinerary_mock.daily_schedules = [MagicMock(), MagicMock()]
        itinerary_mock.daily_schedules[0].model_dump.return_value = {
            "date": "2024-03-15",
            "activities": ["arrival", "hotel_checkin", "canal_walk"],
            "estimated_cost": 280.0,
        }
        itinerary_mock.daily_schedules[1].model_dump.return_value = {
            "date": "2024-03-16",
            "activities": ["van_gogh_museum", "lunch", "departure"],
            "estimated_cost": 120.0,
        }
        itinerary_mock.budget_summary.model_dump.return_value = {
            "total_estimated_cost": {"amount": 1400.0, "currency": "USD"},
            "breakdown": {"flights": 650.0, "hotels": 360.0, "activities": 250.0, "food": 140.0},
        }
        itinerary_mock.optimization_score = 9.2
        itinerary_mock.recommendations = ["Book museum tickets in advance", "Try local stroopwafels"]
        mocks["itinerary"] = itinerary_mock

        return mocks

    @pytest.mark.asyncio
    @patch("travel_companion.workflows.orchestrator.get_settings")
    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.nodes.WeatherAgent")
    @patch("travel_companion.workflows.nodes.FlightAgent")
    @patch("travel_companion.workflows.nodes.HotelAgent")
    @patch("travel_companion.workflows.nodes.ActivityAgent")
    @patch("travel_companion.workflows.nodes.FoodAgent")
    @patch("travel_companion.workflows.nodes.ItineraryAgent")
    async def test_end_to_end_successful_short_trip_planning(
        self,
        mock_itinerary_agent,
        mock_food_agent,
        mock_activity_agent,
        mock_hotel_agent,
        mock_flight_agent,
        mock_weather_agent,
        mock_get_redis,
        mock_get_settings,
        sample_trip_request_short,
        mock_successful_agents,
    ):
        """Test complete end-to-end workflow for successful short trip planning."""
        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.workflow_timeout_seconds = 300
        mock_settings.workflow_state_ttl = 3600
        mock_settings.workflow_enable_debug_logging = True
        mock_get_settings.return_value = mock_settings

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.setex = AsyncMock()
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        # Setup agent mocks
        agent_mocks = {}
        agent_classes = [
            (mock_weather_agent, "weather"),
            (mock_flight_agent, "flight"),
            (mock_hotel_agent, "hotel"),
            (mock_activity_agent, "activity"),
            (mock_food_agent, "food"),
            (mock_itinerary_agent, "itinerary"),
        ]

        for mock_class, agent_type in agent_classes:
            agent_mock = AsyncMock()
            agent_mock.process.return_value = mock_successful_agents[agent_type]
            mock_class.return_value = agent_mock
            agent_mocks[agent_type] = agent_mock

        # Execute workflow
        workflow = TripPlanningWorkflow()
        start_time = time.time()

        result = await workflow.execute_trip_planning(
            sample_trip_request_short, user_id="test_user", request_id="short_trip_test"
        )

        end_time = time.time()
        execution_time = end_time - start_time

        # Verify results
        assert "trip_plan_id" in result
        assert "workflow_id" in result
        assert "execution_summary" in result
        assert "flight_options" in result
        assert "hotel_options" in result
        assert "activity_options" in result
        assert "weather_forecast" in result
        assert "food_recommendations" in result
        assert "optimized_itinerary" in result

        # Check execution summary
        execution_summary = result["execution_summary"]
        assert execution_summary["status"] == "completed"
        assert execution_summary["total_execution_time"] < 300  # Within timeout
        assert len(execution_summary["agents_completed"]) >= 5  # Most agents completed
        assert execution_summary["optimization_score"] > 8.0  # High quality score

        # Verify agent interactions
        for agent_mock in agent_mocks.values():
            agent_mock.process.assert_called_once()

        # Performance verification
        assert execution_time < 10  # Should complete quickly with mocks
        assert len(result["flight_options"]) > 0
        assert len(result["hotel_options"]) > 0

    @pytest.mark.asyncio
    @patch("travel_companion.workflows.orchestrator.get_settings")
    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.nodes.WeatherAgent")
    @patch("travel_companion.workflows.nodes.FlightAgent")
    @patch("travel_companion.workflows.nodes.HotelAgent")
    @patch("travel_companion.workflows.nodes.ActivityAgent")
    @patch("travel_companion.workflows.nodes.FoodAgent")
    @patch("travel_companion.workflows.nodes.ItineraryAgent")
    async def test_end_to_end_partial_failure_scenario(
        self,
        mock_itinerary_agent,
        mock_food_agent,
        mock_activity_agent,
        mock_hotel_agent,
        mock_flight_agent,
        mock_weather_agent,
        mock_get_redis,
        mock_get_settings,
        sample_trip_request_short,
        mock_successful_agents,
    ):
        """Test workflow handling partial agent failures gracefully."""
        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.workflow_timeout_seconds = 300
        mock_settings.workflow_state_ttl = 3600
        mock_get_settings.return_value = mock_settings

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.setex = AsyncMock()
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        # Setup successful agents
        weather_mock = AsyncMock()
        weather_mock.process.return_value = mock_successful_agents["weather"]
        mock_weather_agent.return_value = weather_mock

        flight_mock = AsyncMock()
        flight_mock.process.return_value = mock_successful_agents["flight"]
        mock_flight_agent.return_value = flight_mock

        hotel_mock = AsyncMock()
        hotel_mock.process.return_value = mock_successful_agents["hotel"]
        mock_hotel_agent.return_value = hotel_mock

        # Setup failing agents
        activity_mock = AsyncMock()
        activity_mock.process.side_effect = ExternalAPIError("TripAdvisor API unavailable")
        mock_activity_agent.return_value = activity_mock

        food_mock = AsyncMock()
        food_mock.process.side_effect = ExternalAPIError("Yelp API rate limit exceeded")
        mock_food_agent.return_value = food_mock

        # Setup itinerary to handle partial failures
        itinerary_mock = AsyncMock()
        itinerary_result = MagicMock()
        itinerary_result.optimized_itinerary.model_dump.return_value = {
            "trip_id": "partial_failure_trip",
            "optimization_score": 7.5,  # Lower due to missing data
        }
        itinerary_result.daily_schedules = [MagicMock()]
        itinerary_result.daily_schedules[0].model_dump.return_value = {
            "date": "2024-03-15",
            "activities": ["arrival", "hotel_checkin"],  # Limited due to failures
            "estimated_cost": 200.0,
        }
        itinerary_result.budget_summary.model_dump.return_value = {
            "total_estimated_cost": {"amount": 1200.0, "currency": "USD"}
        }
        itinerary_result.optimization_score = 7.5
        itinerary_result.recommendations = ["Some agents failed - plan may be incomplete"]
        itinerary_mock.process.return_value = itinerary_result
        mock_itinerary_agent.return_value = itinerary_mock

        # Execute workflow
        workflow = TripPlanningWorkflow()

        result = await workflow.execute_trip_planning(
            sample_trip_request_short, user_id="test_user", request_id="partial_failure_test"
        )

        # Verify graceful handling of failures
        assert "trip_plan_id" in result
        assert "execution_summary" in result

        execution_summary = result["execution_summary"]
        assert execution_summary["status"] == "completed"  # Still completed
        assert len(execution_summary["agents_failed"]) == 2  # Activity and food agents failed
        assert "activity_agent" in execution_summary["agents_failed"]
        assert "food_agent" in execution_summary["agents_failed"]
        assert len(execution_summary["agents_completed"]) >= 3  # Core agents succeeded

        # Verify critical services still worked
        assert len(result["flight_options"]) > 0
        assert len(result["hotel_options"]) > 0
        assert result["weather_forecast"] is not None

        # Verify fallback handling
        assert "activity_options" in result  # Should exist even if empty
        assert "food_recommendations" in result  # Should exist even if empty

    @pytest.mark.asyncio
    @patch("travel_companion.workflows.orchestrator.get_settings")
    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    async def test_critical_agent_failure_scenario(
        self, mock_get_redis, mock_get_settings, sample_trip_request_short
    ):
        """Test workflow behavior when critical agents (flight, hotel) fail."""
        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.workflow_timeout_seconds = 300
        mock_settings.workflow_state_ttl = 3600
        mock_get_settings.return_value = mock_settings

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.setex = AsyncMock()
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        # Setup all agents to fail
        with (
            patch("travel_companion.workflows.nodes.WeatherAgent") as mock_weather,
            patch("travel_companion.workflows.nodes.FlightAgent") as mock_flight,
            patch("travel_companion.workflows.nodes.HotelAgent") as mock_hotel,
            patch("travel_companion.workflows.nodes.ActivityAgent") as mock_activity,
            patch("travel_companion.workflows.nodes.FoodAgent") as mock_food,
        ):
            # Make critical agents fail
            for mock_agent in [mock_weather, mock_flight, mock_hotel, mock_activity, mock_food]:
                agent_instance = AsyncMock()
                agent_instance.process.side_effect = ExternalAPIError("Service unavailable")
                mock_agent.return_value = agent_instance

            # Execute workflow
            workflow = TripPlanningWorkflow()

            # Should handle critical failures gracefully
            result = await workflow.execute_trip_planning(
                sample_trip_request_short, user_id="test_user", request_id="critical_failure_test"
            )

            # Verify failure handling
            assert "execution_summary" in result
            execution_summary = result["execution_summary"]
            assert execution_summary["status"] == "completed"  # Should still complete
            assert len(execution_summary["agents_failed"]) >= 2  # Critical agents failed

    @pytest.mark.asyncio
    async def test_workflow_state_transitions_comprehensive(self, sample_trip_request_short):
        """Test comprehensive workflow state transitions through all nodes."""
        workflow = TripPlanningWorkflow()

        # Test initial state creation
        initial_state = workflow.create_initial_state(
            sample_trip_request_short, user_id="state_test_user", request_id="state_test_req"
        )

        # Verify initial state
        assert initial_state["status"] == "running"
        assert initial_state["current_node"] == "initialize_trip"
        assert initial_state["agents_completed"] == []
        assert initial_state["agents_failed"] == []
        assert initial_state["error"] is None

        # Test state progression through workflow nodes
        expected_node_sequence = [
            "initialize_trip",
            "coordinated_execution",  # The new coordinated execution approach
            "finalize_plan",
        ]

        # Verify workflow can transition through expected states
        workflow.build_graph()
        assert workflow._graph is not None

        # Check that the graph has the expected nodes and transitions
        nodes = workflow.define_nodes()
        edges = workflow.define_edges()

        assert "initialize_trip" in nodes
        assert "coordinated_execution" in nodes
        assert "finalize_plan" in nodes

        # Verify edge connections
        assert ("initialize_trip", "coordinated_execution") in edges
        assert ("coordinated_execution", "finalize_plan") in edges

    @pytest.mark.asyncio
    @patch("travel_companion.workflows.orchestrator.get_settings")
    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    async def test_workflow_timeout_handling(
        self, mock_get_redis, mock_get_settings, sample_trip_request_long
    ):
        """Test workflow timeout handling for long-running operations."""
        # Setup very short timeout
        mock_settings = MagicMock()
        mock_settings.workflow_timeout_seconds = 0.1  # Very short timeout
        mock_settings.workflow_state_ttl = 3600
        mock_get_settings.return_value = mock_settings

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.setex = AsyncMock()
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        # Setup slow agents
        with (
            patch("travel_companion.workflows.nodes.WeatherAgent") as mock_weather,
            patch("travel_companion.workflows.nodes.FlightAgent") as mock_flight,
        ):
            # Make agents slow
            async def slow_process(*args, **kwargs):
                await asyncio.sleep(1)  # Longer than timeout
                return MagicMock()

            weather_mock = AsyncMock()
            weather_mock.process = slow_process
            mock_weather.return_value = weather_mock

            flight_mock = AsyncMock()
            flight_mock.process = slow_process
            mock_flight.return_value = flight_mock

            # Execute workflow - should timeout
            workflow = TripPlanningWorkflow()

            with pytest.raises(TimeoutError):
                await workflow.execute_trip_planning(
                    sample_trip_request_long, user_id="timeout_test", request_id="timeout_req"
                )

    @pytest.mark.asyncio
    @patch("travel_companion.workflows.orchestrator.get_settings")
    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    async def test_budget_constraint_workflow_termination(
        self, mock_get_redis, mock_get_settings, sample_trip_request_short
    ):
        """Test workflow termination when budget constraints are exceeded."""
        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.workflow_timeout_seconds = 300
        mock_settings.workflow_state_ttl = 3600
        mock_get_settings.return_value = mock_settings

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.setex = AsyncMock()
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        # Create high-cost responses that exceed budget
        expensive_flight = FlightOption(
            external_id="EXPENSIVE",
            airline="Premium Air",
            flight_number="PA001",
            origin="JFK",
            destination="AMS",
            departure_time=datetime(2024, 3, 15, 14, 30),
            arrival_time=datetime(2024, 3, 16, 2, 45),
            duration_minutes=495,
            stops=0,
            price=Decimal("2000.00"),  # Exceeds total budget
            currency="USD",
            travel_class=TravelClass.BUSINESS,
            booking_url="https://example.com/expensive",
        )

        with (
            patch("travel_companion.workflows.nodes.WeatherAgent") as mock_weather,
            patch("travel_companion.workflows.nodes.FlightAgent") as mock_flight,
        ):
            # Weather succeeds
            weather_mock = AsyncMock()
            weather_response = WeatherSearchResponse(
                forecast=MagicMock(), historical_data=[], search_time_ms=100, search_metadata={}
            )
            weather_mock.process.return_value = weather_response
            mock_weather.return_value = weather_mock

            # Flight returns expensive option
            flight_mock = AsyncMock()
            expensive_flight_response = FlightSearchResponse(
                flights=[expensive_flight], search_time_ms=500, search_metadata={}
            )
            flight_mock.process.return_value = expensive_flight_response
            mock_flight.return_value = flight_mock

            # Execute workflow
            workflow = TripPlanningWorkflow()

            result = await workflow.execute_trip_planning(
                sample_trip_request_short, user_id="budget_test", request_id="budget_constraint"
            )

            # Verify budget handling - workflow should complete but note budget issues
            assert "execution_summary" in result
            execution_summary = result["execution_summary"]
            assert execution_summary["status"] == "completed"

    def test_workflow_health_check_comprehensive(self):
        """Test comprehensive workflow health check functionality."""
        workflow = TripPlanningWorkflow()

        # Build graph first
        with (
            patch("travel_companion.workflows.orchestrator.get_settings") as mock_settings,
            patch("travel_companion.workflows.orchestrator.get_redis_manager") as mock_redis_mgr,
        ):
            mock_settings.return_value = MagicMock()
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis_mgr.return_value = MagicMock(client=mock_redis)

            workflow.build_graph()
            health = workflow.get_health_status()

            assert health["workflow_type"] == "trip_planning"
            assert health["status"] == "healthy"
            assert health["graph_built"] is True
            assert health["redis_connected"] is True
            assert health["node_count"] > 0
            assert health["edge_count"] > 0

    @pytest.mark.asyncio
    async def test_complex_multi_agent_coordination_patterns(self, sample_trip_request_long):
        """Test complex coordination patterns between multiple agents."""
        workflow = TripPlanningWorkflow()

        # Test dependency resolution
        initial_state = workflow.create_initial_state(sample_trip_request_long)

        # Verify agent dependencies are properly configured
        dependencies = initial_state["agent_dependencies"]

        # Activity agent should depend on weather
        assert "activity_agent" in dependencies
        assert "weather_agent" in dependencies["activity_agent"]

        # Itinerary agent should depend on all others
        assert "itinerary_agent" in dependencies
        expected_itinerary_deps = ["flight_agent", "hotel_agent", "activity_agent", "food_agent"]
        for dep in expected_itinerary_deps:
            assert dep in dependencies["itinerary_agent"]

        # Verify budget allocation logic
        budget_tracking = initial_state["budget_tracking"]
        assert budget_tracking["total_budget"] == 8000.0
        assert budget_tracking["allocated"] == 8000.0
        assert budget_tracking["spent"] == 0.0
        assert budget_tracking["remaining"] == 8000.0

        # Check budget allocations percentages
        allocations = budget_tracking["allocations"]
        total_allocated = sum(allocations.values())
        assert abs(total_allocated - 8000.0) < 0.01

        # Verify specific percentages
        assert allocations["flights"] == 3200.0  # 40%
        assert allocations["hotels"] == 2400.0  # 30%
        assert allocations["activities"] == 1600.0  # 20%
        assert allocations["food"] == 800.0  # 10%

    @pytest.mark.asyncio
    async def test_workflow_performance_metrics_tracking(self, sample_trip_request_short):
        """Test comprehensive performance metrics tracking."""
        workflow = TripPlanningWorkflow()

        initial_state = workflow.create_initial_state(sample_trip_request_short)

        # Verify initial metrics
        metrics = initial_state["optimization_metrics"]
        assert "execution_time" in metrics
        assert "nodes_executed" in metrics
        assert "parallel_executions" in metrics
        assert "total_api_calls" in metrics
        assert "cache_hits" in metrics
        assert "cache_misses" in metrics

        # Check initial values
        assert metrics["nodes_executed"] == 0
        assert metrics["parallel_executions"] == 0
        assert metrics["total_api_calls"] == 0
        assert metrics["cache_hits"] == 0
        assert metrics["cache_misses"] == 0

    @pytest.mark.asyncio
    async def test_edge_case_empty_results_handling(self, sample_trip_request_short):
        """Test workflow handling when agents return empty results."""
        with (
            patch("travel_companion.workflows.orchestrator.get_settings") as mock_settings,
            patch("travel_companion.workflows.orchestrator.get_redis_manager") as mock_redis_mgr,
            patch("travel_companion.workflows.nodes.WeatherAgent") as mock_weather,
            patch("travel_companion.workflows.nodes.FlightAgent") as mock_flight,
            patch("travel_companion.workflows.nodes.HotelAgent") as mock_hotel,
            patch("travel_companion.workflows.nodes.ActivityAgent") as mock_activity,
            patch("travel_companion.workflows.nodes.FoodAgent") as mock_food,
            patch("travel_companion.workflows.nodes.ItineraryAgent") as mock_itinerary,
        ):
            # Setup mocks
            mock_settings.return_value = MagicMock(
                workflow_timeout_seconds=300, workflow_state_ttl=3600
            )
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis.setex = AsyncMock()
            mock_redis_mgr.return_value = MagicMock(client=mock_redis)

            # Setup agents to return empty results
            weather_mock = AsyncMock()
            weather_mock.process.return_value = WeatherSearchResponse(
                forecast=None, historical_data=[], search_time_ms=100, search_metadata={}
            )
            mock_weather.return_value = weather_mock

            flight_mock = AsyncMock()
            flight_mock.process.return_value = FlightSearchResponse(
                flights=[], search_time_ms=500, search_metadata={}
            )
            mock_flight.return_value = flight_mock

            hotel_mock = AsyncMock()
            hotel_mock.process.return_value = HotelSearchResponse(
                hotels=[], search_time_ms=400, search_metadata={}
            )
            mock_hotel.return_value = hotel_mock

            activity_mock = AsyncMock()
            activity_mock.process.return_value = ActivitySearchResponse(
                activities=[], search_time_ms=300, search_metadata={}
            )
            mock_activity.return_value = activity_mock

            food_mock = AsyncMock()
            food_mock.process.return_value = RestaurantSearchResponse(
                restaurants=[], search_time_ms=200, search_metadata={}, total_results=0
            )
            mock_food.return_value = food_mock

            # Itinerary should handle empty inputs gracefully
            itinerary_mock_obj = AsyncMock()
            minimal_itinerary = MagicMock()
            minimal_itinerary.optimized_itinerary.model_dump.return_value = {
                "trip_id": "minimal_trip",
                "optimization_score": 3.0,  # Low score due to lack of data
            }
            minimal_itinerary.daily_schedules = []
            minimal_itinerary.budget_summary.model_dump.return_value = {
                "total_estimated_cost": {"amount": 0.0, "currency": "USD"}
            }
            minimal_itinerary.optimization_score = 3.0
            minimal_itinerary.recommendations = ["No options found - try different dates"]
            itinerary_mock_obj.process.return_value = minimal_itinerary
            mock_itinerary.return_value = itinerary_mock_obj

            # Execute workflow
            workflow = TripPlanningWorkflow()

            result = await workflow.execute_trip_planning(
                sample_trip_request_short, user_id="empty_results", request_id="empty_test"
            )

            # Verify graceful handling of empty results
            assert "execution_summary" in result
            execution_summary = result["execution_summary"]
            assert execution_summary["status"] == "completed"

            # Results should be empty but structured
            assert "flight_options" in result
            assert "hotel_options" in result
            assert "activity_options" in result
            assert len(result["flight_options"]) == 0
            assert len(result["hotel_options"]) == 0
            assert len(result["activity_options"]) == 0
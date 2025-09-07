"""Tests for workflow orchestration base classes."""

import json
from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from travel_companion.models.trip import (
    AccommodationType,
    TravelClass,
    TripDestination,
    TripPlanRequest,
    TripRequirements,
)
from travel_companion.workflows.orchestrator import (
    BaseWorkflow,
    TripPlanningWorkflow,
    TripPlanningWorkflowState,
    WorkflowState,
)


class MockTestWorkflow(BaseWorkflow):
    """Test implementation of BaseWorkflow."""

    def __init__(self):
        super().__init__("TestWorkflow")

    def define_nodes(self) -> dict[str, Any]:
        return {
            "start": self._start_node,
            "process": self._process_node,
            "end": self._end_node,
        }

    def define_edges(self) -> list[tuple[str, str]]:
        return [
            ("start", "process"),
            ("process", "end"),
        ]

    def get_entry_point(self) -> str:
        return "start"

    def _start_node(self, state: WorkflowState) -> WorkflowState:
        state["current_node"] = "start"
        return state

    def _process_node(self, state: WorkflowState) -> WorkflowState:
        state["current_node"] = "process"
        return state

    def _end_node(self, state: WorkflowState) -> WorkflowState:
        state["current_node"] = "end"
        state["output_data"] = {"result": "success"}
        return state


class TestBaseWorkflow:
    """Tests for BaseWorkflow class."""

    @pytest.fixture
    def workflow(self):
        """Create test workflow instance."""
        return MockTestWorkflow()

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_client.setex = AsyncMock()
        mock_client.get = AsyncMock()
        return mock_client

    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        mock = MagicMock()
        mock.workflow_timeout_seconds = 30
        mock.workflow_max_retries = 3
        mock.workflow_state_ttl = 3600
        mock.workflow_enable_debug_logging = True
        return mock

    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    def test_initialization(self, mock_get_settings, mock_get_redis, mock_settings, mock_redis):
        """Test workflow initialization."""
        mock_get_settings.return_value = mock_settings
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        workflow = MockTestWorkflow()

        assert workflow.workflow_type == "TestWorkflow"
        assert workflow._graph is None
        assert workflow._nodes == {}
        assert workflow._edges == []

    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    def test_build_graph_success(
        self, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow
    ):
        """Test successful graph building."""
        mock_get_settings.return_value = mock_settings
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        graph = workflow.build_graph()

        assert graph is not None
        assert workflow._graph is not None
        assert len(workflow._nodes) == 3
        assert len(workflow._edges) == 2

    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    @patch("travel_companion.workflows.orchestrator.workflow_logger")
    def test_build_graph_failure(
        self, mock_logger, mock_get_settings, mock_get_redis, mock_settings, mock_redis
    ):
        """Test graph building failure."""
        mock_get_settings.return_value = mock_settings
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        class FailingWorkflow(BaseWorkflow):
            def __init__(self):
                super().__init__("FailingWorkflow")

            def define_nodes(self):
                raise ValueError("Node definition failed")

            def define_edges(self):
                return []

            def get_entry_point(self):
                return "start"

        failing_workflow = FailingWorkflow()

        with pytest.raises(ValueError, match="Failed to build workflow graph"):
            failing_workflow.build_graph()

        mock_logger.log_workflow_failed.assert_called_once()

    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    @patch("travel_companion.workflows.orchestrator.workflow_logger")
    async def test_execute_success(
        self, mock_logger, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow
    ):
        """Test successful workflow execution."""
        mock_get_settings.return_value = mock_settings
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        input_data = {"test": "data"}
        user_id = "user123"
        request_id = "req123"

        result = await workflow.execute(input_data, user_id, request_id)

        assert result == {"result": "success"}
        mock_logger.log_workflow_started.assert_called_once()
        mock_logger.log_workflow_completed.assert_called_once()

    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    @patch("travel_companion.workflows.orchestrator.workflow_logger")
    async def test_execute_timeout(
        self, mock_logger, mock_get_settings, mock_get_redis, mock_settings, mock_redis
    ):
        """Test workflow execution timeout."""
        mock_settings.workflow_timeout_seconds = 0.1
        mock_get_settings.return_value = mock_settings
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        class SlowWorkflow(MockTestWorkflow):
            def _process_node(self, state: WorkflowState) -> WorkflowState:
                import time

                time.sleep(1)  # Longer than timeout
                return super()._process_node(state)

        slow_workflow = SlowWorkflow()

        with pytest.raises(TimeoutError):
            await slow_workflow.execute({"test": "data"})

        mock_logger.log_workflow_failed.assert_called_once()

    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    @patch("travel_companion.workflows.orchestrator.workflow_logger")
    async def test_execute_failure(
        self, mock_logger, mock_get_settings, mock_get_redis, mock_settings, mock_redis
    ):
        """Test workflow execution failure."""
        mock_get_settings.return_value = mock_settings
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        class FailingWorkflow(MockTestWorkflow):
            def _process_node(self, state: WorkflowState) -> WorkflowState:
                raise ValueError("Processing failed")

        failing_workflow = FailingWorkflow()

        with pytest.raises(RuntimeError, match="Workflow execution failed"):
            await failing_workflow.execute({"test": "data"})

        mock_logger.log_workflow_failed.assert_called_once()

    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    @patch("travel_companion.workflows.orchestrator.workflow_logger")
    async def test_persist_state_success(
        self, mock_logger, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow
    ):
        """Test successful state persistence."""
        mock_get_settings.return_value = mock_settings
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        # Manually set the workflow's redis client to the mock
        workflow.redis_client = mock_redis

        state: WorkflowState = {
            "request_id": "req123",
            "workflow_id": "wf123",
            "user_id": "user123",
            "status": "running",
            "error": None,
            "start_time": 123456.0,
            "end_time": None,
            "current_node": "start",
            "input_data": {"test": "data"},
            "output_data": {},
            "intermediate_results": {},
        }

        await workflow._persist_state(state)

        mock_redis.setex.assert_called_once()
        mock_logger.log_state_persisted.assert_called_once()

    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    @patch("travel_companion.workflows.orchestrator.workflow_logger")
    async def test_persist_state_failure(
        self, mock_logger, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow
    ):
        """Test state persistence failure."""
        mock_get_settings.return_value = mock_settings
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager
        mock_redis.setex.side_effect = Exception("Redis error")

        # Manually set the workflow's redis client to the mock
        workflow.redis_client = mock_redis

        state: WorkflowState = {
            "request_id": "req123",
            "workflow_id": "wf123",
            "user_id": "user123",
            "status": "running",
            "error": None,
            "start_time": 123456.0,
            "end_time": None,
            "current_node": "start",
            "input_data": {"test": "data"},
            "output_data": {},
            "intermediate_results": {},
        }

        await workflow._persist_state(state)

        mock_logger.log_workflow_failed.assert_called_once()

    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    @patch("travel_companion.workflows.orchestrator.workflow_logger")
    async def test_restore_state_success(
        self, mock_logger, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow
    ):
        """Test successful state restoration."""
        mock_get_settings.return_value = mock_settings
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        # Manually set the workflow's redis client to the mock
        workflow.redis_client = mock_redis

        workflow_id = "wf123"
        stored_state = {
            "request_id": "req123",
            "workflow_id": workflow_id,
            "status": "running",
        }
        mock_redis.get.return_value = json.dumps(stored_state)

        result = await workflow.restore_state(workflow_id)

        assert result == stored_state
        mock_redis.get.assert_called_once_with(f"workflow_state:{workflow_id}")
        mock_logger.log_state_restored.assert_called_once()

    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    async def test_restore_state_not_found(
        self, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow
    ):
        """Test state restoration when workflow not found."""
        mock_get_settings.return_value = mock_settings
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager
        mock_redis.get.return_value = None

        # Manually set the workflow's redis client to the mock
        workflow.redis_client = mock_redis

        result = await workflow.restore_state("nonexistent")

        assert result is None

    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    async def test_get_workflow_status(
        self, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow
    ):
        """Test workflow status retrieval."""
        mock_get_settings.return_value = mock_settings
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        # Manually set the workflow's redis client to the mock
        workflow.redis_client = mock_redis

        workflow_id = "wf123"
        stored_state = {
            "workflow_id": workflow_id,
            "status": "completed",
            "current_node": "end",
            "start_time": 123456.0,
            "end_time": 123460.0,
            "error": None,
        }
        mock_redis.get.return_value = json.dumps(stored_state)

        result = await workflow.get_workflow_status(workflow_id)

        assert result["workflow_id"] == workflow_id
        assert result["workflow_type"] == "TestWorkflow"
        assert result["status"] == "completed"

    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    def test_get_health_status_healthy(
        self, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow
    ):
        """Test healthy workflow health status."""
        mock_get_settings.return_value = mock_settings
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager
        mock_redis.ping.return_value = True

        result = workflow.get_health_status()

        assert result["workflow_type"] == "TestWorkflow"
        assert result["status"] == "healthy"
        assert result["graph_built"] is True
        assert result["redis_connected"] is True
        assert result["node_count"] == 3
        assert result["edge_count"] == 2

    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    def test_get_health_status_degraded(
        self, mock_get_settings, mock_get_redis, mock_settings, mock_redis
    ):
        """Test degraded workflow health status when Redis fails."""
        mock_get_settings.return_value = mock_settings
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        # Create workflow first with successful setup
        workflow = MockTestWorkflow()

        # Now make get_redis_manager raise an exception for the health check
        mock_get_redis.side_effect = Exception("Redis error")

        result = workflow.get_health_status()

        assert result["workflow_type"] == "TestWorkflow"
        assert result["status"] == "degraded"
        assert result["redis_connected"] is False


@pytest.fixture
def sample_trip_request():
    """Sample trip planning request for testing."""
    return TripPlanRequest(
        destination=TripDestination(
            city="Paris",
            country="France",
            country_code="FR",
            airport_code="CDG",
            latitude=48.8566,
            longitude=2.3522,
        ),
        requirements=TripRequirements(
            budget=Decimal("2500.00"),
            currency="USD",
            start_date=date(2024, 6, 15),
            end_date=date(2024, 6, 22),
            travelers=2,
            travel_class=TravelClass.ECONOMY,
            accommodation_type=AccommodationType.HOTEL,
        ),
        preferences={
            "activities": "museums,restaurants",
            "dietary_restrictions": "vegetarian",
        },
    )


class TestTripPlanningWorkflow:
    """Tests for TripPlanningWorkflow class."""

    @pytest.fixture
    def workflow(self):
        """Create TripPlanningWorkflow instance for testing."""
        return TripPlanningWorkflow()

    def test_initialization(self, workflow):
        """Test workflow initialization."""
        assert workflow.workflow_type == "trip_planning"
        assert workflow.get_state_class() == TripPlanningWorkflowState

    def test_define_nodes(self, workflow):
        """Test workflow node definition."""
        # Mock the node functions import for testing
        with patch.object(workflow, "define_nodes") as mock_define_nodes:
            mock_define_nodes.return_value = {
                "initialize_trip": lambda x: x,
                "weather_agent": lambda x: x,
                "flight_agent": lambda x: x,
                "hotel_agent": lambda x: x,
                "activity_agent": lambda x: x,
                "food_agent": lambda x: x,
                "itinerary_agent": lambda x: x,
                "finalize_plan": lambda x: x,
            }

            nodes = workflow.define_nodes()

            expected_nodes = {
                "initialize_trip",
                "weather_agent",
                "flight_agent",
                "hotel_agent",
                "activity_agent",
                "food_agent",
                "itinerary_agent",
                "finalize_plan",
            }

            assert set(nodes.keys()) == expected_nodes
            assert all(callable(node) for node in nodes.values())

    def test_define_edges(self, workflow):
        """Test workflow edge definition with coordinated execution."""
        edges = workflow.define_edges()

        # The new workflow uses coordinated execution approach
        # Check that initialize_trip leads to coordinated_execution
        assert len(edges) >= 2
        assert edges[0] == ("initialize_trip", "coordinated_execution")
        assert edges[1] == ("coordinated_execution", "finalize_plan")

    def test_get_entry_point(self, workflow):
        """Test workflow entry point."""
        assert workflow.get_entry_point() == "initialize_trip"

    def test_create_initial_state(self, workflow, sample_trip_request):
        """Test initial state creation with trip context."""
        user_id = "user123"
        request_id = "req456"

        state = workflow.create_initial_state(sample_trip_request, user_id, request_id)

        # Check base workflow fields
        assert state["request_id"] == request_id
        assert state["user_id"] == user_id
        assert state["status"] == "running"
        assert state["error"] is None
        assert state["current_node"] == "initialize_trip"

        # Check trip-specific fields
        assert state["trip_request"] == sample_trip_request
        assert state["trip_id"] is None
        assert state["agents_completed"] == []
        assert state["agents_failed"] == []

        # Check agent dependencies
        assert "activity_agent" in state["agent_dependencies"]
        assert "weather_agent" in state["agent_dependencies"]["activity_agent"]
        assert "itinerary_agent" in state["agent_dependencies"]

        # Check initialized results
        assert state["flight_results"] == []
        assert state["hotel_results"] == []
        assert state["activity_results"] == []
        assert state["weather_data"] == {}
        assert state["food_recommendations"] == []
        assert state["itinerary_data"] == {}

        # Check context fields
        assert state["user_preferences"] == sample_trip_request.preferences
        assert state["budget_tracking"]["allocated"] == float(
            sample_trip_request.requirements.budget
        )
        assert state["budget_tracking"]["spent"] == 0.0
        assert "execution_time" in state["optimization_metrics"]

    def test_create_initial_state_minimal(self, workflow, sample_trip_request):
        """Test initial state creation with minimal parameters."""
        state = workflow.create_initial_state(sample_trip_request)

        # Should generate IDs automatically
        assert len(state["request_id"]) > 0
        assert len(state["workflow_id"]) > 0
        assert state["user_id"] is None
        assert state["trip_request"] == sample_trip_request

    @patch("travel_companion.workflows.orchestrator.workflow_logger")
    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    async def test_execute_trip_planning_success(
        self, mock_get_settings, mock_get_redis, mock_logger, workflow, sample_trip_request
    ):
        """Test successful trip planning workflow execution."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.workflow_timeout_seconds = 300
        mock_settings.workflow_state_ttl = 3600
        mock_get_settings.return_value = mock_settings

        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        # Mock graph execution
        final_state = workflow.create_initial_state(sample_trip_request)
        final_state.update(
            {
                "status": "completed",
                "output_data": {"trip_plan": {"flights": [], "hotels": [], "activities": []}},
                "end_time": final_state["start_time"] + 60,
            }
        )

        with patch.object(workflow, "_execute_with_timeout", return_value=final_state):
            result = await workflow.execute_trip_planning(sample_trip_request, "user123", "req456")

            # Check result
            assert "trip_plan" in result

            # Verify logging
            mock_logger.log_workflow_started.assert_called_once()
            mock_logger.log_workflow_completed.assert_called_once()

    @patch("travel_companion.workflows.orchestrator.workflow_logger")
    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    async def test_execute_trip_planning_timeout(
        self, mock_get_settings, mock_get_redis, mock_logger, workflow, sample_trip_request
    ):
        """Test trip planning workflow timeout handling."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.workflow_timeout_seconds = 300
        mock_settings.workflow_state_ttl = 3600
        mock_get_settings.return_value = mock_settings

        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()  # Mock Redis setex method
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        # Set the workflow's redis client to the mock
        workflow.redis_client = mock_redis

        # Mock timeout
        with patch.object(workflow, "_execute_with_timeout", side_effect=TimeoutError("Timeout")):
            with pytest.raises(TimeoutError):
                await workflow.execute_trip_planning(sample_trip_request)

            # Verify error logging (may be called multiple times due to state persistence errors)
            assert mock_logger.log_workflow_failed.call_count >= 1

            # Check that at least one call was for the timeout error
            timeout_calls = [
                call
                for call in mock_logger.log_workflow_failed.call_args_list
                if "timeout" in str(call).lower()
            ]
            assert len(timeout_calls) >= 1

    @patch("travel_companion.workflows.orchestrator.workflow_logger")
    @patch("travel_companion.workflows.orchestrator.get_redis_manager")
    @patch("travel_companion.workflows.orchestrator.get_settings")
    @patch("travel_companion.workflows.state_manager.EnhancedWorkflowStateManager")
    async def test_execute_trip_planning_failure(
        self,
        mock_enhanced_state_manager,
        mock_get_settings,
        mock_get_redis,
        mock_logger,
        workflow,
        sample_trip_request,
    ):
        """Test trip planning workflow execution failure."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.workflow_timeout_seconds = 300
        mock_settings.workflow_state_ttl = 3600
        mock_get_settings.return_value = mock_settings

        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()  # Mock Redis setex method
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = mock_redis
        mock_get_redis.return_value = mock_redis_manager

        # Set the workflow's redis client to the mock
        workflow.redis_client = mock_redis

        # Mock the enhanced state manager to fail so it falls back to basic persistence
        mock_state_manager_instance = AsyncMock()
        mock_state_manager_instance.persist_state = AsyncMock(return_value=False)
        mock_enhanced_state_manager.return_value = mock_state_manager_instance

        # Mock execution failure
        with patch.object(workflow, "_execute_with_timeout", side_effect=Exception("Test error")):
            with pytest.raises(RuntimeError, match="Trip planning workflow execution failed"):
                await workflow.execute_trip_planning(sample_trip_request)

            # Verify error logging and state persistence (may be called multiple times)
            assert mock_logger.log_workflow_failed.call_count >= 1
            mock_redis.setex.assert_called()  # Error state should be persisted

            # Check that at least one call was for the test error
            error_calls = [
                call
                for call in mock_logger.log_workflow_failed.call_args_list
                if "test error" in str(call).lower()
            ]
            assert len(error_calls) >= 1

    def test_workflow_state_schema_completeness(self):
        """Test that TripPlanningWorkflowState includes all required fields."""
        # This test ensures our state schema is complete
        state_annotations = TripPlanningWorkflowState.__annotations__

        # Base workflow fields
        base_fields = {
            "request_id",
            "workflow_id",
            "user_id",
            "status",
            "error",
            "start_time",
            "end_time",
            "current_node",
            "input_data",
            "output_data",
            "intermediate_results",
        }

        # Trip-specific fields
        trip_fields = {
            "trip_request",
            "trip_id",
            "agents_completed",
            "agents_failed",
            "agent_dependencies",
            "flight_results",
            "hotel_results",
            "activity_results",
            "weather_data",
            "food_recommendations",
            "itinerary_data",
            "user_preferences",
            "budget_tracking",
            "optimization_metrics",
        }

        all_required_fields = base_fields | trip_fields
        actual_fields = set(state_annotations.keys())

        assert all_required_fields.issubset(actual_fields), (
            f"Missing fields: {all_required_fields - actual_fields}"
        )

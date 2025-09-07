"""Tests for workflow API integration endpoints."""

import time
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from travel_companion.models.trip import (
    TravelClass,
    TripDestination,
    TripPlanRequest,
    TripRequirements,
)
from travel_companion.models.user import User
from travel_companion.workflows.orchestrator import TripPlanningWorkflow


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    return User(
        user_id=UUID("12345678-1234-1234-1234-123456789012"),
        email="test@example.com",
        full_name="Test User",
        password_hash="$2b$12$dummy_hash_for_testing",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_trip_request():
    """Create a sample trip planning request."""
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
            budget=Decimal("3000.00"),
            currency="EUR",
            start_date=date(2024, 7, 1),
            end_date=date(2024, 7, 7),
            travelers=2,
            travel_class=TravelClass.ECONOMY,
            accommodation_type="hotel",
        ),
        preferences={
            "activities": ["sightseeing", "museums"],
            "food": ["french", "cafe"],
        },
    )


@pytest.fixture
def workflow_execution_request(sample_trip_request):
    """Create a workflow execution request."""
    return {
        "input_data": {
            "destination": sample_trip_request.destination.model_dump(),
            "requirements": sample_trip_request.requirements.model_dump(mode="json"),
            "preferences": sample_trip_request.preferences,
        },
        "user_id": "12345678-1234-1234-1234-123456789012",
        "request_id": str(uuid4()),
    }


class TestTripPlanningIntegration:
    """Test trip planning endpoint with workflow integration."""

    def test_generate_trip_plan_success(
        self, authenticated_client: TestClient, sample_trip_request
    ):
        """Test successful trip plan generation."""
        with patch.object(
            TripPlanningWorkflow, "execute_trip_planning", new_callable=AsyncMock
        ) as mock_execute:
            # Mock successful workflow execution - return minimal data for API testing
            mock_execute.return_value = {
                "trip_id": str(uuid4()),
                "itinerary_data": None,  # Simplified for API integration testing
            }

            response = authenticated_client.post(
                "/api/v1/trips/plan",
                json=sample_trip_request.model_dump(mode="json"),
            )

            if response.status_code != 200:
                print(f"Response error: {response.json()}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Trip plan generated successfully"
            assert "data" in data
            assert data["data"]["destination"]["city"] == "Paris"
            # Plan can be None in simplified test
            assert "plan" in data["data"]

    def test_generate_trip_plan_timeout(
        self, authenticated_client: TestClient, sample_trip_request
    ):
        """Test trip plan generation timeout handling."""
        with patch.object(
            TripPlanningWorkflow, "execute_trip_planning", new_callable=AsyncMock
        ) as mock_execute:
            # Mock timeout error
            mock_execute.side_effect = TimeoutError("Workflow execution exceeded timeout")

            response = authenticated_client.post(
                "/api/v1/trips/plan",
                json=sample_trip_request.model_dump(mode="json"),
            )

            assert response.status_code == status.HTTP_408_REQUEST_TIMEOUT
            data = response.json()
            assert data["detail"]["error_code"] == "WORKFLOW_TIMEOUT"

    def test_generate_trip_plan_error(self, authenticated_client: TestClient, sample_trip_request):
        """Test trip plan generation error handling."""
        with patch.object(
            TripPlanningWorkflow, "execute_trip_planning", new_callable=AsyncMock
        ) as mock_execute:
            # Mock execution error
            mock_execute.side_effect = RuntimeError("Agent execution failed")

            response = authenticated_client.post(
                "/api/v1/trips/plan",
                json=sample_trip_request.model_dump(mode="json"),
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert data["detail"]["error_code"] == "TRIP_PLANNING_ERROR"


class TestWorkflowExecutionEndpoints:
    """Test workflow execution endpoints."""

    def test_execute_workflow_sync(self, client: TestClient, workflow_execution_request):
        """Test synchronous workflow execution."""
        with patch.object(
            TripPlanningWorkflow, "execute_trip_planning", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = {
                "workflow_id": str(uuid4()),
                "status": "completed",
                "itinerary_data": {"test": "data"},
            }

            response = client.post(
                "/api/v1/workflows/execute",
                json=workflow_execution_request,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "completed"
            assert data["workflow_type"] == "TripPlanningWorkflow"
            assert "execution_time_ms" in data

    @pytest.mark.skip(
        reason="Redis connection causes hanging - needs Redis service running or comprehensive mocking"
    )
    def test_execute_workflow_async(self, client: TestClient, workflow_execution_request):
        """Test asynchronous workflow execution."""
        # This test hangs because WorkflowStateManager tries to connect to Redis
        # during initialization. The Redis connection happens at import time and
        # requires either:
        # 1. A running Redis service, or
        # 2. More comprehensive mocking at the module import level

        # TODO: Fix by either:
        # - Setting up Redis in test environment
        # - Creating a test-specific WorkflowStateManager that doesn't use Redis
        # - Mocking Redis at the module level before any imports
        pass


class TestWorkflowStatusEndpoints:
    """Test workflow status and progress endpoints."""

    def test_get_workflow_status(self, client: TestClient):
        """Test getting workflow status."""
        workflow_id = str(uuid4())

        with patch.object(
            TripPlanningWorkflow, "get_workflow_status", new_callable=AsyncMock
        ) as mock_status:
            mock_status.return_value = {
                "workflow_id": workflow_id,
                "status": "running",
                "current_node": "execute_flight_agent",
                "start_time": time.time(),
                "workflow_type": "TripPlanningWorkflow",
            }

            response = client.get(f"/api/v1/workflows/status/{workflow_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["workflow_id"] == workflow_id
            assert data["status"] == "running"
            assert data["workflow_type"] == "TripPlanningWorkflow"

    def test_get_workflow_status_not_found(self, client: TestClient):
        """Test getting status for non-existent workflow."""
        workflow_id = str(uuid4())

        with patch.object(
            TripPlanningWorkflow, "get_workflow_status", new_callable=AsyncMock
        ) as mock_status:
            mock_status.return_value = None

            response = client.get(f"/api/v1/workflows/status/{workflow_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert data["detail"]["error"] == "WORKFLOW_NOT_FOUND"

    def test_get_workflow_progress(self, client: TestClient):
        """Test getting workflow progress."""
        workflow_id = str(uuid4())

        with patch("travel_companion.api.v1.workflows.WorkflowStateManager") as mock_sm:
            mock_state_manager = AsyncMock()
            mock_sm.return_value = mock_state_manager
            mock_state_manager.get_progress = AsyncMock(
                return_value={
                    "workflow_id": workflow_id,
                    "percentage_complete": 60,
                    "current_phase": "agent_execution",
                    "agents_completed": ["weather_agent", "flight_agent"],
                    "agents_pending": ["hotel_agent", "activity_agent"],
                    "estimated_completion_time": 15.5,
                }
            )

            response = client.get(f"/api/v1/workflows/progress/{workflow_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["workflow_id"] == workflow_id
            assert data["percentage_complete"] == 60
            assert len(data["agents_completed"]) == 2

    def test_get_workflow_result(self, client: TestClient):
        """Test getting workflow results."""
        workflow_id = str(uuid4())

        with patch("travel_companion.api.v1.workflows.WorkflowStateManager") as mock_sm:
            mock_state_manager = AsyncMock()
            mock_sm.return_value = mock_state_manager
            mock_state_manager.restore_state = AsyncMock(
                return_value={
                    "workflow_id": workflow_id,
                    "status": "completed",
                    "start_time": time.time() - 30,
                    "end_time": time.time(),
                    "output_data": {
                        "itinerary": "test_data",
                        "success": True,
                    },
                }
            )

            response = client.get(f"/api/v1/workflows/result/{workflow_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["workflow_id"] == workflow_id
            assert data["status"] == "completed"
            assert data["output_data"]["success"] is True
            assert "execution_time_ms" in data

    def test_get_workflow_result_not_ready(self, client: TestClient):
        """Test getting results for still-running workflow."""
        workflow_id = str(uuid4())

        with patch("travel_companion.api.v1.workflows.WorkflowStateManager") as mock_sm:
            mock_state_manager = AsyncMock()
            mock_sm.return_value = mock_state_manager
            mock_state_manager.restore_state = AsyncMock(
                return_value={
                    "workflow_id": workflow_id,
                    "status": "running",
                }
            )

            response = client.get(f"/api/v1/workflows/result/{workflow_id}")

            assert response.status_code == status.HTTP_425_TOO_EARLY
            data = response.json()
            assert data["detail"]["error"] == "WORKFLOW_NOT_COMPLETED"


class TestWorkflowManagementEndpoints:
    """Test workflow cancellation and cleanup endpoints."""

    def test_cancel_workflow(self, client: TestClient):
        """Test cancelling a running workflow."""
        workflow_id = str(uuid4())

        with (
            patch("travel_companion.api.v1.workflows.WorkflowStateManager") as mock_sm,
            patch("travel_companion.api.v1.workflows.workflow_logger"),
        ):
            mock_state_manager = AsyncMock()
            mock_sm.return_value = mock_state_manager
            mock_state_manager.restore_state = AsyncMock(
                return_value={
                    "workflow_id": workflow_id,
                    "status": "running",
                    "request_id": str(uuid4()),
                }
            )
            mock_state_manager.persist_state = AsyncMock(return_value=True)

            response = client.post(f"/api/v1/workflows/cancel/{workflow_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["workflow_id"] == workflow_id
            assert data["message"] == "Workflow cancelled successfully"
            assert data["status"] == "cancelled"

    def test_cancel_completed_workflow(self, client: TestClient):
        """Test cancelling an already completed workflow."""
        workflow_id = str(uuid4())

        with patch("travel_companion.api.v1.workflows.WorkflowStateManager") as mock_sm:
            mock_state_manager = AsyncMock()
            mock_sm.return_value = mock_state_manager
            mock_state_manager.restore_state = AsyncMock(
                return_value={
                    "workflow_id": workflow_id,
                    "status": "completed",
                }
            )

            response = client.post(f"/api/v1/workflows/cancel/{workflow_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "Workflow already completed"

    def test_cleanup_workflow(self, client: TestClient):
        """Test cleaning up workflow data."""
        workflow_id = str(uuid4())

        with (
            patch("travel_companion.api.v1.workflows.WorkflowStateManager") as mock_sm,
            patch("travel_companion.api.v1.workflows.workflow_logger"),
        ):
            mock_state_manager = AsyncMock()
            mock_sm.return_value = mock_state_manager
            mock_state_manager.cleanup_workflow = AsyncMock(return_value=True)

            response = client.delete(f"/api/v1/workflows/cleanup/{workflow_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["workflow_id"] == workflow_id
            assert data["message"] == "Workflow data cleaned up successfully"

    def test_cleanup_nonexistent_workflow(self, client: TestClient):
        """Test cleaning up non-existent workflow."""
        workflow_id = str(uuid4())

        with patch("travel_companion.api.v1.workflows.WorkflowStateManager") as mock_sm:
            mock_state_manager = AsyncMock()
            mock_sm.return_value = mock_state_manager
            mock_state_manager.cleanup_workflow = AsyncMock(return_value=False)

            response = client.delete(f"/api/v1/workflows/cleanup/{workflow_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert data["detail"]["error"] == "WORKFLOW_NOT_FOUND"


class TestWorkflowHealthEndpoint:
    """Test workflow health check endpoint."""

    def test_workflow_health_check_healthy(self, client: TestClient):
        """Test health check when workflow is healthy."""
        with patch.object(TripPlanningWorkflow, "get_health_status") as mock_health:
            mock_health.return_value = {
                "workflow_type": "trip_planning",
                "status": "healthy",
                "graph_built": True,
                "redis_connected": True,
                "node_count": 8,
                "edge_count": 10,
            }

            response = client.get("/api/v1/workflows/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "healthy"
            assert data["redis_connected"] is True
            assert data["total_workflows"] == 1

    def test_workflow_health_check_degraded(self, client: TestClient):
        """Test health check when workflow is degraded."""
        with patch.object(TripPlanningWorkflow, "get_health_status") as mock_health:
            mock_health.return_value = {
                "workflow_type": "trip_planning",
                "status": "degraded",
                "graph_built": True,
                "redis_connected": False,
                "node_count": 8,
                "edge_count": 10,
            }

            response = client.get("/api/v1/workflows/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "unhealthy"  # Redis failure makes it unhealthy
            assert data["redis_connected"] is False

    def test_workflow_health_check_error(self, client: TestClient):
        """Test health check when there's an error."""
        with patch.object(TripPlanningWorkflow, "get_health_status") as mock_health:
            mock_health.side_effect = Exception("Health check failed")

            response = client.get("/api/v1/workflows/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["redis_connected"] is False
            assert data["total_workflows"] == 0

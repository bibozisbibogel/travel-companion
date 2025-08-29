"""Tests for workflow API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from travel_companion.main import app


class TestWorkflowAPI:
    """Tests for workflow API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def sample_workflow_request(self):
        """Create sample workflow execution request."""
        return {
            "input_data": {
                "destination": "Paris, France",
                "travel_dates": {"start": "2024-06-01", "end": "2024-06-07"},
                "budget": 2000,
                "preferences": {
                    "accommodation_type": "hotel",
                    "activity_types": ["cultural", "culinary"],
                },
            },
            "user_id": "user123",
            "request_id": "req123",
        }

    @pytest.fixture
    def mock_workflow_result(self):
        """Create mock workflow execution result."""
        return {
            "workflow_id": "wf123",
            "request_id": "req123",
            "execution_summary": {
                "start_time": 1234567890.0,
                "processing_time_ms": 150.5,
                "nodes_executed": ["start", "process", "end"],
                "status": "completed",
            },
            "results": {
                "process_results": {
                    "original_input": {"destination": "Paris, France"},
                    "processed_at": 1234567890.1,
                    "processing_node": "process",
                    "workflow_id": "wf123",
                }
            },
            "input_echo": {"destination": "Paris, France"},
        }

    @patch("travel_companion.api.v1.workflows.TravelPlanningWorkflow")
    def test_execute_workflow_success(
        self, mock_workflow_class, client, sample_workflow_request, mock_workflow_result
    ):
        """Test successful workflow execution."""
        # Mock workflow instance and execution
        mock_workflow = AsyncMock()
        mock_workflow.execute.return_value = mock_workflow_result
        mock_workflow_class.return_value = mock_workflow

        response = client.post("/api/v1/workflows/execute", json=sample_workflow_request)

        assert response.status_code == 200
        data = response.json()

        assert data["workflow_id"] == "wf123"
        assert data["request_id"] == "req123"
        assert data["status"] == "completed"
        assert data["workflow_type"] == "TravelPlanningWorkflow"
        assert "execution_time_ms" in data
        assert data["output_data"] == mock_workflow_result

        # Verify workflow was called correctly
        mock_workflow.execute.assert_called_once_with(
            input_data=sample_workflow_request["input_data"], user_id="user123", request_id="req123"
        )

    @patch("travel_companion.api.v1.workflows.TravelPlanningWorkflow")
    def test_execute_workflow_timeout(self, mock_workflow_class, client, sample_workflow_request):
        """Test workflow execution timeout."""
        mock_workflow = AsyncMock()
        mock_workflow.execute.side_effect = TimeoutError("Workflow timeout")
        mock_workflow_class.return_value = mock_workflow

        response = client.post("/api/v1/workflows/execute", json=sample_workflow_request)

        assert response.status_code == 408
        data = response.json()
        assert data["detail"]["error"] == "WORKFLOW_TIMEOUT"
        assert "timeout limit" in data["detail"]["message"]

    @patch("travel_companion.api.v1.workflows.TravelPlanningWorkflow")
    def test_execute_workflow_failure(self, mock_workflow_class, client, sample_workflow_request):
        """Test workflow execution failure."""
        mock_workflow = AsyncMock()
        mock_workflow.execute.side_effect = RuntimeError("Workflow failed")
        mock_workflow_class.return_value = mock_workflow

        response = client.post("/api/v1/workflows/execute", json=sample_workflow_request)

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "WORKFLOW_EXECUTION_FAILED"
        assert "encountered an error" in data["detail"]["message"]

    def test_execute_workflow_invalid_input(self, client):
        """Test workflow execution with invalid input."""
        invalid_request = {
            "input_data": "invalid_data_type"  # Should be dict
        }

        response = client.post("/api/v1/workflows/execute", json=invalid_request)

        assert response.status_code == 422  # Validation error

    def test_execute_workflow_missing_input_data(self, client):
        """Test workflow execution with missing required fields."""
        incomplete_request = {
            "user_id": "user123"
            # Missing input_data
        }

        response = client.post("/api/v1/workflows/execute", json=incomplete_request)

        assert response.status_code == 422  # Validation error

    @patch("travel_companion.api.v1.workflows.TravelPlanningWorkflow")
    def test_get_workflow_status_success(self, mock_workflow_class, client):
        """Test successful workflow status retrieval."""
        mock_workflow = AsyncMock()
        mock_status = {
            "workflow_id": "wf123",
            "workflow_type": "TravelPlanningWorkflow",
            "status": "completed",
            "current_node": "end",
            "start_time": 1234567890.0,
            "end_time": 1234567920.0,
            "error": None,
        }
        mock_workflow.get_workflow_status.return_value = mock_status
        mock_workflow_class.return_value = mock_workflow

        response = client.get("/api/v1/workflows/status/wf123")

        assert response.status_code == 200
        data = response.json()
        assert data == mock_status
        mock_workflow.get_workflow_status.assert_called_once_with("wf123")

    @patch("travel_companion.api.v1.workflows.TravelPlanningWorkflow")
    def test_get_workflow_status_not_found(self, mock_workflow_class, client):
        """Test workflow status when workflow not found."""
        mock_workflow = AsyncMock()
        mock_workflow.get_workflow_status.return_value = None
        mock_workflow_class.return_value = mock_workflow

        response = client.get("/api/v1/workflows/status/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "WORKFLOW_NOT_FOUND"
        assert "nonexistent" in data["detail"]["message"]

    @patch("travel_companion.api.v1.workflows.TravelPlanningWorkflow")
    def test_get_workflow_status_error(self, mock_workflow_class, client):
        """Test workflow status retrieval with error."""
        mock_workflow = AsyncMock()
        mock_workflow.get_workflow_status.side_effect = Exception("Database error")
        mock_workflow_class.return_value = mock_workflow

        response = client.get("/api/v1/workflows/status/wf123")

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "STATUS_CHECK_FAILED"
        assert data["detail"]["workflow_id"] == "wf123"

    @patch("travel_companion.api.v1.workflows.TravelPlanningWorkflow")
    def test_get_workflow_health_success(self, mock_workflow_class, client):
        """Test successful workflow health check."""
        mock_workflow = MagicMock()
        mock_health = {
            "workflow_type": "TravelPlanningWorkflow",
            "status": "healthy",
            "graph_built": True,
            "redis_connected": True,
            "node_count": 3,
            "edge_count": 2,
        }
        mock_workflow.get_health_status.return_value = mock_health
        mock_workflow_class.return_value = mock_workflow

        response = client.get("/api/v1/workflows/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["redis_connected"] is True
        assert data["total_workflows"] == 1
        assert len(data["workflows"]) == 1
        assert data["workflows"][0] == mock_health
        assert "timestamp" in data

    @patch("travel_companion.api.v1.workflows.TravelPlanningWorkflow")
    def test_get_workflow_health_degraded(self, mock_workflow_class, client):
        """Test workflow health check with degraded status."""
        mock_workflow = MagicMock()
        mock_health = {
            "workflow_type": "TravelPlanningWorkflow",
            "status": "degraded",
            "graph_built": True,
            "redis_connected": False,  # Redis issue
            "node_count": 3,
            "edge_count": 2,
        }
        mock_workflow.get_health_status.return_value = mock_health
        mock_workflow_class.return_value = mock_workflow

        response = client.get("/api/v1/workflows/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "unhealthy"
        assert data["redis_connected"] is False
        assert data["workflows"][0]["status"] == "degraded"

    @patch("travel_companion.api.v1.workflows.TravelPlanningWorkflow")
    def test_get_workflow_health_error(self, mock_workflow_class, client):
        """Test workflow health check with error."""
        mock_workflow_class.side_effect = Exception("Initialization error")

        response = client.get("/api/v1/workflows/health")

        assert response.status_code == 200  # Health endpoint should not fail
        data = response.json()

        assert data["status"] == "unhealthy"
        assert data["redis_connected"] is False
        assert data["total_workflows"] == 0
        assert len(data["workflows"]) == 1
        assert data["workflows"][0]["status"] == "unhealthy"
        assert "error" in data["workflows"][0]

    def test_workflow_execute_endpoint_path(self, client):
        """Test that workflow execute endpoint is properly routed."""
        # Test with minimal valid data to check routing
        minimal_request = {"input_data": {"test": "data"}}

        # Should reach the endpoint (may fail due to mock setup, but routing should work)
        response = client.post("/api/v1/workflows/execute", json=minimal_request)

        # Should not be 404 (route exists)
        assert response.status_code != 404

    @patch("travel_companion.api.v1.workflows.TravelPlanningWorkflow")
    def test_workflow_status_endpoint_path(self, mock_workflow_class, client):
        """Test that workflow status endpoint is properly routed."""
        # Mock the workflow to avoid Redis connection issues
        mock_workflow = MagicMock()
        mock_workflow.get_workflow_status.return_value = {
            "workflow_id": "test123",
            "workflow_type": "TravelPlanningWorkflow",
            "status": "running",
            "current_node": "start",
            "start_time": 12345.0,
            "end_time": None,
            "error": None,
        }
        mock_workflow_class.return_value = mock_workflow

        response = client.get("/api/v1/workflows/status/test123")

        # Should not be 404 (route exists)
        assert response.status_code != 404

    def test_workflow_health_endpoint_path(self, client):
        """Test that workflow health endpoint is properly routed."""
        response = client.get("/api/v1/workflows/health")

        # Should not be 404 (route exists)
        assert response.status_code != 404

    @patch("travel_companion.api.v1.workflows.TravelPlanningWorkflow")
    def test_execute_workflow_optional_fields(
        self, mock_workflow_class, client, mock_workflow_result
    ):
        """Test workflow execution with optional fields."""
        mock_workflow = AsyncMock()
        mock_workflow.execute.return_value = mock_workflow_result
        mock_workflow_class.return_value = mock_workflow

        # Request without optional fields
        minimal_request = {"input_data": {"destination": "London"}}

        response = client.post("/api/v1/workflows/execute", json=minimal_request)

        assert response.status_code == 200

        # Verify workflow was called with None for optional fields
        mock_workflow.execute.assert_called_once_with(
            input_data=minimal_request["input_data"], user_id=None, request_id=None
        )

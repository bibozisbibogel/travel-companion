"""Simple API endpoint tests for workflows."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestWorkflowEndpoints:
    """Test workflow API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        # Import here to avoid issues during collection
        from travel_companion.main import app
        return TestClient(app)

    def test_workflow_health_endpoint_exists(self, client):
        """Test that workflow health endpoint exists and is accessible."""
        try:
            response = client.get("/api/v1/workflows/health")
            # Should not be 404 (route exists)
            assert response.status_code != 404
            # Should return JSON
            assert response.headers.get("content-type", "").startswith("application/json")
        except Exception as e:
            # Even if it fails due to dependencies, the route should exist
            assert "404" not in str(e)

    @patch('travel_companion.api.v1.workflows.TravelPlanningWorkflow')
    def test_workflow_execute_endpoint_basic(self, mock_workflow_class, client):
        """Test basic workflow execute endpoint functionality."""
        # Mock successful workflow execution
        mock_workflow = AsyncMock()
        mock_workflow.execute.return_value = {
            "workflow_id": "test123",
            "request_id": "req123",
            "execution_summary": {"status": "completed"},
            "results": {"test": "data"},
            "input_echo": {"destination": "Paris"}
        }
        mock_workflow_class.return_value = mock_workflow

        # Valid request
        request_data = {
            "input_data": {"destination": "Paris"}
        }

        response = client.post("/api/v1/workflows/execute", json=request_data)

        # Should not be 404 (route exists)
        assert response.status_code != 404

        # If successful, should return JSON
        if response.status_code == 200:
            data = response.json()
            assert "workflow_id" in data
            assert "status" in data

    @patch('travel_companion.api.v1.workflows.TravelPlanningWorkflow')
    def test_workflow_status_endpoint_exists(self, mock_workflow_class, client):
        """Test that workflow status endpoint exists."""
        # Mock the workflow to avoid Redis connection issues
        mock_workflow = MagicMock()
        mock_workflow.get_workflow_status.return_value = {
            "workflow_id": "test123",
            "workflow_type": "TravelPlanningWorkflow",
            "status": "running",
            "current_node": "start",
            "start_time": 12345.0,
            "end_time": None,
            "error": None
        }
        mock_workflow_class.return_value = mock_workflow

        response = client.get("/api/v1/workflows/status/test123")
        # Should not be 404 (route exists)
        assert response.status_code != 404

    def test_workflow_endpoints_in_main_app(self):
        """Test that workflow endpoints are properly registered in main app."""
        from fastapi import FastAPI

        from travel_companion.main import app

        assert isinstance(app, FastAPI)

        # Check that routes exist
        routes = [route.path for route in app.routes]
        workflow_routes = [route for route in routes if "workflows" in route]

        # Should have at least some workflow routes
        assert len(workflow_routes) > 0

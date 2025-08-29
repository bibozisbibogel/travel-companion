"""Simple integration tests for workflow functionality."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestWorkflowIntegration:
    """Integration tests for workflow system."""

    @patch('travel_companion.workflows.orchestrator.get_redis_manager')
    @patch('travel_companion.workflows.orchestrator.get_settings')
    def test_workflow_imports_and_instantiation(self, mock_get_settings, mock_get_redis):
        """Test that workflows can be imported and instantiated."""
        from travel_companion.workflows.simple_workflow import TravelPlanningWorkflow

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.workflow_timeout_seconds = 30
        mock_settings.workflow_max_retries = 3
        mock_settings.workflow_state_ttl = 3600
        mock_get_settings.return_value = mock_settings

        # Mock Redis
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = AsyncMock()
        mock_get_redis.return_value = mock_redis_manager

        # Should not raise
        workflow = TravelPlanningWorkflow()
        assert workflow.workflow_type == "TravelPlanningWorkflow"

    @patch('travel_companion.workflows.orchestrator.get_redis_manager')
    @patch('travel_companion.workflows.orchestrator.get_settings')
    def test_workflow_graph_building(self, mock_get_settings, mock_get_redis):
        """Test that workflow graph can be built."""
        from travel_companion.workflows.simple_workflow import TravelPlanningWorkflow

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.workflow_timeout_seconds = 30
        mock_get_settings.return_value = mock_settings

        # Mock Redis
        mock_redis_manager = MagicMock()
        mock_redis_manager.client = AsyncMock()
        mock_get_redis.return_value = mock_redis_manager

        workflow = TravelPlanningWorkflow()

        # Should not raise
        graph = workflow.build_graph()
        assert graph is not None
        assert len(workflow._nodes) == 3
        assert len(workflow._edges) == 2

    def test_workflow_nodes_exist(self):
        """Test that workflow nodes can be imported and called."""
        import time

        from travel_companion.workflows.nodes import WorkflowNodes
        from travel_companion.workflows.orchestrator import WorkflowState

        # Create sample state
        state: WorkflowState = {
            "request_id": "test123",
            "workflow_id": "wf123",
            "user_id": "user123",
            "status": "running",
            "error": None,
            "start_time": time.time(),
            "end_time": None,
            "current_node": "init",
            "input_data": {"test": "data"},
            "output_data": {},
            "intermediate_results": {},
        }

        # Test nodes execute without error
        result1 = WorkflowNodes.start_node(state)
        assert result1["current_node"] == "start"
        assert result1["status"] == "processing"

        result2 = WorkflowNodes.process_node(result1)
        assert result2["current_node"] == "process"
        assert "process_results" in result2["intermediate_results"]

        result3 = WorkflowNodes.end_node(result2)
        assert result3["current_node"] == "end"
        assert result3["status"] == "completed"
        assert result3["output_data"] is not None

    def test_workflow_api_models(self):
        """Test that workflow API models can be instantiated."""
        from travel_companion.models.workflow import (
            WorkflowExecutionRequest,
            WorkflowExecutionResponse,
        )

        # Test request model
        request = WorkflowExecutionRequest(
            input_data={"destination": "Paris"},
            user_id="user123"
        )
        assert request.input_data["destination"] == "Paris"
        assert request.user_id == "user123"

        # Test response models can be instantiated
        response = WorkflowExecutionResponse(
            workflow_id="wf123",
            request_id="req123",
            status="completed",
            output_data={"result": "success"},
            execution_time_ms=150.0,
            workflow_type="TravelPlanningWorkflow"
        )
        assert response.workflow_id == "wf123"
        assert response.status == "completed"

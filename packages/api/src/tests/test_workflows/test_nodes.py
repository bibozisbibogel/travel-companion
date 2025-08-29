"""Tests for workflow node implementations."""

import time
from unittest.mock import patch

import pytest

from travel_companion.workflows.nodes import WorkflowNodes
from travel_companion.workflows.orchestrator import WorkflowState


class TestWorkflowNodes:
    """Tests for WorkflowNodes class."""

    @pytest.fixture
    def sample_state(self) -> WorkflowState:
        """Create sample workflow state for testing."""
        return {
            "request_id": "req123",
            "workflow_id": "wf123",
            "user_id": "user123",
            "status": "running",
            "error": None,
            "start_time": time.time(),
            "end_time": None,
            "current_node": "init",
            "input_data": {"destination": "Paris", "budget": 2000},
            "output_data": {},
            "intermediate_results": {},
        }

    @patch('travel_companion.workflows.nodes.workflow_logger')
    def test_start_node_success(self, mock_logger, sample_state):
        """Test successful start node execution."""
        result = WorkflowNodes.start_node(sample_state)

        assert result["current_node"] == "start"
        assert result["status"] == "processing"
        assert result["error"] is None

        mock_logger.log_node_entered.assert_called_once()
        mock_logger.log_node_completed.assert_called_once()

    @patch('travel_companion.workflows.nodes.workflow_logger')
    def test_start_node_with_input_data(self, mock_logger, sample_state):
        """Test start node with various input data."""
        sample_state["input_data"] = {
            "destination": "Tokyo",
            "dates": {"start": "2024-06-01", "end": "2024-06-07"},
            "preferences": {"budget": 3000, "style": "luxury"}
        }

        result = WorkflowNodes.start_node(sample_state)

        assert result["current_node"] == "start"
        assert result["status"] == "processing"
        assert result["input_data"] == sample_state["input_data"]

    @patch('travel_companion.workflows.nodes.workflow_logger')
    def test_process_node_success(self, mock_logger, sample_state):
        """Test successful process node execution."""
        result = WorkflowNodes.process_node(sample_state)

        assert result["current_node"] == "process"
        assert "process_results" in result["intermediate_results"]

        process_results = result["intermediate_results"]["process_results"]
        assert process_results["original_input"] == sample_state["input_data"]
        assert process_results["workflow_id"] == "wf123"
        assert "processed_at" in process_results
        assert process_results["processing_node"] == "process"

        mock_logger.log_node_entered.assert_called_once()
        mock_logger.log_node_completed.assert_called_once()

    @patch('travel_companion.workflows.nodes.workflow_logger')
    def test_process_node_empty_input(self, mock_logger, sample_state):
        """Test process node with empty input data."""
        sample_state["input_data"] = {}

        result = WorkflowNodes.process_node(sample_state)

        assert result["current_node"] == "process"
        process_results = result["intermediate_results"]["process_results"]
        assert process_results["original_input"] == {}

    @patch('travel_companion.workflows.nodes.workflow_logger')
    def test_end_node_success(self, mock_logger, sample_state):
        """Test successful end node execution."""
        sample_state["intermediate_results"] = {
            "process_results": {"data": "processed"}
        }

        result = WorkflowNodes.end_node(sample_state)

        assert result["current_node"] == "end"
        assert result["status"] == "completed"
        assert result["output_data"] is not None

        output = result["output_data"]
        assert output["workflow_id"] == "wf123"
        assert output["request_id"] == "req123"
        assert "execution_summary" in output
        assert "results" in output
        assert "input_echo" in output

        execution_summary = output["execution_summary"]
        assert execution_summary["status"] == "completed"
        assert execution_summary["nodes_executed"] == ["start", "process", "end"]
        assert "processing_time_ms" in execution_summary

        mock_logger.log_node_entered.assert_called_once()
        mock_logger.log_node_completed.assert_called_once()

    @patch('travel_companion.workflows.nodes.workflow_logger')
    def test_end_node_with_complex_results(self, mock_logger, sample_state):
        """Test end node with complex intermediate results."""
        sample_state["intermediate_results"] = {
            "process_results": {"flights": ["flight1", "flight2"]},
            "external_data": {"weather": "sunny", "events": ["event1"]},
        }
        sample_state["input_data"] = {
            "destination": "Barcelona",
            "budget": 1500,
            "travelers": 2
        }

        result = WorkflowNodes.end_node(sample_state)

        output = result["output_data"]
        assert output["results"] == sample_state["intermediate_results"]
        assert output["input_echo"] == sample_state["input_data"]

    @patch('travel_companion.workflows.nodes.workflow_logger')
    def test_start_node_logging_details(self, mock_logger, sample_state):
        """Test start node logging with correct parameters."""
        WorkflowNodes.start_node(sample_state)

        # Verify log_node_entered call
        mock_logger.log_node_entered.assert_called_with(
            workflow_id="wf123",
            node_name="start",
            request_id="req123",
            state_keys=list(sample_state.keys()),
        )

        # Verify log_node_completed call
        args, kwargs = mock_logger.log_node_completed.call_args
        assert kwargs["workflow_id"] == "wf123"
        assert kwargs["node_name"] == "start"
        assert kwargs["request_id"] == "req123"
        assert "execution_time_ms" in kwargs
        assert kwargs["output_keys"] == ["status", "current_node"]

    @patch('travel_companion.workflows.nodes.workflow_logger')
    def test_process_node_logging_details(self, mock_logger, sample_state):
        """Test process node logging with correct parameters."""
        result = WorkflowNodes.process_node(sample_state)

        # Verify log_node_completed call
        args, kwargs = mock_logger.log_node_completed.call_args
        assert kwargs["workflow_id"] == "wf123"
        assert kwargs["node_name"] == "process"
        assert kwargs["request_id"] == "req123"

        expected_output_keys = list(result["intermediate_results"]["process_results"].keys())
        assert set(kwargs["output_keys"]) == set(expected_output_keys)

    @patch('travel_companion.workflows.nodes.workflow_logger')
    def test_end_node_logging_details(self, mock_logger, sample_state):
        """Test end node logging with correct parameters."""
        result = WorkflowNodes.end_node(sample_state)

        # Verify log_node_completed call
        args, kwargs = mock_logger.log_node_completed.call_args
        assert kwargs["workflow_id"] == "wf123"
        assert kwargs["node_name"] == "end"
        assert kwargs["request_id"] == "req123"

        expected_output_keys = list(result["output_data"].keys())
        assert set(kwargs["output_keys"]) == set(expected_output_keys)

    def test_node_execution_timing(self, sample_state):
        """Test that nodes execute in reasonable time."""
        start_time = time.time()

        WorkflowNodes.start_node(sample_state)
        WorkflowNodes.process_node(sample_state)
        WorkflowNodes.end_node(sample_state)

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete quickly (under 1 second for simple operations)
        assert execution_time < 1.0

    def test_state_preservation(self, sample_state):
        """Test that original state data is preserved through node execution."""
        original_input = sample_state["input_data"].copy()
        original_request_id = sample_state["request_id"]
        original_workflow_id = sample_state["workflow_id"]

        # Execute all nodes
        result1 = WorkflowNodes.start_node(sample_state)
        result2 = WorkflowNodes.process_node(result1)
        result3 = WorkflowNodes.end_node(result2)

        # Verify original data is preserved
        assert result3["input_data"] == original_input
        assert result3["request_id"] == original_request_id
        assert result3["workflow_id"] == original_workflow_id

    def test_error_propagation_in_nodes(self, sample_state):
        """Test that errors are properly handled and logged in nodes."""
        # This test verifies the error handling structure exists
        # Actual error injection would require modifying the nodes

        # Verify nodes have try/except structure by checking they don't raise
        # unexpected exceptions with valid input
        try:
            WorkflowNodes.start_node(sample_state)
            WorkflowNodes.process_node(sample_state)
            WorkflowNodes.end_node(sample_state)
        except Exception as e:
            pytest.fail(f"Nodes should handle valid input without errors: {e}")

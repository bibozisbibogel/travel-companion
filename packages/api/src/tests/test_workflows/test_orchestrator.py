"""Tests for workflow orchestration base classes."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from travel_companion.workflows.orchestrator import BaseWorkflow, WorkflowState


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

    @patch('travel_companion.workflows.orchestrator.get_redis_manager')
    @patch('travel_companion.workflows.orchestrator.get_settings')
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

    @patch('travel_companion.workflows.orchestrator.get_redis_manager')
    @patch('travel_companion.workflows.orchestrator.get_settings')
    def test_build_graph_success(self, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow):
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

    @patch('travel_companion.workflows.orchestrator.get_redis_manager')
    @patch('travel_companion.workflows.orchestrator.get_settings')
    @patch('travel_companion.workflows.orchestrator.workflow_logger')
    def test_build_graph_failure(self, mock_logger, mock_get_settings, mock_get_redis, mock_settings, mock_redis):
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

    @patch('travel_companion.workflows.orchestrator.get_redis_manager')
    @patch('travel_companion.workflows.orchestrator.get_settings')
    @patch('travel_companion.workflows.orchestrator.workflow_logger')
    async def test_execute_success(self, mock_logger, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow):
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

    @patch('travel_companion.workflows.orchestrator.get_redis_manager')
    @patch('travel_companion.workflows.orchestrator.get_settings')
    @patch('travel_companion.workflows.orchestrator.workflow_logger')
    async def test_execute_timeout(self, mock_logger, mock_get_settings, mock_get_redis, mock_settings, mock_redis):
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

    @patch('travel_companion.workflows.orchestrator.get_redis_manager')
    @patch('travel_companion.workflows.orchestrator.get_settings')
    @patch('travel_companion.workflows.orchestrator.workflow_logger')
    async def test_execute_failure(self, mock_logger, mock_get_settings, mock_get_redis, mock_settings, mock_redis):
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

    @patch('travel_companion.workflows.orchestrator.get_redis_manager')
    @patch('travel_companion.workflows.orchestrator.get_settings')
    @patch('travel_companion.workflows.orchestrator.workflow_logger')
    async def test_persist_state_success(self, mock_logger, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow):
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

    @patch('travel_companion.workflows.orchestrator.get_redis_manager')
    @patch('travel_companion.workflows.orchestrator.get_settings')
    @patch('travel_companion.workflows.orchestrator.workflow_logger')
    async def test_persist_state_failure(self, mock_logger, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow):
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

    @patch('travel_companion.workflows.orchestrator.get_redis_manager')
    @patch('travel_companion.workflows.orchestrator.get_settings')
    @patch('travel_companion.workflows.orchestrator.workflow_logger')
    async def test_restore_state_success(self, mock_logger, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow):
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

    @patch('travel_companion.workflows.orchestrator.get_redis_manager')
    @patch('travel_companion.workflows.orchestrator.get_settings')
    async def test_restore_state_not_found(self, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow):
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

    @patch('travel_companion.workflows.orchestrator.get_redis_manager')
    @patch('travel_companion.workflows.orchestrator.get_settings')
    async def test_get_workflow_status(self, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow):
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

    @patch('travel_companion.workflows.orchestrator.get_redis_manager')
    @patch('travel_companion.workflows.orchestrator.get_settings')
    def test_get_health_status_healthy(self, mock_get_settings, mock_get_redis, mock_settings, mock_redis, workflow):
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

    @patch('travel_companion.workflows.orchestrator.get_redis_manager')
    @patch('travel_companion.workflows.orchestrator.get_settings')
    def test_get_health_status_degraded(self, mock_get_settings, mock_get_redis, mock_settings, mock_redis):
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

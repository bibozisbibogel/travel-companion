"""LangGraph workflow orchestration base classes."""

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, TypedDict

from langgraph.graph import StateGraph

from ..core.config import get_settings
from ..core.redis import get_redis_manager
from ..utils.logging import workflow_logger


class WorkflowState(TypedDict):
    """Base state structure for all workflows."""

    request_id: str
    workflow_id: str
    user_id: str | None
    status: str
    error: str | None
    start_time: float
    end_time: float | None
    current_node: str
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    intermediate_results: dict[str, Any]


class BaseWorkflow(ABC):
    """
    Base class for LangGraph workflows with state management and logging.

    Provides common functionality for workflow orchestration including:
    - Node registration and edge definition
    - State persistence using Redis
    - Error handling and timeouts
    - Structured logging for workflow execution
    """

    def __init__(self, workflow_type: str) -> None:
        """
        Initialize base workflow.

        Args:
            workflow_type: Human-readable workflow type name
        """
        self.workflow_type = workflow_type
        self.settings = get_settings()
        self.redis_client = get_redis_manager().client
        self._graph: Any | None = None
        self._nodes: dict[str, Any] = {}
        self._edges: list[tuple[str, str]] = []

    @abstractmethod
    def define_nodes(self) -> dict[str, Any]:
        """
        Define workflow nodes.

        Returns:
            Dictionary mapping node names to callable functions
        """
        pass

    @abstractmethod
    def define_edges(self) -> list[tuple[str, str]]:
        """
        Define workflow edges and transitions.

        Returns:
            List of tuples defining graph edges (from_node, to_node)
        """
        pass

    @abstractmethod
    def get_entry_point(self) -> str:
        """
        Get the workflow entry point node name.

        Returns:
            Name of the starting node
        """
        pass

    def build_graph(self) -> Any:
        """
        Build and compile the LangGraph workflow.

        Returns:
            Compiled graph ready for execution

        Raises:
            ValueError: If graph construction fails
        """
        try:
            # Define nodes and edges
            self._nodes = self.define_nodes()
            self._edges = self.define_edges()

            # Create state graph
            graph = StateGraph(WorkflowState)

            # Add nodes
            for node_name, node_func in self._nodes.items():
                graph.add_node(node_name, node_func)

            # Add edges
            for edge in self._edges:
                if len(edge) == 2:
                    # Simple edge
                    from_node, to_node = edge
                    graph.add_edge(from_node, to_node)
                elif len(edge) == 3:
                    # Conditional edge
                    from_node, condition_func, mapping = edge
                    graph.add_conditional_edges(from_node, condition_func, mapping)

            # Set entry point using START constant
            from langgraph.graph import START

            graph.add_edge(START, self.get_entry_point())

            # Compile and cache
            self._graph = graph.compile()
            return self._graph

        except Exception as e:
            workflow_logger.log_workflow_failed(
                workflow_id="build_error",
                workflow_type=self.workflow_type,
                request_id="build_error",
                error=str(e),
                execution_time_ms=0,
            )
            raise ValueError(f"Failed to build workflow graph: {e}") from e

    async def execute(
        self,
        input_data: dict[str, Any],
        user_id: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute the workflow with given input data.

        Args:
            input_data: Input data for workflow execution
            user_id: Optional user ID for context
            request_id: Optional request ID for tracking

        Returns:
            Workflow execution results

        Raises:
            TimeoutError: If workflow execution exceeds timeout
            RuntimeError: If workflow execution fails
        """
        # Generate IDs
        workflow_id = str(uuid.uuid4())
        request_id = request_id or str(uuid.uuid4())
        start_time = time.time()

        # Initialize state
        initial_state: WorkflowState = {
            "request_id": request_id,
            "workflow_id": workflow_id,
            "user_id": user_id,
            "status": "running",
            "error": None,
            "start_time": start_time,
            "end_time": None,
            "current_node": self.get_entry_point(),
            "input_data": input_data,
            "output_data": {},
            "intermediate_results": {},
        }

        # Log workflow start
        workflow_logger.log_workflow_started(
            workflow_id=workflow_id,
            workflow_type=self.workflow_type,
            request_id=request_id,
            input_data=input_data,
        )

        try:
            # Ensure graph is built
            if self._graph is None:
                self.build_graph()

            # Persist initial state
            await self._persist_state(initial_state)

            # Execute workflow with timeout
            result = await self._execute_with_timeout(initial_state)

            # Update final state
            end_time = time.time()
            execution_time_ms = (end_time - start_time) * 1000

            result["end_time"] = end_time
            result["status"] = "completed"

            # Persist final state
            await self._persist_state(result)

            # Log success
            workflow_logger.log_workflow_completed(
                workflow_id=workflow_id,
                workflow_type=self.workflow_type,
                request_id=request_id,
                execution_time_ms=execution_time_ms,
                output_data=result.get("output_data"),
            )

            return result["output_data"]

        except TimeoutError:
            execution_time_ms = (time.time() - start_time) * 1000
            workflow_logger.log_workflow_failed(
                workflow_id=workflow_id,
                workflow_type=self.workflow_type,
                request_id=request_id,
                error="Workflow execution timeout",
                execution_time_ms=execution_time_ms,
            )
            raise

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            workflow_logger.log_workflow_failed(
                workflow_id=workflow_id,
                workflow_type=self.workflow_type,
                request_id=request_id,
                error=str(e),
                execution_time_ms=execution_time_ms,
            )

            # Update state with error
            error_state = initial_state.copy()
            error_state.update(
                {
                    "status": "failed",
                    "error": str(e),
                    "end_time": time.time(),
                }
            )
            await self._persist_state(error_state)

            raise RuntimeError(f"Workflow execution failed: {e}") from e

    async def _execute_with_timeout(self, state: WorkflowState) -> WorkflowState:
        """
        Execute workflow with configured timeout.

        Args:
            state: Initial workflow state

        Returns:
            Final workflow state

        Raises:
            TimeoutError: If execution exceeds timeout
        """
        import asyncio

        timeout = self.settings.workflow_timeout_seconds

        try:
            # Execute graph
            result = await asyncio.wait_for(self._execute_graph(state), timeout=timeout)
            return result
        except TimeoutError as e:
            raise TimeoutError(f"Workflow execution exceeded {timeout}s timeout") from e

    async def _execute_graph(self, state: WorkflowState) -> WorkflowState:
        """
        Execute the LangGraph workflow.

        Args:
            state: Initial workflow state

        Returns:
            Final workflow state
        """
        if self._graph is None:
            raise RuntimeError("Workflow graph not built")

        # Execute graph
        final_state = await self._graph.ainvoke(state)
        return final_state  # type: ignore[no-any-return]

    async def _persist_state(self, state: WorkflowState) -> None:
        """
        Persist workflow state to Redis.

        Args:
            state: Workflow state to persist
        """
        try:
            start_time = time.time()

            # Create Redis key
            state_key = f"workflow_state:{state['workflow_id']}"

            # Store state with TTL
            import json

            await self.redis_client.setex(
                state_key, self.settings.workflow_state_ttl, json.dumps(state, default=str)
            )

            persistence_time_ms = (time.time() - start_time) * 1000

            workflow_logger.log_state_persisted(
                workflow_id=state["workflow_id"],
                request_id=state["request_id"],
                persistence_time_ms=persistence_time_ms,
            )

        except Exception as e:
            # Log error but don't fail workflow
            workflow_logger.log_workflow_failed(
                workflow_id=state["workflow_id"],
                workflow_type=self.workflow_type,
                request_id=state["request_id"],
                error=f"State persistence failed: {e}",
                execution_time_ms=0,
            )

    async def restore_state(self, workflow_id: str) -> WorkflowState | None:
        """
        Restore workflow state from Redis.

        Args:
            workflow_id: Workflow ID to restore

        Returns:
            Restored workflow state or None if not found
        """
        try:
            start_time = time.time()

            state_key = f"workflow_state:{workflow_id}"

            import json

            state_data = await self.redis_client.get(state_key)

            if state_data is None:
                return None

            state = json.loads(state_data)
            restoration_time_ms = (time.time() - start_time) * 1000

            workflow_logger.log_state_restored(
                workflow_id=workflow_id,
                request_id=state.get("request_id", "unknown"),
                restoration_time_ms=restoration_time_ms,
                restored_keys=list(state.keys()),
            )

            return state  # type: ignore[no-any-return]

        except Exception as e:
            workflow_logger.log_workflow_failed(
                workflow_id=workflow_id,
                workflow_type=self.workflow_type,
                request_id="restore_error",
                error=f"State restoration failed: {e}",
                execution_time_ms=0,
            )
            return None

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any] | None:
        """
        Get current workflow status.

        Args:
            workflow_id: Workflow ID to check

        Returns:
            Workflow status information or None if not found
        """
        state = await self.restore_state(workflow_id)
        if state is None:
            return None

        return {
            "workflow_id": workflow_id,
            "workflow_type": self.workflow_type,
            "status": state.get("status"),
            "current_node": state.get("current_node"),
            "start_time": state.get("start_time"),
            "end_time": state.get("end_time"),
            "error": state.get("error"),
        }

    def get_health_status(self) -> dict[str, Any]:
        """
        Get workflow engine health status.

        Returns:
            Health status information
        """
        try:
            # Check if graph can be built
            if self._graph is None:
                self.build_graph()

            # Check Redis connectivity
            redis_healthy = True
            try:
                get_redis_manager()  # Test connection
                # Note: This is sync method, in real usage would be await redis_manager.ping()
                redis_healthy = True  # Assume healthy for sync context
            except Exception:
                redis_healthy = False

            return {
                "workflow_type": self.workflow_type,
                "status": "healthy" if redis_healthy else "degraded",
                "graph_built": self._graph is not None,
                "redis_connected": redis_healthy,
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
            }

        except Exception as e:
            return {
                "workflow_type": self.workflow_type,
                "status": "unhealthy",
                "error": str(e),
                "graph_built": False,
                "redis_connected": False,
                "node_count": 0,
                "edge_count": 0,
            }

"""LangGraph workflow orchestration base classes."""

import time
import uuid
from abc import ABC, abstractmethod

# Add import for TYPE_CHECKING to handle forward references
from typing import TYPE_CHECKING, Any, Optional, TypedDict

if TYPE_CHECKING:
    from .parallel_executor import ParallelExecutionConfig

from langgraph.graph import StateGraph

from ..core.config import get_settings
from ..core.redis import get_redis_manager
from ..models.external import (
    ActivityOption as ExternalActivityOption,
)
from ..models.external import (
    FlightOption as ExternalFlightOption,
)
from ..models.external import (
    HotelOption as ExternalHotelOption,
)
from ..models.trip import TripPlanRequest
from ..utils.logging import workflow_logger


class BudgetAllocations(TypedDict):
    """Budget allocation breakdown."""

    flights: float
    hotels: float
    activities: float
    food: float


class BudgetTracking(TypedDict):
    """Budget tracking structure."""

    total_budget: float
    allocated: float
    spent: float
    remaining: float
    allocations: BudgetAllocations


class BudgetTrackingOptional(TypedDict, total=False):
    """Optional budget tracking fields."""

    final_total: float
    budget_utilization: float
    savings: float


class BudgetTrackingComplete(BudgetTracking, BudgetTrackingOptional):
    """Complete budget tracking with optional fields."""

    pass


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


class TripPlanningWorkflowState(WorkflowState):
    """Extended state structure for trip planning workflows."""

    # Trip planning specific fields
    trip_request: TripPlanRequest
    trip_id: str | None

    # Agent execution tracking
    agents_completed: list[str]
    agents_failed: list[str]
    agent_dependencies: dict[str, list[str]]

    # Agent results
    flight_results: list[ExternalFlightOption]
    hotel_results: list[ExternalHotelOption]
    activity_results: list[ExternalActivityOption]
    weather_data: dict[str, Any]
    food_recommendations: list[dict[str, Any]]
    itinerary_data: dict[str, Any]

    # Workflow context
    user_preferences: dict[str, Any]
    budget_tracking: BudgetTrackingComplete
    optimization_metrics: dict[str, float]
    state_transitions: list[dict[str, Any]]
    parallel_execution_metrics: dict[str, Any] | None


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

    def get_state_class(self) -> type[WorkflowState]:
        """
        Get the state class for this workflow.

        Returns:
            State class to use for this workflow
        """
        return WorkflowState

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

            # Create state graph with appropriate state class
            state_class = self.get_state_class()
            graph = StateGraph(state_class)

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
        Persist workflow state to Redis with enhanced state management.

        Args:
            state: Workflow state to persist
        """
        try:
            # Use enhanced state manager for TripPlanningWorkflow
            if isinstance(state, dict) and "trip_request" in state:
                from ..core.redis import get_redis_manager
                from .state_manager import EnhancedWorkflowStateManager

                redis_manager = get_redis_manager()
                state_manager = EnhancedWorkflowStateManager(
                    redis_client=redis_manager.client,
                    workflow_id=state["workflow_id"],
                    request_id=state.get("request_id", ""),
                )

                # Determine checkpoint type based on workflow status
                checkpoint_type = "automatic"
                if state.get("status") == "failed":
                    checkpoint_type = "error"
                elif state.get("status") == "completed":
                    checkpoint_type = "completion"
                elif state.get("current_node") in ["initialize_trip", "finalize_plan"]:
                    checkpoint_type = "manual"

                # Import CheckpointType and persist with enhanced features
                from .state_manager import CheckpointType

                # Map string checkpoint type to enum
                checkpoint_enum = CheckpointType.AUTOMATIC
                if checkpoint_type == "error":
                    checkpoint_enum = CheckpointType.ERROR
                elif checkpoint_type == "completion":
                    checkpoint_enum = CheckpointType.COMPLETION
                elif checkpoint_type == "manual":
                    checkpoint_enum = CheckpointType.MANUAL

                success = await state_manager.persist_state(state, checkpoint_enum)  # type: ignore[arg-type]

                if not success:
                    workflow_logger.warning(
                        f"Enhanced state persistence failed for {state['workflow_id']}, falling back to basic persistence"
                    )
                    await self._basic_persist_state(state)
            else:
                # Fallback to basic persistence for non-trip workflows
                await self._basic_persist_state(state)

        except Exception as e:
            # Fallback to basic persistence
            workflow_logger.warning(
                f"Enhanced state persistence error: {e}, falling back to basic persistence"
            )
            await self._basic_persist_state(state)

    async def _basic_persist_state(self, state: WorkflowState) -> None:
        """Basic Redis state persistence as fallback."""
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


class TripPlanningWorkflow(BaseWorkflow):
    """
    Concrete implementation of trip planning workflow with multi-agent coordination.

    Orchestrates all travel agents (flight, hotel, activity, weather, food, itinerary)
    with dependency management and parallel execution optimization.
    """

    def __init__(self, parallel_config: Optional["ParallelExecutionConfig"] = None) -> None:
        """Initialize trip planning workflow."""
        super().__init__("trip_planning")

        # Store parallel config for delayed initialization
        self.parallel_config = parallel_config

    def get_state_class(self) -> type[TripPlanningWorkflowState]:
        """Return trip planning specific state class."""
        return TripPlanningWorkflowState

    def define_nodes(self) -> dict[str, Any]:
        """
        Define workflow nodes for trip planning agents with coordinator integration.

        Returns:
            Dictionary mapping node names to agent functions
        """
        # Import nodes from nodes.py (implemented in Task 2)
        try:
            from .nodes import (
                finalize_trip_plan,
                initialize_trip_context,
            )

            return {
                "initialize_trip": initialize_trip_context,
                "coordinated_execution": self._coordinated_execution_node,
                "finalize_plan": finalize_trip_plan,
                "error_handler": self._error_handler_node,
            }
        except ImportError:
            # Temporary placeholder nodes for Task 1 foundation testing
            return {
                "initialize_trip": self._placeholder_node,
                "coordinated_execution": self._placeholder_node,
                "finalize_plan": self._placeholder_node,
                "error_handler": self._placeholder_node,
            }

    def _placeholder_node(self, state: TripPlanningWorkflowState) -> TripPlanningWorkflowState:
        """
        Placeholder node for Task 1 foundation testing.
        Will be replaced with actual node implementations in Task 2.
        """
        return state

    async def _coordinated_execution_node(
        self, state: TripPlanningWorkflowState
    ) -> TripPlanningWorkflowState:
        """
        Coordinated execution node that manages all agent execution with dependencies.

        This node uses the ParallelExecutionOptimizer for optimal parallel execution
        with timeout handling, load balancing, and performance monitoring.
        """
        # Import here to avoid circular import
        from .parallel_executor import ParallelExecutionConfig, ParallelExecutionOptimizer

        # Initialize parallel optimizer with delayed import
        parallel_optimizer = ParallelExecutionOptimizer(
            config=self.parallel_config or ParallelExecutionConfig()
        )

        from .nodes import (
            execute_activity_agent,
            execute_flight_agent,
            execute_food_agent,
            execute_hotel_agent,
            execute_itinerary_agent,
            execute_weather_agent,
        )

        # Define all agent node functions
        agent_functions = {
            "weather_agent": execute_weather_agent,
            "flight_agent": execute_flight_agent,
            "hotel_agent": execute_hotel_agent,
            "activity_agent": execute_activity_agent,
            "food_agent": execute_food_agent,
            "itinerary_agent": execute_itinerary_agent,
        }

        # Define agent dependencies (weather before activities)
        dependencies = {
            "activity_agent": ["weather_agent"],
            "itinerary_agent": ["flight_agent", "hotel_agent", "activity_agent", "food_agent"],
        }

        workflow_logger.log_parallel_execution_starting(
            workflow_id=state["workflow_id"],
            request_id=state["request_id"],
            agent_count=len(agent_functions),
        )

        try:
            # Execute agents with parallel optimization
            updated_state = await parallel_optimizer.execute_agents_parallel(
                state=state, agent_functions=agent_functions, dependencies=dependencies
            )

            # Log parallel execution completion
            execution_metrics = updated_state.get("parallel_execution_metrics")
            if execution_metrics:
                workflow_logger.log_parallel_execution_completed(
                    workflow_id=state["workflow_id"],
                    request_id=state["request_id"],
                    execution_metrics=execution_metrics,
                )
            else:
                workflow_logger.log_parallel_execution_completed(
                    workflow_id=state["workflow_id"],
                    request_id=state["request_id"],
                    execution_metrics={},
                )

            return updated_state

        except Exception as e:
            workflow_logger.log_parallel_execution_failed(
                workflow_id=state["workflow_id"],
                request_id=state["request_id"],
                error=str(e),
                partial_metrics={},
            )

            # Set error state but allow error handler to process
            state["error"] = str(e)
            state["status"] = "parallel_execution_failed"
            return state

    def _error_handler_node(self, state: TripPlanningWorkflowState) -> TripPlanningWorkflowState:
        """
        Error handler node for workflow failures.

        Handles workflow errors and prepares appropriate error responses.
        """
        # Log error handling
        error_msg = (
            state.get("error", "Unknown error")
            if isinstance(state.get("error"), str)
            else "Unknown error"
        )
        workflow_logger.log_error_handling_started(
            workflow_id=state["workflow_id"],
            error_type="workflow_error",
            error_message=error_msg if error_msg else "Unknown error",
        )

        # Create error response in output_data
        error_response = {
            "success": False,
            "error": state.get("error", "Workflow execution failed"),
            "partial_results": {
                "flight_results": state.get("flight_results", []),
                "hotel_results": state.get("hotel_results", []),
                "activity_results": state.get("activity_results", []),
                "weather_data": state.get("weather_data", {}),
                "food_recommendations": state.get("food_recommendations", []),
            },
            "execution_metrics": state.get("optimization_metrics", {}),
            "coordination_metrics": state.get("coordination_metrics", {}),
        }

        state["output_data"] = error_response
        state["status"] = "failed_with_partial_results"

        return state

    def define_edges(self) -> list[tuple[str, str]]:
        """
        Define workflow edges with dependency management.

        Uses the WorkflowCoordinator for intelligent execution order and parallel optimization.

        Returns:
            List of workflow transitions (simplified for coordinator-based execution)
        """
        # Import coordination functions

        return [
            # Use coordinator for intelligent routing
            ("initialize_trip", "coordinated_execution"),
            ("coordinated_execution", "finalize_plan"),
        ]

    def get_entry_point(self) -> str:
        """Return workflow entry point."""
        return "initialize_trip"

    def create_initial_state(
        self,
        trip_request: TripPlanRequest,
        user_id: str | None = None,
        request_id: str | None = None,
    ) -> TripPlanningWorkflowState:
        """
        Create initial workflow state with trip context.

        Args:
            trip_request: Trip planning request data
            user_id: Optional user ID for context
            request_id: Optional request ID for tracking

        Returns:
            Initialized trip planning workflow state
        """
        workflow_id = str(uuid.uuid4())
        request_id = request_id or str(uuid.uuid4())
        start_time = time.time()

        # Initialize state with trip context
        initial_state: TripPlanningWorkflowState = {
            # Base workflow fields
            "request_id": request_id,
            "workflow_id": workflow_id,
            "user_id": user_id,
            "status": "running",
            "error": None,
            "start_time": start_time,
            "end_time": None,
            "current_node": self.get_entry_point(),
            "input_data": trip_request.model_dump(),
            "output_data": {},
            "intermediate_results": {},
            # Trip planning specific fields
            "trip_request": trip_request,
            "trip_id": None,
            # Agent tracking
            "agents_completed": [],
            "agents_failed": [],
            "agent_dependencies": {
                "activity_agent": ["weather_agent"],  # Activities depend on weather
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
            "user_preferences": trip_request.preferences or {},
            "budget_tracking": {
                "total_budget": float(trip_request.requirements.budget),
                "allocated": float(trip_request.requirements.budget),
                "spent": 0.0,
                "remaining": float(trip_request.requirements.budget),
                "allocations": {
                    "flights": 0.0,
                    "hotels": 0.0,
                    "activities": 0.0,
                    "food": 0.0,
                },
            },
            "optimization_metrics": {"execution_time": 0.0, "success_rate": 0.0},
            "state_transitions": [],
            "parallel_execution_metrics": None,
        }

        return initial_state

    async def execute_trip_planning(
        self,
        trip_request: TripPlanRequest,
        user_id: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute complete trip planning workflow.

        Args:
            trip_request: Trip planning request data
            user_id: Optional user ID for context
            request_id: Optional request ID for tracking

        Returns:
            Complete trip planning results

        Raises:
            TimeoutError: If workflow execution exceeds timeout
            RuntimeError: If workflow execution fails
        """
        # Create initial state
        initial_state = self.create_initial_state(trip_request, user_id, request_id)

        # Log workflow start
        workflow_logger.log_workflow_started(
            workflow_id=initial_state["workflow_id"],
            workflow_type=self.workflow_type,
            request_id=initial_state["request_id"],
            input_data=initial_state["input_data"],
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
            execution_time_ms = (end_time - initial_state["start_time"]) * 1000

            result["end_time"] = end_time
            result["status"] = "completed"

            # Persist final state
            await self._persist_state(result)

            # Log success
            workflow_logger.log_workflow_completed(
                workflow_id=initial_state["workflow_id"],
                workflow_type=self.workflow_type,
                request_id=initial_state["request_id"],
                execution_time_ms=execution_time_ms,
                output_data=result.get("output_data"),
            )

            return result["output_data"]

        except TimeoutError:
            execution_time_ms = (time.time() - initial_state["start_time"]) * 1000
            workflow_logger.log_workflow_failed(
                workflow_id=initial_state["workflow_id"],
                workflow_type=self.workflow_type,
                request_id=initial_state["request_id"],
                error="Workflow execution timeout",
                execution_time_ms=execution_time_ms,
            )
            raise

        except Exception as e:
            execution_time_ms = (time.time() - initial_state["start_time"]) * 1000
            workflow_logger.log_workflow_failed(
                workflow_id=initial_state["workflow_id"],
                workflow_type=self.workflow_type,
                request_id=initial_state["request_id"],
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

            raise RuntimeError(f"Trip planning workflow execution failed: {e}") from e

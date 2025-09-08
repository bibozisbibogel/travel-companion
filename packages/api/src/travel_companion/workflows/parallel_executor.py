"""Parallel execution optimization for LangGraph workflow coordination."""

import asyncio
import copy
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from ..utils.logging import workflow_logger
from .orchestrator import TripPlanningWorkflowState

logger = logging.getLogger(__name__)


class ExecutionPriority(str, Enum):
    """Agent execution priority levels."""

    CRITICAL = "critical"  # Must complete (e.g., weather_agent for activity dependencies)
    HIGH = "high"  # Important for good results (e.g., flight_agent, hotel_agent)
    MEDIUM = "medium"  # Enhances experience (e.g., activity_agent, food_agent)
    LOW = "low"  # Nice to have (e.g., optimization agents)


@dataclass
class ParallelExecutionConfig:
    """Configuration for parallel execution optimization."""

    # Timeout configurations
    default_timeout_seconds: int = 30
    critical_timeout_seconds: int = 45
    high_priority_timeout_seconds: int = 35
    medium_priority_timeout_seconds: int = 25
    low_priority_timeout_seconds: int = 20

    # Concurrency limits
    max_concurrent_agents: int = 6
    max_concurrent_critical: int = 2
    max_concurrent_high: int = 3
    max_concurrent_medium: int = 4
    max_concurrent_low: int = 6

    # Retry configuration
    max_retries: int = 2
    retry_delay_seconds: float = 1.0
    exponential_backoff: bool = True

    # Performance thresholds
    fast_execution_threshold_ms: float = 5000.0  # 5 seconds
    slow_execution_threshold_ms: float = 20000.0  # 20 seconds
    critical_failure_threshold: int = 2  # Max critical failures before aborting

    # Load balancing
    enable_load_balancing: bool = True
    queue_size_limit: int = 50
    adaptive_timeout: bool = True


@dataclass
class ExecutionMetrics:
    """Metrics for a single agent execution."""

    agent_name: str
    priority: ExecutionPriority
    start_time: float
    end_time: float | None = None
    timeout_seconds: float = 30.0
    success: bool = False
    error: str | None = None
    retry_count: int = 0
    queue_time_ms: float = 0.0
    execution_time_ms: float | None = None
    timeout_occurred: bool = False
    circuit_breaker_open: bool = False

    def calculate_execution_time(self) -> float:
        """Calculate execution time in milliseconds."""
        if self.end_time is None:
            return 0.0
        self.execution_time_ms = (self.end_time - self.start_time) * 1000
        return self.execution_time_ms

    @property
    def is_fast_execution(self) -> bool:
        """Check if execution was fast."""
        return (self.execution_time_ms or 0) < 5000.0  # Less than 5 seconds

    @property
    def is_slow_execution(self) -> bool:
        """Check if execution was slow."""
        return (self.execution_time_ms or 0) > 15000.0  # More than 15 seconds


@dataclass
class WorkflowExecutionMetrics:
    """Comprehensive workflow execution metrics."""

    workflow_id: str
    total_agents: int = 0
    agents_executed: int = 0
    agents_succeeded: int = 0
    agents_failed: int = 0
    agents_timeout: int = 0
    agents_skipped: int = 0

    # Timing metrics
    total_execution_time_ms: float = 0.0
    parallel_execution_time_ms: float = 0.0
    sequential_execution_time_ms: float = 0.0
    average_execution_time_ms: float = 0.0

    # Performance metrics
    fast_executions: int = 0
    slow_executions: int = 0
    timeout_occurrences: int = 0
    circuit_breaker_activations: int = 0

    # Parallelization metrics
    max_concurrent_agents: int = 0
    average_concurrent_agents: float = 0.0
    parallel_efficiency: float = 0.0  # % time saved by parallelization

    # Load balancing metrics
    queue_max_size: int = 0
    queue_average_wait_time_ms: float = 0.0
    load_balance_decisions: int = 0

    agent_metrics: list[ExecutionMetrics] = field(default_factory=list)

    def calculate_summary_metrics(self) -> None:
        """Calculate summary metrics from individual agent metrics."""
        if not self.agent_metrics:
            return

        # Calculate basic metrics
        self.total_agents = len(self.agent_metrics)
        self.agents_executed = len([m for m in self.agent_metrics if m.end_time is not None])
        self.agents_succeeded = len([m for m in self.agent_metrics if m.success])
        self.agents_failed = len(
            [m for m in self.agent_metrics if not m.success and m.end_time is not None]
        )
        self.agents_timeout = len([m for m in self.agent_metrics if m.timeout_occurred])

        # Calculate timing metrics
        execution_times = [
            m.execution_time_ms for m in self.agent_metrics if m.execution_time_ms is not None
        ]
        if execution_times:
            self.total_execution_time_ms = sum(execution_times)
            self.average_execution_time_ms = self.total_execution_time_ms / len(execution_times)

        # Performance categorization
        self.fast_executions = len([m for m in self.agent_metrics if m.is_fast_execution])
        self.slow_executions = len([m for m in self.agent_metrics if m.is_slow_execution])
        self.timeout_occurrences = len([m for m in self.agent_metrics if m.timeout_occurred])
        self.circuit_breaker_activations = len(
            [m for m in self.agent_metrics if m.circuit_breaker_open]
        )


class ParallelExecutionQueue:
    """Queue management for parallel agent execution with load balancing."""

    def __init__(self, config: ParallelExecutionConfig):
        """Initialize execution queue."""
        self.config = config
        self.priority_queues: dict[
            ExecutionPriority, list[tuple[str, Callable[..., Any], dict[str, Any]]]
        ] = {priority: [] for priority in ExecutionPriority}
        self.active_executions: dict[ExecutionPriority, set[str]] = {
            priority: set() for priority in ExecutionPriority
        }
        self.execution_semaphores: dict[ExecutionPriority, asyncio.Semaphore] = {
            ExecutionPriority.CRITICAL: asyncio.Semaphore(config.max_concurrent_critical),
            ExecutionPriority.HIGH: asyncio.Semaphore(config.max_concurrent_high),
            ExecutionPriority.MEDIUM: asyncio.Semaphore(config.max_concurrent_medium),
            ExecutionPriority.LOW: asyncio.Semaphore(config.max_concurrent_low),
        }
        self.queue_times: dict[str, float] = {}
        self.load_balance_stats: dict[str, Any] = {"decisions": 0, "queue_sizes": []}

    async def enqueue_agent(
        self,
        agent_name: str,
        agent_function: Callable[..., Any],
        priority: ExecutionPriority,
        execution_context: dict[str, Any],
    ) -> None:
        """
        Enqueue an agent for execution with priority and load balancing.

        Args:
            agent_name: Name of the agent
            agent_function: Function to execute
            priority: Execution priority
            execution_context: Additional context for execution
        """
        enqueue_time = time.time()
        self.queue_times[agent_name] = enqueue_time

        # Apply load balancing logic
        if self.config.enable_load_balancing:
            priority = self._apply_load_balancing(agent_name, priority)

        # Add to appropriate priority queue
        self.priority_queues[priority].append((agent_name, agent_function, execution_context))

        # Track queue size for metrics
        total_queued = sum(len(queue) for queue in self.priority_queues.values())
        self.load_balance_stats["queue_sizes"].append(total_queued)

        workflow_logger.debug(
            f"Agent {agent_name} enqueued with priority {priority.value}, total queued: {total_queued}"
        )

    def _apply_load_balancing(
        self, agent_name: str, priority: ExecutionPriority
    ) -> ExecutionPriority:
        """
        Apply load balancing logic to adjust priority based on current queue state.

        Args:
            agent_name: Name of the agent
            priority: Original priority

        Returns:
            Adjusted priority based on load balancing
        """
        self.load_balance_stats["decisions"] += 1

        # Check current queue sizes
        queue_sizes = {p: len(self.priority_queues[p]) for p in ExecutionPriority}
        active_counts = {p: len(self.active_executions[p]) for p in ExecutionPriority}

        # If high priority queue is overloaded, demote non-critical agents
        if queue_sizes[ExecutionPriority.HIGH] > 3 and priority == ExecutionPriority.HIGH:
            if agent_name not in [
                "flight_agent",
                "hotel_agent",
            ]:  # Keep critical agents in high priority
                workflow_logger.info(
                    f"Load balancing: Demoting {agent_name} from HIGH to MEDIUM priority"
                )
                return ExecutionPriority.MEDIUM

        # If critical queue has space, promote important agents
        if (
            queue_sizes[ExecutionPriority.CRITICAL] == 0
            and active_counts[ExecutionPriority.CRITICAL] == 0
        ):
            if agent_name in ["weather_agent"] and priority == ExecutionPriority.HIGH:
                workflow_logger.info(
                    f"Load balancing: Promoting {agent_name} from HIGH to CRITICAL priority"
                )
                return ExecutionPriority.CRITICAL

        return priority

    async def get_next_agent(
        self,
    ) -> tuple[str, Callable[..., Any], dict[str, Any], ExecutionPriority] | None:
        """
        Get the next agent to execute based on priority and availability.

        Returns:
            Tuple of (agent_name, function, context, priority) or None if no agents available
        """
        # Check queues in priority order
        for priority in [
            ExecutionPriority.CRITICAL,
            ExecutionPriority.HIGH,
            ExecutionPriority.MEDIUM,
            ExecutionPriority.LOW,
        ]:
            if self.priority_queues[priority]:
                # Check if we can execute more agents of this priority
                semaphore = self.execution_semaphores[priority]
                if semaphore._value > 0:  # Semaphore has available slots
                    agent_name, function, context = self.priority_queues[priority].pop(0)
                    self.active_executions[priority].add(agent_name)

                    # Calculate queue time
                    enqueue_time = self.queue_times.pop(agent_name, time.time())
                    queue_time_ms = (time.time() - enqueue_time) * 1000
                    context["queue_time_ms"] = queue_time_ms

                    return agent_name, function, context, priority

        return None

    def mark_agent_completed(self, agent_name: str, priority: ExecutionPriority) -> None:
        """Mark an agent as completed and remove from active executions."""
        if agent_name in self.active_executions[priority]:
            self.active_executions[priority].remove(agent_name)

    def get_queue_metrics(self) -> dict[str, Any]:
        """Get queue performance metrics."""
        total_queued = sum(len(queue) for queue in self.priority_queues.values())
        total_active = sum(len(active) for active in self.active_executions.values())

        avg_queue_size = 0.0
        if self.load_balance_stats["queue_sizes"]:
            avg_queue_size = sum(self.load_balance_stats["queue_sizes"]) / len(
                self.load_balance_stats["queue_sizes"]
            )

        return {
            "total_queued": total_queued,
            "total_active": total_active,
            "queued_by_priority": {
                p.value: len(self.priority_queues[p]) for p in ExecutionPriority
            },
            "active_by_priority": {
                p.value: len(self.active_executions[p]) for p in ExecutionPriority
            },
            "average_queue_size": avg_queue_size,
            "max_queue_size": max(self.load_balance_stats["queue_sizes"], default=0),
            "load_balance_decisions": self.load_balance_stats["decisions"],
        }


class ParallelExecutionOptimizer:
    """
    Optimizes parallel execution of workflow agents with advanced coordination features.

    Provides:
    - Priority-based agent execution
    - Timeout management with adaptive timeouts
    - Circuit breaker integration
    - Load balancing and queue management
    - Comprehensive performance metrics
    - Retry logic with exponential backoff
    """

    def __init__(self, config: ParallelExecutionConfig | None = None):
        """Initialize parallel execution optimizer."""
        self.config = config or ParallelExecutionConfig()
        self.execution_queue = ParallelExecutionQueue(self.config)
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.workflow_metrics: WorkflowExecutionMetrics | None = None
        self.active_tasks: dict[str, asyncio.Task[Any]] = {}

        # Performance tracking
        self.concurrent_agent_count: list[int] = []
        self.execution_start_time: float | None = None

        # Logging
        self.logger = logging.getLogger(__name__)

    def _get_circuit_breaker(self, agent_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for an agent."""
        if agent_name not in self.circuit_breakers:
            self.circuit_breakers[agent_name] = CircuitBreaker(
                failure_threshold=5, recovery_timeout=30, expected_exception=Exception
            )
        return self.circuit_breakers[agent_name]

    def _determine_agent_priority(self, agent_name: str) -> ExecutionPriority:
        """Determine execution priority for an agent."""
        priority_map = {
            # Critical agents - dependencies or essential functionality
            "weather_agent": ExecutionPriority.CRITICAL,
            "initialize_trip": ExecutionPriority.CRITICAL,
            "finalize_plan": ExecutionPriority.CRITICAL,
            # High priority - core travel components
            "flight_agent": ExecutionPriority.HIGH,
            "hotel_agent": ExecutionPriority.HIGH,
            "itinerary_agent": ExecutionPriority.HIGH,
            # Medium priority - enhancing experience
            "activity_agent": ExecutionPriority.MEDIUM,
            "food_agent": ExecutionPriority.MEDIUM,
            # Low priority - nice to have
            "optimization_agent": ExecutionPriority.LOW,
            "analytics_agent": ExecutionPriority.LOW,
        }

        return priority_map.get(agent_name, ExecutionPriority.MEDIUM)

    def _get_agent_timeout(self, agent_name: str, priority: ExecutionPriority) -> float:
        """Get timeout for an agent based on priority and historical performance."""
        base_timeouts = {
            ExecutionPriority.CRITICAL: self.config.critical_timeout_seconds,
            ExecutionPriority.HIGH: self.config.high_priority_timeout_seconds,
            ExecutionPriority.MEDIUM: self.config.medium_priority_timeout_seconds,
            ExecutionPriority.LOW: self.config.low_priority_timeout_seconds,
        }

        base_timeout = base_timeouts[priority]

        # Adaptive timeout based on historical performance
        if self.config.adaptive_timeout and agent_name in self.circuit_breakers:
            cb = self.circuit_breakers[agent_name]
            if hasattr(cb, "average_response_time") and cb.average_response_time > 0:
                # Add 50% buffer to average response time
                adaptive_timeout = cb.average_response_time * 1.5
                return float(min(max(adaptive_timeout, base_timeout), base_timeout * 2))

        return base_timeout

    async def execute_agents_parallel(
        self,
        state: TripPlanningWorkflowState,
        agent_functions: dict[str, Callable[..., Any]],
        dependencies: dict[str, list[str]] | None = None,
    ) -> TripPlanningWorkflowState:
        """
        Execute agents in parallel with optimization and coordination.

        Args:
            state: Current workflow state
            agent_functions: Dictionary of agent name -> function mappings
            dependencies: Optional agent dependency mapping

        Returns:
            Updated workflow state with results from all agents
        """
        self.execution_start_time = time.time()
        self.workflow_metrics = WorkflowExecutionMetrics(workflow_id=state["workflow_id"])

        workflow_logger.log_parallel_execution_started(
            workflow_id=state["workflow_id"],
            request_id=state["request_id"],
            total_agents=len(agent_functions),
            config=self.config.__dict__,
        )

        try:
            # Phase 1: Queue all agents with priorities
            await self._queue_all_agents(agent_functions, state, dependencies or {})

            # Phase 2: Execute agents with parallel coordination
            updated_state = await self._execute_queued_agents(state)

            # Phase 3: Calculate final metrics
            self._finalize_metrics()

            # Update state with execution metrics
            updated_state["parallel_execution_metrics"] = self._get_execution_summary()

            workflow_logger.log_parallel_execution_completed(
                workflow_id=state["workflow_id"],
                request_id=state["request_id"],
                execution_metrics=self.workflow_metrics.__dict__,
            )

            return updated_state

        except Exception as e:
            workflow_logger.log_parallel_execution_failed(
                workflow_id=state["workflow_id"],
                request_id=state["request_id"],
                error=str(e),
                partial_metrics=self._get_execution_summary() if self.workflow_metrics else {},
            )
            raise RuntimeError(f"Parallel execution failed: {e}") from e

    async def _queue_all_agents(
        self,
        agent_functions: dict[str, Callable[..., Any]],
        state: TripPlanningWorkflowState,
        dependencies: dict[str, list[str]],
    ) -> None:
        """Queue all agents based on dependencies and priorities."""

        # Separate independent and dependent agents
        independent_agents = []
        dependent_agents = []

        for agent_name, agent_function in agent_functions.items():
            if agent_name in dependencies and dependencies[agent_name]:
                dependent_agents.append((agent_name, agent_function))
            else:
                independent_agents.append((agent_name, agent_function))

        # Queue independent agents (no dependencies)
        for agent_name, agent_function in independent_agents:
            priority = self._determine_agent_priority(agent_name)
            await self.execution_queue.enqueue_agent(
                agent_name=agent_name,
                agent_function=agent_function,
                priority=priority,
                execution_context={"dependencies": []},  # Don't store state in context
            )

        # Queue dependent agents (will be processed after dependencies complete)
        for agent_name, agent_function in dependent_agents:
            priority = self._determine_agent_priority(agent_name)
            await self.execution_queue.enqueue_agent(
                agent_name=agent_name,
                agent_function=agent_function,
                priority=priority,
                execution_context={
                    "dependencies": dependencies.get(agent_name, [])  # Only store dependencies
                },
            )

    async def _execute_queued_agents(
        self, initial_state: TripPlanningWorkflowState
    ) -> TripPlanningWorkflowState:
        """Execute all queued agents with parallel coordination."""
        current_state = copy.deepcopy(initial_state)
        dependency_retry_count: dict[
            str, int
        ] = {}  # Track how many times we've retried each agent due to dependencies
        max_dependency_retries = 100  # Prevent infinite loops

        while True:
            # First, process any completed tasks to update state
            if self.active_tasks:
                done_tasks = [task for task in self.active_tasks.values() if task.done()]
                for task in done_tasks:
                    # Extract agent name and mark as completed BEFORE processing
                    agent_name = None
                    for name, t in list(self.active_tasks.items()):
                        if t == task:
                            agent_name = name
                            break

                    if agent_name:
                        try:
                            metrics = task.result()
                            if isinstance(metrics, ExecutionMetrics) and metrics.success:
                                # Mark agent as completed in current_state for dependency tracking
                                if "agents_completed" not in current_state:
                                    current_state["agents_completed"] = []
                                if agent_name not in current_state["agents_completed"]:
                                    current_state["agents_completed"].append(agent_name)
                                    workflow_logger.debug(
                                        f"Agent {agent_name} marked as completed for dependency tracking"
                                    )
                        except Exception as e:
                            workflow_logger.error(
                                f"Failed to get task result for {agent_name}: {e}"
                            )

                    await self._process_completed_task(task, current_state)

            # Get next available agent
            next_agent = await self.execution_queue.get_next_agent()
            if next_agent is None:
                # No more agents available - check if any are still running or queued
                if not self.active_tasks:
                    # Check if there are any agents still in queue (possibly waiting for dependencies)
                    has_queued = any(
                        self.execution_queue.priority_queues[p] for p in ExecutionPriority
                    )
                    if not has_queued:
                        break  # All done - no active tasks and no queued agents

                    # There are queued agents but no active tasks - possible deadlock
                    # Try to pull agents again in case dependencies were just satisfied
                    # But prevent infinite loop
                    deadlock_check_count = getattr(self, "_deadlock_check_count", 0)
                    self._deadlock_check_count = deadlock_check_count + 1

                    if self._deadlock_check_count > 10:
                        # Likely a true deadlock - log remaining agents and exit
                        remaining = []
                        for priority in ExecutionPriority:
                            for agent_name, _, _ in self.execution_queue.priority_queues[priority]:
                                remaining.append(agent_name)
                        if remaining:
                            self.logger.warning(
                                f"Deadlock detected. Agents stuck in queue with unsatisfied dependencies: {remaining}"
                            )
                        break

                    # Give a small delay to let any pending state updates propagate
                    await asyncio.sleep(0.1)
                    continue
                else:
                    # Reset deadlock counter when we have active tasks
                    self._deadlock_check_count = 0

                # Wait for at least one task to complete
                if self.active_tasks:
                    done, pending = await asyncio.wait(
                        self.active_tasks.values(), return_when=asyncio.FIRST_COMPLETED
                    )
                    # Process completed tasks
                    for task in done:
                        await self._process_completed_task(task, current_state)
                continue

            agent_name, agent_function, context, priority = next_agent

            # Check dependencies before execution
            if not self._check_dependencies_satisfied(agent_name, context, current_state):
                # Track retry count to prevent infinite loops
                retry_count = dependency_retry_count.get(agent_name, 0) + 1
                dependency_retry_count[agent_name] = retry_count

                # Debug logging to understand dependency issues
                deps = context.get("dependencies", [])
                completed = current_state.get("agents_completed", [])
                self.logger.debug(
                    f"Agent {agent_name} dependencies not satisfied. "
                    f"Required: {deps}, Completed: {completed}, Retry: {retry_count}"
                )

                if retry_count >= max_dependency_retries:
                    # Log warning and skip this agent to prevent hanging
                    self.logger.warning(
                        f"Agent {agent_name} has unsatisfied dependencies after {retry_count} retries. "
                        f"Dependencies: {context.get('dependencies', [])}. Skipping agent."
                    )
                    # Mark as failed to prevent blocking
                    if "agents_failed" not in current_state:
                        current_state["agents_failed"] = []
                    current_state["agents_failed"].append(agent_name)
                    continue

                # Re-queue agent for later execution
                # Update context to only contain dependencies, not stale state
                updated_context = {"dependencies": context.get("dependencies", [])}
                # Lower priority for agents with unsatisfied dependencies to avoid priority inversion
                # This allows other runnable agents to execute first
                lowered_priority = (
                    ExecutionPriority.LOW if priority != ExecutionPriority.LOW else priority
                )
                await self.execution_queue.enqueue_agent(
                    agent_name, agent_function, lowered_priority, updated_context
                )

                # Small delay to prevent tight loop when only unsatisfiable agents remain
                await asyncio.sleep(0.001)
                continue

            # Reset dependency retry count since we're executing
            if agent_name in dependency_retry_count:
                del dependency_retry_count[agent_name]

            # Create and start execution task
            task = asyncio.create_task(
                self._execute_single_agent_with_metrics(
                    agent_name, agent_function, context, priority, current_state
                )
            )
            self.active_tasks[agent_name] = task

            # Track concurrent execution count
            self.concurrent_agent_count.append(len(self.active_tasks))

        # Wait for all remaining tasks to complete
        while self.active_tasks or any(
            self.execution_queue.priority_queues[p] for p in ExecutionPriority
        ):
            if self.active_tasks:
                # Wait for any task to complete
                done, pending = await asyncio.wait(
                    self.active_tasks.values(), return_when=asyncio.FIRST_COMPLETED
                )

                # Process completed tasks
                for task in done:
                    # Process the completed task - extract agent name and update current_state
                    agent_name = None
                    for name, t in list(self.active_tasks.items()):
                        if t == task:
                            agent_name = name
                            del self.active_tasks[name]
                            break

                    if agent_name:
                        try:
                            metrics = task.result()
                            if isinstance(metrics, ExecutionMetrics) and metrics.success:
                                # Mark agent as completed in current_state for dependency tracking
                                if "agents_completed" not in current_state:
                                    current_state["agents_completed"] = []
                                if agent_name not in current_state["agents_completed"]:
                                    current_state["agents_completed"].append(agent_name)
                                    workflow_logger.debug(
                                        f"Agent {agent_name} marked as completed in current_state"
                                    )
                        except Exception as e:
                            workflow_logger.error(
                                f"Failed to process task result for {agent_name}: {e}"
                            )

                    await self._process_completed_task(task, current_state)
            else:
                # Small delay to avoid busy waiting
                await asyncio.sleep(0.01)

            # Track concurrent execution count
            self.concurrent_agent_count.append(len(self.active_tasks))

        return current_state

    def _check_dependencies_satisfied(
        self, agent_name: str, context: dict[str, Any], current_state: TripPlanningWorkflowState
    ) -> bool:
        """Check if agent dependencies are satisfied."""
        dependencies = context.get("dependencies", [])
        if not dependencies:
            return True

        completed_agents = set(current_state.get("agents_completed", []))
        satisfied = all(dep in completed_agents for dep in dependencies)

        # Debug logging
        if not satisfied:
            missing = [dep for dep in dependencies if dep not in completed_agents]
            self.logger.debug(
                f"Dependencies check for {agent_name}: "
                f"Required={dependencies}, Completed={list(completed_agents)}, "
                f"Missing={missing}, Satisfied={satisfied}"
            )

        return satisfied

    async def _execute_single_agent_with_metrics(
        self,
        agent_name: str,
        agent_function: Callable[..., Any],
        context: dict[str, Any],
        priority: ExecutionPriority,
        state: TripPlanningWorkflowState,
    ) -> ExecutionMetrics:
        """Execute a single agent with comprehensive metrics tracking."""

        # Initialize metrics
        timeout_seconds = self._get_agent_timeout(agent_name, priority)
        metrics = ExecutionMetrics(
            agent_name=agent_name,
            priority=priority,
            start_time=time.time(),
            timeout_seconds=timeout_seconds,
            queue_time_ms=context.get("queue_time_ms", 0.0),
        )

        circuit_breaker = self._get_circuit_breaker(agent_name)
        semaphore = self.execution_queue.execution_semaphores[priority]

        async with semaphore:  # Respect concurrency limits
            for attempt in range(self.config.max_retries + 1):
                try:
                    metrics.retry_count = attempt

                    # Use circuit breaker for execution
                    async def execute_agent() -> Any:
                        if asyncio.iscoroutinefunction(agent_function):
                            return await agent_function(state)
                        else:
                            return await asyncio.get_event_loop().run_in_executor(
                                None, agent_function, state
                            )

                    # Execute with timeout and circuit breaker
                    result = await asyncio.wait_for(
                        circuit_breaker.call(execute_agent), timeout=timeout_seconds
                    )

                    # Success - update metrics and state
                    metrics.success = True
                    metrics.end_time = time.time()
                    metrics.calculate_execution_time()

                    # Update state with results
                    if isinstance(result, dict):
                        # Type ignore needed for TypedDict update
                        state.update(result)  # type: ignore[typeddict-item]

                    # Mark as completed
                    if "agents_completed" not in state:
                        state["agents_completed"] = []
                    if agent_name not in state["agents_completed"]:
                        state["agents_completed"].append(agent_name)

                    break  # Success, exit retry loop

                except TimeoutError:
                    metrics.timeout_occurred = True
                    error_msg = f"Agent {agent_name} timed out after {timeout_seconds}s"

                    if attempt < self.config.max_retries:
                        # Retry with exponential backoff
                        delay = self.config.retry_delay_seconds * (
                            2**attempt if self.config.exponential_backoff else 1
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Final timeout failure
                        metrics.error = error_msg
                        # Circuit breaker failure is handled internally when using call()
                        break

                except Exception as e:
                    error_msg = f"Agent {agent_name} failed: {str(e)}"
                    metrics.error = error_msg

                    if attempt < self.config.max_retries and not isinstance(
                        e, CircuitBreakerOpenError
                    ):
                        # Retry for recoverable errors
                        delay = self.config.retry_delay_seconds * (
                            2**attempt if self.config.exponential_backoff else 1
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        break  # Give up after max retries

            # Finalize metrics if not already set
            if metrics.end_time is None:
                metrics.end_time = time.time()
                metrics.calculate_execution_time()

            # Mark agent failure in state if unsuccessful
            if not metrics.success:
                if "agents_failed" not in state:
                    state["agents_failed"] = []
                if agent_name not in state["agents_failed"]:
                    state["agents_failed"].append(agent_name)

        # Clean up and record metrics
        self.execution_queue.mark_agent_completed(agent_name, priority)
        # Metrics will be added in _process_completed_task to avoid duplication

        return metrics

    async def _process_completed_task(
        self, task: asyncio.Task[Any], state: TripPlanningWorkflowState
    ) -> None:
        """Process a completed task and update state."""
        # Find and remove the task from active tasks
        agent_name = None
        for name, t in list(self.active_tasks.items()):
            if t == task:
                agent_name = name
                del self.active_tasks[name]
                break

        if agent_name and self.workflow_metrics:
            # Get the result from the task
            try:
                metrics = task.result()
                if isinstance(metrics, ExecutionMetrics):
                    # Add to workflow metrics
                    if metrics.timeout_occurred:
                        self.workflow_metrics.agents_timeout += 1
                    if metrics.success:
                        self.workflow_metrics.agents_succeeded += 1
                    else:
                        self.workflow_metrics.agents_failed += 1

                    self.workflow_metrics.agent_metrics.append(metrics)
                    self.workflow_metrics.agents_executed += 1

                workflow_logger.debug(f"Processed completed task for agent: {agent_name}")
            except Exception as e:
                workflow_logger.error(f"Failed to process task result for {agent_name}: {e}")
                if self.workflow_metrics:
                    self.workflow_metrics.agents_failed += 1

    def _finalize_metrics(self) -> None:
        """Calculate and finalize all execution metrics."""
        if not self.workflow_metrics or not self.execution_start_time:
            return

        # Calculate total execution time
        total_time = time.time() - self.execution_start_time
        self.workflow_metrics.total_execution_time_ms = total_time * 1000

        # Calculate parallel execution efficiency
        if self.workflow_metrics.agent_metrics:
            # Sequential time would be sum of all execution times
            sequential_time = sum(
                m.execution_time_ms or 0 for m in self.workflow_metrics.agent_metrics
            )

            if sequential_time > 0:
                self.workflow_metrics.parallel_efficiency = (
                    (sequential_time - self.workflow_metrics.total_execution_time_ms)
                    / sequential_time
                    * 100
                )

        # Calculate concurrent agent statistics
        if self.concurrent_agent_count:
            self.workflow_metrics.max_concurrent_agents = max(self.concurrent_agent_count)
            self.workflow_metrics.average_concurrent_agents = sum(
                self.concurrent_agent_count
            ) / len(self.concurrent_agent_count)

        # Calculate summary metrics
        self.workflow_metrics.calculate_summary_metrics()

    def _get_execution_summary(self) -> dict[str, Any]:
        """Get comprehensive execution summary."""
        if not self.workflow_metrics:
            return {}

        queue_metrics = self.execution_queue.get_queue_metrics()

        summary = {
            # Basic execution stats
            "total_agents": self.workflow_metrics.total_agents,
            "agents_succeeded": self.workflow_metrics.agents_succeeded,
            "agents_failed": self.workflow_metrics.agents_failed,
            "agents_timeout": self.workflow_metrics.agents_timeout,
            "success_rate": (
                self.workflow_metrics.agents_succeeded / self.workflow_metrics.total_agents
                if self.workflow_metrics.total_agents > 0
                else 0
            ),
            # Timing metrics
            "total_execution_time_ms": self.workflow_metrics.total_execution_time_ms,
            "average_execution_time_ms": self.workflow_metrics.average_execution_time_ms,
            "parallel_efficiency_percent": self.workflow_metrics.parallel_efficiency,
            # Performance categorization
            "fast_executions": self.workflow_metrics.fast_executions,
            "slow_executions": self.workflow_metrics.slow_executions,
            "timeout_occurrences": self.workflow_metrics.timeout_occurrences,
            "circuit_breaker_activations": self.workflow_metrics.circuit_breaker_activations,
            # Concurrency metrics
            "max_concurrent_agents": self.workflow_metrics.max_concurrent_agents,
            "average_concurrent_agents": self.workflow_metrics.average_concurrent_agents,
            # Queue and load balancing metrics
            "queue_metrics": queue_metrics,
            # Individual agent performance
            "agent_performance": [
                {
                    "agent_name": m.agent_name,
                    "priority": m.priority.value,
                    "success": m.success,
                    "execution_time_ms": m.execution_time_ms,
                    "queue_time_ms": m.queue_time_ms,
                    "retry_count": m.retry_count,
                    "timeout_occurred": m.timeout_occurred,
                    "circuit_breaker_open": m.circuit_breaker_open,
                    "performance_category": (
                        "fast"
                        if m.is_fast_execution
                        else "slow"
                        if m.is_slow_execution
                        else "normal"
                    ),
                }
                for m in self.workflow_metrics.agent_metrics
            ],
            # Configuration used
            "execution_config": {
                "max_concurrent_agents": self.config.max_concurrent_agents,
                "default_timeout_seconds": self.config.default_timeout_seconds,
                "max_retries": self.config.max_retries,
                "load_balancing_enabled": self.config.enable_load_balancing,
                "adaptive_timeout_enabled": self.config.adaptive_timeout,
            },
        }

        return summary


# Utility functions for workflow integration
async def execute_agents_with_parallel_optimization(
    state: TripPlanningWorkflowState,
    agent_functions: dict[str, Callable[..., Any]],
    config: ParallelExecutionConfig | None = None,
    dependencies: dict[str, list[str]] | None = None,
) -> TripPlanningWorkflowState:
    """
    Convenience function to execute agents with parallel optimization.

    Args:
        state: Current workflow state
        agent_functions: Dictionary of agent functions to execute
        config: Optional parallel execution configuration
        dependencies: Optional agent dependency mapping

    Returns:
        Updated workflow state with parallel execution results
    """
    optimizer = ParallelExecutionOptimizer(config)
    return await optimizer.execute_agents_parallel(state, agent_functions, dependencies)


def create_optimized_parallel_config(
    max_concurrent: int = 6, timeout_seconds: int = 30, enable_adaptive: bool = True
) -> ParallelExecutionConfig:
    """
    Create an optimized parallel execution configuration.

    Args:
        max_concurrent: Maximum concurrent agent executions
        timeout_seconds: Default timeout for agent execution
        enable_adaptive: Enable adaptive timeout adjustments

    Returns:
        Configured ParallelExecutionConfig instance
    """
    return ParallelExecutionConfig(
        max_concurrent_agents=max_concurrent,
        default_timeout_seconds=timeout_seconds,
        adaptive_timeout=enable_adaptive,
        enable_load_balancing=True,
        exponential_backoff=True,
    )

"""Agent coordination and dependency management for LangGraph workflows."""

import asyncio
import time
from typing import Any, Dict, List, Set
from dataclasses import dataclass, field
from enum import Enum

from ..utils.logging import workflow_logger
from .orchestrator import TripPlanningWorkflowState


class AgentStatus(str, Enum):
    """Agent execution status."""
    
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionPhase(str, Enum):
    """Workflow execution phases."""
    
    INITIALIZATION = "initialization"
    PARALLEL_EXECUTION = "parallel_execution"
    COORDINATION = "coordination"
    FINALIZATION = "finalization"


@dataclass
class AgentExecutionInfo:
    """Information about an agent's execution."""
    
    agent_name: str
    status: AgentStatus = AgentStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    start_time: float | None = None
    end_time: float | None = None
    error: str | None = None
    retry_count: int = 0
    execution_phase: ExecutionPhase = ExecutionPhase.INITIALIZATION
    is_critical: bool = True  # Whether failure of this agent should fail the entire workflow
    
    @property
    def execution_time_ms(self) -> float | None:
        """Calculate execution time in milliseconds."""
        if self.start_time is None or self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000
    
    @property
    def is_finished(self) -> bool:
        """Check if agent execution is finished (completed, failed, or skipped)."""
        return self.status in [AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.SKIPPED]


class AgentDependencyResolver:
    """
    Resolves agent dependencies and determines execution order for optimal parallel execution.
    
    Manages agent dependencies, execution phases, and coordinates parallel execution
    while respecting dependency constraints.
    """
    
    def __init__(self, dependency_map: Dict[str, List[str]], critical_agents: Set[str] | None = None):
        """
        Initialize dependency resolver.
        
        Args:
            dependency_map: Map of agent_name -> list of required dependencies
            critical_agents: Set of agents whose failure should fail the workflow
        """
        self.dependency_map = dependency_map
        self.critical_agents = critical_agents or set()
        self.agents: Dict[str, AgentExecutionInfo] = {}
        self.execution_phases: Dict[ExecutionPhase, List[str]] = {
            ExecutionPhase.INITIALIZATION: [],
            ExecutionPhase.PARALLEL_EXECUTION: [],
            ExecutionPhase.COORDINATION: [],
            ExecutionPhase.FINALIZATION: []
        }
        
        # Initialize agent execution info
        self._initialize_agents()
        self._calculate_execution_phases()
    
    def _initialize_agents(self) -> None:
        """Initialize agent execution information."""
        all_agents = set()
        
        # Get all agents from dependency map
        for agent, deps in self.dependency_map.items():
            all_agents.add(agent)
            all_agents.update(deps)
        
        # Create execution info for each agent
        for agent in all_agents:
            dependencies = self.dependency_map.get(agent, [])
            is_critical = agent in self.critical_agents
            
            self.agents[agent] = AgentExecutionInfo(
                agent_name=agent,
                dependencies=dependencies,
                is_critical=is_critical
            )
    
    def _calculate_execution_phases(self) -> None:
        """Calculate execution phases for optimal parallel execution."""
        # Phase 1: Initialization - agents with no dependencies
        initialization_agents = [
            agent for agent, info in self.agents.items() 
            if not info.dependencies
        ]
        
        # Phase 2: Parallel execution - agents that can run after initialization
        parallel_agents = []
        
        # Phase 3: Coordination - agents that depend on multiple parallel agents
        coordination_agents = []
        
        # Phase 4: Finalization - final processing agents
        finalization_agents = []
        
        # Categorize agents based on dependency patterns
        for agent, info in self.agents.items():
            if not info.dependencies:
                initialization_agents.append(agent)
                info.execution_phase = ExecutionPhase.INITIALIZATION
            elif len(info.dependencies) == 1 and info.dependencies[0] in initialization_agents:
                parallel_agents.append(agent)
                info.execution_phase = ExecutionPhase.PARALLEL_EXECUTION
            elif len(info.dependencies) > 1:
                coordination_agents.append(agent)
                info.execution_phase = ExecutionPhase.COORDINATION
            else:
                finalization_agents.append(agent)
                info.execution_phase = ExecutionPhase.FINALIZATION
        
        self.execution_phases = {
            ExecutionPhase.INITIALIZATION: initialization_agents,
            ExecutionPhase.PARALLEL_EXECUTION: parallel_agents,
            ExecutionPhase.COORDINATION: coordination_agents,
            ExecutionPhase.FINALIZATION: finalization_agents
        }
    
    def get_ready_agents(self) -> List[str]:
        """
        Get list of agents ready for execution.
        
        Returns:
            List of agent names that can be executed now
        """
        ready_agents = []
        
        for agent_name, info in self.agents.items():
            if info.status != AgentStatus.PENDING:
                continue
                
            # Check if all dependencies are completed
            dependencies_met = all(
                self.agents[dep].status == AgentStatus.COMPLETED
                for dep in info.dependencies
                if dep in self.agents
            )
            
            if dependencies_met:
                ready_agents.append(agent_name)
                info.status = AgentStatus.READY
        
        return ready_agents
    
    def mark_agent_running(self, agent_name: str) -> None:
        """Mark an agent as running."""
        if agent_name in self.agents:
            self.agents[agent_name].status = AgentStatus.RUNNING
            self.agents[agent_name].start_time = time.time()
    
    def mark_agent_completed(self, agent_name: str) -> None:
        """Mark an agent as completed."""
        if agent_name in self.agents:
            self.agents[agent_name].status = AgentStatus.COMPLETED
            self.agents[agent_name].end_time = time.time()
    
    def mark_agent_failed(self, agent_name: str, error: str, retry_count: int = 0) -> None:
        """Mark an agent as failed."""
        if agent_name in self.agents:
            info = self.agents[agent_name]
            info.status = AgentStatus.FAILED
            info.end_time = time.time()
            info.error = error
            info.retry_count = retry_count
    
    def mark_agent_skipped(self, agent_name: str, reason: str) -> None:
        """Mark an agent as skipped."""
        if agent_name in self.agents:
            info = self.agents[agent_name]
            info.status = AgentStatus.SKIPPED
            info.end_time = time.time()
            info.error = f"Skipped: {reason}"
    
    def should_fail_workflow(self) -> bool:
        """
        Check if workflow should fail based on critical agent failures.
        
        Returns:
            True if workflow should fail
        """
        for agent_name in self.critical_agents:
            if agent_name in self.agents:
                agent_info = self.agents[agent_name]
                if agent_info.status == AgentStatus.FAILED:
                    return True
        return False
    
    def can_continue_workflow(self) -> bool:
        """
        Check if workflow can continue despite some failures.
        
        Returns:
            True if workflow can continue
        """
        # Workflow can continue if no critical agents have failed
        return not self.should_fail_workflow()
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get execution summary for all agents.
        
        Returns:
            Dictionary with execution statistics and status
        """
        total_agents = len(self.agents)
        completed = sum(1 for info in self.agents.values() if info.status == AgentStatus.COMPLETED)
        failed = sum(1 for info in self.agents.values() if info.status == AgentStatus.FAILED)
        skipped = sum(1 for info in self.agents.values() if info.status == AgentStatus.SKIPPED)
        running = sum(1 for info in self.agents.values() if info.status == AgentStatus.RUNNING)
        
        # Calculate total execution time
        total_execution_time = 0.0
        for info in self.agents.values():
            if info.execution_time_ms:
                total_execution_time += info.execution_time_ms
        
        return {
            "total_agents": total_agents,
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "running": running,
            "success_rate": completed / total_agents if total_agents > 0 else 0,
            "total_execution_time_ms": total_execution_time,
            "critical_failures": [
                info.agent_name for info in self.agents.values()
                if info.status == AgentStatus.FAILED and info.is_critical
            ],
            "execution_phases": {
                phase.value: agents for phase, agents in self.execution_phases.items()
            },
            "agent_details": {
                agent_name: {
                    "status": info.status,
                    "execution_time_ms": info.execution_time_ms,
                    "error": info.error,
                    "retry_count": info.retry_count,
                    "phase": info.execution_phase.value,
                    "is_critical": info.is_critical
                }
                for agent_name, info in self.agents.items()
            }
        }
    
    def get_agents_by_phase(self, phase: ExecutionPhase) -> List[str]:
        """
        Get agents for a specific execution phase.
        
        Args:
            phase: Execution phase to get agents for
            
        Returns:
            List of agent names in the specified phase
        """
        return self.execution_phases.get(phase, [])


class WorkflowCoordinator:
    """
    Coordinates workflow execution with dependency management and state transitions.
    
    Manages the overall workflow execution, handles state persistence,
    and coordinates agent execution with proper error boundaries.
    """
    
    def __init__(self, state: TripPlanningWorkflowState):
        """
        Initialize workflow coordinator.
        
        Args:
            state: Current workflow state
        """
        self.state = state
        self.workflow_id = state["workflow_id"]
        self.request_id = state["request_id"]
        
        # Initialize dependency resolver
        dependency_map = state.get("agent_dependencies", {})
        critical_agents = {"initialize_trip", "itinerary_agent", "finalize_plan"}
        
        self.dependency_resolver = AgentDependencyResolver(
            dependency_map=dependency_map,
            critical_agents=critical_agents
        )
        
        # Execution coordination
        self.current_phase = ExecutionPhase.INITIALIZATION
        self.parallel_execution_tasks: Dict[str, asyncio.Task] = {}
        self.state_transitions: List[Dict[str, Any]] = []
    
    async def coordinate_execution(self, node_functions: Dict[str, Any]) -> TripPlanningWorkflowState:
        """
        Coordinate the execution of all workflow nodes with dependency management.
        
        Args:
            node_functions: Dictionary of node name -> function mappings
            
        Returns:
            Final workflow state
        """
        workflow_logger.log_coordination_started(
            workflow_id=self.workflow_id,
            request_id=self.request_id,
            total_agents=len(self.dependency_resolver.agents)
        )
        
        try:
            # Execute phases in order
            await self._execute_initialization_phase(node_functions)
            await self._execute_parallel_phase(node_functions)
            await self._execute_coordination_phase(node_functions)
            await self._execute_finalization_phase(node_functions)
            
            # Update final state
            self.state["status"] = "completed"
            execution_summary = self.dependency_resolver.get_execution_summary()
            self.state["optimization_metrics"].update(execution_summary)
            
            workflow_logger.log_coordination_completed(
                workflow_id=self.workflow_id,
                request_id=self.request_id,
                execution_summary=execution_summary
            )
            
            return self.state
            
        except Exception as e:
            workflow_logger.log_coordination_failed(
                workflow_id=self.workflow_id,
                request_id=self.request_id,
                error=str(e),
                execution_summary=self.dependency_resolver.get_execution_summary()
            )
            
            self.state["status"] = "failed"
            self.state["error"] = str(e)
            raise
    
    async def _execute_initialization_phase(self, node_functions: Dict[str, Any]) -> None:
        """Execute initialization phase agents."""
        self.current_phase = ExecutionPhase.INITIALIZATION
        initialization_agents = self.dependency_resolver.get_agents_by_phase(ExecutionPhase.INITIALIZATION)
        
        for agent_name in initialization_agents:
            if agent_name in node_functions:
                await self._execute_single_agent(agent_name, node_functions[agent_name])
    
    async def _execute_parallel_phase(self, node_functions: Dict[str, Any]) -> None:
        """Execute parallel phase agents concurrently."""
        self.current_phase = ExecutionPhase.PARALLEL_EXECUTION
        parallel_agents = self.dependency_resolver.get_agents_by_phase(ExecutionPhase.PARALLEL_EXECUTION)
        
        # Create tasks for parallel execution
        tasks = []
        for agent_name in parallel_agents:
            if agent_name in node_functions:
                task = asyncio.create_task(
                    self._execute_single_agent(agent_name, node_functions[agent_name])
                )
                tasks.append((agent_name, task))
                self.parallel_execution_tasks[agent_name] = task
        
        # Wait for all parallel tasks to complete
        if tasks:
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            # Process results and handle any exceptions
            for (agent_name, task), result in zip(tasks, results):
                if isinstance(result, Exception):
                    self.dependency_resolver.mark_agent_failed(
                        agent_name, str(result)
                    )
                    if not self.dependency_resolver.can_continue_workflow():
                        raise result
    
    async def _execute_coordination_phase(self, node_functions: Dict[str, Any]) -> None:
        """Execute coordination phase agents."""
        self.current_phase = ExecutionPhase.COORDINATION
        coordination_agents = self.dependency_resolver.get_agents_by_phase(ExecutionPhase.COORDINATION)
        
        for agent_name in coordination_agents:
            if agent_name in node_functions:
                # Check if dependencies are met
                if self._check_agent_dependencies(agent_name):
                    await self._execute_single_agent(agent_name, node_functions[agent_name])
                else:
                    self.dependency_resolver.mark_agent_skipped(
                        agent_name, "Dependencies not met"
                    )
    
    async def _execute_finalization_phase(self, node_functions: Dict[str, Any]) -> None:
        """Execute finalization phase agents."""
        self.current_phase = ExecutionPhase.FINALIZATION
        finalization_agents = self.dependency_resolver.get_agents_by_phase(ExecutionPhase.FINALIZATION)
        
        for agent_name in finalization_agents:
            if agent_name in node_functions:
                await self._execute_single_agent(agent_name, node_functions[agent_name])
    
    async def _execute_single_agent(self, agent_name: str, agent_function: Any) -> None:
        """
        Execute a single agent with error boundaries.
        
        Args:
            agent_name: Name of the agent to execute
            agent_function: Function to execute for this agent
        """
        start_time = time.time()
        
        try:
            self.dependency_resolver.mark_agent_running(agent_name)
            
            # Record state transition
            self._record_state_transition(agent_name, "started")
            
            workflow_logger.log_agent_execution_started(
                workflow_id=self.workflow_id,
                request_id=self.request_id,
                agent_name=agent_name,
                phase=self.current_phase.value
            )
            
            # Execute agent function
            if asyncio.iscoroutinefunction(agent_function):
                updated_state = await agent_function(self.state)
            else:
                updated_state = agent_function(self.state)
            
            # Update state with results
            self.state.update(updated_state)
            
            # Mark as completed
            self.dependency_resolver.mark_agent_completed(agent_name)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Record successful completion
            self._record_state_transition(agent_name, "completed", execution_time_ms)
            
            workflow_logger.log_agent_execution_completed(
                workflow_id=self.workflow_id,
                request_id=self.request_id,
                agent_name=agent_name,
                execution_time_ms=execution_time_ms
            )
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            self.dependency_resolver.mark_agent_failed(agent_name, error_msg)
            
            # Record failure
            self._record_state_transition(agent_name, "failed", execution_time_ms, error_msg)
            
            workflow_logger.log_agent_execution_failed(
                workflow_id=self.workflow_id,
                request_id=self.request_id,
                agent_name=agent_name,
                error=error_msg,
                execution_time_ms=execution_time_ms
            )
            
            # Check if this is a critical failure
            if not self.dependency_resolver.can_continue_workflow():
                raise RuntimeError(f"Critical agent {agent_name} failed: {error_msg}") from e
            
            # For non-critical failures, log but continue
            workflow_logger.log_agent_failure_handled(
                workflow_id=self.workflow_id,
                request_id=self.request_id,
                agent_name=agent_name,
                error=error_msg,
                workflow_continuing=True
            )
    
    def _check_agent_dependencies(self, agent_name: str) -> bool:
        """
        Check if all dependencies for an agent are satisfied.
        
        Args:
            agent_name: Name of the agent to check
            
        Returns:
            True if dependencies are satisfied
        """
        if agent_name not in self.dependency_resolver.agents:
            return False
            
        agent_info = self.dependency_resolver.agents[agent_name]
        
        for dep in agent_info.dependencies:
            if dep in self.dependency_resolver.agents:
                dep_info = self.dependency_resolver.agents[dep]
                if dep_info.status != AgentStatus.COMPLETED:
                    return False
        
        return True
    
    def _record_state_transition(
        self, 
        agent_name: str, 
        transition_type: str, 
        execution_time_ms: float | None = None,
        error: str | None = None
    ) -> None:
        """Record a state transition for audit and debugging."""
        transition = {
            "timestamp": time.time(),
            "agent_name": agent_name,
            "transition_type": transition_type,
            "phase": self.current_phase.value,
            "execution_time_ms": execution_time_ms,
            "error": error
        }
        
        self.state_transitions.append(transition)
        
        # Store in workflow state for persistence
        if "state_transitions" not in self.state:
            self.state["state_transitions"] = []
        self.state["state_transitions"].append(transition)
    
    def get_coordination_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive coordination metrics.
        
        Returns:
            Dictionary with coordination statistics
        """
        execution_summary = self.dependency_resolver.get_execution_summary()
        
        # Calculate phase timings
        phase_timings = {}
        for phase in ExecutionPhase:
            phase_transitions = [
                t for t in self.state_transitions 
                if t["phase"] == phase.value and t["execution_time_ms"] is not None
            ]
            
            if phase_transitions:
                total_time = sum(t["execution_time_ms"] for t in phase_transitions)
                phase_timings[phase.value] = {
                    "total_time_ms": total_time,
                    "agent_count": len(phase_transitions),
                    "average_time_ms": total_time / len(phase_transitions)
                }
        
        return {
            **execution_summary,
            "phase_timings": phase_timings,
            "total_state_transitions": len(self.state_transitions),
            "parallel_tasks_count": len(self.parallel_execution_tasks),
            "current_phase": self.current_phase.value
        }
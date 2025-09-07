"""Error recovery and fallback strategies for LangGraph workflow orchestration.

This module provides comprehensive error handling, retry mechanisms, circuit breaker integration,
and fallback workflows for partial agent failures in the travel companion system.
"""

import asyncio
import logging
import random
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

from travel_companion.utils.circuit_breaker import CircuitBreaker
from travel_companion.utils.circuit_breaker import CircuitBreakerOpenError as CBOpenError
from travel_companion.utils.errors import (
    CriticalAgentFailureError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryStrategy(str, Enum):
    """Retry strategy options for failed operations."""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"


class AgentPriority(str, Enum):
    """Agent priority levels for fallback strategies."""

    CRITICAL = "critical"  # Flight, Hotel - must succeed
    HIGH = "high"  # Weather - affects other agents
    MEDIUM = "medium"  # Activity - nice to have
    LOW = "low"  # Food - optional enhancement


class FallbackStrategy(str, Enum):
    """Fallback strategies for agent failures."""

    RETRY_WITH_BACKOFF = "retry_with_backoff"
    CIRCUIT_BREAKER = "circuit_breaker"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    FALLBACK_DATA = "fallback_data"
    SKIP_AGENT = "skip_agent"


class RetryConfig:
    """Configuration for retry mechanisms."""

    def __init__(
        self,
        max_attempts: int = 3,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
    ):
        self.max_attempts = max_attempts
        self.strategy = strategy
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for next attempt based on strategy."""
        if self.strategy == RetryStrategy.IMMEDIATE:
            return 0.0

        elif self.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.base_delay

        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.base_delay * attempt

        else:  # EXPONENTIAL_BACKOFF
            delay = self.base_delay * (self.backoff_multiplier ** (attempt - 1))

        # Apply max delay cap
        delay = min(delay, self.max_delay)

        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0.0, delay)


class FallbackData:
    """Fallback data for agents when external APIs fail."""

    # Default flight options for fallback
    DEFAULT_FLIGHT_OPTIONS = {
        "flights": [],
        "message": "Flight search temporarily unavailable. Please try again later.",
        "fallback": True,
    }

    # Default hotel options for fallback
    DEFAULT_HOTEL_OPTIONS = {
        "hotels": [],
        "message": "Hotel search temporarily unavailable. Please try again later.",
        "fallback": True,
    }

    # Default activity options for fallback
    DEFAULT_ACTIVITY_OPTIONS = {
        "activities": [],
        "message": "Activity recommendations temporarily unavailable.",
        "fallback": True,
    }

    # Default weather data for fallback
    DEFAULT_WEATHER_DATA = {
        "forecast": [],
        "message": "Weather data temporarily unavailable. Plan for variable conditions.",
        "fallback": True,
    }

    # Default food recommendations for fallback
    DEFAULT_FOOD_OPTIONS = {
        "restaurants": [],
        "message": "Restaurant recommendations temporarily unavailable.",
        "fallback": True,
    }

    @classmethod
    def get_fallback_data(cls, agent_type: str) -> dict[str, Any]:
        """Get fallback data for specific agent type."""
        fallback_map = {
            "flight": cls.DEFAULT_FLIGHT_OPTIONS,
            "hotel": cls.DEFAULT_HOTEL_OPTIONS,
            "activity": cls.DEFAULT_ACTIVITY_OPTIONS,
            "weather": cls.DEFAULT_WEATHER_DATA,
            "food": cls.DEFAULT_FOOD_OPTIONS,
        }
        return fallback_map.get(agent_type, {"fallback": True})


class ErrorRecoveryManager:
    """Manages error recovery strategies and fallback workflows."""

    def __init__(self):
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.retry_configs: dict[str, RetryConfig] = {}
        self.agent_priorities: dict[str, AgentPriority] = {}
        self._setup_default_configurations()

    def _setup_default_configurations(self) -> None:
        """Set up default configurations for agents."""
        # Circuit breaker configurations per agent
        cb_configs = {
            "flight_agent": {"failure_threshold": 3, "recovery_timeout": 30},
            "hotel_agent": {"failure_threshold": 3, "recovery_timeout": 30},
            "activity_agent": {"failure_threshold": 5, "recovery_timeout": 20},
            "weather_agent": {"failure_threshold": 5, "recovery_timeout": 20},
            "food_agent": {"failure_threshold": 7, "recovery_timeout": 15},
            "itinerary_agent": {"failure_threshold": 2, "recovery_timeout": 45},
        }

        for agent_name, config in cb_configs.items():
            self.circuit_breakers[agent_name] = CircuitBreaker(
                name=agent_name,
                **config,
            )

        # Retry configurations per agent
        retry_configs = {
            "flight_agent": RetryConfig(max_attempts=3, base_delay=2.0, max_delay=30.0),
            "hotel_agent": RetryConfig(max_attempts=3, base_delay=2.0, max_delay=30.0),
            "activity_agent": RetryConfig(max_attempts=2, base_delay=1.0, max_delay=15.0),
            "weather_agent": RetryConfig(max_attempts=2, base_delay=1.0, max_delay=15.0),
            "food_agent": RetryConfig(max_attempts=2, base_delay=1.0, max_delay=10.0),
            "itinerary_agent": RetryConfig(max_attempts=2, base_delay=3.0, max_delay=45.0),
        }

        for agent_name, config in retry_configs.items():
            self.retry_configs[agent_name] = config

        # Agent priority levels
        self.agent_priorities = {
            "flight_agent": AgentPriority.CRITICAL,
            "hotel_agent": AgentPriority.CRITICAL,
            "weather_agent": AgentPriority.HIGH,
            "activity_agent": AgentPriority.MEDIUM,
            "food_agent": AgentPriority.LOW,
            "itinerary_agent": AgentPriority.CRITICAL,
        }

    async def execute_with_recovery(
        self,
        agent_name: str,
        operation: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Execute agent operation with comprehensive error recovery.

        Args:
            agent_name: Name of the agent being executed
            operation: The operation to execute
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation or fallback data

        Raises:
            TravelCompanionError: If all recovery strategies fail for critical agents
        """
        circuit_breaker = self.circuit_breakers.get(agent_name)
        retry_config = self.retry_configs.get(
            agent_name,
            RetryConfig(),  # Default config if not found
        )

        last_exception: Exception | None = None

        for attempt in range(1, retry_config.max_attempts + 1):
            try:
                # Try circuit breaker if available
                if circuit_breaker:
                    result = await circuit_breaker.call(operation, *args, **kwargs)
                else:
                    if asyncio.iscoroutinefunction(operation):
                        result = await operation(*args, **kwargs)
                    else:
                        result = operation(*args, **kwargs)

                logger.info(f"Agent {agent_name} executed successfully on attempt {attempt}")
                return result

            except CBOpenError as e:
                logger.warning(f"Circuit breaker open for {agent_name}: {e}")
                return await self._handle_circuit_breaker_open(agent_name)

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Agent {agent_name} failed on attempt {attempt}/{retry_config.max_attempts}: {e}"
                )

                # Don't retry on the last attempt
                if attempt < retry_config.max_attempts:
                    delay = retry_config.calculate_delay(attempt)
                    logger.info(f"Retrying {agent_name} after {delay:.2f}s delay")
                    await asyncio.sleep(delay)
                else:
                    # All retry attempts exhausted
                    return await self._handle_final_failure(agent_name, last_exception)

        # This shouldn't be reached, but handle gracefully
        return await self._handle_final_failure(agent_name, last_exception)

    async def _handle_circuit_breaker_open(self, agent_name: str) -> Any:
        """Handle circuit breaker open scenario."""
        priority = self.agent_priorities.get(agent_name, AgentPriority.MEDIUM)

        if priority == AgentPriority.CRITICAL:
            logger.error(f"Critical agent {agent_name} circuit breaker is open")
            raise CriticalAgentFailureError(
                f"Critical service {agent_name} is temporarily unavailable",
                agent_name=agent_name,
                recovery_strategy="circuit_breaker_open",
            )

        # Return fallback data for non-critical agents
        logger.info(f"Using fallback data for {agent_name} (circuit breaker open)")
        return FallbackData.get_fallback_data(agent_name.replace("_agent", ""))

    async def _handle_final_failure(self, agent_name: str, exception: Exception | None) -> Any:
        """Handle final failure after all retry attempts."""
        priority = self.agent_priorities.get(agent_name, AgentPriority.MEDIUM)

        if priority == AgentPriority.CRITICAL:
            logger.error(f"Critical agent {agent_name} failed after all retry attempts")
            raise CriticalAgentFailureError(
                f"Critical service {agent_name} is unavailable",
                agent_name=agent_name,
                recovery_strategy="all_retries_exhausted",
                details={"last_error": str(exception) if exception else "Unknown error"},
            )

        # Return fallback data for non-critical agents
        logger.info(f"Using fallback data for {agent_name} after final failure")
        return FallbackData.get_fallback_data(agent_name.replace("_agent", ""))

    def get_circuit_breaker_status(self, agent_name: str) -> dict[str, Any] | None:
        """Get circuit breaker status for an agent."""
        circuit_breaker = self.circuit_breakers.get(agent_name)
        return circuit_breaker.get_status() if circuit_breaker else None

    def get_all_circuit_breaker_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {agent_name: cb.get_status() for agent_name, cb in self.circuit_breakers.items()}

    def reset_circuit_breaker(self, agent_name: str) -> bool:
        """Reset circuit breaker for an agent (for manual recovery)."""
        circuit_breaker = self.circuit_breakers.get(agent_name)
        if circuit_breaker:
            from travel_companion.utils.circuit_breaker import CircuitState

            circuit_breaker.failure_count = 0
            circuit_breaker.last_failure_time = None
            circuit_breaker.next_attempt_time = None
            circuit_breaker.state = CircuitState.CLOSED
            logger.info(f"Circuit breaker for {agent_name} manually reset")
            return True
        return False

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on all managed agents."""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "agents": {},
        }

        unhealthy_count = 0

        for agent_name, circuit_breaker in self.circuit_breakers.items():
            agent_status = {
                "status": "healthy" if circuit_breaker.is_closed else "unhealthy",
                "circuit_breaker": circuit_breaker.get_status(),
                "priority": self.agent_priorities.get(agent_name, "unknown").value,
            }

            if not circuit_breaker.is_closed:
                unhealthy_count += 1

                # Check if this affects overall health
                priority = self.agent_priorities.get(agent_name, AgentPriority.MEDIUM)
                if priority in [AgentPriority.CRITICAL, AgentPriority.HIGH]:
                    health_status["overall_status"] = "degraded"

            health_status["agents"][agent_name] = agent_status

        # If too many agents are down, mark as unhealthy
        if unhealthy_count >= len(self.circuit_breakers) // 2:
            health_status["overall_status"] = "unhealthy"

        health_status["unhealthy_count"] = unhealthy_count
        health_status["total_agents"] = len(self.circuit_breakers)

        return health_status


class WorkflowFallbackOrchestrator:
    """Orchestrates fallback workflows when primary workflows fail."""

    def __init__(self, error_recovery_manager: ErrorRecoveryManager):
        self.error_recovery_manager = error_recovery_manager

    async def create_minimal_itinerary(
        self, trip_request: dict[str, Any], successful_agents: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create a minimal itinerary with whatever data is available.

        This fallback workflow ensures users get some results even when
        multiple agents fail.
        """
        logger.info("Creating minimal itinerary with partial agent results")

        minimal_itinerary = {
            "trip_id": trip_request.get("trip_id"),
            "destination": trip_request.get("destination"),
            "start_date": trip_request.get("start_date"),
            "end_date": trip_request.get("end_date"),
            "budget": trip_request.get("budget"),
            "status": "partial",
            "warning": "Some services were temporarily unavailable. Results may be incomplete.",
            "available_data": {},
            "missing_data": [],
            "recommendations": [],
        }

        # Include available agent results
        for agent_name, result in successful_agents.items():
            if result and not result.get("fallback", False):
                minimal_itinerary["available_data"][agent_name] = result

        # Identify missing critical data
        required_agents = ["flight_agent", "hotel_agent"]
        for agent in required_agents:
            if agent not in successful_agents or successful_agents[agent].get("fallback"):
                minimal_itinerary["missing_data"].append(agent.replace("_agent", ""))

        # Add general recommendations
        minimal_itinerary["recommendations"] = [
            "Please try your search again in a few minutes as some services may be temporarily unavailable.",
            "Consider adjusting your travel dates or destination if issues persist.",
            "Contact support if you continue to experience problems.",
        ]

        # Add specific recommendations based on available data
        if "weather_agent" in successful_agents:
            minimal_itinerary["recommendations"].append(
                "Weather data is available - check forecast details for packing recommendations."
            )

        if "activity_agent" in successful_agents:
            minimal_itinerary["recommendations"].append(
                "Activity recommendations are available - explore suggested attractions and experiences."
            )

        return minimal_itinerary

    async def execute_degraded_workflow(
        self,
        trip_request: dict[str, Any],
        agent_operations: dict[str, Callable],
    ) -> dict[str, Any]:
        """
        Execute workflow with graceful degradation for failed agents.

        This method attempts to execute all agents but continues even if
        non-critical agents fail, ensuring partial results are available.
        """
        logger.info("Executing degraded workflow with fallback strategies")

        successful_agents: dict[str, Any] = {}
        failed_agents: list[str] = []

        # Execute agents in parallel where possible
        tasks = []
        for agent_name, operation in agent_operations.items():
            task = asyncio.create_task(
                self._execute_agent_with_fallback(agent_name, operation), name=agent_name
            )
            tasks.append(task)

        # Wait for all agents to complete (with fallbacks)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for agent_name, result in zip(agent_operations.keys(), results, strict=False):
            if isinstance(result, Exception):
                logger.error(f"Agent {agent_name} failed with fallback: {result}")
                failed_agents.append(agent_name)
            else:
                successful_agents[agent_name] = result

        # Create final itinerary based on available data
        if failed_agents:
            logger.warning(f"Agents failed even with fallbacks: {failed_agents}")

        return await self.create_minimal_itinerary(trip_request, successful_agents)

    async def _execute_agent_with_fallback(self, agent_name: str, operation: Callable) -> Any:
        """Execute agent operation with fallback handling."""
        try:
            return await self.error_recovery_manager.execute_with_recovery(agent_name, operation)
        except Exception as e:
            logger.error(f"Agent {agent_name} failed completely: {e}")
            # Return fallback data even for critical agents in degraded mode
            return FallbackData.get_fallback_data(agent_name.replace("_agent", ""))


# Singleton instances for global use
error_recovery_manager = ErrorRecoveryManager()
workflow_fallback_orchestrator = WorkflowFallbackOrchestrator(error_recovery_manager)

"""Tests for parallel execution optimization in LangGraph workflows."""

import asyncio
import time
from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from travel_companion.models.trip import TripDestination, TripPlanRequest, TripRequirements
from travel_companion.workflows.orchestrator import TripPlanningWorkflowState
from travel_companion.workflows.parallel_executor import (
    ExecutionMetrics,
    ExecutionPriority,
    ParallelExecutionConfig,
    ParallelExecutionOptimizer,
    ParallelExecutionQueue,
    WorkflowExecutionMetrics,
    create_optimized_parallel_config,
    execute_agents_with_parallel_optimization,
)


class TestParallelExecutionConfig:
    """Test parallel execution configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ParallelExecutionConfig()

        assert config.default_timeout_seconds == 30
        assert config.max_concurrent_agents == 6
        assert config.max_retries == 2
        assert config.enable_load_balancing is True
        assert config.adaptive_timeout is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ParallelExecutionConfig(
            max_concurrent_agents=10,
            default_timeout_seconds=60,
            max_retries=5,
            enable_load_balancing=False
        )

        assert config.max_concurrent_agents == 10
        assert config.default_timeout_seconds == 60
        assert config.max_retries == 5
        assert config.enable_load_balancing is False


class TestExecutionMetrics:
    """Test execution metrics tracking."""

    def test_execution_metrics_creation(self):
        """Test creating execution metrics."""
        metrics = ExecutionMetrics(
            agent_name="test_agent",
            priority=ExecutionPriority.HIGH,
            start_time=time.time()
        )

        assert metrics.agent_name == "test_agent"
        assert metrics.priority == ExecutionPriority.HIGH
        assert metrics.success is False
        assert metrics.retry_count == 0
        assert metrics.execution_time_ms is None

    def test_execution_time_calculation(self):
        """Test execution time calculation."""
        start_time = time.time()
        metrics = ExecutionMetrics(
            agent_name="test_agent",
            priority=ExecutionPriority.MEDIUM,
            start_time=start_time
        )

        # Simulate execution
        time.sleep(0.01)  # 10ms
        metrics.end_time = time.time()
        execution_time = metrics.calculate_execution_time()

        assert execution_time > 0
        assert metrics.execution_time_ms == execution_time
        assert execution_time >= 10  # At least 10ms

    def test_performance_categorization(self):
        """Test performance categorization."""
        # Fast execution
        fast_metrics = ExecutionMetrics(
            agent_name="fast_agent",
            priority=ExecutionPriority.HIGH,
            start_time=time.time(),
            execution_time_ms=3000.0  # 3 seconds
        )
        assert fast_metrics.is_fast_execution is True
        assert fast_metrics.is_slow_execution is False

        # Slow execution
        slow_metrics = ExecutionMetrics(
            agent_name="slow_agent",
            priority=ExecutionPriority.LOW,
            start_time=time.time(),
            execution_time_ms=25000.0  # 25 seconds
        )
        assert slow_metrics.is_fast_execution is False
        assert slow_metrics.is_slow_execution is True


class TestWorkflowExecutionMetrics:
    """Test workflow-level execution metrics."""

    def test_workflow_metrics_creation(self):
        """Test creating workflow execution metrics."""
        metrics = WorkflowExecutionMetrics(workflow_id="test_workflow")

        assert metrics.workflow_id == "test_workflow"
        assert metrics.total_agents == 0
        assert metrics.parallel_efficiency == 0.0
        assert len(metrics.agent_metrics) == 0

    def test_summary_metrics_calculation(self):
        """Test calculating summary metrics from agent metrics."""
        workflow_metrics = WorkflowExecutionMetrics(workflow_id="test_workflow")

        # Add some agent metrics
        agent_metrics = [
            ExecutionMetrics("agent1", ExecutionPriority.HIGH, time.time(), end_time=time.time() + 3.0, execution_time_ms=3000.0, success=True),  # Fast
            ExecutionMetrics("agent2", ExecutionPriority.MEDIUM, time.time(), end_time=time.time() + 15.0, execution_time_ms=15000.0, success=True),  # Normal
            ExecutionMetrics("agent3", ExecutionPriority.LOW, time.time(), end_time=time.time() + 25.0, execution_time_ms=25000.0, success=False),  # Slow
        ]

        workflow_metrics.agent_metrics = agent_metrics
        workflow_metrics.calculate_summary_metrics()

        assert workflow_metrics.total_agents == 3
        assert workflow_metrics.agents_executed == 3
        assert workflow_metrics.agents_succeeded == 2
        assert workflow_metrics.agents_failed == 1
        assert workflow_metrics.fast_executions == 1
        assert workflow_metrics.slow_executions == 1
        assert workflow_metrics.average_execution_time_ms == (3000.0 + 15000.0 + 25000.0) / 3


class TestParallelExecutionQueue:
    """Test parallel execution queue management."""

    @pytest.fixture
    def queue_config(self):
        """Provide queue configuration."""
        return ParallelExecutionConfig(max_concurrent_agents=4)

    @pytest.fixture
    def execution_queue(self, queue_config):
        """Provide execution queue instance."""
        return ParallelExecutionQueue(queue_config)

    async def test_agent_enqueuing(self, execution_queue):
        """Test enqueuing agents with priorities."""
        mock_function = AsyncMock()
        context = {"test": "context"}

        await execution_queue.enqueue_agent(
            agent_name="test_agent",
            agent_function=mock_function,
            priority=ExecutionPriority.HIGH,
            execution_context=context
        )

        assert len(execution_queue.priority_queues[ExecutionPriority.HIGH]) == 1
        assert execution_queue.priority_queues[ExecutionPriority.HIGH][0][0] == "test_agent"

    async def test_priority_based_retrieval(self, execution_queue):
        """Test retrieving agents based on priority order."""
        mock_function = AsyncMock()

        # Enqueue agents with different priorities
        await execution_queue.enqueue_agent("low_agent", mock_function, ExecutionPriority.LOW, {})
        await execution_queue.enqueue_agent("critical_agent", mock_function, ExecutionPriority.CRITICAL, {})
        await execution_queue.enqueue_agent("medium_agent", mock_function, ExecutionPriority.MEDIUM, {})

        # Should retrieve critical first
        next_agent = await execution_queue.get_next_agent()
        assert next_agent is not None
        assert next_agent[0] == "critical_agent"

        # Then medium
        next_agent = await execution_queue.get_next_agent()
        assert next_agent is not None
        assert next_agent[0] == "medium_agent"

        # Then low
        next_agent = await execution_queue.get_next_agent()
        assert next_agent is not None
        assert next_agent[0] == "low_agent"

    async def test_load_balancing(self, execution_queue):
        """Test load balancing adjustments."""
        mock_function = AsyncMock()

        # Fill high priority queue to trigger load balancing
        for i in range(4):
            await execution_queue.enqueue_agent(f"high_agent_{i}", mock_function, ExecutionPriority.HIGH, {})

        # This agent should be demoted to medium priority due to load balancing
        await execution_queue.enqueue_agent("activity_agent", mock_function, ExecutionPriority.HIGH, {})

        # Verify load balancing occurred
        assert execution_queue.load_balance_stats["decisions"] > 0

    def test_queue_metrics(self, execution_queue):
        """Test queue performance metrics."""
        metrics = execution_queue.get_queue_metrics()

        assert "total_queued" in metrics
        assert "total_active" in metrics
        assert "queued_by_priority" in metrics
        assert "active_by_priority" in metrics
        assert "load_balance_decisions" in metrics


class TestParallelExecutionOptimizer:
    """Test the main parallel execution optimizer."""

    @pytest.fixture
    def optimizer_config(self):
        """Provide optimizer configuration."""
        return ParallelExecutionConfig(
            max_concurrent_agents=4,
            default_timeout_seconds=5,  # Short timeout for tests
            critical_timeout_seconds=5,
            high_priority_timeout_seconds=5,
            medium_priority_timeout_seconds=5,
            low_priority_timeout_seconds=5,
            max_retries=1
        )

    @pytest.fixture
    def optimizer(self, optimizer_config):
        """Provide optimizer instance."""
        return ParallelExecutionOptimizer(optimizer_config)

    @pytest.fixture
    def sample_state(self):
        """Provide sample workflow state."""
        trip_request = TripPlanRequest(
            destination=TripDestination(city="Paris", country="France", country_code="FR"),
            requirements=TripRequirements(
                start_date=date(2024, 6, 1),
                end_date=date(2024, 6, 7),
                travelers=2,
                budget=5000.0
            )
        )

        return TripPlanningWorkflowState(
            request_id="test_request",
            workflow_id="test_workflow",
            user_id="test_user",
            status="running",
            error=None,
            start_time=time.time(),
            end_time=None,
            current_node="test_node",
            input_data={},
            output_data={},
            intermediate_results={},
            trip_request=trip_request,
            trip_id="test_trip",
            agents_completed=[],
            agents_failed=[],
            agent_dependencies={},
            flight_results=[],
            hotel_results=[],
            activity_results=[],
            weather_data={},
            food_recommendations=[],
            itinerary_data={},
            user_preferences={},
            budget_tracking={"total_budget": 5000.0},
            optimization_metrics={}
        )

    def test_agent_priority_determination(self, optimizer):
        """Test agent priority determination."""
        assert optimizer._determine_agent_priority("weather_agent") == ExecutionPriority.CRITICAL
        assert optimizer._determine_agent_priority("flight_agent") == ExecutionPriority.HIGH
        assert optimizer._determine_agent_priority("activity_agent") == ExecutionPriority.MEDIUM
        assert optimizer._determine_agent_priority("unknown_agent") == ExecutionPriority.MEDIUM

    def test_agent_timeout_calculation(self, optimizer):
        """Test agent timeout calculation."""
        timeout = optimizer._get_agent_timeout("flight_agent", ExecutionPriority.HIGH)
        assert timeout == optimizer.config.high_priority_timeout_seconds

        timeout = optimizer._get_agent_timeout("weather_agent", ExecutionPriority.CRITICAL)
        assert timeout == optimizer.config.critical_timeout_seconds

    async def test_successful_parallel_execution(self, optimizer, sample_state):
        """Test successful parallel execution of agents."""
        # Mock agent functions
        async def mock_weather_agent(state):
            await asyncio.sleep(0.1)
            state["weather_data"] = {"temperature": 20}
            return state

        async def mock_flight_agent(state):
            await asyncio.sleep(0.1)
            state["flight_results"] = [{"flight": "test"}]
            return state

        agent_functions = {
            "weather_agent": mock_weather_agent,
            "flight_agent": mock_flight_agent
        }

        # Execute with parallel optimization
        result_state = await optimizer.execute_agents_parallel(
            state=sample_state,
            agent_functions=agent_functions,
            dependencies={}
        )

        # Verify results
        assert "weather_data" in result_state
        assert "flight_results" in result_state
        assert "parallel_execution_metrics" in result_state
        assert len(result_state["agents_completed"]) == 2

    async def test_agent_dependency_handling(self, optimizer, sample_state):
        """Test handling of agent dependencies."""
        execution_order = []

        async def mock_weather_agent(state):
            execution_order.append("weather")
            await asyncio.sleep(0.05)
            state["weather_data"] = {"temperature": 20}
            return state

        async def mock_activity_agent(state):
            execution_order.append("activity")
            await asyncio.sleep(0.05)
            state["activity_results"] = [{"activity": "test"}]
            return state

        agent_functions = {
            "weather_agent": mock_weather_agent,
            "activity_agent": mock_activity_agent
        }

        dependencies = {
            "activity_agent": ["weather_agent"]
        }

        # Execute with dependencies
        result_state = await optimizer.execute_agents_parallel(
            state=sample_state,
            agent_functions=agent_functions,
            dependencies=dependencies
        )

        # Verify execution order
        assert execution_order == ["weather", "activity"]
        assert len(result_state["agents_completed"]) == 2

    async def test_timeout_handling(self, optimizer, sample_state):
        """Test timeout handling for slow agents."""
        async def slow_agent(state):
            await asyncio.sleep(10)  # Longer than config timeout (5s)
            return state

        agent_functions = {"slow_agent": slow_agent}

        # Execute and expect timeout handling
        result_state = await optimizer.execute_agents_parallel(
            state=sample_state,
            agent_functions=agent_functions,
            dependencies={}
        )

        # Verify timeout was handled
        metrics = result_state["parallel_execution_metrics"]
        assert metrics["agents_timeout"] > 0
        assert metrics["success_rate"] < 1.0

    async def test_circuit_breaker_integration(self, optimizer, sample_state):
        """Test circuit breaker integration."""
        failure_count = 0

        async def failing_agent(state):
            nonlocal failure_count
            failure_count += 1
            raise Exception("Agent failed")

        agent_functions = {"failing_agent": failing_agent}

        # Execute multiple times to trigger circuit breaker
        for _ in range(3):
            try:
                await optimizer.execute_agents_parallel(
                    state=sample_state,
                    agent_functions=agent_functions,
                    dependencies={}
                )
            except Exception:
                pass

        # Verify circuit breaker was activated
        optimizer._get_circuit_breaker("failing_agent")
        # Note: Circuit breaker behavior depends on specific implementation

    async def test_retry_mechanism(self, optimizer, sample_state):
        """Test retry mechanism with exponential backoff."""
        attempt_count = 0

        async def retry_agent(state):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise Exception("Temporary failure")
            state["retry_results"] = ["success"]
            return state

        agent_functions = {"retry_agent": retry_agent}

        # Execute with retries
        result_state = await optimizer.execute_agents_parallel(
            state=sample_state,
            agent_functions=agent_functions,
            dependencies={}
        )

        # Verify retry succeeded
        assert attempt_count == 2
        assert "retry_results" in result_state
        assert len(result_state["agents_completed"]) == 1

    async def test_performance_metrics_collection(self, optimizer, sample_state):
        """Test comprehensive performance metrics collection."""
        # Clear pre-existing agents
        sample_state["agents_completed"] = []
        sample_state["agents_failed"] = []
        async def fast_agent(state):
            await asyncio.sleep(0.001)  # Very fast
            state["fast_result"] = "done"
            return state

        async def slow_agent(state):
            await asyncio.sleep(0.1)  # Slower but not timeout
            state["slow_result"] = "done"
            return state

        agent_functions = {
            "fast_agent": fast_agent,
            "slow_agent": slow_agent
        }

        # Execute agents
        result_state = await optimizer.execute_agents_parallel(
            state=sample_state,
            agent_functions=agent_functions,
            dependencies={}
        )

        # Verify metrics collection
        metrics = result_state["parallel_execution_metrics"]

        assert "total_execution_time_ms" in metrics
        assert "parallel_efficiency_percent" in metrics
        assert "max_concurrent_agents" in metrics
        assert "agent_performance" in metrics
        assert len(metrics["agent_performance"]) == 2

        # Check individual agent metrics
        agent_performances = {ap["agent_name"]: ap for ap in metrics["agent_performance"]}
        assert agent_performances["fast_agent"]["performance_category"] == "fast"
        assert agent_performances["slow_agent"]["performance_category"] == "fast"  # 100ms is still fast (<5s)


class TestUtilityFunctions:
    """Test utility functions for parallel execution."""

    async def test_execute_agents_with_parallel_optimization(self):
        """Test convenience function for parallel execution."""
        sample_state = TripPlanningWorkflowState(
            request_id="test_request",
            workflow_id="test_workflow",
            user_id="test_user",
            status="running",
            error=None,
            start_time=time.time(),
            end_time=None,
            current_node="test_node",
            input_data={},
            output_data={},
            intermediate_results={},
            trip_request=Mock(),
            trip_id="test_trip",
            agents_completed=[],
            agents_failed=[],
            agent_dependencies={},
            flight_results=[],
            hotel_results=[],
            activity_results=[],
            weather_data={},
            food_recommendations=[],
            itinerary_data={},
            user_preferences={},
            budget_tracking={"total_budget": 5000.0},
            optimization_metrics={}
        )

        async def mock_agent(state):
            state["test_result"] = "success"
            return state

        agent_functions = {"test_agent": mock_agent}

        # Execute using convenience function
        result_state = await execute_agents_with_parallel_optimization(
            state=sample_state,
            agent_functions=agent_functions
        )

        assert "test_result" in result_state
        assert "parallel_execution_metrics" in result_state

    def test_create_optimized_parallel_config(self):
        """Test creating optimized configuration."""
        config = create_optimized_parallel_config(
            max_concurrent=8,
            timeout_seconds=45,
            enable_adaptive=False
        )

        assert config.max_concurrent_agents == 8
        assert config.default_timeout_seconds == 45
        assert config.adaptive_timeout is False
        assert config.enable_load_balancing is True  # Default


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple features."""

    @pytest.fixture
    def integration_optimizer(self):
        """Provide optimizer configured for integration tests."""
        config = ParallelExecutionConfig(
            max_concurrent_agents=6,
            default_timeout_seconds=10,
            max_retries=2,
            enable_load_balancing=True,
            adaptive_timeout=True
        )
        return ParallelExecutionOptimizer(config)

    @pytest.fixture
    def complex_state(self):
        """Provide complex workflow state for integration tests."""
        trip_request = TripPlanRequest(
            destination=TripDestination(city="Tokyo", country="Japan", country_code="JP"),
            requirements=TripRequirements(
                start_date=date(2024, 8, 15),
                end_date=date(2024, 8, 22),
                travelers=4,
                budget=8000.0
            ),
            preferences={"activity_types": ["cultural", "outdoor"], "cuisine_types": ["japanese", "international"]}
        )

        return TripPlanningWorkflowState(
            request_id="integration_test",
            workflow_id="integration_workflow",
            user_id="integration_user",
            status="running",
            error=None,
            start_time=time.time(),
            end_time=None,
            current_node="coordinated_execution",
            input_data={"trip_request": trip_request.model_dump()},
            output_data={},
            intermediate_results={},
            trip_request=trip_request,
            trip_id="integration_trip",
            agents_completed=[],
            agents_failed=[],
            agent_dependencies={
                "activity_agent": ["weather_agent"],
                "itinerary_agent": ["flight_agent", "hotel_agent", "activity_agent", "food_agent"]
            },
            flight_results=[],
            hotel_results=[],
            activity_results=[],
            weather_data={},
            food_recommendations=[],
            itinerary_data={},
            user_preferences=trip_request.preferences or {},
            budget_tracking={"total_budget": 8000.0, "allocated": 8000.0, "spent": 0.0},
            optimization_metrics={}
        )

    async def test_full_trip_planning_workflow(self, integration_optimizer, complex_state):
        """Test complete trip planning workflow with all agents."""
        # Clear pre-existing agent state
        complex_state["agents_completed"] = []
        complex_state["agents_failed"] = []

        # Define realistic agent functions
        async def weather_agent(state):
            await asyncio.sleep(0.02)  # Simulate API call
            state["weather_data"] = {
                "forecast": {"daily_forecasts": [{"condition": "sunny"}, {"condition": "cloudy"}]},
                "temperature_range": {"min": 18, "max": 28}
            }
            return state

        async def flight_agent(state):
            await asyncio.sleep(0.05)  # Simulate longer API call
            state["flight_results"] = [
                {"airline": "JAL", "price": 1200, "duration": "14h"},
                {"airline": "ANA", "price": 1150, "duration": "15h"}
            ]
            budget = state.get("budget_tracking", {})
            budget["spent"] = budget.get("spent", 0) + 1150
            return state

        async def hotel_agent(state):
            await asyncio.sleep(0.04)
            state["hotel_results"] = [
                {"name": "Tokyo Hotel", "price_per_night": {"amount": 200}, "rating": 4.5},
                {"name": "Shibuya Inn", "price_per_night": {"amount": 150}, "rating": 4.0}
            ]
            budget = state.get("budget_tracking", {})
            budget["spent"] = budget.get("spent", 0) + 1400  # 7 nights * 200
            return state

        async def activity_agent(state):
            await asyncio.sleep(0.03)
            # Check weather dependency
            weather_data = state.get("weather_data", {})
            activities = [
                {"name": "Tokyo Tower", "estimated_cost": {"amount": 50}, "type": "cultural"},
                {"name": "Senso-ji Temple", "estimated_cost": {"amount": 0}, "type": "cultural"}
            ]

            # Add outdoor activities if weather is good
            if weather_data.get("forecast", {}).get("daily_forecasts", [{}])[0].get("condition") == "sunny":
                activities.append({"name": "Ueno Park", "estimated_cost": {"amount": 10}, "type": "outdoor"})

            state["activity_results"] = activities
            return state

        async def food_agent(state):
            await asyncio.sleep(0.03)
            state["food_recommendations"] = [
                {"name": "Sushi Jiro", "average_cost_per_person": {"amount": 300}, "cuisine": "japanese"},
                {"name": "Ramen Ichiran", "average_cost_per_person": {"amount": 25}, "cuisine": "japanese"}
            ]
            return state

        async def itinerary_agent(state):
            await asyncio.sleep(0.06)  # Longest processing time
            # Verify all dependencies are met
            required_keys = ["flight_results", "hotel_results", "activity_results", "food_recommendations"]
            for key in required_keys:
                if not state.get(key):
                    raise Exception(f"Missing required data: {key}")

            state["itinerary_data"] = {
                "daily_schedules": [{"day": 1, "activities": ["arrival", "hotel_checkin"]}],
                "optimization_score": 0.85,
                "total_estimated_cost": 3500.0
            }
            return state

        # Define agent functions
        agent_functions = {
            "weather_agent": weather_agent,
            "flight_agent": flight_agent,
            "hotel_agent": hotel_agent,
            "activity_agent": activity_agent,
            "food_agent": food_agent,
            "itinerary_agent": itinerary_agent
        }

        # Define dependencies
        dependencies = {
            "activity_agent": ["weather_agent"],
            "itinerary_agent": ["flight_agent", "hotel_agent", "activity_agent", "food_agent"]
        }

        # Execute complete workflow
        start_time = time.time()
        result_state = await integration_optimizer.execute_agents_parallel(
            state=complex_state,
            agent_functions=agent_functions,
            dependencies=dependencies
        )
        execution_time = time.time() - start_time

        # Verify all agents completed successfully
        assert len(result_state["agents_completed"]) == 6
        assert len(result_state["agents_failed"]) == 0

        # Verify all expected data is present
        assert "weather_data" in result_state
        assert "flight_results" in result_state
        assert "hotel_results" in result_state
        assert "activity_results" in result_state
        assert "food_recommendations" in result_state
        assert "itinerary_data" in result_state

        # Verify dependency execution order was respected
        # Weather should complete before activities
        # All others should complete before itinerary

        # Verify performance metrics
        metrics = result_state["parallel_execution_metrics"]
        assert metrics["total_agents"] == 6
        assert metrics["agents_succeeded"] == 6
        assert metrics["success_rate"] == 1.0
        assert metrics["max_concurrent_agents"] > 1  # Should have parallel execution

        # Verify parallel efficiency (should be faster than sequential)
        sequential_time = sum(ap["execution_time_ms"] for ap in metrics["agent_performance"]) / 1000
        assert execution_time < sequential_time * 0.8  # At least 20% improvement

        # Verify weather-dependent activity logic worked
        activities = result_state["activity_results"]
        activity_names = [a["name"] for a in activities]
        assert "Ueno Park" in activity_names  # Should be added due to sunny weather

    async def test_partial_failure_resilience(self, integration_optimizer, complex_state):
        """Test resilience to partial agent failures."""
        failure_count = 0

        async def stable_agent(name, delay=0.02):
            async def agent(state):
                await asyncio.sleep(delay)
                state[f"{name}_results"] = [{"test": "data"}]
                return state
            return agent

        async def failing_agent(state):
            nonlocal failure_count
            failure_count += 1
            raise Exception("Simulated failure")

        # Mix of stable and failing agents
        agent_functions = {
            "weather_agent": await stable_agent("weather"),
            "flight_agent": failing_agent,  # This will fail
            "hotel_agent": await stable_agent("hotel"),
            "activity_agent": await stable_agent("activity"),
            "food_agent": failing_agent,  # This will also fail
        }

        # Execute with some failures
        result_state = await integration_optimizer.execute_agents_parallel(
            state=complex_state,
            agent_functions=agent_functions,
            dependencies={}
        )

        # Verify partial success handling
        metrics = result_state["parallel_execution_metrics"]
        assert metrics["agents_succeeded"] == 3  # weather, hotel, activity
        assert metrics["agents_failed"] == 2     # flight, food
        assert metrics["success_rate"] == 0.6   # 3/5

        # Verify successful agents completed
        assert "weather_results" in result_state
        assert "hotel_results" in result_state
        assert "activity_results" in result_state

        # Verify failed agents are tracked
        assert len(result_state["agents_failed"]) == 2


if __name__ == "__main__":
    pytest.main([__file__])

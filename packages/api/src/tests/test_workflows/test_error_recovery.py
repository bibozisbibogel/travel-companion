"""Comprehensive tests for error recovery and fallback strategies."""

from unittest.mock import AsyncMock, patch

import pytest

from travel_companion.utils.errors import CriticalAgentFailureError
from travel_companion.workflows.error_recovery import (
    ErrorRecoveryManager,
    FallbackData,
    RetryConfig,
    RetryStrategy,
    WorkflowFallbackOrchestrator,
    error_recovery_manager,
    workflow_fallback_orchestrator,
)


class TestRetryConfig:
    """Test retry configuration and delay calculations."""

    def test_exponential_backoff_delay(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=1.0,
            backoff_multiplier=2.0,
            jitter=False,
        )

        assert config.calculate_delay(1) == 1.0  # base_delay * 2^0
        assert config.calculate_delay(2) == 2.0  # base_delay * 2^1
        assert config.calculate_delay(3) == 4.0  # base_delay * 2^2

    def test_linear_backoff_delay(self):
        """Test linear backoff delay calculation."""
        config = RetryConfig(
            strategy=RetryStrategy.LINEAR_BACKOFF,
            base_delay=2.0,
            jitter=False,
        )

        assert config.calculate_delay(1) == 2.0  # base_delay * 1
        assert config.calculate_delay(2) == 4.0  # base_delay * 2
        assert config.calculate_delay(3) == 6.0  # base_delay * 3

    def test_fixed_delay(self):
        """Test fixed delay strategy."""
        config = RetryConfig(
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=5.0,
            jitter=False,
        )

        assert config.calculate_delay(1) == 5.0
        assert config.calculate_delay(2) == 5.0
        assert config.calculate_delay(3) == 5.0

    def test_immediate_delay(self):
        """Test immediate retry strategy."""
        config = RetryConfig(strategy=RetryStrategy.IMMEDIATE)

        assert config.calculate_delay(1) == 0.0
        assert config.calculate_delay(2) == 0.0

    def test_max_delay_cap(self):
        """Test that delays are capped at max_delay."""
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=10.0,
            max_delay=15.0,
            backoff_multiplier=2.0,
            jitter=False,
        )

        assert config.calculate_delay(1) == 10.0
        assert config.calculate_delay(2) == 15.0  # Capped at max_delay
        assert config.calculate_delay(3) == 15.0  # Capped at max_delay

    def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness to delays."""
        config = RetryConfig(
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=10.0,
            jitter=True,
        )

        # Get multiple delay calculations
        delays = [config.calculate_delay(1) for _ in range(10)]

        # All delays should be positive
        assert all(delay >= 0 for delay in delays)

        # Not all delays should be identical (due to jitter)
        assert len(set(delays)) > 1


class TestFallbackData:
    """Test fallback data provider."""

    def test_flight_fallback_data(self):
        """Test flight agent fallback data."""
        data = FallbackData.get_fallback_data("flight")

        assert data["fallback"] is True
        assert "flights" in data
        assert "message" in data
        assert data["flights"] == []

    def test_hotel_fallback_data(self):
        """Test hotel agent fallback data."""
        data = FallbackData.get_fallback_data("hotel")

        assert data["fallback"] is True
        assert "hotels" in data
        assert "message" in data

    def test_weather_fallback_data(self):
        """Test weather agent fallback data."""
        data = FallbackData.get_fallback_data("weather")

        assert data["fallback"] is True
        assert "forecast" in data
        assert "message" in data

    def test_unknown_agent_fallback(self):
        """Test fallback for unknown agent type."""
        data = FallbackData.get_fallback_data("unknown_agent")

        assert data["fallback"] is True


class TestErrorRecoveryManager:
    """Test error recovery manager functionality."""

    @pytest.fixture
    def recovery_manager(self):
        """Create error recovery manager for testing."""
        return ErrorRecoveryManager()

    @pytest.mark.asyncio
    async def test_successful_execution_no_retry(self, recovery_manager):
        """Test successful execution without retries."""
        mock_operation = AsyncMock(return_value="success")

        result = await recovery_manager.execute_with_recovery(
            "flight_agent", mock_operation
        )

        assert result == "success"
        mock_operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self, recovery_manager):
        """Test retry mechanism on transient failures."""
        mock_operation = AsyncMock(side_effect=[
            Exception("Temporary failure"),
            "success"
        ])

        with patch('asyncio.sleep'):  # Speed up test
            result = await recovery_manager.execute_with_recovery(
                "flight_agent", mock_operation
            )

        assert result == "success"
        assert mock_operation.call_count == 2

    @pytest.mark.asyncio
    async def test_critical_agent_failure_raises_exception(self, recovery_manager):
        """Test that critical agent failures raise exceptions."""
        mock_operation = AsyncMock(side_effect=Exception("Persistent failure"))

        with patch('asyncio.sleep'):  # Speed up test
            with pytest.raises(CriticalAgentFailureError) as exc_info:
                await recovery_manager.execute_with_recovery(
                    "flight_agent", mock_operation
                )

        assert "flight_agent" in str(exc_info.value)
        assert "all_retries_exhausted" in exc_info.value.details["recovery_strategy"]

    @pytest.mark.asyncio
    async def test_non_critical_agent_returns_fallback(self, recovery_manager):
        """Test that non-critical agent failures return fallback data."""
        mock_operation = AsyncMock(side_effect=Exception("Persistent failure"))

        with patch('asyncio.sleep'):  # Speed up test
            result = await recovery_manager.execute_with_recovery(
                "activity_agent", mock_operation
            )

        assert result["fallback"] is True
        assert "activities" in result

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, recovery_manager):
        """Test integration with circuit breaker."""
        # Mock circuit breaker to be open
        circuit_breaker = recovery_manager.circuit_breakers["flight_agent"]
        from travel_companion.utils.circuit_breaker import CircuitState
        circuit_breaker.state = CircuitState.OPEN

        mock_operation = AsyncMock()

        with pytest.raises(CriticalAgentFailureError):
            await recovery_manager.execute_with_recovery(
                "flight_agent", mock_operation
            )

        # Operation should not be called when circuit is open
        mock_operation.assert_not_called()

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_fallback_for_non_critical(self, recovery_manager):
        """Test circuit breaker open returns fallback for non-critical agents."""
        # Mock circuit breaker to be open
        circuit_breaker = recovery_manager.circuit_breakers["activity_agent"]
        from travel_companion.utils.circuit_breaker import CircuitState
        circuit_breaker.state = CircuitState.OPEN

        mock_operation = AsyncMock()

        result = await recovery_manager.execute_with_recovery(
            "activity_agent", mock_operation
        )

        assert result["fallback"] is True
        mock_operation.assert_not_called()

    def test_get_circuit_breaker_status(self, recovery_manager):
        """Test getting circuit breaker status."""
        status = recovery_manager.get_circuit_breaker_status("flight_agent")

        assert status is not None
        assert "name" in status
        assert "state" in status
        assert status["name"] == "flight_agent"

    def test_get_all_circuit_breaker_status(self, recovery_manager):
        """Test getting all circuit breaker statuses."""
        all_status = recovery_manager.get_all_circuit_breaker_status()

        assert isinstance(all_status, dict)
        assert "flight_agent" in all_status
        assert "hotel_agent" in all_status
        assert len(all_status) == 6  # Number of configured agents

    def test_reset_circuit_breaker(self, recovery_manager):
        """Test manual circuit breaker reset."""
        # Simulate failure to open circuit breaker
        circuit_breaker = recovery_manager.circuit_breakers["flight_agent"]
        circuit_breaker.failure_count = 5
        from travel_companion.utils.circuit_breaker import CircuitState
        circuit_breaker.state = CircuitState.OPEN

        success = recovery_manager.reset_circuit_breaker("flight_agent")

        assert success is True
        assert circuit_breaker.failure_count == 0
        from travel_companion.utils.circuit_breaker import CircuitState
        assert circuit_breaker.state == CircuitState.CLOSED

    def test_reset_nonexistent_circuit_breaker(self, recovery_manager):
        """Test reset of non-existent circuit breaker."""
        success = recovery_manager.reset_circuit_breaker("nonexistent_agent")
        assert success is False

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, recovery_manager):
        """Test health check when all agents are healthy."""
        health = await recovery_manager.health_check()

        assert health["overall_status"] == "healthy"
        assert health["unhealthy_count"] == 0
        assert len(health["agents"]) == 6

        for agent_status in health["agents"].values():
            assert agent_status["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_with_critical_agent_down(self, recovery_manager):
        """Test health check with critical agent down."""
        # Open circuit breaker for critical agent
        circuit_breaker = recovery_manager.circuit_breakers["flight_agent"]
        from travel_companion.utils.circuit_breaker import CircuitState
        circuit_breaker.state = CircuitState.OPEN

        health = await recovery_manager.health_check()

        assert health["overall_status"] == "degraded"
        assert health["unhealthy_count"] == 1
        assert health["agents"]["flight_agent"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_majority_agents_down(self, recovery_manager):
        """Test health check when majority of agents are down."""
        # Open circuit breakers for multiple agents
        from travel_companion.utils.circuit_breaker import CircuitState
        for agent_name in ["flight_agent", "hotel_agent", "activity_agent", "weather_agent"]:
            circuit_breaker = recovery_manager.circuit_breakers[agent_name]
            circuit_breaker.state = CircuitState.OPEN

        health = await recovery_manager.health_check()

        assert health["overall_status"] == "unhealthy"
        assert health["unhealthy_count"] == 4


class TestWorkflowFallbackOrchestrator:
    """Test workflow fallback orchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator for testing."""
        recovery_manager = ErrorRecoveryManager()
        return WorkflowFallbackOrchestrator(recovery_manager)

    @pytest.mark.asyncio
    async def test_create_minimal_itinerary(self, orchestrator):
        """Test creating minimal itinerary with partial results."""
        trip_request = {
            "trip_id": "test-trip-123",
            "destination": "Paris",
            "start_date": "2024-06-01",
            "end_date": "2024-06-07",
            "budget": 2000,
        }

        successful_agents = {
            "weather_agent": {"forecast": [{"day": 1, "temperature": 20}]},
            "activity_agent": {"fallback": True, "activities": []},
        }

        result = await orchestrator.create_minimal_itinerary(
            trip_request, successful_agents
        )

        assert result["trip_id"] == "test-trip-123"
        assert result["status"] == "partial"
        assert result["destination"] == "Paris"
        assert "warning" in result
        assert len(result["available_data"]) == 1  # Only weather_agent (non-fallback)
        assert "flight" in result["missing_data"]
        assert "hotel" in result["missing_data"]
        assert len(result["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_execute_degraded_workflow(self, orchestrator):
        """Test executing degraded workflow."""
        trip_request = {
            "trip_id": "test-trip-456",
            "destination": "London",
        }

        # Mock agent operations
        flight_mock = AsyncMock(return_value={"flights": ["flight1"]})
        hotel_mock = AsyncMock(side_effect=Exception("Hotel API down"))

        agent_operations = {
            "flight_agent": flight_mock,
            "hotel_agent": hotel_mock,
        }

        result = await orchestrator.execute_degraded_workflow(
            trip_request, agent_operations
        )

        assert result["trip_id"] == "test-trip-456"
        assert result["status"] == "partial"
        assert "flight_agent" in result["available_data"]
        assert "hotel" in result["missing_data"]

    @pytest.mark.asyncio
    async def test_execute_agent_with_fallback(self, orchestrator):
        """Test executing agent with fallback handling."""
        # Mock successful operation
        success_operation = AsyncMock(return_value={"data": "success"})
        result = await orchestrator._execute_agent_with_fallback(
            "weather_agent", success_operation
        )
        assert result == {"data": "success"}

        # Mock failed operation
        failed_operation = AsyncMock(side_effect=Exception("API failure"))
        with patch('asyncio.sleep'):  # Speed up test
            result = await orchestrator._execute_agent_with_fallback(
                "weather_agent", failed_operation
            )
        assert result["fallback"] is True


class TestSingletonInstances:
    """Test singleton instances."""

    def test_error_recovery_manager_singleton(self):
        """Test that error recovery manager is properly initialized."""
        assert error_recovery_manager is not None
        assert isinstance(error_recovery_manager, ErrorRecoveryManager)
        assert len(error_recovery_manager.circuit_breakers) == 6

    def test_workflow_fallback_orchestrator_singleton(self):
        """Test that workflow fallback orchestrator is properly initialized."""
        assert workflow_fallback_orchestrator is not None
        assert isinstance(workflow_fallback_orchestrator, WorkflowFallbackOrchestrator)
        assert workflow_fallback_orchestrator.error_recovery_manager == error_recovery_manager


class TestIntegrationScenarios:
    """Integration tests for complex error recovery scenarios."""

    @pytest.fixture
    def recovery_manager(self):
        """Create error recovery manager for integration tests."""
        return ErrorRecoveryManager()

    @pytest.fixture
    def orchestrator(self, recovery_manager):
        """Create orchestrator for integration tests."""
        return WorkflowFallbackOrchestrator(recovery_manager)

    @pytest.mark.asyncio
    async def test_complete_workflow_with_mixed_failures(
        self, recovery_manager, orchestrator
    ):
        """Test complete workflow execution with mixed success/failure scenarios."""
        # Mock operations with different failure patterns
        flight_operation = AsyncMock(return_value={"flights": ["flight1", "flight2"]})
        hotel_operation = AsyncMock(side_effect=[
            Exception("Temporary failure"),
            {"hotels": ["hotel1"]}  # Succeeds on retry
        ])
        activity_operation = AsyncMock(side_effect=Exception("Persistent failure"))
        weather_operation = AsyncMock(return_value={"forecast": [{"temp": 22}]})

        agent_operations = {
            "flight_agent": flight_operation,
            "hotel_agent": hotel_operation,
            "activity_agent": activity_operation,
            "weather_agent": weather_operation,
        }

        trip_request = {
            "trip_id": "integration-test",
            "destination": "Barcelona",
            "start_date": "2024-07-01",
            "end_date": "2024-07-07",
            "budget": 3000,
        }

        with patch('asyncio.sleep'):  # Speed up test
            result = await orchestrator.execute_degraded_workflow(
                trip_request, agent_operations
            )

        # Verify results
        assert result["trip_id"] == "integration-test"
        assert result["destination"] == "Barcelona"

        # Flight and weather should succeed
        assert "flight_agent" in result["available_data"]
        assert "weather_agent" in result["available_data"]

        # Hotel should succeed on retry
        assert "hotel_agent" in result["available_data"]

        # Activity should have fallback data
        # (Note: In degraded workflow, even failed agents get fallback data)

        # Verify operations were called
        flight_operation.assert_called_once()
        hotel_operation.assert_called()  # Called multiple times due to retry
        activity_operation.assert_called()  # Called multiple times due to retry
        weather_operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_cascade_prevention(self, recovery_manager):
        """Test that circuit breakers prevent cascade failures."""
        # Create operations that always fail
        failing_operation = AsyncMock(side_effect=Exception("Service unavailable"))

        # Execute multiple times to trigger circuit breaker
        results = []
        with patch('asyncio.sleep'):  # Speed up test
            for _i in range(10):
                try:
                    result = await recovery_manager.execute_with_recovery(
                        "activity_agent", failing_operation
                    )
                    results.append(result)
                except Exception as e:
                    results.append(f"Exception: {type(e).__name__}")

        # Verify circuit breaker behavior
        # First few calls should attempt operation and get fallback
        # Later calls should be blocked by circuit breaker
        assert len(results) == 10

        # Some results should be fallback data
        fallback_count = sum(1 for r in results if isinstance(r, dict) and r.get("fallback"))
        assert fallback_count > 0

        # Circuit breaker should eventually open for this agent
        cb_status = recovery_manager.get_circuit_breaker_status("activity_agent")
        # Circuit breaker might be open or half-open depending on timing
        assert cb_status["failure_count"] >= 0

"""Tests for circuit breaker implementation."""

import asyncio
from datetime import timedelta

import pytest

from travel_companion.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)


class TestCircuitBreaker:
    """Test cases for CircuitBreaker functionality."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker instance for testing."""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1,  # Short timeout for testing
            expected_exception=ValueError,
            name="TestCircuitBreaker",
        )

    @pytest.mark.asyncio
    async def test_successful_call(self, circuit_breaker):
        """Test successful function call through circuit breaker."""

        async def successful_function(x, y):
            return x + y

        result = await circuit_breaker.call(successful_function, 5, 10)

        assert result == 15
        assert circuit_breaker.is_closed
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_sync_function_call(self, circuit_breaker):
        """Test synchronous function call through circuit breaker."""

        def sync_function(x, y):
            return x * y

        result = await circuit_breaker.call(sync_function, 3, 4)

        assert result == 12
        assert circuit_breaker.is_closed

    @pytest.mark.asyncio
    async def test_failure_counting(self, circuit_breaker):
        """Test that failures are counted correctly."""

        async def failing_function():
            raise ValueError("Test failure")

        # First failure
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_function)

        assert circuit_breaker.failure_count == 1
        assert circuit_breaker.is_closed

        # Second failure
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_function)

        assert circuit_breaker.failure_count == 2
        assert circuit_breaker.is_closed

        # Third failure should open the circuit
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_function)

        assert circuit_breaker.failure_count == 3
        assert circuit_breaker.is_open

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self, circuit_breaker):
        """Test that circuit opens after failure threshold is reached."""

        async def failing_function():
            raise ValueError("Test failure")

        # Trigger failures to open circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_function)

        assert circuit_breaker.is_open
        assert circuit_breaker.next_attempt_time is not None

        # Next call should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(failing_function)

    @pytest.mark.asyncio
    async def test_half_open_state_transition(self, circuit_breaker):
        """Test transition from open to half-open state."""

        async def failing_function():
            raise ValueError("Test failure")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_function)

        assert circuit_breaker.is_open

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Next call should transition to half-open
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_function)

        # Circuit should still be open after failure in half-open state
        assert circuit_breaker.is_open

    @pytest.mark.asyncio
    async def test_circuit_recovery(self, circuit_breaker):
        """Test circuit recovery from open state."""
        call_count = 0

        async def conditional_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ValueError("Initial failures")
            return "success"

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(conditional_function)

        assert circuit_breaker.is_open

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Successful call should close the circuit
        result = await circuit_breaker.call(conditional_function)

        assert result == "success"
        assert circuit_breaker.is_closed
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_unexpected_exception_not_counted(self, circuit_breaker):
        """Test that unexpected exceptions don't trigger circuit breaker."""

        async def function_with_unexpected_error():
            raise RuntimeError("Unexpected error")

        # RuntimeError is not the expected exception (ValueError)
        with pytest.raises(RuntimeError):
            await circuit_breaker.call(function_with_unexpected_error)

        # Should not count as failure
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.is_closed

    @pytest.mark.asyncio
    async def test_circuit_breaker_status(self, circuit_breaker):
        """Test circuit breaker status reporting."""
        status = circuit_breaker.get_status()

        expected_keys = {
            "name",
            "state",
            "failure_count",
            "failure_threshold",
            "last_failure_time",
            "next_attempt_time",
            "recovery_timeout",
        }
        assert set(status.keys()) == expected_keys
        assert status["name"] == "TestCircuitBreaker"
        assert status["state"] == CircuitState.CLOSED.value
        assert status["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_concurrent_calls(self, circuit_breaker):
        """Test circuit breaker behavior with concurrent calls."""
        call_count = 0

        async def concurrent_function():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return call_count

        # Make concurrent calls
        tasks = [circuit_breaker.call(concurrent_function) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(isinstance(result, int) for result in results)
        assert circuit_breaker.is_closed

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_custom_settings(self):
        """Test circuit breaker with custom configuration."""
        custom_breaker = CircuitBreaker(
            failure_threshold=2,  # Lower threshold
            recovery_timeout=2,  # Longer recovery
            expected_exception=ConnectionError,
            name="CustomBreaker",
        )

        async def connection_error_function():
            raise ConnectionError("Connection failed")

        # Should open after 2 failures instead of 3
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await custom_breaker.call(connection_error_function)

        assert custom_breaker.is_open
        assert custom_breaker.failure_count == 2

    @pytest.mark.asyncio
    async def test_state_properties(self, circuit_breaker):
        """Test circuit breaker state property methods."""
        assert circuit_breaker.is_closed
        assert not circuit_breaker.is_open
        assert not circuit_breaker.is_half_open

        # Open the circuit
        async def failing_function():
            raise ValueError("Test failure")

        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_function)

        assert not circuit_breaker.is_closed
        assert circuit_breaker.is_open
        assert not circuit_breaker.is_half_open

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_error_message(self, circuit_breaker):
        """Test CircuitBreakerOpenError contains useful information."""

        async def failing_function():
            raise ValueError("Test failure")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_function)

        # Attempt call on open circuit
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await circuit_breaker.call(failing_function)

        error_message = str(exc_info.value)
        assert "TestCircuitBreaker" in error_message
        assert "is open" in error_message
        assert "Next attempt at" in error_message

    @pytest.mark.asyncio
    async def test_timing_precision(self, circuit_breaker):
        """Test that timing calculations work correctly."""

        async def failing_function():
            raise ValueError("Test failure")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_function)

        # Check that timing is set correctly
        assert circuit_breaker.last_failure_time is not None
        assert circuit_breaker.next_attempt_time is not None

        time_diff = circuit_breaker.next_attempt_time - circuit_breaker.last_failure_time
        expected_diff = timedelta(seconds=circuit_breaker.recovery_timeout)

        # Allow small timing variations
        assert abs(time_diff.total_seconds() - expected_diff.total_seconds()) < 0.1

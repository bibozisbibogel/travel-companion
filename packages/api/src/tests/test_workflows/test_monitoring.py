"""Comprehensive tests for workflow monitoring and logging functionality."""

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.asyncio import Redis

from travel_companion.workflows.monitoring import (
    CorrelationContext,
    HealthStatus,
    StructuredWorkflowLogger,
    WorkflowDebugLogger,
    WorkflowHealthMonitor,
    WorkflowMetrics,
    WorkflowPerformanceMonitor,
)


class TestCorrelationContext:
    """Tests for correlation context functionality."""

    def test_create_correlation_context(self):
        """Test creating a correlation context."""
        context = CorrelationContext(
            workflow_id="test-workflow",
            user_id="user-123",
            session_id="session-456",
        )

        assert context.workflow_id == "test-workflow"
        assert context.user_id == "user-123"
        assert context.session_id == "session-456"
        assert context.correlation_id is not None
        assert context.request_id is not None
        assert context.span_id is not None

    def test_correlation_context_to_dict(self):
        """Test converting correlation context to dictionary."""
        context = CorrelationContext(
            workflow_id="test-workflow",
            trace_flags={"debug": True},
        )

        context_dict = context.to_dict()

        assert "correlation_id" in context_dict
        assert "request_id" in context_dict
        assert "workflow_id" in context_dict
        assert "span_id" in context_dict
        assert context_dict["workflow_id"] == "test-workflow"
        assert context_dict["trace_flags"] == {"debug": True}

    def test_child_span_creation(self):
        """Test creating a child span from correlation context."""
        parent_context = CorrelationContext(
            workflow_id="test-workflow",
            user_id="user-123",
        )

        child_context = parent_context.child_span()

        # Child should inherit parent properties
        assert child_context.correlation_id == parent_context.correlation_id
        assert child_context.request_id == parent_context.request_id
        assert child_context.workflow_id == parent_context.workflow_id
        assert child_context.user_id == parent_context.user_id

        # Child should have parent's span as parent_span_id
        assert child_context.parent_span_id == parent_context.span_id

        # Child should have its own span_id
        assert child_context.span_id != parent_context.span_id


class TestWorkflowMetrics:
    """Tests for workflow metrics functionality."""

    def test_create_workflow_metrics(self):
        """Test creating workflow metrics."""
        metrics = WorkflowMetrics(
            workflow_id="test-workflow",
            workflow_type="trip_planning",
            started_at=datetime.now(UTC),
        )

        assert metrics.workflow_id == "test-workflow"
        assert metrics.workflow_type == "trip_planning"
        assert metrics.started_at is not None
        assert metrics.completed_at is None
        assert metrics.total_agents == 0
        assert metrics.successful_agents == 0
        assert metrics.failed_agents == 0

    def test_calculate_success_rate(self):
        """Test calculating success rate."""
        metrics = WorkflowMetrics(
            workflow_id="test-workflow",
            workflow_type="trip_planning",
            started_at=datetime.now(UTC),
        )

        # Test with no agents
        assert metrics.calculate_success_rate() == 0.0

        # Test with successful agents
        metrics.total_agents = 10
        metrics.successful_agents = 8
        assert metrics.calculate_success_rate() == 80.0

        # Test with all successful
        metrics.successful_agents = 10
        assert metrics.calculate_success_rate() == 100.0

    def test_calculate_error_rate(self):
        """Test calculating error rate."""
        metrics = WorkflowMetrics(
            workflow_id="test-workflow",
            workflow_type="trip_planning",
            started_at=datetime.now(UTC),
        )

        # Test with no agents
        assert metrics.calculate_error_rate() == 0.0

        # Test with failed agents
        metrics.total_agents = 10
        metrics.failed_agents = 3
        assert metrics.calculate_error_rate() == 30.0

    def test_calculate_cache_hit_rate(self):
        """Test calculating cache hit rate."""
        metrics = WorkflowMetrics(
            workflow_id="test-workflow",
            workflow_type="trip_planning",
            started_at=datetime.now(UTC),
        )

        # Test with no API calls
        assert metrics.calculate_cache_hit_rate() == 0.0

        # Test with cached calls
        metrics.total_api_calls = 100
        metrics.cached_api_calls = 75
        assert metrics.calculate_cache_hit_rate() == 75.0

    def test_calculate_parallel_efficiency(self):
        """Test calculating parallel efficiency."""
        metrics = WorkflowMetrics(
            workflow_id="test-workflow",
            workflow_type="trip_planning",
            started_at=datetime.now(UTC),
        )

        # Test with no execution times
        assert metrics.calculate_parallel_efficiency() == 0.0

        # Test with execution times
        metrics.agent_execution_times = {
            "flight": 1000,
            "hotel": 1500,
            "activity": 800,
        }
        metrics.parallel_execution_time_ms = 1500  # Max of individual times

        # Efficiency = (1000 + 1500 + 800) / 1500 * 100 = 220%
        assert abs(metrics.calculate_parallel_efficiency() - 220.0) < 0.01

    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = WorkflowMetrics(
            workflow_id="test-workflow",
            workflow_type="trip_planning",
            started_at=datetime.now(UTC),
        )

        metrics.total_agents = 5
        metrics.successful_agents = 4
        metrics.failed_agents = 1
        metrics.total_api_calls = 10
        metrics.cached_api_calls = 3

        metrics_dict = metrics.to_dict()

        assert metrics_dict["workflow_id"] == "test-workflow"
        assert metrics_dict["workflow_type"] == "trip_planning"
        assert metrics_dict["total_agents"] == 5
        assert metrics_dict["successful_agents"] == 4
        assert metrics_dict["failed_agents"] == 1
        assert metrics_dict["success_rate"] == 80.0
        assert metrics_dict["error_rate"] == 20.0
        assert metrics_dict["cache_hit_rate"] == 30.0


class TestStructuredWorkflowLogger:
    """Tests for structured workflow logger."""

    def test_create_structured_logger(self):
        """Test creating structured logger."""
        logger = StructuredWorkflowLogger()

        assert logger.base_logger is not None
        assert logger.structured_logger is not None
        assert logger.correlation_contexts == {}

    def test_create_and_get_correlation_context(self):
        """Test creating and retrieving correlation context."""
        logger = StructuredWorkflowLogger()

        context = logger.create_correlation_context(
            workflow_id="test-workflow",
            user_id="user-123",
        )

        assert context.workflow_id == "test-workflow"
        assert context.user_id == "user-123"

        # Should be stored in logger
        retrieved_context = logger.get_correlation_context("test-workflow")
        assert retrieved_context == context

    @patch("travel_companion.workflows.monitoring.structlog.get_logger")
    def test_log_with_correlation(self, mock_get_logger):
        """Test logging with correlation context."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        logger = StructuredWorkflowLogger()
        context = CorrelationContext(workflow_id="test-workflow")

        logger.log_with_correlation(
            "info",
            "Test message",
            context,
            extra_field="extra_value",
        )

        # Verify log method was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "Test message"
        assert "correlation_id" in call_args[1]
        assert "extra_field" in call_args[1]
        assert call_args[1]["extra_field"] == "extra_value"

    @patch("travel_companion.workflows.monitoring.structlog.get_logger")
    def test_log_state_transition(self, mock_get_logger):
        """Test logging state transitions."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        logger = StructuredWorkflowLogger()
        context = CorrelationContext(workflow_id="test-workflow")

        logger.log_state_transition(
            "test-workflow",
            "initializing",
            "running",
            "user_request_received",
            context,
            {"user": "test-user"},
        )

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert "State transition" in call_args[0][0]
        assert call_args[1]["from_state"] == "initializing"
        assert call_args[1]["to_state"] == "running"
        assert call_args[1]["transition_reason"] == "user_request_received"


class TestWorkflowPerformanceMonitor:
    """Tests for workflow performance monitoring."""

    @pytest.mark.asyncio
    async def test_start_workflow_monitoring(self):
        """Test starting workflow monitoring."""
        mock_redis = AsyncMock(spec=Redis)
        mock_redis_manager = MagicMock()
        mock_redis_manager.get_client = AsyncMock(return_value=mock_redis)

        monitor = WorkflowPerformanceMonitor(mock_redis_manager)
        context = CorrelationContext(workflow_id="test-workflow")

        metrics = await monitor.start_workflow_monitoring(
            "test-workflow",
            "trip_planning",
            context,
        )

        assert metrics.workflow_id == "test-workflow"
        assert metrics.workflow_type == "trip_planning"
        assert metrics.started_at is not None
        assert "test-workflow" in monitor.metrics

        # Verify Redis persistence
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_agent_execution(self):
        """Test recording agent execution metrics."""
        mock_redis = AsyncMock(spec=Redis)
        mock_redis_manager = MagicMock()
        mock_redis_manager.get_client = AsyncMock(return_value=mock_redis)

        monitor = WorkflowPerformanceMonitor(mock_redis_manager)
        context = CorrelationContext(workflow_id="test-workflow")

        # Start monitoring first
        await monitor.start_workflow_monitoring(
            "test-workflow",
            "trip_planning",
            context,
        )

        # Record successful agent execution
        await monitor.record_agent_execution(
            "test-workflow",
            "flight_agent",
            1500.0,
            True,
            context,
        )

        metrics = monitor.metrics["test-workflow"]
        assert metrics.total_agents == 1
        assert metrics.successful_agents == 1
        assert metrics.failed_agents == 0
        assert metrics.agent_execution_times["flight_agent"] == 1500.0

        # Record failed agent execution
        await monitor.record_agent_execution(
            "test-workflow",
            "hotel_agent",
            2000.0,
            False,
            context,
        )

        assert metrics.total_agents == 2
        assert metrics.successful_agents == 1
        assert metrics.failed_agents == 1
        assert metrics.agent_execution_times["hotel_agent"] == 2000.0

    @pytest.mark.asyncio
    async def test_record_api_call(self):
        """Test recording API call metrics."""
        mock_redis = AsyncMock(spec=Redis)
        mock_redis_manager = MagicMock()
        mock_redis_manager.get_client = AsyncMock(return_value=mock_redis)

        monitor = WorkflowPerformanceMonitor(mock_redis_manager)
        context = CorrelationContext(workflow_id="test-workflow")

        # Start monitoring
        await monitor.start_workflow_monitoring(
            "test-workflow",
            "trip_planning",
            context,
        )

        # Record API calls
        await monitor.record_api_call("test-workflow", "aviationstack", 500.0, cached=False)
        await monitor.record_api_call("test-workflow", "aviationstack", 10.0, cached=True)

        metrics = monitor.metrics["test-workflow"]
        assert metrics.total_api_calls == 2
        assert metrics.cached_api_calls == 1
        assert len(metrics.api_call_times["aviationstack"]) == 2
        assert metrics.api_call_times["aviationstack"][0] == 500.0
        assert metrics.api_call_times["aviationstack"][1] == 10.0

    @pytest.mark.asyncio
    async def test_complete_workflow_monitoring(self):
        """Test completing workflow monitoring."""
        mock_redis = AsyncMock(spec=Redis)
        mock_redis_manager = MagicMock()
        mock_redis_manager.get_client = AsyncMock(return_value=mock_redis)

        monitor = WorkflowPerformanceMonitor(mock_redis_manager)
        context = CorrelationContext(workflow_id="test-workflow")

        # Start and record some metrics
        await monitor.start_workflow_monitoring(
            "test-workflow",
            "trip_planning",
            context,
        )

        await monitor.record_agent_execution(
            "test-workflow",
            "flight_agent",
            1000.0,
            True,
            context,
        )

        # Complete monitoring
        completed_metrics = await monitor.complete_workflow_monitoring(
            "test-workflow",
            context,
        )

        assert completed_metrics.completed_at is not None
        assert completed_metrics.total_execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_get_aggregate_metrics(self):
        """Test getting aggregated metrics."""
        mock_redis = AsyncMock(spec=Redis)
        mock_redis_manager = MagicMock()
        mock_redis_manager.get_client = AsyncMock(return_value=mock_redis)

        # Mock Redis scan_iter to return metric keys
        async def mock_scan_iter(pattern):
            for key in ["workflow:metrics:test1", "workflow:metrics:test2"]:
                yield key

        mock_redis.scan_iter = mock_scan_iter

        # Mock Redis get to return metric data
        metrics_data = {
            "workflow_id": "test",
            "workflow_type": "trip_planning",
            "started_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
            "total_execution_time_ms": 5000,
            "total_agents": 5,
            "successful_agents": 4,
            "failed_agents": 1,
            "total_api_calls": 10,
            "cached_api_calls": 3,
            "total_retries": 2,
            "total_timeouts": 1,
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(metrics_data))

        monitor = WorkflowPerformanceMonitor(mock_redis_manager)

        aggregates = await monitor.get_aggregate_metrics(
            workflow_type="trip_planning",
            time_window_hours=24,
        )

        assert "total_workflows" in aggregates
        assert "avg_execution_time_ms" in aggregates
        assert "avg_success_rate" in aggregates


class TestWorkflowHealthMonitor:
    """Tests for workflow health monitoring."""

    @pytest.mark.asyncio
    async def test_check_redis_health(self):
        """Test checking Redis health."""
        mock_redis = AsyncMock(spec=Redis)
        mock_redis.ping = AsyncMock()
        mock_redis.info = AsyncMock(
            return_value={
                "used_memory": 1000000,
                "maxmemory": 2000000,
            }
        )

        mock_redis_manager = MagicMock()
        mock_redis_manager.get_client = AsyncMock(return_value=mock_redis)

        monitor = WorkflowHealthMonitor(mock_redis_manager)

        redis_health = await monitor._check_redis_health()

        assert redis_health["status"] == HealthStatus.HEALTHY
        assert "ping_time_ms" in redis_health
        assert redis_health["memory_usage_percentage"] == 50.0

    @pytest.mark.asyncio
    async def test_check_redis_health_degraded(self):
        """Test Redis health check with degraded status."""
        mock_redis = AsyncMock(spec=Redis)

        # Simulate slow ping
        async def slow_ping():
            await asyncio.sleep(0.15)
            return True

        mock_redis.ping = slow_ping
        mock_redis.info = AsyncMock(
            return_value={
                "used_memory": 1000000,
                "maxmemory": 2000000,
            }
        )

        mock_redis_manager = MagicMock()
        mock_redis_manager.get_client = AsyncMock(return_value=mock_redis)

        monitor = WorkflowHealthMonitor(mock_redis_manager)

        redis_health = await monitor._check_redis_health()

        assert redis_health["status"] == HealthStatus.DEGRADED
        assert "High Redis latency" in redis_health["message"]

    @pytest.mark.asyncio
    async def test_check_system_health(self):
        """Test comprehensive system health check."""
        mock_redis = AsyncMock(spec=Redis)
        mock_redis.ping = AsyncMock()
        mock_redis.info = AsyncMock(
            return_value={
                "used_memory": 1000000,
                "maxmemory": 2000000,
            }
        )

        # Mock scan_iter for metrics check
        async def mock_scan_iter(pattern):
            return
            yield  # Empty generator

        mock_redis.scan_iter = mock_scan_iter

        mock_redis_manager = MagicMock()
        mock_redis_manager.get_client = AsyncMock(return_value=mock_redis)

        monitor = WorkflowHealthMonitor(mock_redis_manager)

        system_health = await monitor.check_system_health()

        assert "status" in system_health
        assert "timestamp" in system_health
        assert "checks" in system_health
        assert "redis" in system_health["checks"]
        assert "metrics" in system_health["checks"]
        assert "agents" in system_health["checks"]
        assert "overall_health_score" in system_health

    @pytest.mark.asyncio
    async def test_check_workflow_health(self):
        """Test checking specific workflow health."""
        mock_redis = AsyncMock(spec=Redis)
        mock_redis_manager = MagicMock()
        mock_redis_manager.get_client = AsyncMock(return_value=mock_redis)

        # Create a mock performance monitor
        monitor = WorkflowHealthMonitor(mock_redis_manager)

        # Mock get_workflow_metrics
        mock_metrics = WorkflowMetrics(
            workflow_id="test-workflow",
            workflow_type="trip_planning",
            started_at=datetime.now(UTC),
        )
        mock_metrics.total_agents = 5
        mock_metrics.successful_agents = 4
        mock_metrics.failed_agents = 1
        mock_metrics.total_execution_time_ms = 5000

        monitor.performance_monitor.get_workflow_metrics = AsyncMock(return_value=mock_metrics)

        workflow_health = await monitor.check_workflow_health("test-workflow")

        assert workflow_health["status"] == HealthStatus.HEALTHY.value
        assert workflow_health["workflow_id"] == "test-workflow"
        assert workflow_health["success_rate"] == 80.0
        assert workflow_health["error_rate"] == 20.0


class TestWorkflowDebugLogger:
    """Tests for workflow debug logging."""

    def test_debug_logger_disabled(self):
        """Test debug logger when disabled."""
        logger = WorkflowDebugLogger(enable_debug=False)
        context = CorrelationContext(workflow_id="test-workflow")

        # Should not log when disabled
        logger.log_state_transition_debug(
            "test-workflow",
            "init",
            "running",
            {"test": "data"},
            context,
        )

        # No state history should be recorded
        assert len(logger.state_history) == 0

    def test_debug_logger_enabled(self):
        """Test debug logger when enabled."""
        logger = WorkflowDebugLogger(enable_debug=True)
        context = CorrelationContext(workflow_id="test-workflow")

        # Log state transition
        logger.log_state_transition_debug(
            "test-workflow",
            "init",
            "running",
            {"test": "data"},
            context,
        )

        # State history should be recorded
        assert "test-workflow" in logger.state_history
        assert len(logger.state_history["test-workflow"]) == 1

        transition = logger.state_history["test-workflow"][0]
        assert transition["from_state"] == "init"
        assert transition["to_state"] == "running"
        assert transition["data"] == {"test": "data"}
        assert transition["correlation_id"] == context.correlation_id

    def test_log_performance_bottleneck(self):
        """Test logging performance bottlenecks."""
        logger = WorkflowDebugLogger(enable_debug=True)
        context = CorrelationContext(workflow_id="test-workflow")

        with patch.object(logger.logger, "log_with_correlation") as mock_log:
            # Should log when exceeding threshold
            logger.log_performance_bottleneck(
                "test-workflow",
                "flight_agent",
                5000.0,
                3000.0,
                context,
            )

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == "warning"
            assert "bottleneck" in call_args[0][1].lower()
            assert call_args[0][2] == context

    def test_export_debug_report(self):
        """Test exporting debug report."""
        logger = WorkflowDebugLogger(enable_debug=True)
        context = CorrelationContext(workflow_id="test-workflow")

        # Log some state transitions
        logger.log_state_transition_debug(
            "test-workflow",
            "init",
            "running",
            {"step": 1},
            context,
        )

        logger.log_state_transition_debug(
            "test-workflow",
            "running",
            "completed",
            {"step": 2},
            context,
        )

        # Export report
        report = logger.export_debug_report("test-workflow")

        assert report["workflow_id"] == "test-workflow"
        assert len(report["state_history"]) == 2
        assert report["debug_enabled"] is True
        assert "generated_at" in report


class TestMonitoringIntegration:
    """Integration tests for monitoring components."""

    @pytest.mark.asyncio
    async def test_full_workflow_monitoring_flow(self):
        """Test complete workflow monitoring flow."""
        mock_redis = AsyncMock(spec=Redis)
        mock_redis_manager = MagicMock()
        mock_redis_manager.get_client = AsyncMock(return_value=mock_redis)

        # Initialize components
        structured_logger = StructuredWorkflowLogger()
        performance_monitor = WorkflowPerformanceMonitor(mock_redis_manager)
        debug_logger = WorkflowDebugLogger(enable_debug=True)

        # Create correlation context
        context = structured_logger.create_correlation_context(
            workflow_id="integration-test",
            user_id="user-123",
        )

        # Start workflow monitoring
        await performance_monitor.start_workflow_monitoring(
            "integration-test",
            "trip_planning",
            context,
        )

        # Log state transition
        debug_logger.log_state_transition_debug(
            "integration-test",
            "initializing",
            "processing_agents",
            {"agents": ["flight", "hotel"]},
            context,
        )

        # Record agent executions
        await performance_monitor.record_agent_execution(
            "integration-test",
            "flight_agent",
            1500.0,
            True,
            context,
        )

        await performance_monitor.record_agent_execution(
            "integration-test",
            "hotel_agent",
            2000.0,
            True,
            context,
        )

        # Record API calls
        await performance_monitor.record_api_call(
            "integration-test",
            "aviationstack",
            500.0,
            cached=False,
        )

        # Complete workflow
        final_metrics = await performance_monitor.complete_workflow_monitoring(
            "integration-test",
            context,
        )

        # Verify final metrics
        assert final_metrics.workflow_id == "integration-test"
        assert final_metrics.total_agents == 2
        assert final_metrics.successful_agents == 2
        assert final_metrics.failed_agents == 0
        assert final_metrics.total_api_calls == 1
        assert final_metrics.completed_at is not None

        # Verify debug report
        debug_report = debug_logger.export_debug_report("integration-test")
        assert len(debug_report["state_history"]) == 1
        assert debug_report["state_history"][0]["from_state"] == "initializing"

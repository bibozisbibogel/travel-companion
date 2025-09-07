"""Comprehensive monitoring and logging integration for workflow orchestration.

This module provides structured logging with correlation IDs, performance metrics,
health checks, and debug logging for workflow state transitions.
"""

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

import structlog

from ..core.redis import RedisManager
from ..utils.errors import WorkflowError
from ..utils.logging import WorkflowEvent, WorkflowLogger


class MetricType(str, Enum):
    """Types of workflow metrics."""

    EXECUTION_TIME = "execution_time"
    SUCCESS_RATE = "success_rate"
    ERROR_RATE = "error_rate"
    AGENT_PERFORMANCE = "agent_performance"
    PARALLEL_EFFICIENCY = "parallel_efficiency"
    CACHE_HIT_RATE = "cache_hit_rate"
    API_CALL_COUNT = "api_call_count"
    RETRY_COUNT = "retry_count"
    TIMEOUT_COUNT = "timeout_count"
    PARTIAL_SUCCESS_RATE = "partial_success_rate"


class HealthStatus(str, Enum):
    """Health check status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class CorrelationContext:
    """Correlation context for distributed tracing."""

    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    request_id: str = field(default_factory=lambda: str(uuid4()))
    workflow_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    parent_span_id: str | None = None
    span_id: str = field(default_factory=lambda: str(uuid4()))
    trace_flags: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for logging."""
        return {
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "workflow_id": self.workflow_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "parent_span_id": self.parent_span_id,
            "span_id": self.span_id,
            "trace_flags": self.trace_flags,
        }

    def child_span(self) -> "CorrelationContext":
        """Create a child span context."""
        return CorrelationContext(
            correlation_id=self.correlation_id,
            request_id=self.request_id,
            workflow_id=self.workflow_id,
            user_id=self.user_id,
            session_id=self.session_id,
            parent_span_id=self.span_id,
            trace_flags=self.trace_flags.copy(),
        )


@dataclass
class WorkflowMetrics:
    """Container for workflow execution metrics."""

    workflow_id: str
    workflow_type: str
    started_at: datetime
    completed_at: datetime | None = None
    total_execution_time_ms: float = 0.0

    # Agent metrics
    total_agents: int = 0
    successful_agents: int = 0
    failed_agents: int = 0
    agent_execution_times: dict[str, float] = field(default_factory=dict)

    # Performance metrics
    parallel_execution_time_ms: float = 0.0
    sequential_execution_time_ms: float = 0.0
    parallel_efficiency: float = 0.0

    # API metrics
    total_api_calls: int = 0
    cached_api_calls: int = 0
    api_call_times: dict[str, list[float]] = field(default_factory=dict)

    # Error metrics
    total_retries: int = 0
    total_timeouts: int = 0
    error_codes: list[str] = field(default_factory=list)

    # State transition metrics
    state_transitions: list[dict[str, Any]] = field(default_factory=list)
    checkpoint_count: int = 0

    def calculate_success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_agents == 0:
            return 0.0
        return (self.successful_agents / self.total_agents) * 100

    def calculate_error_rate(self) -> float:
        """Calculate overall error rate."""
        if self.total_agents == 0:
            return 0.0
        return (self.failed_agents / self.total_agents) * 100

    def calculate_cache_hit_rate(self) -> float:
        """Calculate API cache hit rate."""
        if self.total_api_calls == 0:
            return 0.0
        return (self.cached_api_calls / self.total_api_calls) * 100

    def calculate_parallel_efficiency(self) -> float:
        """Calculate parallel execution efficiency."""
        if self.parallel_execution_time_ms == 0:
            return 0.0

        theoretical_sequential = sum(self.agent_execution_times.values())
        if theoretical_sequential == 0:
            return 0.0

        return (theoretical_sequential / self.parallel_execution_time_ms) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for reporting."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_execution_time_ms": self.total_execution_time_ms,
            "total_agents": self.total_agents,
            "successful_agents": self.successful_agents,
            "failed_agents": self.failed_agents,
            "success_rate": self.calculate_success_rate(),
            "error_rate": self.calculate_error_rate(),
            "cache_hit_rate": self.calculate_cache_hit_rate(),
            "parallel_efficiency": self.calculate_parallel_efficiency(),
            "total_api_calls": self.total_api_calls,
            "cached_api_calls": self.cached_api_calls,
            "total_retries": self.total_retries,
            "total_timeouts": self.total_timeouts,
            "error_codes": self.error_codes,
            "checkpoint_count": self.checkpoint_count,
            "agent_execution_times": self.agent_execution_times,
            "state_transition_count": len(self.state_transitions),
        }


class StructuredWorkflowLogger:
    """Enhanced workflow logger with structured logging and correlation IDs."""

    def __init__(self, logger_name: str = "travel_companion.workflow.monitoring"):
        """Initialize structured logger."""
        self.base_logger = WorkflowLogger()
        self.structured_logger = structlog.get_logger(logger_name)
        self.correlation_contexts: dict[str, CorrelationContext] = {}

    def create_correlation_context(
        self,
        workflow_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> CorrelationContext:
        """Create a new correlation context."""
        context = CorrelationContext(
            workflow_id=workflow_id,
            user_id=user_id,
            session_id=session_id,
        )

        if workflow_id:
            self.correlation_contexts[workflow_id] = context

        return context

    def get_correlation_context(self, workflow_id: str) -> CorrelationContext | None:
        """Get correlation context for a workflow."""
        return self.correlation_contexts.get(workflow_id)

    def log_with_correlation(
        self,
        level: str,
        message: str,
        correlation_context: CorrelationContext,
        **extra_fields: Any,
    ) -> None:
        """Log with correlation context."""
        log_data = {
            **correlation_context.to_dict(),
            **extra_fields,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        log_method = getattr(self.structured_logger, level)
        log_method(message, **log_data)

    def log_workflow_started_with_correlation(
        self,
        workflow_id: str,
        workflow_type: str,
        correlation_context: CorrelationContext,
        input_data: dict[str, Any] | None = None,
    ) -> None:
        """Log workflow start with correlation."""
        self.log_with_correlation(
            "info",
            f"Workflow {workflow_type} started",
            correlation_context,
            event_type=WorkflowEvent.WORKFLOW_STARTED,
            workflow_type=workflow_type,
            input_summary=self._summarize_input(input_data),
        )

    def log_state_transition(
        self,
        workflow_id: str,
        from_state: str,
        to_state: str,
        transition_reason: str,
        correlation_context: CorrelationContext,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log detailed state transition."""
        self.log_with_correlation(
            "debug",
            f"State transition: {from_state} -> {to_state}",
            correlation_context,
            event_type="state_transition",
            from_state=from_state,
            to_state=to_state,
            transition_reason=transition_reason,
            metadata=metadata or {},
        )

    def log_agent_execution_with_correlation(
        self,
        workflow_id: str,
        agent_name: str,
        phase: str,
        correlation_context: CorrelationContext,
        **extra_fields: Any,
    ) -> None:
        """Log agent execution with correlation."""
        child_context = correlation_context.child_span()
        self.log_with_correlation(
            "debug",
            f"Agent {agent_name} executing in phase {phase}",
            child_context,
            event_type=WorkflowEvent.AGENT_EXECUTION_STARTED,
            agent_name=agent_name,
            phase=phase,
            **extra_fields,
        )

    def log_performance_metrics(
        self,
        workflow_id: str,
        metrics: WorkflowMetrics,
        correlation_context: CorrelationContext,
    ) -> None:
        """Log workflow performance metrics."""
        self.log_with_correlation(
            "info",
            "Workflow performance metrics",
            correlation_context,
            event_type="performance_metrics",
            metrics=metrics.to_dict(),
        )

    def log_debug_state_snapshot(
        self,
        workflow_id: str,
        state_snapshot: dict[str, Any],
        correlation_context: CorrelationContext,
        description: str = "State snapshot",
    ) -> None:
        """Log debug state snapshot for troubleshooting."""
        self.log_with_correlation(
            "debug",
            description,
            correlation_context,
            event_type="state_snapshot",
            state_keys=list(state_snapshot.keys()),
            state_summary=self._summarize_state(state_snapshot),
        )

    def _summarize_input(self, input_data: dict[str, Any] | None) -> dict[str, Any]:
        """Summarize input data for logging."""
        if not input_data:
            return {}

        return {
            "keys": list(input_data.keys()),
            "size": len(str(input_data)),
            "has_user_request": "user_request" in input_data,
            "has_trip_params": "trip_params" in input_data,
        }

    def _summarize_state(self, state: dict[str, Any]) -> dict[str, Any]:
        """Summarize state for logging."""
        summary = {
            "total_keys": len(state),
            "has_errors": "errors" in state,
            "has_results": any(k.endswith("_results") for k in state.keys()),
            "agent_states": {},
        }

        # Summarize agent-specific states
        for key, value in state.items():
            if "_results" in key:
                agent_name = key.replace("_results", "")
                summary["agent_states"][agent_name] = {
                    "has_data": bool(value),
                    "data_size": len(str(value)) if value else 0,
                }

        return summary


class WorkflowPerformanceMonitor:
    """Monitor and track workflow performance metrics."""

    def __init__(self, redis_manager: RedisManager | None = None):
        """Initialize performance monitor."""
        self.redis_manager = redis_manager or RedisManager()
        self.logger = StructuredWorkflowLogger()
        self.metrics: dict[str, WorkflowMetrics] = {}
        self.metric_ttl = 86400  # 24 hours

    async def start_workflow_monitoring(
        self,
        workflow_id: str,
        workflow_type: str,
        correlation_context: CorrelationContext,
    ) -> WorkflowMetrics:
        """Start monitoring a workflow execution."""
        metrics = WorkflowMetrics(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            started_at=datetime.now(UTC),
        )

        self.metrics[workflow_id] = metrics

        # Store in Redis for persistence
        await self._persist_metrics(workflow_id, metrics)

        self.logger.log_with_correlation(
            "info",
            "Started workflow monitoring",
            correlation_context,
            event_type="monitoring_started",
            workflow_id=workflow_id,
            workflow_type=workflow_type,
        )

        return metrics

    async def record_agent_execution(
        self,
        workflow_id: str,
        agent_name: str,
        execution_time_ms: float,
        success: bool,
        correlation_context: CorrelationContext | None = None,
    ) -> None:
        """Record agent execution metrics."""
        metrics = self.metrics.get(workflow_id)
        if not metrics:
            return

        metrics.total_agents += 1
        metrics.agent_execution_times[agent_name] = execution_time_ms

        if success:
            metrics.successful_agents += 1
        else:
            metrics.failed_agents += 1

        await self._persist_metrics(workflow_id, metrics)

        if correlation_context:
            self.logger.log_with_correlation(
                "debug",
                f"Recorded agent execution: {agent_name}",
                correlation_context,
                event_type="agent_metric_recorded",
                agent_name=agent_name,
                execution_time_ms=execution_time_ms,
                success=success,
            )

    async def record_api_call(
        self,
        workflow_id: str,
        api_name: str,
        execution_time_ms: float,
        cached: bool = False,
    ) -> None:
        """Record API call metrics."""
        metrics = self.metrics.get(workflow_id)
        if not metrics:
            return

        metrics.total_api_calls += 1
        if cached:
            metrics.cached_api_calls += 1

        if api_name not in metrics.api_call_times:
            metrics.api_call_times[api_name] = []
        metrics.api_call_times[api_name].append(execution_time_ms)

        await self._persist_metrics(workflow_id, metrics)

    async def record_retry(self, workflow_id: str, agent_name: str) -> None:
        """Record retry attempt."""
        metrics = self.metrics.get(workflow_id)
        if not metrics:
            return

        metrics.total_retries += 1
        await self._persist_metrics(workflow_id, metrics)

    async def record_timeout(self, workflow_id: str, agent_name: str) -> None:
        """Record timeout occurrence."""
        metrics = self.metrics.get(workflow_id)
        if not metrics:
            return

        metrics.total_timeouts += 1
        await self._persist_metrics(workflow_id, metrics)

    async def record_error(self, workflow_id: str, error_code: str) -> None:
        """Record error occurrence."""
        metrics = self.metrics.get(workflow_id)
        if not metrics:
            return

        metrics.error_codes.append(error_code)
        await self._persist_metrics(workflow_id, metrics)

    async def record_state_transition(
        self,
        workflow_id: str,
        from_state: str,
        to_state: str,
        transition_time_ms: float,
    ) -> None:
        """Record state transition."""
        metrics = self.metrics.get(workflow_id)
        if not metrics:
            return

        metrics.state_transitions.append(
            {
                "from": from_state,
                "to": to_state,
                "time_ms": transition_time_ms,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        await self._persist_metrics(workflow_id, metrics)

    async def record_checkpoint(self, workflow_id: str) -> None:
        """Record checkpoint creation."""
        metrics = self.metrics.get(workflow_id)
        if not metrics:
            return

        metrics.checkpoint_count += 1
        await self._persist_metrics(workflow_id, metrics)

    async def complete_workflow_monitoring(
        self,
        workflow_id: str,
        correlation_context: CorrelationContext,
    ) -> WorkflowMetrics:
        """Complete workflow monitoring and calculate final metrics."""
        metrics = self.metrics.get(workflow_id)
        if not metrics:
            raise WorkflowError(f"No metrics found for workflow {workflow_id}")

        metrics.completed_at = datetime.now(UTC)
        metrics.total_execution_time_ms = (
            metrics.completed_at - metrics.started_at
        ).total_seconds() * 1000

        # Calculate parallel efficiency
        if metrics.agent_execution_times:
            metrics.parallel_efficiency = metrics.calculate_parallel_efficiency()

        # Persist final metrics
        await self._persist_metrics(workflow_id, metrics)

        # Log performance summary
        self.logger.log_performance_metrics(workflow_id, metrics, correlation_context)

        return metrics

    async def get_workflow_metrics(self, workflow_id: str) -> WorkflowMetrics | None:
        """Get metrics for a specific workflow."""
        # Try memory first
        if workflow_id in self.metrics:
            return self.metrics[workflow_id]

        # Try Redis
        redis_client = await self.redis_manager.get_client()
        metrics_data = await redis_client.get(f"workflow:metrics:{workflow_id}")

        if metrics_data:
            return self._deserialize_metrics(json.loads(metrics_data))

        return None

    async def get_aggregate_metrics(
        self,
        workflow_type: str | None = None,
        time_window_hours: int = 24,
    ) -> dict[str, Any]:
        """Get aggregated metrics across workflows."""
        redis_client = await self.redis_manager.get_client()

        # Get all workflow metrics keys
        pattern = "workflow:metrics:*"
        keys = []
        async for key in redis_client.scan_iter(pattern):
            keys.append(key)

        if not keys:
            return {}

        # Fetch all metrics
        metrics_list = []
        cutoff_time = datetime.now(UTC) - timedelta(hours=time_window_hours)

        for key in keys:
            metrics_data = await redis_client.get(key)
            if metrics_data:
                metrics = self._deserialize_metrics(json.loads(metrics_data))

                # Filter by time window
                if metrics.started_at >= cutoff_time:
                    # Filter by workflow type if specified
                    if not workflow_type or metrics.workflow_type == workflow_type:
                        metrics_list.append(metrics)

        if not metrics_list:
            return {}

        # Calculate aggregates
        return {
            "total_workflows": len(metrics_list),
            "avg_execution_time_ms": sum(m.total_execution_time_ms for m in metrics_list)
            / len(metrics_list),
            "avg_success_rate": sum(m.calculate_success_rate() for m in metrics_list)
            / len(metrics_list),
            "avg_error_rate": sum(m.calculate_error_rate() for m in metrics_list)
            / len(metrics_list),
            "avg_cache_hit_rate": sum(m.calculate_cache_hit_rate() for m in metrics_list)
            / len(metrics_list),
            "total_api_calls": sum(m.total_api_calls for m in metrics_list),
            "total_retries": sum(m.total_retries for m in metrics_list),
            "total_timeouts": sum(m.total_timeouts for m in metrics_list),
            "time_window_hours": time_window_hours,
            "workflow_type": workflow_type,
        }

    async def _persist_metrics(self, workflow_id: str, metrics: WorkflowMetrics) -> None:
        """Persist metrics to Redis."""
        try:
            redis_client = await self.redis_manager.get_client()
            await redis_client.setex(
                f"workflow:metrics:{workflow_id}",
                self.metric_ttl,
                json.dumps(metrics.to_dict()),
            )
        except Exception as e:
            self.logger.structured_logger.error(f"Failed to persist metrics: {e}")

    def _deserialize_metrics(self, data: dict[str, Any]) -> WorkflowMetrics:
        """Deserialize metrics from dictionary."""
        metrics = WorkflowMetrics(
            workflow_id=data["workflow_id"],
            workflow_type=data["workflow_type"],
            started_at=datetime.fromisoformat(data["started_at"]),
        )

        if data.get("completed_at"):
            metrics.completed_at = datetime.fromisoformat(data["completed_at"])

        metrics.total_execution_time_ms = data.get("total_execution_time_ms", 0)
        metrics.total_agents = data.get("total_agents", 0)
        metrics.successful_agents = data.get("successful_agents", 0)
        metrics.failed_agents = data.get("failed_agents", 0)
        metrics.agent_execution_times = data.get("agent_execution_times", {})
        metrics.total_api_calls = data.get("total_api_calls", 0)
        metrics.cached_api_calls = data.get("cached_api_calls", 0)
        metrics.total_retries = data.get("total_retries", 0)
        metrics.total_timeouts = data.get("total_timeouts", 0)
        metrics.error_codes = data.get("error_codes", [])
        metrics.checkpoint_count = data.get("checkpoint_count", 0)

        return metrics


class WorkflowHealthMonitor:
    """Monitor workflow system health and provide health check endpoints."""

    def __init__(self, redis_manager: RedisManager | None = None):
        """Initialize health monitor."""
        self.redis_manager = redis_manager or RedisManager()
        self.logger = StructuredWorkflowLogger()
        self.performance_monitor = WorkflowPerformanceMonitor(redis_manager)

    async def check_system_health(self) -> dict[str, Any]:
        """Perform comprehensive system health check."""
        health_status = HealthStatus.HEALTHY
        checks = {}

        # Check Redis connectivity
        redis_health = await self._check_redis_health()
        checks["redis"] = redis_health
        if redis_health["status"] != HealthStatus.HEALTHY:
            health_status = HealthStatus.DEGRADED

        # Check workflow metrics
        metrics_health = await self._check_metrics_health()
        checks["metrics"] = metrics_health
        if metrics_health["status"] == HealthStatus.UNHEALTHY:
            health_status = HealthStatus.UNHEALTHY
        elif (
            metrics_health["status"] == HealthStatus.DEGRADED
            and health_status == HealthStatus.HEALTHY
        ):
            health_status = HealthStatus.DEGRADED

        # Check agent health
        agent_health = await self._check_agent_health()
        checks["agents"] = agent_health
        if agent_health["status"] == HealthStatus.UNHEALTHY:
            health_status = HealthStatus.UNHEALTHY
        elif (
            agent_health["status"] == HealthStatus.DEGRADED
            and health_status == HealthStatus.HEALTHY
        ):
            health_status = HealthStatus.DEGRADED

        return {
            "status": health_status.value,
            "timestamp": datetime.now(UTC).isoformat(),
            "checks": checks,
            "overall_health_score": self._calculate_health_score(checks),
        }

    async def check_workflow_health(self, workflow_id: str) -> dict[str, Any]:
        """Check health of a specific workflow."""
        try:
            metrics = await self.performance_monitor.get_workflow_metrics(workflow_id)
            if not metrics:
                return {
                    "status": HealthStatus.UNKNOWN.value,
                    "message": "Workflow not found",
                }

            # Determine health based on metrics
            if metrics.calculate_error_rate() > 50:
                status = HealthStatus.UNHEALTHY
            elif metrics.calculate_error_rate() > 20:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY

            return {
                "status": status.value,
                "workflow_id": workflow_id,
                "success_rate": metrics.calculate_success_rate(),
                "error_rate": metrics.calculate_error_rate(),
                "execution_time_ms": metrics.total_execution_time_ms,
                "total_agents": metrics.total_agents,
                "successful_agents": metrics.successful_agents,
                "failed_agents": metrics.failed_agents,
            }

        except Exception as e:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": str(e),
            }

    async def get_health_metrics(self) -> dict[str, Any]:
        """Get detailed health metrics for monitoring."""
        # Get aggregate metrics
        aggregate_metrics = await self.performance_monitor.get_aggregate_metrics()

        # Get system health
        system_health = await self.check_system_health()

        return {
            "system_health": system_health,
            "aggregate_metrics": aggregate_metrics,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def _check_redis_health(self) -> dict[str, Any]:
        """Check Redis connectivity and performance."""
        try:
            redis_client = await self.redis_manager.get_client()

            # Ping test
            start_time = time.time()
            await redis_client.ping()
            ping_time_ms = (time.time() - start_time) * 1000

            # Check memory usage
            info = await redis_client.info("memory")
            used_memory = info.get("used_memory", 0)
            max_memory = info.get("maxmemory", 0)

            if ping_time_ms > 100:
                status = HealthStatus.DEGRADED
                message = "High Redis latency"
            elif max_memory > 0 and used_memory / max_memory > 0.9:
                status = HealthStatus.DEGRADED
                message = "High Redis memory usage"
            else:
                status = HealthStatus.HEALTHY
                message = "Redis is healthy"

            return {
                "status": status,
                "message": message,
                "ping_time_ms": ping_time_ms,
                "memory_usage_percentage": (used_memory / max_memory * 100)
                if max_memory > 0
                else 0,
            }

        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Redis connection failed: {str(e)}",
            }

    async def _check_metrics_health(self) -> dict[str, Any]:
        """Check workflow metrics health."""
        try:
            # Get recent metrics
            aggregate_metrics = await self.performance_monitor.get_aggregate_metrics(
                time_window_hours=1
            )

            if not aggregate_metrics:
                return {
                    "status": HealthStatus.UNKNOWN,
                    "message": "No recent workflow executions",
                }

            avg_error_rate = aggregate_metrics.get("avg_error_rate", 0)
            avg_execution_time = aggregate_metrics.get("avg_execution_time_ms", 0)

            if avg_error_rate > 50:
                status = HealthStatus.UNHEALTHY
                message = "High error rate detected"
            elif avg_error_rate > 20 or avg_execution_time > 30000:
                status = HealthStatus.DEGRADED
                message = "Performance degradation detected"
            else:
                status = HealthStatus.HEALTHY
                message = "Metrics are healthy"

            return {
                "status": status,
                "message": message,
                "avg_error_rate": avg_error_rate,
                "avg_execution_time_ms": avg_execution_time,
                "total_workflows": aggregate_metrics.get("total_workflows", 0),
            }

        except Exception as e:
            return {
                "status": HealthStatus.UNKNOWN,
                "message": f"Failed to check metrics: {str(e)}",
            }

    async def _check_agent_health(self) -> dict[str, Any]:
        """Check individual agent health."""
        # This would integrate with circuit breakers and agent-specific health checks
        # For now, return a placeholder
        return {
            "status": HealthStatus.HEALTHY,
            "message": "Agent health checks not yet implemented",
            "agents": {},
        }

    def _calculate_health_score(self, checks: dict[str, Any]) -> float:
        """Calculate overall health score from individual checks."""
        scores = {
            HealthStatus.HEALTHY: 100,
            HealthStatus.DEGRADED: 60,
            HealthStatus.UNHEALTHY: 20,
            HealthStatus.UNKNOWN: 50,
        }

        total_score = 0
        check_count = 0

        for check in checks.values():
            if isinstance(check, dict) and "status" in check:
                status = check["status"]
                if isinstance(status, HealthStatus):
                    total_score += scores.get(status, 50)
                else:
                    total_score += scores.get(HealthStatus[status.upper()], 50)
                check_count += 1

        return (total_score / check_count) if check_count > 0 else 0


class WorkflowDebugLogger:
    """Enhanced debug logging for workflow state transitions and troubleshooting."""

    def __init__(self, enable_debug: bool = False):
        """Initialize debug logger."""
        self.enable_debug = enable_debug
        self.logger = StructuredWorkflowLogger()
        self.state_history: dict[str, list[dict[str, Any]]] = {}

    def log_state_transition_debug(
        self,
        workflow_id: str,
        from_state: str,
        to_state: str,
        transition_data: dict[str, Any],
        correlation_context: CorrelationContext,
    ) -> None:
        """Log detailed state transition for debugging."""
        if not self.enable_debug:
            return

        # Track state history
        if workflow_id not in self.state_history:
            self.state_history[workflow_id] = []

        transition_record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "from_state": from_state,
            "to_state": to_state,
            "data": transition_data,
            "correlation_id": correlation_context.correlation_id,
        }

        self.state_history[workflow_id].append(transition_record)

        # Log detailed transition
        self.logger.log_with_correlation(
            "debug",
            f"DEBUG: State transition {from_state} -> {to_state}",
            correlation_context,
            event_type="debug_state_transition",
            from_state=from_state,
            to_state=to_state,
            transition_data=transition_data,
            state_history_length=len(self.state_history[workflow_id]),
        )

    def log_agent_input_output(
        self,
        workflow_id: str,
        agent_name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        correlation_context: CorrelationContext,
    ) -> None:
        """Log agent input/output for debugging."""
        if not self.enable_debug:
            return

        self.logger.log_with_correlation(
            "debug",
            f"DEBUG: Agent {agent_name} I/O",
            correlation_context,
            event_type="debug_agent_io",
            agent_name=agent_name,
            input_summary={
                "keys": list(input_data.keys()),
                "size": len(str(input_data)),
            },
            output_summary={
                "keys": list(output_data.keys()),
                "size": len(str(output_data)),
                "has_error": "error" in output_data,
            },
        )

    def log_performance_bottleneck(
        self,
        workflow_id: str,
        component: str,
        execution_time_ms: float,
        threshold_ms: float,
        correlation_context: CorrelationContext,
    ) -> None:
        """Log performance bottlenecks."""
        if execution_time_ms > threshold_ms:
            self.logger.log_with_correlation(
                "warning",
                f"Performance bottleneck detected in {component}",
                correlation_context,
                event_type="performance_bottleneck",
                component=component,
                execution_time_ms=execution_time_ms,
                threshold_ms=threshold_ms,
                exceeded_by_ms=execution_time_ms - threshold_ms,
            )

    def get_state_history(self, workflow_id: str) -> list[dict[str, Any]]:
        """Get state transition history for a workflow."""
        return self.state_history.get(workflow_id, [])

    def export_debug_report(self, workflow_id: str) -> dict[str, Any]:
        """Export comprehensive debug report for a workflow."""
        return {
            "workflow_id": workflow_id,
            "state_history": self.get_state_history(workflow_id),
            "generated_at": datetime.now(UTC).isoformat(),
            "debug_enabled": self.enable_debug,
        }


# Export main components
__all__ = [
    "CorrelationContext",
    "WorkflowMetrics",
    "StructuredWorkflowLogger",
    "WorkflowPerformanceMonitor",
    "WorkflowHealthMonitor",
    "WorkflowDebugLogger",
    "MetricType",
    "HealthStatus",
]

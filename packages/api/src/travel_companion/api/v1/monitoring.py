"""Monitoring and health check endpoints for workflow orchestration."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ...core.deps import get_redis_manager
from ...core.redis import RedisManager
from ...workflows.monitoring import (
    HealthStatus,
    WorkflowHealthMonitor,
    WorkflowPerformanceMonitor,
)

# Create router
router = APIRouter(
    prefix="/monitoring",
    tags=["monitoring"],
)


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Overall health status")
    timestamp: str = Field(..., description="Check timestamp")
    checks: dict[str, Any] = Field(..., description="Individual component checks")
    overall_health_score: float = Field(..., description="Overall health score (0-100)")


class WorkflowHealthResponse(BaseModel):
    """Workflow-specific health response model."""

    status: str = Field(..., description="Workflow health status")
    workflow_id: str = Field(..., description="Workflow identifier")
    success_rate: float = Field(..., description="Success rate percentage")
    error_rate: float = Field(..., description="Error rate percentage")
    execution_time_ms: float = Field(..., description="Total execution time in milliseconds")
    total_agents: int = Field(..., description="Total number of agents")
    successful_agents: int = Field(..., description="Number of successful agents")
    failed_agents: int = Field(..., description="Number of failed agents")


class MetricsResponse(BaseModel):
    """Metrics response model."""

    total_workflows: int = Field(0, description="Total number of workflows")
    avg_execution_time_ms: float = Field(0, description="Average execution time")
    avg_success_rate: float = Field(0, description="Average success rate")
    avg_error_rate: float = Field(0, description="Average error rate")
    avg_cache_hit_rate: float = Field(0, description="Average cache hit rate")
    total_api_calls: int = Field(0, description="Total API calls made")
    total_retries: int = Field(0, description="Total retry attempts")
    total_timeouts: int = Field(0, description="Total timeout occurrences")
    time_window_hours: int = Field(..., description="Time window for metrics")
    workflow_type: str | None = Field(None, description="Filtered workflow type")


class HealthMetricsResponse(BaseModel):
    """Combined health and metrics response."""

    system_health: dict[str, Any] = Field(..., description="System health status")
    aggregate_metrics: dict[str, Any] = Field(..., description="Aggregate performance metrics")
    timestamp: str = Field(..., description="Response timestamp")


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> HealthCheckResponse:
    """
    Perform comprehensive system health check.

    Returns overall system health status and individual component checks.
    """
    health_monitor = WorkflowHealthMonitor(redis_manager)
    health_status = await health_monitor.check_system_health()

    return HealthCheckResponse(**health_status)


@router.get("/health/ready")
async def readiness_check(
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> dict[str, str]:
    """
    Kubernetes readiness probe endpoint.

    Returns 200 if system is ready to accept traffic, 503 otherwise.
    """
    health_monitor = WorkflowHealthMonitor(redis_manager)
    health_status = await health_monitor.check_system_health()

    if health_status["status"] in [HealthStatus.HEALTHY.value, HealthStatus.DEGRADED.value]:
        return {"status": "ready"}
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System not ready",
        )


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """
    Kubernetes liveness probe endpoint.

    Simple check to verify the service is alive.
    """
    return {"status": "alive"}


@router.get("/workflows/{workflow_id}/health", response_model=WorkflowHealthResponse)
async def workflow_health_check(
    workflow_id: str,
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> WorkflowHealthResponse:
    """
    Check health status of a specific workflow.

    Args:
        workflow_id: The workflow identifier to check

    Returns:
        Detailed health status for the specified workflow
    """
    health_monitor = WorkflowHealthMonitor(redis_manager)
    health_status = await health_monitor.check_workflow_health(workflow_id)

    if health_status.get("status") == HealthStatus.UNKNOWN.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    return WorkflowHealthResponse(**health_status)


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    workflow_type: str | None = Query(None, description="Filter by workflow type"),
    time_window_hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> MetricsResponse:
    """
    Get aggregated workflow performance metrics.

    Args:
        workflow_type: Optional filter by workflow type
        time_window_hours: Time window for metrics aggregation (1-168 hours)

    Returns:
        Aggregated metrics for the specified time window
    """
    performance_monitor = WorkflowPerformanceMonitor(redis_manager)
    metrics = await performance_monitor.get_aggregate_metrics(
        workflow_type=workflow_type,
        time_window_hours=time_window_hours,
    )

    if not metrics:
        return MetricsResponse(
            time_window_hours=time_window_hours,
            workflow_type=workflow_type,
        )

    return MetricsResponse(**metrics)


@router.get("/workflows/{workflow_id}/metrics")
async def get_workflow_metrics(
    workflow_id: str,
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> dict[str, Any]:
    """
    Get detailed metrics for a specific workflow.

    Args:
        workflow_id: The workflow identifier

    Returns:
        Detailed performance metrics for the workflow
    """
    performance_monitor = WorkflowPerformanceMonitor(redis_manager)
    metrics = await performance_monitor.get_workflow_metrics(workflow_id)

    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metrics not found for workflow {workflow_id}",
        )

    return metrics.to_dict()


@router.get("/health/metrics", response_model=HealthMetricsResponse)
async def get_health_metrics(
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> HealthMetricsResponse:
    """
    Get combined health status and performance metrics.

    Provides a comprehensive view of system health and performance.
    """
    health_monitor = WorkflowHealthMonitor(redis_manager)
    health_metrics = await health_monitor.get_health_metrics()

    return HealthMetricsResponse(**health_metrics)


@router.post("/workflows/{workflow_id}/debug/enable")
async def enable_debug_logging(
    workflow_id: str,
) -> dict[str, str]:
    """
    Enable debug logging for a specific workflow.

    Args:
        workflow_id: The workflow identifier

    Returns:
        Confirmation of debug logging enablement
    """
    # This would integrate with the WorkflowDebugLogger
    # For now, return a placeholder response
    return {
        "status": "enabled",
        "workflow_id": workflow_id,
        "message": "Debug logging enabled for workflow",
    }


@router.get("/workflows/{workflow_id}/debug/report")
async def get_debug_report(
    workflow_id: str,
) -> dict[str, Any]:
    """
    Get debug report for a specific workflow.

    Args:
        workflow_id: The workflow identifier

    Returns:
        Comprehensive debug report including state history
    """
    # This would integrate with the WorkflowDebugLogger
    # For now, return a placeholder response
    return {
        "workflow_id": workflow_id,
        "debug_report": "Debug report generation not yet implemented",
        "state_history": [],
    }


# Export router
__all__ = ["router"]

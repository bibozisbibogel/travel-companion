"""Pydantic models for workflow API requests and responses."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class WorkflowExecutionRequest(BaseModel):
    """Request model for workflow execution."""

    input_data: dict[str, Any] = Field(
        ...,
        description="Input data for workflow execution",
        examples=[
            {
                "destination": "Paris, France",
                "travel_dates": {"start": "2024-06-01", "end": "2024-06-07"},
                "budget": 2000,
                "preferences": {
                    "accommodation_type": "hotel",
                    "activity_types": ["cultural", "culinary"],
                },
            }
        ],
    )

    user_id: str | None = Field(None, description="Optional user ID for context")

    request_id: str | None = Field(None, description="Optional request ID for tracking")


class WorkflowExecutionResponse(BaseModel):
    """Response model for workflow execution."""

    workflow_id: str = Field(..., description="Unique workflow execution ID")

    request_id: str = Field(..., description="Request tracking ID")

    status: str = Field(
        ..., description="Workflow execution status", examples=["completed", "running", "failed"]
    )

    output_data: dict[str, Any] = Field(..., description="Workflow execution results")

    execution_time_ms: float = Field(..., description="Total execution time in milliseconds")

    workflow_type: str = Field(..., description="Type of workflow executed")


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status check."""

    workflow_id: str = Field(..., description="Workflow execution ID")

    workflow_type: str = Field(..., description="Type of workflow")

    status: str = Field(
        ...,
        description="Current workflow status",
        examples=["running", "completed", "failed", "timeout"],
    )

    current_node: str = Field(..., description="Current executing node")

    start_time: float = Field(..., description="Workflow start timestamp")

    end_time: float | None = Field(None, description="Workflow completion timestamp")

    error: str | None = Field(None, description="Error message if workflow failed")


class WorkflowHealthResponse(BaseModel):
    """Response model for workflow engine health check."""

    status: str = Field(
        ..., description="Overall health status", examples=["healthy", "degraded", "unhealthy"]
    )

    workflows: list[dict[str, Any]] = Field(
        ..., description="Health status of individual workflow types"
    )

    redis_connected: bool = Field(..., description="Redis connection status for state persistence")

    total_workflows: int = Field(..., description="Total number of workflow types registered")

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Health check timestamp"
    )

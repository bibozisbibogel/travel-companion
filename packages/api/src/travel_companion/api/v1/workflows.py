"""Workflow execution API endpoints."""

import time

from fastapi import APIRouter, HTTPException, status

from ...models.workflow import (
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowHealthResponse,
    WorkflowStatusResponse,
)
from ...workflows.simple_workflow import TravelPlanningWorkflow

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post(
    "/execute",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute workflow",
    description="Execute a travel planning workflow with provided input data",
)
async def execute_workflow(request: WorkflowExecutionRequest) -> WorkflowExecutionResponse:
    """
    Execute a travel planning workflow.

    This endpoint initiates workflow execution and returns results upon completion.
    The workflow processes travel planning requests through multiple stages.
    """
    try:
        # Initialize workflow
        workflow = TravelPlanningWorkflow()

        # Execute workflow
        start_time = time.time()

        result = await workflow.execute(
            input_data=request.input_data, user_id=request.user_id, request_id=request.request_id
        )

        execution_time_ms = (time.time() - start_time) * 1000

        # Extract workflow metadata from result
        workflow_id = result.get("workflow_id", "unknown")
        request_id = result.get("request_id", request.request_id or "unknown")

        return WorkflowExecutionResponse(
            workflow_id=workflow_id,
            request_id=request_id,
            status="completed",
            output_data=result,
            execution_time_ms=execution_time_ms,
            workflow_type="TravelPlanningWorkflow",
        )

    except TimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail={
                "error": "WORKFLOW_TIMEOUT",
                "message": "Workflow execution exceeded timeout limit",
                "details": str(e),
            },
        ) from e

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "WORKFLOW_EXECUTION_FAILED",
                "message": "Workflow execution encountered an error",
                "details": str(e),
            },
        ) from e


@router.get(
    "/status/{workflow_id}",
    response_model=WorkflowStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get workflow status",
    description="Retrieve the current status of a running or completed workflow",
)
async def get_workflow_status(workflow_id: str) -> WorkflowStatusResponse:
    """
    Get the current status of a workflow execution.

    Args:
        workflow_id: Unique identifier of the workflow to check

    Returns:
        Current workflow status and execution details
    """
    try:
        # Initialize workflow to access state management
        workflow = TravelPlanningWorkflow()

        # Get workflow status
        status_info = await workflow.get_workflow_status(workflow_id)

        if status_info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow with ID {workflow_id} not found",
                    "workflow_id": workflow_id,
                },
            )

        return WorkflowStatusResponse(**status_info)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "STATUS_CHECK_FAILED",
                "message": "Failed to retrieve workflow status",
                "details": str(e),
                "workflow_id": workflow_id,
            },
        ) from e


@router.get(
    "/health",
    response_model=WorkflowHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Workflow engine health check",
    description="Check the health status of the workflow engine and its components",
)
async def get_workflow_health() -> WorkflowHealthResponse:
    """
    Check the health status of the workflow engine.

    Validates:
    - Workflow graph compilation
    - Redis connectivity for state persistence
    - Individual workflow type health

    Returns:
        Comprehensive health status of the workflow system
    """
    try:
        workflows_health = []
        redis_connected = True

        # Check travel planning workflow health
        travel_workflow = TravelPlanningWorkflow()
        workflow_health = travel_workflow.get_health_status()
        workflows_health.append(workflow_health)

        # Update global Redis status
        if not workflow_health.get("redis_connected", False):
            redis_connected = False

        # Determine overall status
        unhealthy_workflows = [w for w in workflows_health if w.get("status") != "healthy"]

        if not redis_connected:
            overall_status = "unhealthy"
        elif unhealthy_workflows:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return WorkflowHealthResponse(
            status=overall_status,
            workflows=workflows_health,
            redis_connected=redis_connected,
            total_workflows=len(workflows_health),
        )

    except Exception as e:
        # Return unhealthy status on any error
        return WorkflowHealthResponse(
            status="unhealthy",
            workflows=[
                {
                    "workflow_type": "unknown",
                    "status": "unhealthy",
                    "error": str(e),
                    "graph_built": False,
                    "redis_connected": False,
                    "node_count": 0,
                    "edge_count": 0,
                }
            ],
            redis_connected=False,
            total_workflows=0,
        )

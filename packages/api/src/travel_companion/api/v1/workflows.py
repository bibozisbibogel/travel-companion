"""Workflow execution API endpoints."""

import time
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from ...models.trip import TripPlanRequest
from ...models.workflow import (
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowHealthResponse,
    WorkflowStatusResponse,
)
from ...utils.logging import workflow_logger
from ...workflows.orchestrator import TripPlanningWorkflow
from ...workflows.state_manager import WorkflowStateManager

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
    Execute a travel planning workflow synchronously.

    This endpoint initiates workflow execution and returns results upon completion.
    The workflow processes travel planning requests through multiple stages.
    """
    try:
        # Initialize workflow
        workflow = TripPlanningWorkflow()

        # Execute workflow
        start_time = time.time()

        # Convert input data to TripPlanRequest if needed
        if "destination" in request.input_data and "requirements" in request.input_data:
            from ...models.trip import TripDestination, TripRequirements

            trip_request = TripPlanRequest(
                destination=TripDestination(**request.input_data["destination"]),
                requirements=TripRequirements(**request.input_data["requirements"]),
                preferences=request.input_data.get("preferences", {}),
            )

            result = await workflow.execute_trip_planning(
                trip_request=trip_request,
                user_id=request.user_id,
                request_id=request.request_id,
            )
        else:
            result = await workflow.execute(
                input_data=request.input_data,
                user_id=request.user_id,
                request_id=request.request_id,
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
            workflow_type="TripPlanningWorkflow",
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


@router.post(
    "/execute-async",
    response_model=dict[str, str],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute workflow asynchronously",
    description="Start a travel planning workflow in the background and return workflow ID for polling",
)
async def execute_workflow_async(
    request: WorkflowExecutionRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """
    Execute a travel planning workflow asynchronously.

    Returns immediately with a workflow ID that can be used to poll for status and results.
    The workflow continues executing in the background.
    """
    try:
        # Initialize workflow
        workflow = TripPlanningWorkflow()

        # Generate workflow ID
        import uuid

        workflow_id = str(uuid.uuid4())
        request_id = request.request_id or str(uuid.uuid4())

        # Create initial state for async execution
        initial_state = {
            "workflow_id": workflow_id,
            "request_id": request_id,
            "user_id": request.user_id,
            "status": "pending",
            "input_data": request.input_data,
        }

        # Store initial state
        state_manager = WorkflowStateManager(workflow_id=workflow_id)
        await state_manager.persist_state(initial_state, "automatic")

        # Execute workflow in background
        async def run_workflow():
            try:
                workflow_logger.log_workflow_started(
                    workflow_id=workflow_id,
                    workflow_type="TripPlanningWorkflow",
                    request_id=request_id,
                    input_data=request.input_data,
                )

                # Convert input data to TripPlanRequest if needed
                if "destination" in request.input_data and "requirements" in request.input_data:
                    from ...models.trip import TripDestination, TripRequirements

                    trip_request = TripPlanRequest(
                        destination=TripDestination(**request.input_data["destination"]),
                        requirements=TripRequirements(**request.input_data["requirements"]),
                        preferences=request.input_data.get("preferences", {}),
                    )

                    # Use pre-generated workflow_id for tracking
                    result = await workflow.execute_trip_planning(
                        trip_request=trip_request,
                        user_id=request.user_id,
                        request_id=request_id,
                    )
                else:
                    result = await workflow.execute(
                        input_data=request.input_data,
                        user_id=request.user_id,
                        request_id=request_id,
                    )

                # Update state with results
                final_state = await state_manager.restore_state()
                if final_state:
                    final_state["status"] = "completed"
                    final_state["output_data"] = result
                    await state_manager.persist_state(final_state, "completion")

            except Exception as e:
                # Update state with error
                error_state = await state_manager.restore_state()
                if error_state:
                    error_state["status"] = "failed"
                    error_state["error"] = str(e)
                    await state_manager.persist_state(error_state, "error")

        # Add to background tasks
        background_tasks.add_task(run_workflow)

        return {
            "workflow_id": workflow_id,
            "request_id": request_id,
            "message": "Workflow started in background",
            "status_url": f"/api/v1/workflows/status/{workflow_id}",
            "progress_url": f"/api/v1/workflows/progress/{workflow_id}",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "WORKFLOW_START_FAILED",
                "message": "Failed to start workflow execution",
                "details": str(e),
            },
        ) from e


@router.get(
    "/progress/{workflow_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get workflow progress",
    description="Retrieve real-time progress information for a running workflow",
)
async def get_workflow_progress(workflow_id: str) -> dict[str, Any]:
    """
    Get real-time progress information for a workflow.

    Returns detailed progress metrics including:
    - Current execution phase
    - Completed and pending agents
    - Performance metrics
    - Estimated completion time
    """
    try:
        # Use enhanced state manager for progress tracking
        state_manager = WorkflowStateManager(workflow_id=workflow_id)

        # Get progress information
        progress = await state_manager.get_progress()

        if progress is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow with ID {workflow_id} not found",
                    "workflow_id": workflow_id,
                },
            )

        return progress

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PROGRESS_CHECK_FAILED",
                "message": "Failed to retrieve workflow progress",
                "details": str(e),
                "workflow_id": workflow_id,
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
        # Initialize workflow for status check
        workflow = TripPlanningWorkflow()
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
    "/result/{workflow_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get workflow results",
    description="Retrieve the results of a completed workflow",
)
async def get_workflow_result(workflow_id: str) -> dict[str, Any]:
    """
    Get the results of a completed workflow.

    Returns the complete output data from the workflow execution.
    Returns 404 if workflow not found, 425 if workflow still running.
    """
    try:
        # Use enhanced state manager for result retrieval
        state_manager = WorkflowStateManager(workflow_id=workflow_id)

        # Get workflow state
        state = await state_manager.restore_state()

        if state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow with ID {workflow_id} not found",
                    "workflow_id": workflow_id,
                },
            )

        # Check if workflow is completed
        if state.get("status") not in ["completed", "failed", "failed_with_partial_results"]:
            raise HTTPException(
                status_code=status.HTTP_425_TOO_EARLY,
                detail={
                    "error": "WORKFLOW_NOT_COMPLETED",
                    "message": f"Workflow {workflow_id} is still running",
                    "status": state.get("status", "unknown"),
                    "workflow_id": workflow_id,
                },
            )

        # Return results
        return {
            "workflow_id": workflow_id,
            "status": state.get("status"),
            "output_data": state.get("output_data", {}),
            "error": state.get("error"),
            "execution_time_ms": (
                (state.get("end_time", 0) - state.get("start_time", 0)) * 1000
                if state.get("end_time") and state.get("start_time")
                else None
            ),
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "RESULT_RETRIEVAL_FAILED",
                "message": "Failed to retrieve workflow results",
                "details": str(e),
                "workflow_id": workflow_id,
            },
        ) from e


@router.post(
    "/cancel/{workflow_id}",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Cancel workflow execution",
    description="Cancel a running workflow and perform cleanup",
)
async def cancel_workflow(workflow_id: str) -> dict[str, str]:
    """
    Cancel a running workflow execution.

    Attempts to gracefully stop the workflow and clean up resources.
    Returns success even if workflow was already completed.
    """
    try:
        # Use enhanced state manager for cancellation
        state_manager = WorkflowStateManager(workflow_id=workflow_id)

        # Get current state
        state = await state_manager.restore_state()

        if state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow with ID {workflow_id} not found",
                    "workflow_id": workflow_id,
                },
            )

        # Check if already completed
        if state.get("status") in ["completed", "failed", "cancelled"]:
            return {
                "workflow_id": workflow_id,
                "message": f"Workflow already {state.get('status')}",
                "status": state.get("status"),
            }

        # Update state to cancelled
        state["status"] = "cancelled"
        state["end_time"] = time.time()
        state["error"] = "Workflow cancelled by user"

        # Persist cancellation state
        await state_manager.persist_state(state, "manual")

        # Log cancellation
        workflow_logger.log_workflow_cancelled(
            workflow_id=workflow_id,
            request_id=state.get("request_id", "unknown"),
        )

        return {
            "workflow_id": workflow_id,
            "message": "Workflow cancelled successfully",
            "status": "cancelled",
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "CANCELLATION_FAILED",
                "message": "Failed to cancel workflow",
                "details": str(e),
                "workflow_id": workflow_id,
            },
        ) from e


@router.delete(
    "/cleanup/{workflow_id}",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Clean up workflow data",
    description="Remove workflow state and associated data from storage",
)
async def cleanup_workflow(workflow_id: str) -> dict[str, str]:
    """
    Clean up workflow data and state from storage.

    Removes all workflow-related data including state, checkpoints, and snapshots.
    This action cannot be undone.
    """
    try:
        # Use enhanced state manager for cleanup
        state_manager = WorkflowStateManager(workflow_id=workflow_id)

        # Perform cleanup
        cleanup_success = await state_manager.cleanup_workflow()

        if not cleanup_success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow with ID {workflow_id} not found or already cleaned up",
                    "workflow_id": workflow_id,
                },
            )

        # Log cleanup
        workflow_logger.log_workflow_cleanup(
            workflow_id=workflow_id,
        )

        return {
            "workflow_id": workflow_id,
            "message": "Workflow data cleaned up successfully",
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "CLEANUP_FAILED",
                "message": "Failed to clean up workflow data",
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
        travel_workflow = TripPlanningWorkflow()
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

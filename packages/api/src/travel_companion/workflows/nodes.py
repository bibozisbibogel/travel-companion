"""Workflow node implementations for travel planning."""

import time

from ..utils.logging import workflow_logger
from .orchestrator import WorkflowState


class WorkflowNodes:
    """Collection of reusable workflow nodes."""

    @staticmethod
    def start_node(state: WorkflowState) -> WorkflowState:
        """
        Entry point for workflow execution.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state
        """
        start_time = time.time()

        workflow_logger.log_node_entered(
            workflow_id=state["workflow_id"],
            node_name="start",
            request_id=state["request_id"],
            state_keys=list(state.keys()),
        )

        try:
            # Initialize workflow
            state["current_node"] = "start"
            state["status"] = "processing"

            # Log input data keys (not values for privacy) - tracked for logging context

            execution_time_ms = (time.time() - start_time) * 1000

            workflow_logger.log_node_completed(
                workflow_id=state["workflow_id"],
                node_name="start",
                request_id=state["request_id"],
                execution_time_ms=execution_time_ms,
                output_keys=["status", "current_node"],
            )

            return state

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000

            workflow_logger.log_node_failed(
                workflow_id=state["workflow_id"],
                node_name="start",
                request_id=state["request_id"],
                error=str(e),
                execution_time_ms=execution_time_ms,
            )

            state["error"] = str(e)
            state["status"] = "failed"
            raise

    @staticmethod
    def process_node(state: WorkflowState) -> WorkflowState:
        """
        Main processing node for workflow logic.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state
        """
        start_time = time.time()

        workflow_logger.log_node_entered(
            workflow_id=state["workflow_id"],
            node_name="process",
            request_id=state["request_id"],
            state_keys=list(state.keys()),
        )

        try:
            # Update current node
            state["current_node"] = "process"

            # Simulate processing logic
            input_data = state.get("input_data", {})

            # Basic processing - echo input data with processing metadata
            processed_data = {
                "original_input": input_data,
                "processed_at": time.time(),
                "processing_node": "process",
                "workflow_id": state["workflow_id"],
            }

            # Store intermediate results
            state["intermediate_results"]["process_results"] = processed_data

            execution_time_ms = (time.time() - start_time) * 1000

            workflow_logger.log_node_completed(
                workflow_id=state["workflow_id"],
                node_name="process",
                request_id=state["request_id"],
                execution_time_ms=execution_time_ms,
                output_keys=list(processed_data.keys()),
            )

            return state

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000

            workflow_logger.log_node_failed(
                workflow_id=state["workflow_id"],
                node_name="process",
                request_id=state["request_id"],
                error=str(e),
                execution_time_ms=execution_time_ms,
            )

            state["error"] = str(e)
            state["status"] = "failed"
            raise

    @staticmethod
    def end_node(state: WorkflowState) -> WorkflowState:
        """
        Final node for workflow completion.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state with final results
        """
        start_time = time.time()

        workflow_logger.log_node_entered(
            workflow_id=state["workflow_id"],
            node_name="end",
            request_id=state["request_id"],
            state_keys=list(state.keys()),
        )

        try:
            # Update current node
            state["current_node"] = "end"

            # Prepare final output
            output_data = {
                "workflow_id": state["workflow_id"],
                "request_id": state["request_id"],
                "execution_summary": {
                    "start_time": state["start_time"],
                    "processing_time_ms": (time.time() - state["start_time"]) * 1000,
                    "nodes_executed": ["start", "process", "end"],
                    "status": "completed",
                },
                "results": state.get("intermediate_results", {}),
                "input_echo": state.get("input_data", {}),
            }

            # Set final output
            state["output_data"] = output_data
            state["status"] = "completed"

            execution_time_ms = (time.time() - start_time) * 1000

            workflow_logger.log_node_completed(
                workflow_id=state["workflow_id"],
                node_name="end",
                request_id=state["request_id"],
                execution_time_ms=execution_time_ms,
                output_keys=list(output_data.keys()),
            )

            return state

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000

            workflow_logger.log_node_failed(
                workflow_id=state["workflow_id"],
                node_name="end",
                request_id=state["request_id"],
                error=str(e),
                execution_time_ms=execution_time_ms,
            )

            state["error"] = str(e)
            state["status"] = "failed"
            raise

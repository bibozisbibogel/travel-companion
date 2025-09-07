"""Workflow state management with Redis persistence and progress tracking."""

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, TypedDict

import redis.asyncio as redis

from travel_companion.utils.logging import WorkflowLogger

# Initialize workflow logger
workflow_logger = WorkflowLogger()
logger = workflow_logger.logger


class WorkflowStatus(Enum):
    """Workflow execution states."""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class CheckpointType(Enum):
    """Types of workflow checkpoints."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"
    PHASE_TRANSITION = "phase_transition"
    ERROR = "error"
    COMPLETION = "completion"


class CheckpointEnum(Enum):
    """Legacy checkpoint enum for backward compatibility."""

    START = "start"
    PREFERENCES = "preferences"
    ITINERARY = "itinerary"
    ACCOMMODATIONS = "accommodations"
    ACTIVITIES = "activities"
    RESTAURANTS = "restaurants"
    WEATHER = "weather"
    COMPLETE = "complete"
    ERROR = "error"
    CUSTOM = "custom"


class TripPlanningWorkflowState(TypedDict, total=False):
    """Type definition for workflow state."""

    # Core workflow data
    request_id: str
    workflow_id: str
    status: str
    current_node: str | None
    agent_dependencies: dict[str, list[str]]
    agents_completed: list[str]
    agents_failed: list[str]

    # User and trip data
    user_preferences: dict[str, Any]
    itinerary: dict[str, Any] | None
    accommodations: list[dict[str, Any]]
    activities: list[dict[str, Any]]
    restaurants: list[dict[str, Any]]
    weather_data: dict[str, Any] | None

    # Workflow context
    budget_tracking: dict[str, Any]
    optimization_metrics: dict[str, float]
    state_transitions: list[dict[str, Any]]
    parallel_execution_metrics: dict[str, Any] | None

    # Error handling
    errors: list[dict[str, Any]]
    retry_count: int
    max_retries: int

    # Metadata
    created_at: str
    updated_at: str
    completed_at: str | None
    current_step: str | None
    recovered_from: str | None
    recovery_timestamp: str | None

    # Workflow lifecycle
    suspension_reason: str | None
    suspended_at: str | None
    resumed_at: str | None
    completion_message: str | None


@dataclass
class StateSnapshot:
    """Represents a state snapshot with metadata."""

    workflow_id: str
    timestamp: float
    snapshot_id: str
    state_data: dict[str, Any]
    checkpoint_type: str
    agents_completed: list[str] = field(default_factory=list)
    agents_failed: list[str] = field(default_factory=list)
    current_phase: str = "unknown"
    description: str = ""


@dataclass
class WorkflowConfig:
    """Configuration for workflow state management."""

    # TTL settings (in seconds)
    pending_workflow_ttl: int = 300  # 5 minutes
    active_workflow_ttl: int = 3600  # 1 hour
    suspended_workflow_ttl: int = 7200  # 2 hours
    completed_workflow_ttl: int = 86400  # 24 hours
    failed_workflow_ttl: int = 1800  # 30 minutes
    expired_workflow_ttl: int = 600  # 10 minutes

    # State management
    checkpoint_interval: int = 120  # 2 minutes
    heartbeat_interval: int = 30  # 30 seconds
    progress_update_interval: int = 10  # 10 seconds

    # Storage limits
    max_snapshots_per_workflow: int = 20
    snapshot_compression_threshold: int = 1024 * 10  # 10KB

    # Retry settings
    default_max_retries: int = 3
    retry_delay: int = 5  # seconds

    # Cleanup settings
    cleanup_interval: int = 300  # 5 minutes
    expired_workflow_retention: int = 3600  # 1 hour after expiry

    # Performance tuning
    batch_size: int = 100
    enable_compression: bool = True
    enable_progress_tracking: bool = True
    enable_heartbeat: bool = True


class EnhancedWorkflowStateManager:
    """Enhanced state manager with progress tracking, recovery, and monitoring."""

    def __init__(
        self,
        redis_client: redis.Redis,
        workflow_id: str,
        request_id: str | None = None,
        config: WorkflowConfig | None = None,
        enable_heartbeat: bool = True,
    ):
        """Initialize enhanced workflow state manager."""
        self.redis_client = redis_client
        self.workflow_id = workflow_id
        self.request_id = request_id or workflow_id
        self.config = config or WorkflowConfig()
        self.enable_heartbeat = enable_heartbeat

        # Keys for Redis storage
        self.state_key = f"workflow:state:{workflow_id}"
        self.metadata_key = f"workflow:metadata:{workflow_id}"
        self.snapshots_key = f"workflow:snapshots:{workflow_id}"
        self.progress_key = f"workflow:progress:{workflow_id}"
        self.heartbeat_key = f"workflow:heartbeat:{workflow_id}"
        self.lock_key = f"workflow:lock:{workflow_id}"
        self.index_key = "workflow:index"

        # State tracking
        self.workflow_status = WorkflowStatus.PENDING
        self.current_state: TripPlanningWorkflowState | None = None
        self.ttl = self.config.active_workflow_ttl

        # Progress tracking
        self.last_checkpoint_time = 0.0
        self.last_progress_update = 0.0
        self.last_heartbeat = 0.0
        self.progress_data: dict[str, Any] | None = None

        # Performance metrics
        self.operation_count = 0
        self.state_size_bytes = 0

        # Cleanup tasks tracking
        self._cleanup_tasks: set[str] = set()

        # Initialize logger
        workflow_logger.info(
            "Workflow state manager initialized",
            extra={
                "workflow_id": workflow_id,
                "request_id": request_id,
                "config": self.config.__dict__,
            },
        )

    # Core state persistence methods

    async def initialize_workflow(
        self, state: TripPlanningWorkflowState, estimated_duration_minutes: int | None = None
    ) -> bool:
        """Initialize a new workflow with state and metadata."""
        try:
            # Set initial status
            state["status"] = "active"
            state["created_at"] = datetime.now(UTC).isoformat()
            state["updated_at"] = datetime.now(UTC).isoformat()
            self.workflow_status = WorkflowStatus.ACTIVE

            # Calculate TTL based on estimated duration
            if estimated_duration_minutes:
                # Use 2x estimated duration as TTL for safety
                ttl = max(estimated_duration_minutes * 60 * 2, self.config.active_workflow_ttl)
            else:
                ttl = self.config.active_workflow_ttl
            self.ttl = ttl

            # Initialize progress tracking
            await self._initialize_progress_tracking(state)

            # Start heartbeat
            if self.enable_heartbeat:
                await self._start_heartbeat()

            # Persist initial state
            result = await self.persist_state(state, CheckpointType.AUTOMATIC)

            # Add to workflow index
            await self._add_to_workflow_index()

            return result

        except Exception as e:
            workflow_logger.error(
                "Failed to initialize workflow",
                extra={
                    "workflow_id": self.workflow_id,
                    "error": str(e),
                },
            )
            return False

    async def persist_state(
        self,
        state: TripPlanningWorkflowState,
        checkpoint_type: CheckpointType | str = CheckpointType.AUTOMATIC,
    ) -> bool:
        """Persist workflow state with automatic checkpointing and progress tracking."""
        try:
            # Handle backward compatibility for string checkpoint types
            if isinstance(checkpoint_type, str):
                # Map string to CheckpointType enum
                checkpoint_type_map = {
                    "automatic": CheckpointType.AUTOMATIC,
                    "manual": CheckpointType.MANUAL,
                    "phase_transition": CheckpointType.PHASE_TRANSITION,
                    "error": CheckpointType.ERROR,
                    "completion": CheckpointType.COMPLETION,
                }
                checkpoint_type = checkpoint_type_map.get(
                    checkpoint_type.lower(), CheckpointType.AUTOMATIC
                )

            # Update state timestamp
            state["updated_at"] = datetime.now(UTC).isoformat()

            # Update workflow status
            self._update_workflow_status(state)

            # Serialize state
            serialized_state = json.dumps(state, default=self._json_serializer)
            self.state_size_bytes = len(serialized_state.encode())

            # Calculate appropriate TTL
            ttl = self._calculate_ttl(self.workflow_status)

            # Persist to Redis with TTL
            await self.redis_client.setex(self.state_key, ttl, serialized_state)

            # Check if TTL needs extension
            current_ttl = await self._get_current_ttl()
            if current_ttl > 0 and current_ttl < 600:  # Less than 10 minutes
                # Extend TTL
                await self.redis_client.expire(self.state_key, ttl)

            # Update metadata
            await self._update_metadata(state, checkpoint_type)

            # Create checkpoint if needed
            if await self._should_create_checkpoint(checkpoint_type):
                await self._create_checkpoint(state, checkpoint_type)

            # Update progress tracking
            if self.config.enable_progress_tracking:
                await self._update_progress_tracking(state)

            # Update heartbeat
            if self.enable_heartbeat:
                await self._update_heartbeat()

            # Update workflow index
            await self._add_to_workflow_index()

            self.operation_count += 1
            self.current_state = state

            workflow_logger.log_state_persisted(
                workflow_id=self.workflow_id,
                request_id=self.request_id,
                persistence_time_ms=0,  # Placeholder
            )

            return True

        except Exception as e:
            workflow_logger.log_state_persistence_error(
                workflow_id=self.workflow_id,
                request_id=self.request_id,
                error=str(e),
                checkpoint_type=checkpoint_type.value
                if isinstance(checkpoint_type, CheckpointType)
                else str(checkpoint_type),
            )
            return False

    async def restore_state(
        self, snapshot_id: str | None = None
    ) -> TripPlanningWorkflowState | None:
        """Restore workflow state from Redis or snapshot."""
        try:
            state: TripPlanningWorkflowState | None = None
            if snapshot_id:
                # Restore from specific snapshot
                state = await self._restore_from_snapshot(snapshot_id)
            else:
                # Restore current state
                state_data = await self.redis_client.get(self.state_key)
                if not state_data:
                    return None
                state = json.loads(state_data)

            if state:
                self.current_state = state
                self._update_workflow_status(state)

                workflow_logger.log_state_restored(
                    workflow_id=self.workflow_id,
                    request_id=self.request_id,
                    restoration_time_ms=0,  # Placeholder
                    restored_keys=list(state.keys()),
                )

            return state

        except Exception as e:
            workflow_logger.log_snapshot_restoration_error(
                workflow_id=self.workflow_id, snapshot_id=snapshot_id or "current", error=str(e)
            )
            return None

    async def persist_state_with_progress(
        self,
        state: TripPlanningWorkflowState,
        checkpoint_type: CheckpointType = CheckpointType.AUTOMATIC,
    ) -> bool:
        """Persist state with progress tracking (wrapper for backward compatibility)."""
        return await self.persist_state(state, checkpoint_type)

    async def create_manual_checkpoint(
        self, state: TripPlanningWorkflowState, description: str
    ) -> str:
        """Create a manual checkpoint with description."""
        snapshot_id = await self._create_enhanced_checkpoint(
            state, CheckpointType.MANUAL, description
        )
        return snapshot_id

    async def _create_enhanced_checkpoint(
        self, state: TripPlanningWorkflowState, checkpoint_type: CheckpointType, description: str
    ) -> str:
        """Create an enhanced checkpoint with metadata and description."""
        snapshot_id = f"{checkpoint_type.value}_{int(time.time())}"

        # Convert TripPlanningWorkflowState to dict for snapshot
        state_dict = dict(state) if isinstance(state, dict) else state

        snapshot = StateSnapshot(
            workflow_id=self.workflow_id,
            timestamp=time.time(),
            snapshot_id=snapshot_id,
            state_data=state_dict,
            checkpoint_type=checkpoint_type.value,
            agents_completed=state.get("agents_completed", []),
            agents_failed=state.get("agents_failed", []),
            current_phase=state.get("current_node") or "unknown",
            description=description,
        )

        await self._store_enhanced_snapshot(snapshot)

        workflow_logger.log_enhanced_checkpoint_created(
            workflow_id=self.workflow_id,
            request_id=self.request_id,
            snapshot_id=snapshot_id,
            checkpoint_type=checkpoint_type.value,
            description=description,
        )

        return snapshot_id

    async def _store_enhanced_snapshot(self, snapshot: StateSnapshot) -> None:
        """Store an enhanced snapshot (wrapper for _store_snapshot)."""
        await self._store_snapshot(snapshot)

    async def suspend_workflow(self, reason: str) -> bool:
        """Suspend the workflow with a reason."""
        try:
            if self.current_state:
                self.current_state["status"] = "suspended"
                self.current_state["suspension_reason"] = reason
                self.current_state["suspended_at"] = datetime.now(UTC).isoformat()
                self.workflow_status = WorkflowStatus.SUSPENDED

                # Create suspension checkpoint
                await self._create_enhanced_checkpoint(
                    self.current_state, CheckpointType.MANUAL, f"Suspended: {reason}"
                )

                # Persist state with suspended status
                result = await self.persist_state(self.current_state, CheckpointType.MANUAL)

                # Stop heartbeat
                if self.enable_heartbeat:
                    await self._stop_heartbeat()

                return result
            return False

        except Exception as e:
            workflow_logger.error(
                "Failed to suspend workflow",
                extra={
                    "workflow_id": self.workflow_id,
                    "error": str(e),
                },
            )
            return False

    async def resume_workflow(self) -> dict[str, Any] | None:
        """Resume a suspended workflow."""
        try:
            # Restore state
            state = await self.restore_state()
            if not state:
                return None

            # Update status
            state["status"] = "active"
            state["resumed_at"] = datetime.now(UTC).isoformat()
            self.workflow_status = WorkflowStatus.ACTIVE

            # Restart heartbeat
            if self.enable_heartbeat:
                await self._start_heartbeat()

            # Persist resumed state
            await self.persist_state(state, CheckpointType.MANUAL)

            return {"state": state}

        except Exception as e:
            workflow_logger.error(
                "Failed to resume workflow",
                extra={
                    "workflow_id": self.workflow_id,
                    "error": str(e),
                },
            )
            return None

    async def complete_workflow(
        self, state: TripPlanningWorkflowState, completion_message: str
    ) -> bool:
        """Mark workflow as completed."""
        try:
            state["status"] = "completed"
            state["completed_at"] = datetime.now(UTC).isoformat()
            state["completion_message"] = completion_message
            self.workflow_status = WorkflowStatus.COMPLETED

            # Create completion checkpoint
            await self._create_enhanced_checkpoint(
                state, CheckpointType.COMPLETION, completion_message
            )

            # Persist final state
            result = await self.persist_state(state, CheckpointType.COMPLETION)

            # Stop heartbeat
            if self.enable_heartbeat:
                await self._stop_heartbeat()

            # Schedule cleanup
            self._cleanup_tasks.add(f"cleanup_{self.workflow_id}")

            return result

        except Exception as e:
            workflow_logger.error(
                "Failed to complete workflow",
                extra={
                    "workflow_id": self.workflow_id,
                    "error": str(e),
                },
            )
            return False

    async def _cleanup_single_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Clean up a single workflow."""
        try:
            await self._cleanup_workflow(workflow_id)
            return {"cleaned": True, "reason": "completed"}
        except Exception as e:
            return {"cleaned": False, "reason": str(e)}

    async def _force_cleanup_workflow_keys(self, workflow_id: str) -> None:
        """Force cleanup all Redis keys for a workflow using pipeline."""
        try:
            pipeline = self.redis_client.pipeline()

            keys_to_delete = [
                f"workflow:state:{workflow_id}",
                f"workflow:metadata:{workflow_id}",
                f"workflow:snapshots:{workflow_id}",
                f"workflow:progress:{workflow_id}",
                f"workflow:heartbeat:{workflow_id}",
                f"workflow:metrics:{workflow_id}",
                f"workflow:lock:{workflow_id}",
            ]

            for key in keys_to_delete:
                pipeline.delete(key)

            await pipeline.execute()

        except Exception as e:
            workflow_logger.error(
                "Failed to force cleanup workflow keys",
                extra={
                    "workflow_id": workflow_id,
                    "error": str(e),
                },
            )

    async def cleanup_old_snapshots(self, max_age_hours: int = 48) -> int:
        """Clean up old snapshots based on age."""
        try:
            snapshots_data = await self.redis_client.get(self.snapshots_key)
            if not snapshots_data:
                return 0

            snapshots = json.loads(snapshots_data)
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600

            # Filter out old snapshots
            cleaned_count = 0
            filtered_snapshots = []

            for snapshot in snapshots:
                age = current_time - snapshot["timestamp"]
                # Keep manual and important checkpoints regardless of age
                if snapshot["checkpoint_type"] in ["manual", "error", "completion"]:
                    filtered_snapshots.append(snapshot)
                elif age < max_age_seconds:
                    filtered_snapshots.append(snapshot)
                else:
                    cleaned_count += 1

            # Update snapshots if any were cleaned
            if cleaned_count > 0:
                ttl = self._calculate_ttl(self.workflow_status)
                await self.redis_client.setex(
                    self.snapshots_key,
                    ttl,
                    json.dumps(filtered_snapshots, default=self._json_serializer),
                )

            return cleaned_count

        except Exception as e:
            workflow_logger.error(
                "Failed to clean up old snapshots",
                extra={
                    "workflow_id": self.workflow_id,
                    "error": str(e),
                },
            )
            return 0

    def _estimate_enhanced_completion_time(
        self, elapsed_time: float, completed_agents: int, total_agents: int
    ) -> float | None:
        """Estimate completion time based on progress."""
        if completed_agents == 0 or total_agents == 0:
            return None

        # Calculate average time per agent
        avg_time_per_agent = elapsed_time / completed_agents

        # Estimate remaining time
        remaining_agents = total_agents - completed_agents
        estimated_remaining_time = avg_time_per_agent * remaining_agents

        # Return estimated completion timestamp
        return time.time() + estimated_remaining_time

    async def restore_workflow_state(
        self, snapshot_id: str | None = None, include_progress: bool = True
    ) -> dict[str, Any] | None:
        """Restore workflow state with optional progress data."""
        try:
            state_data: dict[str, Any] | None = None
            if snapshot_id:
                # Restore from specific snapshot
                snapshots_data = await self.redis_client.get(self.snapshots_key)
                if snapshots_data:
                    snapshots = json.loads(snapshots_data)
                    if snapshot_id in snapshots:
                        state_data = snapshots[snapshot_id].get("state", {})
                    else:
                        logger.warning(f"Snapshot {snapshot_id} not found")
                        return None
                else:
                    return None
            else:
                # Restore current state
                state_data_raw = await self.redis_client.get(self.state_key)
                if not state_data_raw:
                    return None
                state_data = json.loads(state_data_raw)

            if not state_data:
                return None

            # Extract progress data if present
            progress = state_data.pop("_progress", None) if include_progress else None

            # Initialize progress tracking if needed
            if include_progress and not progress:
                # Cast state_data for initialization
                if isinstance(state_data, dict):
                    await self._initialize_progress_tracking(state_data)
                    progress = self.progress_data

            return {"state": state_data, "progress": progress}

        except Exception as e:
            logger.error(f"Failed to restore workflow state: {e}")
            return None

    # Checkpoint management

    async def _should_create_checkpoint(self, checkpoint_type: CheckpointType) -> bool:
        """Determine if a checkpoint should be created."""
        if checkpoint_type in [
            CheckpointType.MANUAL,
            CheckpointType.ERROR,
            CheckpointType.COMPLETION,
        ]:
            return True

        # Create automatic checkpoints at intervals
        current_time = time.time()
        if current_time - self.last_checkpoint_time > self.config.checkpoint_interval:
            self.last_checkpoint_time = current_time
            return True

        return False

    async def _create_checkpoint(
        self, state: TripPlanningWorkflowState, checkpoint_type: CheckpointType
    ) -> str:
        """Create a state checkpoint."""
        snapshot_id = f"{checkpoint_type.value}_{int(time.time())}"

        # Convert TripPlanningWorkflowState to dict for snapshot
        state_dict = dict(state) if isinstance(state, dict) else state

        snapshot = StateSnapshot(
            workflow_id=self.workflow_id,
            timestamp=time.time(),
            snapshot_id=snapshot_id,
            state_data=state_dict,
            checkpoint_type=checkpoint_type.value,
            agents_completed=state.get("agents_completed", []),
            agents_failed=state.get("agents_failed", []),
            current_phase=state.get("current_node") or "unknown",
        )

        await self._store_snapshot(snapshot)

        workflow_logger.log_enhanced_checkpoint_created(
            workflow_id=self.workflow_id,
            request_id=self.request_id,
            snapshot_id=snapshot_id,
            checkpoint_type=checkpoint_type.value,
            description="",
        )

        return snapshot_id

    async def _store_snapshot(self, snapshot: StateSnapshot) -> None:
        """Store a snapshot with size management."""
        try:
            # Get existing snapshots
            snapshots_data = await self.redis_client.get(self.snapshots_key)
            snapshots = json.loads(snapshots_data) if snapshots_data else []

            # Add new snapshot
            snapshot_dict = {
                "snapshot_id": snapshot.snapshot_id,
                "timestamp": snapshot.timestamp,
                "checkpoint_type": snapshot.checkpoint_type,
                "agents_completed": snapshot.agents_completed,
                "agents_failed": snapshot.agents_failed,
                "current_phase": snapshot.current_phase,
                "state_data": snapshot.state_data,
            }

            # Compress if needed
            if (
                self.config.enable_compression
                and self.state_size_bytes > self.config.snapshot_compression_threshold
            ):
                snapshot_dict["compressed"] = True
                snapshot_dict["state_data"] = self._compress_state(snapshot.state_data)
            else:
                snapshot_dict["compressed"] = False

            snapshots.append(snapshot_dict)

            # Cleanup old snapshots
            if len(snapshots) > self.config.max_snapshots_per_workflow:
                # Keep important checkpoints and recent ones
                important_types = [
                    CheckpointType.MANUAL.value,
                    CheckpointType.ERROR.value,
                    CheckpointType.COMPLETION.value,
                ]

                important_snapshots = [
                    s for s in snapshots if s["checkpoint_type"] in important_types
                ]
                regular_snapshots = [
                    s for s in snapshots if s["checkpoint_type"] not in important_types
                ]

                # Sort regular snapshots by timestamp
                regular_snapshots.sort(key=lambda x: x["timestamp"], reverse=True)

                # Keep recent regular snapshots
                keep_regular = self.config.max_snapshots_per_workflow - len(important_snapshots)
                regular_snapshots = regular_snapshots[: max(keep_regular, 0)]

                snapshots = important_snapshots + regular_snapshots

            # Store snapshots
            ttl = self._calculate_ttl(self.workflow_status)
            await self.redis_client.setex(
                self.snapshots_key,
                ttl,
                json.dumps(snapshots, default=self._json_serializer),
            )

        except Exception as e:
            workflow_logger.log_snapshot_storage_error(
                workflow_id=self.workflow_id,
                snapshot_id=snapshot.snapshot_id,
                error=str(e),
            )

    async def _restore_from_snapshot(self, snapshot_id: str) -> TripPlanningWorkflowState | None:
        """Restore state from a specific snapshot."""
        try:
            snapshots_data = await self.redis_client.get(self.snapshots_key)

            if not snapshots_data:
                return None

            snapshots = json.loads(snapshots_data)

            # Find the requested snapshot
            for snapshot in snapshots:
                if snapshot["snapshot_id"] == snapshot_id:
                    state_data = snapshot["state_data"]

                    # Decompress if needed
                    if snapshot.get("compressed", False):
                        state_data = self._decompress_state(state_data)

                    # Return with proper type casting
                    if isinstance(state_data, dict):
                        return state_data  # type: ignore[return-value]
                    return None

            return None

        except Exception as e:
            workflow_logger.log_snapshot_restoration_error(
                workflow_id=self.workflow_id, snapshot_id=snapshot_id, error=str(e)
            )
            return None

    # Progress tracking

    async def _update_progress_tracking(
        self, state: TripPlanningWorkflowState, description: str | None = None
    ) -> None:
        """Update workflow progress tracking."""
        if time.time() - self.last_progress_update < self.config.progress_update_interval:
            return  # Skip update if too frequent

        try:
            progress_data = await self.redis_client.get(self.progress_key)
            progress = json.loads(progress_data) if progress_data else {}

            # Calculate metrics
            completion_percentage = await self._calculate_completion_percentage(state)
            completed_agents = len(state.get("agents_completed", []))
            failed_agents = len(state.get("agents_failed", []))
            total_agents = len(state.get("agent_dependencies", {}))

            # Update progress
            progress.update(
                {
                    "workflow_id": self.workflow_id,
                    "last_update": time.time(),
                    "completion_percentage": completion_percentage,
                    "completed_agents": completed_agents,
                    "failed_agents": failed_agents,
                    "total_agents": total_agents,
                    "current_phase": state.get("current_node", "unknown"),
                    "status": self.workflow_status.value,
                }
            )

            # Add description to history if provided
            if description:
                if "history" not in progress:
                    progress["history"] = []

                progress["history"].append(
                    {
                        "timestamp": time.time(),
                        "description": description,
                        "completion_percentage": completion_percentage,
                    }
                )

                # Keep only recent history
                progress["history"] = progress["history"][-50:]

            # Store progress
            ttl = self._calculate_ttl(self.workflow_status)
            await self.redis_client.setex(self.progress_key, ttl, json.dumps(progress))

            self.last_progress_update = time.time()

        except Exception as e:
            workflow_logger.log_progress_update_error(workflow_id=self.workflow_id, error=str(e))

    async def _calculate_completion_percentage(self, state: TripPlanningWorkflowState) -> float:
        """Calculate overall workflow completion percentage."""
        try:
            total_agents = len(state.get("agent_dependencies", {}))
            completed_agents = len(state.get("agents_completed", []))

            if total_agents == 0:
                return 0.0

            # Basic completion based on agents
            agent_completion = (completed_agents / total_agents) * 100

            # Adjust for workflow phases
            phase_multiplier = 1.0
            current_node = state.get("current_node", "") or ""

            if "complete" in current_node.lower():
                phase_multiplier = 1.0
            elif "restaurant" in current_node.lower() or "activity" in current_node.lower():
                phase_multiplier = 0.8
            elif "accommodation" in current_node.lower() or "hotel" in current_node.lower():
                phase_multiplier = 0.6
            elif "itinerary" in current_node.lower() or "flight" in current_node.lower():
                phase_multiplier = 0.4
            elif "preference" in current_node.lower():
                phase_multiplier = 0.2

            return min(agent_completion * phase_multiplier, 100.0)

        except Exception:
            return 0.0

    async def _update_performance_metrics(self, state: TripPlanningWorkflowState) -> None:
        """Update workflow performance metrics."""
        try:
            metrics = {
                "workflow_id": self.workflow_id,
                "timestamp": time.time(),
                "agents_completed": len(state.get("agents_completed", [])),
                "agents_failed": len(state.get("agents_failed", [])),
                "retry_count": state.get("retry_count", 0),
                "state_size_bytes": self.state_size_bytes,
                "operation_count": self.operation_count,
            }

            # Calculate processing time if available
            created_at_str = state.get("created_at")
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str)
                processing_time = (datetime.now(UTC) - created_at).total_seconds()
                metrics["processing_time_seconds"] = processing_time

            # Store metrics
            metrics_key = f"workflow:metrics:{self.workflow_id}"
            ttl = self._calculate_ttl(self.workflow_status)
            await self.redis_client.setex(metrics_key, ttl, json.dumps(metrics))

        except Exception as e:
            workflow_logger.warning(
                "Failed to update performance metrics",
                extra={
                    "workflow_id": self.workflow_id,
                    "error": str(e),
                },
            )

    async def get_comprehensive_progress(self) -> dict[str, Any]:
        """Get comprehensive workflow progress information."""
        try:
            # Get progress data
            progress_data = await self.redis_client.get(self.progress_key)
            progress = json.loads(progress_data) if progress_data else {}

            # Get metrics data
            metrics_key = f"workflow:metrics:{self.workflow_id}"
            metrics_data = await self.redis_client.get(metrics_key)
            metrics = json.loads(metrics_data) if metrics_data else {}

            # Get heartbeat data
            heartbeat_data = await self.redis_client.get(self.heartbeat_key)
            heartbeat = json.loads(heartbeat_data) if heartbeat_data else {}

            # Combine all progress information
            comprehensive_progress = {
                "workflow_id": self.workflow_id,
                "status": self.workflow_status.value,
                "progress": progress,
                "metrics": metrics,
                "heartbeat": heartbeat,
                "snapshots_available": await self._count_snapshots(),
                "state_size_bytes": self.state_size_bytes,
                "ttl_remaining": await self._get_remaining_ttl(),
            }

            # Calculate estimated completion time
            if progress.get("completion_percentage", 0) > 0 and metrics.get(
                "processing_time_seconds"
            ):
                elapsed_time = metrics["processing_time_seconds"]
                completion_percentage = progress["completion_percentage"]
                if completion_percentage > 0:
                    estimated_total_time = elapsed_time / (completion_percentage / 100)
                    estimated_remaining_time = estimated_total_time - elapsed_time
                    comprehensive_progress["estimated_completion_seconds"] = (
                        estimated_remaining_time
                    )

            return comprehensive_progress

        except Exception as e:
            workflow_logger.log_progress_retrieval_error(workflow_id=self.workflow_id, error=str(e))
            return {}

    # Metadata management

    async def _update_metadata(
        self, state: TripPlanningWorkflowState, checkpoint_type: CheckpointType
    ) -> None:
        """Update workflow metadata."""
        metadata = {
            "workflow_id": self.workflow_id,
            "request_id": self.request_id,
            "last_update": time.time(),
            "status": self.workflow_status.value,
            "checkpoint_type": checkpoint_type.value,
            "agents_completed": len(state.get("agents_completed", [])),
            "agents_failed": len(state.get("agents_failed", [])),
            "current_node": state.get("current_node", "unknown"),
            "retry_count": state.get("retry_count", 0),
            "state_size_bytes": self.state_size_bytes,
        }

        ttl = self._calculate_ttl(self.workflow_status)
        await self.redis_client.setex(self.metadata_key, ttl, json.dumps(metadata))

    async def get_metadata(self) -> dict[str, Any] | None:
        """Get workflow metadata."""
        try:
            metadata_data = await self.redis_client.get(self.metadata_key)
            return json.loads(metadata_data) if metadata_data else None
        except Exception as e:
            workflow_logger.log_metadata_retrieval_error(workflow_id=self.workflow_id, error=str(e))
            return None

    # Heartbeat management

    async def _start_heartbeat(self) -> None:
        """Start heartbeat tracking for the workflow."""
        heartbeat_data = {
            "workflow_id": self.workflow_id,
            "started_at": time.time(),
            "last_heartbeat": time.time(),
            "heartbeat_count": 0,
            "status": "active",
        }

        ttl = self._calculate_ttl(self.workflow_status)
        await self.redis_client.setex(self.heartbeat_key, ttl, json.dumps(heartbeat_data))

    async def _update_heartbeat(self) -> None:
        """Update workflow heartbeat."""
        if time.time() - self.last_heartbeat < self.config.heartbeat_interval:
            return

        try:
            heartbeat_data = await self.redis_client.get(self.heartbeat_key)
            heartbeat = json.loads(heartbeat_data) if heartbeat_data else {}

            heartbeat.update(
                {
                    "last_heartbeat": time.time(),
                    "heartbeat_count": heartbeat.get("heartbeat_count", 0) + 1,
                    "status": "active",
                }
            )

            ttl = self._calculate_ttl(self.workflow_status)
            await self.redis_client.setex(self.heartbeat_key, ttl, json.dumps(heartbeat))

            self.last_heartbeat = time.time()

        except Exception as e:
            workflow_logger.log_heartbeat_update_error(workflow_id=self.workflow_id, error=str(e))

    async def _stop_heartbeat(self) -> None:
        """Stop heartbeat tracking."""
        try:
            heartbeat_data = await self.redis_client.get(self.heartbeat_key)
            heartbeat = json.loads(heartbeat_data) if heartbeat_data else {}

            heartbeat.update({"stopped_at": time.time(), "status": "stopped"})

            ttl = self._calculate_ttl(self.workflow_status)
            await self.redis_client.setex(self.heartbeat_key, ttl, json.dumps(heartbeat))

        except Exception as e:
            workflow_logger.log_heartbeat_stop_error(workflow_id=self.workflow_id, error=str(e))

    # Utility methods

    def _update_workflow_status(self, state: TripPlanningWorkflowState) -> None:
        """Update workflow status based on state."""
        status_str = state.get("status", "pending")
        if status_str:
            status_str = status_str.lower()
        else:
            status_str = "pending"

        if "complete" in status_str:
            self.workflow_status = WorkflowStatus.COMPLETED
        elif "fail" in status_str or "error" in status_str:
            self.workflow_status = WorkflowStatus.FAILED
        elif "suspend" in status_str or "pause" in status_str:
            self.workflow_status = WorkflowStatus.SUSPENDED
        elif "expire" in status_str:
            self.workflow_status = WorkflowStatus.EXPIRED
        elif "active" in status_str or "running" in status_str or "process" in status_str:
            self.workflow_status = WorkflowStatus.ACTIVE
        else:
            self.workflow_status = WorkflowStatus.PENDING

    def _calculate_ttl(self, status: WorkflowStatus) -> int:
        """Calculate TTL based on workflow status."""
        ttl_map = {
            WorkflowStatus.PENDING: self.config.pending_workflow_ttl,
            WorkflowStatus.ACTIVE: self.config.active_workflow_ttl,
            WorkflowStatus.SUSPENDED: self.config.suspended_workflow_ttl,
            WorkflowStatus.COMPLETED: self.config.completed_workflow_ttl,
            WorkflowStatus.FAILED: self.config.failed_workflow_ttl,
            WorkflowStatus.EXPIRED: self.config.expired_workflow_ttl,
        }
        return ttl_map.get(status, self.config.active_workflow_ttl)

    def _json_serializer(self, obj: Any) -> Any:
        """JSON serializer for non-serializable objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        else:
            return str(obj)

    def _compress_state(self, state: dict[str, Any]) -> str:
        """Compress state data for storage."""
        import base64
        import gzip

        json_str = json.dumps(state, default=self._json_serializer)
        compressed = gzip.compress(json_str.encode())
        return base64.b64encode(compressed).decode()

    def _decompress_state(self, compressed_state: str) -> dict[str, Any]:
        """Decompress state data from storage."""
        import base64
        import gzip

        compressed = base64.b64decode(compressed_state.encode())
        json_str = gzip.decompress(compressed).decode()
        result: dict[str, Any] = json.loads(json_str)
        return result

    async def _count_snapshots(self) -> int:
        """Count available snapshots."""
        try:
            snapshots_data = await self.redis_client.get(self.snapshots_key)
            if not snapshots_data:
                return 0
            snapshots = json.loads(snapshots_data)
            return len(snapshots)
        except Exception:
            return 0

    async def _get_remaining_ttl(self) -> int:
        """Get remaining TTL for workflow state."""
        try:
            ttl = await self.redis_client.ttl(self.state_key)
            return max(ttl or 0, 0)
        except Exception:
            return 0

    # Cleanup and maintenance

    async def cleanup_expired_workflows(self, max_workflows: int = 100) -> dict[str, Any]:
        """Clean up expired workflows from Redis."""
        try:
            cleanup_stats = {"scanned": 0, "cleaned": 0, "errors": 0}

            # Get all workflow IDs from index
            index_data = await self.redis_client.get(self.index_key)
            workflow_index = json.loads(index_data) if index_data else {}

            for workflow_id in list(workflow_index.keys()):
                cleanup_stats["scanned"] += 1

                # Check if workflow should be cleaned
                metadata_key = f"workflow:metadata:{workflow_id}"
                metadata_data = await self.redis_client.get(metadata_key)

                if not metadata_data:
                    # Workflow metadata doesn't exist, clean up
                    await self._cleanup_workflow(workflow_id)
                    del workflow_index[workflow_id]
                    cleanup_stats["cleaned"] += 1
                    continue

                metadata = json.loads(metadata_data)
                status = metadata.get("status", "unknown")
                last_update = metadata.get("last_update", 0)
                current_time = time.time()

                # Determine if cleanup is needed
                should_cleanup = False

                if status == WorkflowStatus.COMPLETED.value:
                    if current_time - last_update > self.config.completed_workflow_ttl:
                        should_cleanup = True
                elif status == WorkflowStatus.FAILED.value:
                    if current_time - last_update > self.config.failed_workflow_ttl:
                        should_cleanup = True
                elif status == WorkflowStatus.EXPIRED.value:
                    if current_time - last_update > self.config.expired_workflow_retention:
                        should_cleanup = True
                elif current_time - last_update > self.config.active_workflow_ttl * 2:
                    # Cleanup stale workflows
                    should_cleanup = True

                if should_cleanup:
                    await self._cleanup_workflow(workflow_id)
                    del workflow_index[workflow_id]
                    cleanup_stats["cleaned"] += 1

            # Update workflow index
            await self.redis_client.set(self.index_key, json.dumps(workflow_index))

            workflow_logger.log_workflow_cleanup_completed(
                processed_count=cleanup_stats["scanned"],
                expired_cleaned=cleanup_stats["cleaned"],
                completed_cleaned=0,  # Placeholder
                failed_cleanups=cleanup_stats["errors"],
                cleanup_time=0,  # Placeholder
            )

            return cleanup_stats

        except Exception as e:
            workflow_logger.log_workflow_cleanup_error(error=str(e))
            return {"scanned": 0, "cleaned": 0, "errors": 1}

    async def _cleanup_workflow(self, workflow_id: str) -> None:
        """Clean up all data for a specific workflow."""
        keys_to_delete = [
            f"workflow:state:{workflow_id}",
            f"workflow:metadata:{workflow_id}",
            f"workflow:snapshots:{workflow_id}",
            f"workflow:progress:{workflow_id}",
            f"workflow:heartbeat:{workflow_id}",
            f"workflow:metrics:{workflow_id}",
            f"workflow:lock:{workflow_id}",
        ]

        for key in keys_to_delete:
            await self.redis_client.delete(key)

    # Recovery methods

    async def recover_from_failure(
        self, error_info: dict[str, Any] | None = None
    ) -> TripPlanningWorkflowState | None:
        """Attempt to recover workflow from failure."""
        try:
            # Try to restore from last good checkpoint
            snapshots = await self.list_snapshots()

            # Sort snapshots by timestamp (most recent first)
            snapshots.sort(key=lambda x: x["timestamp"], reverse=True)

            # Try to restore from non-error snapshots
            for snapshot in snapshots:
                if snapshot["checkpoint_type"] != CheckpointType.ERROR.value:
                    state = await self._restore_from_snapshot(snapshot["snapshot_id"])
                    if state:
                        # Update state with recovery information
                        state["recovered_from"] = snapshot["snapshot_id"]
                        state["recovery_timestamp"] = datetime.now(UTC).isoformat()

                        if error_info:
                            if "errors" not in state:
                                state["errors"] = []
                            state["errors"].append(error_info)

                        # Reset retry count if needed
                        state["retry_count"] = state.get("retry_count", 0) + 1

                        # Persist recovered state
                        await self.persist_state(state, CheckpointType.AUTOMATIC)

                        workflow_logger.info(
                            "Workflow recovered from failure",
                            extra={
                                "workflow_id": self.workflow_id,
                                "request_id": self.request_id,
                                "recovered_from": snapshot["snapshot_id"],
                                "retry_count": state["retry_count"],
                            },
                        )

                        return state

            return None

        except Exception as e:
            workflow_logger.error(
                "Failed to recover workflow from failure",
                extra={
                    "workflow_id": self.workflow_id,
                    "error": str(e),
                },
            )
            return None

    async def list_snapshots(self) -> list[dict[str, Any]]:
        """List all available snapshots for this workflow."""
        try:
            snapshots_data = await self.redis_client.get(self.snapshots_key)

            if not snapshots_data:
                return []

            snapshots = json.loads(snapshots_data)

            # Return metadata only (not full state data)
            return [
                {
                    "snapshot_id": snapshot["snapshot_id"],
                    "timestamp": snapshot["timestamp"],
                    "checkpoint_type": snapshot["checkpoint_type"],
                    "agents_completed": snapshot["agents_completed"],
                    "agents_failed": snapshot["agents_failed"],
                    "current_phase": snapshot["current_phase"],
                    "compressed": snapshot.get("compressed", False),
                    "age_seconds": time.time() - snapshot["timestamp"],
                }
                for snapshot in snapshots
            ]

        except Exception as e:
            workflow_logger.log_snapshot_listing_error(workflow_id=self.workflow_id, error=str(e))
            return []

    # Workflow index management

    async def _add_to_workflow_index(self) -> None:
        """Add workflow to global index for tracking."""
        try:
            index_data = await self.redis_client.get(self.index_key)
            workflow_index = json.loads(index_data) if index_data else {}

            workflow_index[self.workflow_id] = {
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "state_key": self.state_key,
                "snapshots_key": self.snapshots_key,
            }

            await self.redis_client.set(self.index_key, json.dumps(workflow_index))
        except Exception as e:
            logger.warning(f"Failed to add workflow to index: {e}")

    async def _initialize_progress_tracking(
        self, state: TripPlanningWorkflowState | dict[str, Any]
    ) -> None:
        """Initialize progress tracking structure."""
        self.progress_data = {
            "workflow_id": self.workflow_id,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "current_phase": "INITIALIZATION",
            "completion_percentage": 0.0,
            "phase_history": [],
            "checkpoints": {},
            "metrics": {
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "retry_count": 0,
            },
        }

    async def _update_progress_tracking_by_phase(
        self, phase: str, percentage: float, checkpoint: str | None = None
    ) -> None:
        """Update progress tracking data."""
        if not self.progress_data:
            await self._initialize_progress_tracking({})

        if self.progress_data:
            self.progress_data["updated_at"] = datetime.now(UTC).isoformat()
            self.progress_data["current_phase"] = phase
            self.progress_data["completion_percentage"] = percentage

            # Add to phase history
            phase_entry = {
                "phase": phase,
                "timestamp": datetime.now(UTC).isoformat(),
                "percentage": percentage,
            }
            self.progress_data["phase_history"].append(phase_entry)

            # Update checkpoint if provided
            if checkpoint:
                self.progress_data["checkpoints"][checkpoint] = {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "phase": phase,
                    "percentage": percentage,
                }

    async def _extract_metrics_from_state(self, state: TripPlanningWorkflowState) -> dict[str, Any]:
        """Extract workflow metrics from state."""
        metrics = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "retry_count": 0,
        }

        # Count tasks based on state contents
        if state.get("itinerary"):
            metrics["total_tasks"] += 1
            metrics["completed_tasks"] += 1

        if state.get("accommodations"):
            metrics["total_tasks"] += 1
            if state.get("accommodations"):
                metrics["completed_tasks"] += 1

        if state.get("restaurants"):
            metrics["total_tasks"] += 1
            if state.get("restaurants"):
                metrics["completed_tasks"] += 1

        if state.get("activities"):
            metrics["total_tasks"] += 1
            if state.get("activities"):
                metrics["completed_tasks"] += 1

        if state.get("weather_data"):
            metrics["total_tasks"] += 1
            if state.get("weather_data"):
                metrics["completed_tasks"] += 1

        # Extract retry count from errors if available
        if "errors" in state:
            metrics["retry_count"] = len(state.get("errors", []))

        return metrics

    async def get_workflow_progress(self) -> dict[str, Any] | None:
        """Get current workflow progress."""
        if self.progress_data:
            return self.progress_data

        # Try to restore from state
        restored = await self.restore_workflow_state(include_progress=True)
        if restored and restored.get("progress"):
            self.progress_data = restored["progress"]
            return self.progress_data

        return None

    async def _create_snapshot(self, state: dict[str, Any], checkpoint: str) -> None:
        """Create a state snapshot."""
        try:
            # Get existing snapshots
            snapshots_data = await self.redis_client.get(self.snapshots_key)
            snapshots = json.loads(snapshots_data) if snapshots_data else {}

            # Create snapshot entry
            snapshot_id = f"{checkpoint}_{datetime.now(UTC).timestamp()}"
            snapshots[snapshot_id] = {
                "state": state,
                "checkpoint": checkpoint,
                "created_at": datetime.now(UTC).isoformat(),
            }

            # Keep only last N snapshots
            if len(snapshots) > 10:
                # Sort by creation time and keep most recent
                sorted_snapshots = sorted(
                    snapshots.items(), key=lambda x: x[1]["created_at"], reverse=True
                )
                snapshots = dict(sorted_snapshots[:10])

            # Save snapshots
            await self.redis_client.set(
                self.snapshots_key, json.dumps(snapshots, default=str), ex=self.ttl
            )
        except Exception as e:
            logger.warning(f"Failed to create snapshot: {e}")

    async def _update_workflow_index(self) -> None:
        """Update workflow in global index."""
        try:
            index_data = await self.redis_client.get(self.index_key)
            workflow_index = json.loads(index_data) if index_data else {}

            if self.workflow_id in workflow_index:
                workflow_index[self.workflow_id]["updated_at"] = datetime.now(UTC).isoformat()
                if self.progress_data:
                    workflow_index[self.workflow_id]["completion"] = self.progress_data[
                        "completion_percentage"
                    ]
                    workflow_index[self.workflow_id]["phase"] = self.progress_data["current_phase"]

                await self.redis_client.set(self.index_key, json.dumps(workflow_index))
        except Exception as e:
            logger.warning(f"Failed to update workflow index: {e}")

    async def _persist_with_ttl(self, key: str, data: dict[str, Any], ttl: int) -> None:
        """Persist data with TTL."""
        serialized_data = json.dumps(data, default=self._json_serializer)
        await self.redis_client.setex(key, ttl, serialized_data)

    async def _get_current_ttl(self) -> int:
        """Get current TTL for workflow state."""
        ttl = await self.redis_client.ttl(self.state_key)
        return ttl if ttl is not None else 0


# Create backward compatibility alias
WorkflowStateManager = EnhancedWorkflowStateManager

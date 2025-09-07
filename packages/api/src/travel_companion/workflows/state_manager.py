"""Enhanced state persistence and management for long-running workflows."""

import json
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from ..core.redis import get_redis_manager
from ..utils.logging import workflow_logger
from .orchestrator import TripPlanningWorkflowState


class WorkflowStatus(Enum):
    """Workflow status enumeration."""
    INITIALIZED = "initialized"
    RUNNING = "running"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class CheckpointType(Enum):
    """Checkpoint type enumeration."""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    ERROR = "error"
    COMPLETION = "completion"
    SUSPENSION = "suspension"


@dataclass
class StateSnapshot:
    """Represents a point-in-time snapshot of workflow state."""

    workflow_id: str
    timestamp: float
    snapshot_id: str
    state_data: dict[str, Any]
    checkpoint_type: str
    agents_completed: list[str]
    agents_failed: list[str]
    current_phase: str
    description: str | None = None

    @property
    def age_seconds(self) -> float:
        """Get age of snapshot in seconds."""
        return time.time() - self.timestamp


@dataclass
class WorkflowPersistenceConfig:
    """Configuration for workflow state persistence."""

    # TTL settings (in seconds)
    active_workflow_ttl: int = 86400  # 24 hours
    completed_workflow_ttl: int = 604800  # 7 days
    failed_workflow_ttl: int = 259200  # 3 days
    cancelled_workflow_ttl: int = 86400  # 24 hours

    # Checkpoint settings
    automatic_checkpoint_interval: int = 300  # 5 minutes
    max_snapshots_per_workflow: int = 50
    snapshot_cleanup_threshold: int = 100  # Clean when exceeding this count

    # Progress tracking
    progress_update_interval: int = 60  # 1 minute
    heartbeat_interval: int = 30  # 30 seconds

    # Cleanup settings
    cleanup_batch_size: int = 100
    expired_workflow_retention: int = 3600  # 1 hour grace period before deletion


class EnhancedWorkflowStateManager:
    """
    Enhanced state manager for long-running workflows with comprehensive Redis persistence.
    
    Task 6 Features:
    1. Redis-based workflow state storage with configurable TTL
    2. Advanced checkpoint and resume functionality with versioning
    3. Real-time progress tracking for long-running operations
    4. Automated state cleanup for completed and expired workflows
    """

    def __init__(
        self,
        workflow_id: str,
        config: WorkflowPersistenceConfig | None = None,
        enable_heartbeat: bool = True
    ):
        """
        Initialize enhanced state manager.
        
        Args:
            workflow_id: Unique workflow identifier
            config: Persistence configuration
            enable_heartbeat: Enable heartbeat for long-running workflows
        """
        self.workflow_id = workflow_id
        self.config = config or WorkflowPersistenceConfig()
        self.enable_heartbeat = enable_heartbeat
        self.redis_client = get_redis_manager().client

        # Redis key patterns with enhanced structure
        self.state_key = f"workflow:state:{workflow_id}"
        self.metadata_key = f"workflow:metadata:{workflow_id}"
        self.snapshots_key = f"workflow:snapshots:{workflow_id}"
        self.progress_key = f"workflow:progress:{workflow_id}"
        self.heartbeat_key = f"workflow:heartbeat:{workflow_id}"
        self.lock_key = f"workflow:lock:{workflow_id}"
        self.index_key = "workflow:index"  # Global workflow index

        # State management
        self.current_state: TripPlanningWorkflowState | None = None
        self.workflow_status: WorkflowStatus = WorkflowStatus.INITIALIZED
        self.last_checkpoint_time: float = 0
        self.last_progress_update: float = 0
        self.last_heartbeat: float = 0
        self._cleanup_tasks: set[str] = set()

    async def initialize_workflow(
        self,
        initial_state: TripPlanningWorkflowState,
        estimated_duration_minutes: int | None = None
    ) -> bool:
        """
        Initialize workflow with enhanced tracking and TTL management.
        
        Args:
            initial_state: Initial workflow state
            estimated_duration_minutes: Expected workflow duration
            
        Returns:
            True if initialization was successful
        """
        try:
            async with self._workflow_lock():
                # Set workflow status
                self.workflow_status = WorkflowStatus.RUNNING
                self.current_state = initial_state

                # Calculate TTL based on workflow type
                ttl = self._calculate_ttl(self.workflow_status, estimated_duration_minutes)

                # Persist initial state
                await self._persist_with_ttl(self.state_key, initial_state, ttl)

                # Create workflow metadata
                metadata = {
                    "workflow_id": self.workflow_id,
                    "status": self.workflow_status.value,
                    "created_at": time.time(),
                    "last_update": time.time(),
                    "estimated_duration_minutes": estimated_duration_minutes,
                    "ttl_seconds": ttl,
                    "checkpoint_count": 0,
                    "progress_percentage": 0.0,
                    "heartbeat_enabled": self.enable_heartbeat
                }

                await self._persist_with_ttl(self.metadata_key, metadata, ttl)

                # Add to global workflow index
                await self._add_to_workflow_index()

                # Initialize progress tracking
                await self._initialize_progress_tracking(initial_state)

                # Start heartbeat if enabled
                if self.enable_heartbeat:
                    await self._start_heartbeat()

                # Create initial checkpoint
                await self._create_enhanced_checkpoint(
                    initial_state,
                    CheckpointType.AUTOMATIC,
                    "Workflow initialized"
                )

                workflow_logger.log_workflow_initialized(
                    workflow_id=self.workflow_id,
                    request_id=initial_state.get("request_id", "unknown"),
                    ttl_seconds=ttl,
                    estimated_duration_minutes=estimated_duration_minutes
                )

                return True

        except Exception as e:
            workflow_logger.log_workflow_initialization_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )
            return False

    async def persist_state_with_progress(
        self,
        state: TripPlanningWorkflowState,
        checkpoint_type: CheckpointType = CheckpointType.AUTOMATIC,
        progress_description: str | None = None
    ) -> bool:
        """
        Enhanced state persistence with progress tracking and dynamic TTL.
        
        Args:
            state: Current workflow state
            checkpoint_type: Type of checkpoint
            progress_description: Description of current progress
            
        Returns:
            True if persistence was successful
        """
        start_time = time.time()

        try:
            async with self._workflow_lock():
                self.current_state = state

                # Update TTL based on current status
                current_ttl = await self._get_current_ttl()
                if self.workflow_status == WorkflowStatus.RUNNING and current_ttl < 3600:
                    # Extend TTL for active workflows
                    new_ttl = self._calculate_ttl(self.workflow_status)
                    await self.redis_client.expire(self.state_key, new_ttl)

                # Persist state with appropriate TTL
                ttl = self._calculate_ttl(self.workflow_status)
                await self._persist_with_ttl(self.state_key, state, ttl)

                # Update progress tracking
                await self._update_progress_tracking(state, progress_description)

                # Create checkpoint if needed
                should_checkpoint = (
                    checkpoint_type != CheckpointType.AUTOMATIC or
                    time.time() - self.last_checkpoint_time > self.config.automatic_checkpoint_interval
                )

                if should_checkpoint:
                    await self._create_enhanced_checkpoint(state, checkpoint_type, progress_description)
                    self.last_checkpoint_time = time.time()

                # Update metadata
                await self._update_enhanced_metadata(state, checkpoint_type)

                # Update heartbeat
                if self.enable_heartbeat:
                    await self._update_heartbeat()

                persistence_time_ms = (time.time() - start_time) * 1000

                workflow_logger.log_enhanced_state_persisted(
                    workflow_id=self.workflow_id,
                    request_id=state.get("request_id", "unknown"),
                    persistence_time_ms=persistence_time_ms,
                    checkpoint_type=checkpoint_type.value,
                    state_size_bytes=len(json.dumps(state, default=self._json_serializer)),
                    progress_description=progress_description
                )

                return True

        except Exception as e:
            workflow_logger.log_state_persistence_error(
                workflow_id=self.workflow_id,
                request_id=state.get("request_id", "unknown") if state else "unknown",
                error=str(e),
                checkpoint_type=checkpoint_type.value
            )
            return False

    async def restore_workflow_state(
        self,
        snapshot_id: str | None = None,
        include_progress: bool = True
    ) -> dict[str, Any] | None:
        """
        Enhanced state restoration with progress information.
        
        Args:
            snapshot_id: Optional specific snapshot to restore
            include_progress: Include progress tracking information
            
        Returns:
            Dictionary containing restored state and metadata
        """
        start_time = time.time()

        try:
            if snapshot_id:
                # Restore from specific snapshot
                restored_data = await self._restore_from_enhanced_snapshot(snapshot_id)
            else:
                # Restore from current state
                state_data = await self.redis_client.get(self.state_key)
                if not state_data:
                    return None

                restored_data = {
                    "state": json.loads(state_data),
                    "snapshot_id": "current",
                    "restoration_type": "current_state"
                }

            if not restored_data:
                return None

            self.current_state = restored_data["state"]

            # Restore metadata and progress if requested
            result = {
                "workflow_id": self.workflow_id,
                "state": restored_data["state"],
                "snapshot_id": restored_data.get("snapshot_id"),
                "restoration_type": restored_data.get("restoration_type", "snapshot"),
                "restoration_time_ms": (time.time() - start_time) * 1000
            }

            if include_progress:
                progress_info = await self._get_enhanced_progress_info()
                result["progress"] = progress_info

                metadata_info = await self._get_enhanced_metadata()
                result["metadata"] = metadata_info

            workflow_logger.log_enhanced_state_restored(
                workflow_id=self.workflow_id,
                request_id=restored_data["state"].get("request_id", "unknown"),
                restoration_time_ms=result["restoration_time_ms"],
                snapshot_id=snapshot_id,
                include_progress=include_progress
            )

            return result

        except Exception as e:
            workflow_logger.log_snapshot_restoration_error(
                workflow_id=self.workflow_id,
                error=str(e),
                snapshot_id=snapshot_id or "current"
            )
            return None

    async def suspend_workflow(self, reason: str = "") -> bool:
        """
        Suspend workflow with state preservation and TTL extension.
        
        Args:
            reason: Reason for suspension
            
        Returns:
            True if suspension was successful
        """
        try:
            async with self._workflow_lock():
                if not self.current_state:
                    return False

                # Update status
                self.workflow_status = WorkflowStatus.SUSPENDED

                # Create suspension checkpoint
                await self._create_enhanced_checkpoint(
                    self.current_state,
                    CheckpointType.SUSPENSION,
                    f"Workflow suspended: {reason}"
                )

                # Extend TTL for suspended workflow
                suspended_ttl = self.config.completed_workflow_ttl  # Extended retention
                await self.redis_client.expire(self.state_key, suspended_ttl)
                await self.redis_client.expire(self.metadata_key, suspended_ttl)

                # Update metadata
                await self._update_enhanced_metadata(self.current_state, CheckpointType.SUSPENSION)

                # Stop heartbeat for suspended workflow
                if self.enable_heartbeat:
                    await self._stop_heartbeat()

                workflow_logger.log_workflow_suspended(
                    workflow_id=self.workflow_id,
                    request_id=self.current_state.get("request_id", "unknown"),
                    reason=reason,
                    suspended_ttl=suspended_ttl
                )

                return True

        except Exception as e:
            workflow_logger.log_workflow_suspension_error(
                workflow_id=self.workflow_id,
                error=str(e),
                reason=reason
            )
            return False

    async def resume_workflow(self, snapshot_id: str | None = None) -> dict[str, Any] | None:
        """
        Resume suspended workflow from checkpoint.
        
        Args:
            snapshot_id: Optional specific snapshot to resume from
            
        Returns:
            Restored workflow state and metadata
        """
        try:
            # Restore state
            restored_data = await self.restore_workflow_state(snapshot_id, include_progress=True)

            if not restored_data:
                return None

            async with self._workflow_lock():
                # Update status to running
                self.workflow_status = WorkflowStatus.RUNNING

                # Reset TTL for active workflow
                active_ttl = self._calculate_ttl(self.workflow_status)
                await self.redis_client.expire(self.state_key, active_ttl)
                await self.redis_client.expire(self.metadata_key, active_ttl)

                # Restart heartbeat
                if self.enable_heartbeat:
                    await self._start_heartbeat()

                # Create resume checkpoint
                await self._create_enhanced_checkpoint(
                    self.current_state,
                    CheckpointType.AUTOMATIC,
                    f"Workflow resumed from {snapshot_id or 'current state'}"
                )

                workflow_logger.log_workflow_resumed(
                    workflow_id=self.workflow_id,
                    request_id=self.current_state.get("request_id", "unknown"),
                    snapshot_id=snapshot_id,
                    active_ttl=active_ttl
                )

                return restored_data

        except Exception as e:
            workflow_logger.log_workflow_resume_error(
                workflow_id=self.workflow_id,
                error=str(e),
                snapshot_id=snapshot_id
            )
            return None

    async def complete_workflow(
        self,
        final_state: TripPlanningWorkflowState,
        completion_summary: str | None = None
    ) -> bool:
        """
        Complete workflow with final state persistence and TTL adjustment.
        
        Args:
            final_state: Final workflow state
            completion_summary: Optional completion summary
            
        Returns:
            True if completion was successful
        """
        try:
            async with self._workflow_lock():
                self.workflow_status = WorkflowStatus.COMPLETED
                self.current_state = final_state

                # Persist final state with completed TTL
                completed_ttl = self.config.completed_workflow_ttl
                await self._persist_with_ttl(self.state_key, final_state, completed_ttl)

                # Create completion checkpoint
                await self._create_enhanced_checkpoint(
                    final_state,
                    CheckpointType.COMPLETION,
                    completion_summary or "Workflow completed successfully"
                )

                # Update final metadata
                await self._update_enhanced_metadata(final_state, CheckpointType.COMPLETION)

                # Final progress update
                await self._finalize_progress_tracking()

                # Stop heartbeat
                if self.enable_heartbeat:
                    await self._stop_heartbeat()

                # Schedule cleanup of temporary data
                await self._schedule_cleanup_after_completion()

                workflow_logger.log_workflow_completed(
                    workflow_id=self.workflow_id,
                    request_id=final_state.get("request_id", "unknown"),
                    completion_summary=completion_summary,
                    completed_ttl=completed_ttl
                )

                return True

        except Exception as e:
            workflow_logger.log_workflow_completion_error(
                workflow_id=self.workflow_id,
                error=str(e),
                completion_summary=completion_summary
            )
            return False

    async def get_comprehensive_progress(self) -> dict[str, Any]:
        """
        Get comprehensive workflow progress with enhanced tracking.
        
        Returns:
            Detailed progress information including metrics and predictions
        """
        try:
            # Get basic progress
            progress_data = await self.redis_client.get(self.progress_key)
            progress = json.loads(progress_data) if progress_data else {}

            # Get metadata
            metadata_data = await self.redis_client.get(self.metadata_key)
            metadata = json.loads(metadata_data) if metadata_data else {}

            # Get heartbeat info
            heartbeat_data = await self.redis_client.get(self.heartbeat_key)
            heartbeat = json.loads(heartbeat_data) if heartbeat_data else {}

            # Calculate enhanced metrics
            current_time = time.time()
            start_time = metadata.get("created_at", current_time)
            elapsed_time = current_time - start_time

            if self.current_state:
                total_agents = len(self.current_state.get("agent_dependencies", {})) + 3
                completed_agents = len(self.current_state.get("agents_completed", []))
                failed_agents = len(self.current_state.get("agents_failed", []))

                progress_percentage = (completed_agents / total_agents * 100) if total_agents > 0 else 0

                # Estimate completion time
                estimated_completion = self._estimate_enhanced_completion_time(
                    elapsed_time, completed_agents, total_agents
                )

                return {
                    "workflow_id": self.workflow_id,
                    "status": self.workflow_status.value,
                    "current_node": self.current_state.get("current_node", "unknown"),
                    "progress_percentage": progress_percentage,
                    "agents_completed": completed_agents,
                    "agents_failed": failed_agents,
                    "total_agents": total_agents,
                    "elapsed_time_seconds": elapsed_time,
                    "estimated_completion_time": estimated_completion,
                    "last_update": metadata.get("last_update", 0),
                    "heartbeat": heartbeat,
                    "checkpoint_count": metadata.get("checkpoint_count", 0),
                    "ttl_remaining": await self._get_current_ttl(),
                    "detailed_progress": progress,
                    "performance_metrics": await self._calculate_performance_metrics()
                }

            return {
                "workflow_id": self.workflow_id,
                "status": "not_found",
                "error": "No current state available"
            }

        except Exception as e:
            return {
                "workflow_id": self.workflow_id,
                "status": "error",
                "error": str(e)
            }

    async def cleanup_old_snapshots(self, max_age_hours: int = 168) -> int:
        """
        Clean up old snapshots to manage storage.
        
        Args:
            max_age_hours: Maximum age for snapshots in hours (default 7 days)
            
        Returns:
            Number of snapshots cleaned up
        """
        try:
            snapshots_data = await self.redis_client.get(self.snapshots_key)

            if not snapshots_data:
                return 0

            snapshots = json.loads(snapshots_data)
            max_age_seconds = max_age_hours * 3600
            current_time = time.time()

            # Filter out old snapshots, but keep at least the 5 most recent
            snapshots.sort(key=lambda x: x["timestamp"], reverse=True)

            recent_snapshots = snapshots[:5]  # Keep 5 most recent
            remaining_snapshots = snapshots[5:]

            # Filter remaining by age
            valid_snapshots = recent_snapshots + [
                snapshot for snapshot in remaining_snapshots
                if current_time - snapshot["timestamp"] < max_age_seconds
            ]

            cleaned_count = len(snapshots) - len(valid_snapshots)

            if cleaned_count > 0:
                # Store updated snapshots
                await self.redis_client.setex(
                    self.snapshots_key,
                    self._calculate_ttl(self.workflow_status),
                    json.dumps(valid_snapshots, default=self._json_serializer)
                )

                workflow_logger.log_snapshots_cleaned(
                    workflow_id=self.workflow_id,
                    cleaned_count=cleaned_count,
                    remaining_count=len(valid_snapshots)
                )

            return cleaned_count

        except Exception as e:
            workflow_logger.log_snapshot_cleanup_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )
            return 0

    async def cleanup_expired_workflows(self, max_workflows: int = 100) -> dict[str, Any]:
        """
        Comprehensive cleanup of expired and completed workflows.
        
        Args:
            max_workflows: Maximum number of workflows to process in one batch
            
        Returns:
            Cleanup summary with counts and results
        """
        try:
            cleanup_start = time.time()

            # Get workflow index
            index_data = await self.redis_client.get(self.index_key)
            if not index_data:
                return {"cleaned": 0, "error": "No workflow index found"}

            workflow_index = json.loads(index_data)

            cleanup_summary = {
                "total_workflows_processed": 0,
                "expired_workflows_cleaned": 0,
                "completed_workflows_cleaned": 0,
                "failed_cleanups": 0,
                "cleanup_time_seconds": 0,
                "errors": []
            }

            processed_count = 0

            for workflow_id in list(workflow_index.keys())[:max_workflows]:
                if processed_count >= max_workflows:
                    break

                try:
                    cleaned = await self._cleanup_single_workflow(workflow_id)

                    if cleaned["cleaned"]:
                        if cleaned["reason"] == "expired":
                            cleanup_summary["expired_workflows_cleaned"] += 1
                        elif cleaned["reason"] == "completed":
                            cleanup_summary["completed_workflows_cleaned"] += 1

                        # Remove from index
                        del workflow_index[workflow_id]

                    processed_count += 1
                    cleanup_summary["total_workflows_processed"] += 1

                except Exception as e:
                    cleanup_summary["failed_cleanups"] += 1
                    cleanup_summary["errors"].append(f"Failed to cleanup {workflow_id}: {str(e)}")

            # Update workflow index
            await self.redis_client.set(self.index_key, json.dumps(workflow_index))

            cleanup_summary["cleanup_time_seconds"] = time.time() - cleanup_start

            workflow_logger.log_workflow_cleanup_completed(
                processed_count=cleanup_summary["total_workflows_processed"],
                expired_cleaned=cleanup_summary["expired_workflows_cleaned"],
                completed_cleaned=cleanup_summary["completed_workflows_cleaned"],
                failed_cleanups=cleanup_summary["failed_cleanups"],
                cleanup_time=cleanup_summary["cleanup_time_seconds"]
            )

            return cleanup_summary

        except Exception as e:
            error_msg = f"Workflow cleanup failed: {str(e)}"
            workflow_logger.log_workflow_cleanup_error(error=error_msg)
            return {
                "total_workflows_processed": 0,
                "expired_workflows_cleaned": 0,
                "completed_workflows_cleaned": 0,
                "failed_cleanups": 1,
                "cleanup_time_seconds": 0,
                "errors": [error_msg]
            }

    async def _create_enhanced_checkpoint(
        self,
        state: TripPlanningWorkflowState,
        checkpoint_type: CheckpointType,
        description: str = ""
    ) -> str:
        """Create an enhanced checkpoint with comprehensive metadata."""
        snapshot_id = f"{checkpoint_type.value}_{int(time.time())}"

        snapshot = StateSnapshot(
            workflow_id=self.workflow_id,
            timestamp=time.time(),
            snapshot_id=snapshot_id,
            state_data=state,
            checkpoint_type=checkpoint_type.value,
            agents_completed=state.get("agents_completed", []),
            agents_failed=state.get("agents_failed", []),
            current_phase=state.get("current_node", "unknown"),
            description=description
        )

        await self._store_enhanced_snapshot(snapshot)

        workflow_logger.log_enhanced_checkpoint_created(
            workflow_id=self.workflow_id,
            request_id=state.get("request_id", "unknown"),
            snapshot_id=snapshot_id,
            checkpoint_type=checkpoint_type.value,
            description=description
        )

        return snapshot_id

    async def _store_enhanced_snapshot(self, snapshot: StateSnapshot) -> None:
        """Store enhanced snapshot with metadata and cleanup management."""
        try:
            snapshots_data = await self.redis_client.get(self.snapshots_key)
            snapshots = json.loads(snapshots_data) if snapshots_data else []

            snapshot_dict = {
                "snapshot_id": snapshot.snapshot_id,
                "timestamp": snapshot.timestamp,
                "checkpoint_type": snapshot.checkpoint_type,
                "agents_completed": snapshot.agents_completed,
                "agents_failed": snapshot.agents_failed,
                "current_phase": snapshot.current_phase,
                "state_data": snapshot.state_data,
                "description": snapshot.description or ""
            }

            snapshots.append(snapshot_dict)

            # Enhanced cleanup logic
            if len(snapshots) > self.config.max_snapshots_per_workflow:
                # Keep important snapshots (manual, completion, error) and most recent
                important_snapshots = [
                    s for s in snapshots
                    if s["checkpoint_type"] in ["manual", "completion", "error"]
                ]

                recent_snapshots = sorted(snapshots, key=lambda x: x["timestamp"], reverse=True)
                recent_snapshots = recent_snapshots[:self.config.max_snapshots_per_workflow // 2]

                # Combine and deduplicate
                combined_snapshots = important_snapshots + [
                    s for s in recent_snapshots
                    if s not in important_snapshots
                ]

                snapshots = combined_snapshots[-self.config.max_snapshots_per_workflow:]

            ttl = self._calculate_ttl(self.workflow_status)
            await self._persist_with_ttl(self.snapshots_key, snapshots, ttl)

        except Exception as e:
            workflow_logger.log_snapshot_storage_error(
                workflow_id=self.workflow_id,
                snapshot_id=snapshot.snapshot_id,
                error=str(e)
            )

    async def _restore_from_enhanced_snapshot(self, snapshot_id: str) -> TripPlanningWorkflowState | None:
        """Restore state from a specific snapshot."""
        try:
            snapshots_data = await self.redis_client.get(self.snapshots_key)

            if not snapshots_data:
                return None

            snapshots = json.loads(snapshots_data)

            # Find the requested snapshot
            for snapshot in snapshots:
                if snapshot["snapshot_id"] == snapshot_id:
                    return snapshot["state_data"]

            return None

        except Exception as e:
            workflow_logger.log_snapshot_restoration_error(
                workflow_id=self.workflow_id,
                snapshot_id=snapshot_id,
                error=str(e)
            )
            return None

    async def _update_enhanced_metadata(self, state: TripPlanningWorkflowState, checkpoint_type: CheckpointType) -> None:
        """Update workflow metadata."""
        metadata = {
            "workflow_id": self.workflow_id,
            "last_update": time.time(),
            "checkpoint_type": checkpoint_type.value,
            "status": state.get("status", "unknown"),
            "current_node": state.get("current_node", "unknown"),
            "agents_completed_count": len(state.get("agents_completed", [])),
            "agents_failed_count": len(state.get("agents_failed", [])),
        }

        await self.redis_client.setex(
            self.metadata_key,
            self._calculate_ttl(self.workflow_status),
            json.dumps(metadata, default=self._json_serializer)
        )

    def _workflow_lock(self):
        """Enhanced context manager for workflow-level locking with timeout."""
        class WorkflowLock:
            def __init__(self, redis_client, lock_key, timeout=30):
                self.redis_client = redis_client
                self.lock_key = lock_key
                self.timeout = timeout
                self.acquired = False

            async def __aenter__(self):
                import asyncio
                # Try to acquire lock with timeout
                for _ in range(self.timeout):
                    if await self.redis_client.set(self.lock_key, "locked", ex=60, nx=True):
                        self.acquired = True
                        return self
                    await asyncio.sleep(1)

                raise TimeoutError(f"Could not acquire workflow lock for {self.lock_key}")

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self.acquired:
                    await self.redis_client.delete(self.lock_key)

        return WorkflowLock(self.redis_client, self.lock_key)

    def _json_serializer(self, obj):
        """Enhanced JSON serializer."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, WorkflowStatus):
            return obj.value
        elif isinstance(obj, CheckpointType):
            return obj.value
        elif hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

    def _estimate_completion_time(self) -> float | None:
        """Estimate workflow completion time based on progress."""
        if not self.current_state:
            return None

        start_time = self.current_state.get("start_time")
        if not start_time:
            return None

        completed_agents = len(self.current_state.get("agents_completed", []))
        total_agents = len(self.current_state.get("agent_dependencies", {})) + 3

        if completed_agents == 0:
            return None

        elapsed_time = time.time() - start_time
        estimated_total_time = (elapsed_time / completed_agents) * total_agents

        return start_time + estimated_total_time

    async def _calculate_performance_metrics(self) -> dict[str, Any]:
        """Calculate performance metrics based on progress."""
        if not self.current_state:
            return {}

        progress_data = await self.redis_client.get(self.progress_key)
        progress = json.loads(progress_data) if progress_data else {}

        metrics = {
            "average_step_time": progress.get("average_step_time", 0),
            "fastest_step_time": progress.get("fastest_step_time", 0),
            "slowest_step_time": progress.get("slowest_step_time", 0),
            "total_processing_time": progress.get("total_processing_time", 0)
        }

        return metrics

    async def _finalize_progress_tracking(self) -> None:
        """Finalize progress tracking for the workflow."""
        try:
            progress_data = await self.redis_client.get(self.progress_key)
            progress = json.loads(progress_data) if progress_data else {}

            current_time = time.time()
            completed_agents = len(self.current_state.get("agents_completed", []))

            # Update progress
            progress.update({
                "last_update": current_time,
                "completed_steps": completed_agents,
                "current_step": self.current_state.get("current_node", "unknown"),
                "progress_percentage": (completed_agents / progress.get("total_steps", 1)) * 100
            })

            ttl = self._calculate_ttl(self.workflow_status)
            await self._persist_with_ttl(self.progress_key, progress, ttl)

        except Exception as e:
            workflow_logger.log_progress_update_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )

    async def _start_heartbeat(self) -> None:
        """Start heartbeat tracking for long-running workflows."""
        heartbeat_data = {
            "workflow_id": self.workflow_id,
            "started_at": time.time(),
            "last_heartbeat": time.time(),
            "heartbeat_count": 0,
            "status": "active"
        }

        ttl = self._calculate_ttl(self.workflow_status)
        await self._persist_with_ttl(self.heartbeat_key, heartbeat_data, ttl)

    async def _update_heartbeat(self) -> None:
        """Update heartbeat information."""
        if time.time() - self.last_heartbeat < self.config.heartbeat_interval:
            return

        try:
            heartbeat_data = await self.redis_client.get(self.heartbeat_key)
            heartbeat = json.loads(heartbeat_data) if heartbeat_data else {}

            heartbeat.update({
                "last_heartbeat": time.time(),
                "heartbeat_count": heartbeat.get("heartbeat_count", 0) + 1,
                "status": "active"
            })

            ttl = self._calculate_ttl(self.workflow_status)
            await self._persist_with_ttl(self.heartbeat_key, heartbeat, ttl)

            self.last_heartbeat = time.time()

        except Exception as e:
            workflow_logger.log_heartbeat_update_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )

    async def _stop_heartbeat(self) -> None:
        """Stop heartbeat for completed/suspended workflows."""
        try:
            heartbeat_data = await self.redis_client.get(self.heartbeat_key)
            heartbeat = json.loads(heartbeat_data) if heartbeat_data else {}

            heartbeat.update({
                "stopped_at": time.time(),
                "status": "stopped"
            })

            ttl = self._calculate_ttl(self.workflow_status)
            await self._persist_with_ttl(self.heartbeat_key, heartbeat, ttl)

        except Exception as e:
            workflow_logger.log_heartbeat_stop_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )

    async def _add_to_workflow_index(self) -> None:
        """Add workflow to global index for tracking."""
        try:
            index_data = await self.redis_client.get(self.index_key)
            workflow_index = json.loads(index_data) if index_data else {}

            workflow_index[self.workflow_id] = {
                "created_at": time.time(),
                "status": self.workflow_status.value,
                "last_update": time.time()
            }

            await self.redis_client.set(self.index_key, json.dumps(workflow_index))

        except Exception as e:
            workflow_logger.log_workflow_index_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )

    async def _initialize_progress_tracking(self, state: TripPlanningWorkflowState) -> None:
        """Initialize progress tracking for the workflow."""
        progress_data = {
            "workflow_id": self.workflow_id,
            "initialized_at": time.time(),
            "total_steps": len(state.get("agent_dependencies", {})) + 3,
            "completed_steps": 0,
            "current_step": "initialization",
            "step_history": [],
            "performance_metrics": {
                "average_step_time": 0,
                "fastest_step_time": 0,
                "slowest_step_time": 0,
                "total_processing_time": 0
            }
        }

        ttl = self._calculate_ttl(self.workflow_status)
        await self._persist_with_ttl(self.progress_key, progress_data, ttl)

    async def _update_progress_tracking(
        self,
        state: TripPlanningWorkflowState,
        description: str | None = None
    ) -> None:
        """Update progress tracking information."""
        if time.time() - self.last_progress_update < self.config.progress_update_interval:
            return  # Skip update if too frequent

        try:
            progress_data = await self.redis_client.get(self.progress_key)
            progress = json.loads(progress_data) if progress_data else {}

            current_time = time.time()
            completed_agents = len(state.get("agents_completed", []))

            # Update progress
            progress.update({
                "last_update": current_time,
                "completed_steps": completed_agents,
                "current_step": state.get("current_node", "unknown"),
                "progress_percentage": (completed_agents / progress.get("total_steps", 1)) * 100
            })

            if description:
                progress["step_history"].append({
                    "timestamp": current_time,
                    "step": state.get("current_node", "unknown"),
                    "description": description
                })

                # Keep only recent history
                progress["step_history"] = progress["step_history"][-20:]

            ttl = self._calculate_ttl(self.workflow_status)
            await self._persist_with_ttl(self.progress_key, progress, ttl)

            self.last_progress_update = current_time

        except Exception as e:
            workflow_logger.log_progress_update_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )

    async def _create_snapshot(self, state: TripPlanningWorkflowState, checkpoint_type: str) -> None:
        """Create a state snapshot."""
        snapshot_id = f"{checkpoint_type}_{int(time.time())}"

        snapshot = StateSnapshot(
            workflow_id=self.workflow_id,
            timestamp=time.time(),
            snapshot_id=snapshot_id,
            state_data=state,
            checkpoint_type=checkpoint_type,
            agents_completed=state.get("agents_completed", []),
            agents_failed=state.get("agents_failed", []),
            current_phase=state.get("current_node", "unknown")
        )

        await self._store_snapshot(snapshot)

    async def _store_snapshot(self, snapshot: StateSnapshot, description: str = "") -> None:
        """Store a snapshot in Redis."""
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
                "description": description
            }

            snapshots.append(snapshot_dict)

            # Keep only the most recent 20 snapshots
            snapshots.sort(key=lambda x: x["timestamp"], reverse=True)
            snapshots = snapshots[:20]

            # Store updated snapshots
            await self.redis_client.setex(
                self.snapshots_key,
                self._calculate_ttl(self.workflow_status),
                json.dumps(snapshots, default=self._json_serializer)
            )

        except Exception as e:
            workflow_logger.log_snapshot_storage_error(
                workflow_id=self.workflow_id,
                snapshot_id=snapshot.snapshot_id,
                error=str(e)
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
                    return snapshot["state_data"]

            return None

        except Exception as e:
            workflow_logger.log_snapshot_restoration_error(
                workflow_id=self.workflow_id,
                snapshot_id=snapshot_id,
                error=str(e)
            )
            return None

    async def _update_metadata(self, state: TripPlanningWorkflowState, checkpoint_type: str) -> None:
        """Update workflow metadata."""
        metadata = {
            "workflow_id": self.workflow_id,
            "last_update": time.time(),
            "checkpoint_type": checkpoint_type,
            "status": state.get("status", "unknown"),
            "current_node": state.get("current_node", "unknown"),
            "agents_completed_count": len(state.get("agents_completed", [])),
            "agents_failed_count": len(state.get("agents_failed", [])),
        }

        await self.redis_client.setex(
            self.metadata_key,
            self._calculate_ttl(self.workflow_status),
            json.dumps(metadata, default=self._json_serializer)
        )

    def _calculate_ttl(
        self,
        status: WorkflowStatus,
        estimated_duration_minutes: int | None = None
    ) -> int:
        """Calculate appropriate TTL based on workflow status and duration."""
        if status == WorkflowStatus.RUNNING:
            # For active workflows, use estimated duration + buffer
            if estimated_duration_minutes:
                return max(
                    estimated_duration_minutes * 60 * 2,  # 2x estimated duration
                    self.config.active_workflow_ttl
                )
            return self.config.active_workflow_ttl

        elif status == WorkflowStatus.COMPLETED:
            return self.config.completed_workflow_ttl

        elif status == WorkflowStatus.FAILED:
            return self.config.failed_workflow_ttl

        elif status == WorkflowStatus.CANCELLED:
            return self.config.cancelled_workflow_ttl

        else:
            return self.config.active_workflow_ttl

    async def _persist_with_ttl(self, key: str, data: Any, ttl: int) -> None:
        """Persist data with TTL."""
        serialized_data = json.dumps(data, default=self._json_serializer)
        await self.redis_client.setex(key, ttl, serialized_data)

    async def _get_current_ttl(self) -> int:
        """Get current TTL for workflow state."""
        return await self.redis_client.ttl(self.state_key)

    async def _add_to_workflow_index(self) -> None:
        """Add workflow to global index for tracking."""
        try:
            index_data = await self.redis_client.get(self.index_key)
            workflow_index = json.loads(index_data) if index_data else {}

            workflow_index[self.workflow_id] = {
                "created_at": time.time(),
                "status": self.workflow_status.value,
                "last_update": time.time()
            }

            await self.redis_client.set(self.index_key, json.dumps(workflow_index))

        except Exception as e:
            workflow_logger.log_workflow_index_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )

    async def _initialize_progress_tracking(self, state: TripPlanningWorkflowState) -> None:
        """Initialize progress tracking for the workflow."""
        progress_data = {
            "workflow_id": self.workflow_id,
            "initialized_at": time.time(),
            "total_steps": len(state.get("agent_dependencies", {})) + 3,
            "completed_steps": 0,
            "current_step": "initialization",
            "step_history": [],
            "performance_metrics": {
                "average_step_time": 0,
                "fastest_step_time": 0,
                "slowest_step_time": 0,
                "total_processing_time": 0
            }
        }

        ttl = self._calculate_ttl(self.workflow_status)
        await self._persist_with_ttl(self.progress_key, progress_data, ttl)

    async def _update_progress_tracking(
        self,
        state: TripPlanningWorkflowState,
        description: str | None = None
    ) -> None:
        """Update progress tracking information."""
        if time.time() - self.last_progress_update < self.config.progress_update_interval:
            return  # Skip update if too frequent

        try:
            progress_data = await self.redis_client.get(self.progress_key)
            progress = json.loads(progress_data) if progress_data else {}

            current_time = time.time()
            completed_agents = len(state.get("agents_completed", []))

            # Update progress
            progress.update({
                "last_update": current_time,
                "completed_steps": completed_agents,
                "current_step": state.get("current_node", "unknown"),
                "progress_percentage": (completed_agents / progress.get("total_steps", 1)) * 100
            })

            if description:
                progress["step_history"].append({
                    "timestamp": current_time,
                    "step": state.get("current_node", "unknown"),
                    "description": description
                })

                # Keep only recent history
                progress["step_history"] = progress["step_history"][-20:]

            ttl = self._calculate_ttl(self.workflow_status)
            await self._persist_with_ttl(self.progress_key, progress, ttl)

            self.last_progress_update = current_time

        except Exception as e:
            workflow_logger.log_progress_update_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )

    async def _start_heartbeat(self) -> None:
        """Start heartbeat tracking for long-running workflows."""
        heartbeat_data = {
            "workflow_id": self.workflow_id,
            "started_at": time.time(),
            "last_heartbeat": time.time(),
            "heartbeat_count": 0,
            "status": "active"
        }

        ttl = self._calculate_ttl(self.workflow_status)
        await self._persist_with_ttl(self.heartbeat_key, heartbeat_data, ttl)

    async def _update_heartbeat(self) -> None:
        """Update heartbeat information."""
        if time.time() - self.last_heartbeat < self.config.heartbeat_interval:
            return

        try:
            heartbeat_data = await self.redis_client.get(self.heartbeat_key)
            heartbeat = json.loads(heartbeat_data) if heartbeat_data else {}

            heartbeat.update({
                "last_heartbeat": time.time(),
                "heartbeat_count": heartbeat.get("heartbeat_count", 0) + 1,
                "status": "active"
            })

            ttl = self._calculate_ttl(self.workflow_status)
            await self._persist_with_ttl(self.heartbeat_key, heartbeat, ttl)

            self.last_heartbeat = time.time()

        except Exception as e:
            workflow_logger.log_heartbeat_update_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )

    async def _stop_heartbeat(self) -> None:
        """Stop heartbeat for completed/suspended workflows."""
        try:
            heartbeat_data = await self.redis_client.get(self.heartbeat_key)
            heartbeat = json.loads(heartbeat_data) if heartbeat_data else {}

            heartbeat.update({
                "stopped_at": time.time(),
                "status": "stopped"
            })

            ttl = self._calculate_ttl(self.workflow_status)
            await self._persist_with_ttl(self.heartbeat_key, heartbeat, ttl)

        except Exception as e:
            workflow_logger.log_heartbeat_stop_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )

    async def _create_enhanced_checkpoint(
        self,
        state: TripPlanningWorkflowState,
        checkpoint_type: CheckpointType,
        description: str = ""
    ) -> str:
        """Create an enhanced checkpoint with comprehensive metadata."""
        snapshot_id = f"{checkpoint_type.value}_{int(time.time())}"

        snapshot = StateSnapshot(
            workflow_id=self.workflow_id,
            timestamp=time.time(),
            snapshot_id=snapshot_id,
            state_data=state,
            checkpoint_type=checkpoint_type.value,
            agents_completed=state.get("agents_completed", []),
            agents_failed=state.get("agents_failed", []),
            current_phase=state.get("current_node", "unknown"),
            description=description
        )

        await self._store_enhanced_snapshot(snapshot)

        workflow_logger.log_enhanced_checkpoint_created(
            workflow_id=self.workflow_id,
            request_id=state.get("request_id", "unknown"),
            snapshot_id=snapshot_id,
            checkpoint_type=checkpoint_type.value,
            description=description
        )

        return snapshot_id

    async def _store_enhanced_snapshot(self, snapshot: StateSnapshot) -> None:
        """Store enhanced snapshot with metadata and cleanup management."""
        try:
            snapshots_data = await self.redis_client.get(self.snapshots_key)
            snapshots = json.loads(snapshots_data) if snapshots_data else []

            snapshot_dict = {
                "snapshot_id": snapshot.snapshot_id,
                "timestamp": snapshot.timestamp,
                "checkpoint_type": snapshot.checkpoint_type,
                "agents_completed": snapshot.agents_completed,
                "agents_failed": snapshot.agents_failed,
                "current_phase": snapshot.current_phase,
                "state_data": snapshot.state_data,
                "description": snapshot.description or ""
            }

            snapshots.append(snapshot_dict)

            # Enhanced cleanup logic
            if len(snapshots) > self.config.max_snapshots_per_workflow:
                # Keep important snapshots (manual, completion, error) and most recent
                important_snapshots = [
                    s for s in snapshots
                    if s["checkpoint_type"] in ["manual", "completion", "error"]
                ]

                recent_snapshots = sorted(snapshots, key=lambda x: x["timestamp"], reverse=True)
                recent_snapshots = recent_snapshots[:self.config.max_snapshots_per_workflow // 2]

                # Combine and deduplicate
                combined_snapshots = important_snapshots + [
                    s for s in recent_snapshots
                    if s not in important_snapshots
                ]

                snapshots = combined_snapshots[-self.config.max_snapshots_per_workflow:]

            ttl = self._calculate_ttl(self.workflow_status)
            await self._persist_with_ttl(self.snapshots_key, snapshots, ttl)

        except Exception as e:
            workflow_logger.log_snapshot_storage_error(
                workflow_id=self.workflow_id,
                snapshot_id=snapshot.snapshot_id,
                error=str(e)
            )

    async def _restore_from_enhanced_snapshot(self, snapshot_id: str) -> TripPlanningWorkflowState | None:
        """Restore state from a specific snapshot."""
        try:
            snapshots_data = await self.redis_client.get(self.snapshots_key)

            if not snapshots_data:
                return None

            snapshots = json.loads(snapshots_data)

            # Find the requested snapshot
            for snapshot in snapshots:
                if snapshot["snapshot_id"] == snapshot_id:
                    return snapshot["state_data"]

            return None

        except Exception as e:
            workflow_logger.log_snapshot_restoration_error(
                workflow_id=self.workflow_id,
                snapshot_id=snapshot_id,
                error=str(e)
            )
            return None

    async def _update_enhanced_metadata(self, state: TripPlanningWorkflowState, checkpoint_type: CheckpointType) -> None:
        """Update workflow metadata."""
        metadata = {
            "workflow_id": self.workflow_id,
            "last_update": time.time(),
            "checkpoint_type": checkpoint_type.value,
            "status": state.get("status", "unknown"),
            "current_node": state.get("current_node", "unknown"),
            "agents_completed_count": len(state.get("agents_completed", [])),
            "agents_failed_count": len(state.get("agents_failed", [])),
        }

        await self.redis_client.setex(
            self.metadata_key,
            self._calculate_ttl(self.workflow_status),
            json.dumps(metadata, default=self._json_serializer)
        )

    def _workflow_lock(self):
        """Enhanced context manager for workflow-level locking with timeout."""
        class WorkflowLock:
            def __init__(self, redis_client, lock_key, timeout=30):
                self.redis_client = redis_client
                self.lock_key = lock_key
                self.timeout = timeout
                self.acquired = False

            async def __aenter__(self):
                import asyncio
                # Try to acquire lock with timeout
                for _ in range(self.timeout):
                    if await self.redis_client.set(self.lock_key, "locked", ex=60, nx=True):
                        self.acquired = True
                        return self
                    await asyncio.sleep(1)

                raise TimeoutError(f"Could not acquire workflow lock for {self.lock_key}")

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self.acquired:
                    await self.redis_client.delete(self.lock_key)

        return WorkflowLock(self.redis_client, self.lock_key)

    async def _cleanup_single_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Clean up a single workflow if it meets cleanup criteria."""
        try:
            metadata_key = f"workflow:metadata:{workflow_id}"
            metadata_data = await self.redis_client.get(metadata_key)

            if not metadata_data:
                # Workflow metadata doesn't exist, clean up any remaining keys
                await self._force_cleanup_workflow_keys(workflow_id)
                return {"cleaned": True, "reason": "orphaned"}

            metadata = json.loads(metadata_data)
            status = metadata.get("status", "unknown")
            last_update = metadata.get("last_update", 0)
            current_time = time.time()

            # Check if workflow should be cleaned up
            should_cleanup = False
            cleanup_reason = ""

            if status == WorkflowStatus.COMPLETED.value:
                # Clean up completed workflows after TTL expires with grace period
                ttl_remaining = await self.redis_client.ttl(f"workflow:state:{workflow_id}")
                if ttl_remaining <= 0:
                    should_cleanup = True
                    cleanup_reason = "completed"

            elif status == WorkflowStatus.FAILED.value:
                # Clean up failed workflows after shorter retention
                if current_time - last_update > self.config.failed_workflow_ttl + self.config.expired_workflow_retention:
                    should_cleanup = True
                    cleanup_reason = "failed"

            elif status == WorkflowStatus.EXPIRED.value:
                # Clean up expired workflows after grace period
                if current_time - last_update > self.config.expired_workflow_retention:
                    should_cleanup = True
                    cleanup_reason = "expired"

            elif current_time - last_update > self.config.active_workflow_ttl * 2:
                # Clean up stale workflows that haven't been updated
                should_cleanup = True
                cleanup_reason = "stale"

            if should_cleanup:
                await self._force_cleanup_workflow_keys(workflow_id)
                return {"cleaned": True, "reason": cleanup_reason}

            return {"cleaned": False, "reason": "active"}

        except Exception as e:
            workflow_logger.log_single_workflow_cleanup_error(
                workflow_id=workflow_id,
                error=str(e)
            )
            return {"cleaned": False, "reason": f"error: {str(e)}"}

    async def _force_cleanup_workflow_keys(self, workflow_id: str) -> None:
        """Force cleanup of all Redis keys for a workflow."""
        keys_to_delete = [
            f"workflow:state:{workflow_id}",
            f"workflow:metadata:{workflow_id}",
            f"workflow:snapshots:{workflow_id}",
            f"workflow:progress:{workflow_id}",
            f"workflow:heartbeat:{workflow_id}",
            f"workflow:lock:{workflow_id}"
        ]

        # Delete all keys in pipeline for efficiency
        pipe = await self.redis_client.pipeline()
        for key in keys_to_delete:
            await pipe.delete(key)
        await pipe.execute()

    async def _schedule_cleanup_after_completion(self) -> None:
        """Schedule cleanup of temporary data after workflow completion."""
        try:
            # Schedule cleanup of temporary progress tracking data after completion
            # This keeps the final state but cleans temporary tracking information
            cleanup_delay = 3600  # 1 hour after completion

            cleanup_task = {
                "workflow_id": self.workflow_id,
                "scheduled_at": time.time(),
                "cleanup_at": time.time() + cleanup_delay,
                "cleanup_type": "post_completion"
            }

            self._cleanup_tasks.add(self.workflow_id)

            workflow_logger.log_cleanup_scheduled(
                workflow_id=self.workflow_id,
                cleanup_delay=cleanup_delay,
                cleanup_type="post_completion"
            )

        except Exception as e:
            workflow_logger.log_cleanup_scheduling_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )

    async def _get_enhanced_progress_info(self) -> dict[str, Any]:
        """Get enhanced progress information."""
        try:
            progress_data = await self.redis_client.get(self.progress_key)
            progress = json.loads(progress_data) if progress_data else {}

            # Add derived metrics
            progress["derived_metrics"] = await self._calculate_performance_metrics()
            progress["ttl_remaining"] = await self._get_current_ttl()

            return progress

        except Exception as e:
            workflow_logger.log_progress_retrieval_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )
            return {}

    async def _get_enhanced_metadata(self) -> dict[str, Any]:
        """Get enhanced metadata information."""
        try:
            metadata_data = await self.redis_client.get(self.metadata_key)
            metadata = json.loads(metadata_data) if metadata_data else {}

            # Add runtime information
            metadata["runtime_info"] = {
                "heartbeat_enabled": self.enable_heartbeat,
                "last_heartbeat": self.last_heartbeat,
                "last_checkpoint": self.last_checkpoint_time,
                "last_progress_update": self.last_progress_update
            }

            return metadata

        except Exception as e:
            workflow_logger.log_metadata_retrieval_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )
            return {}

    def _estimate_enhanced_completion_time(
        self,
        elapsed_time: float,
        completed_agents: int,
        total_agents: int
    ) -> float | None:
        """Enhanced completion time estimation with multiple factors."""
        if completed_agents == 0:
            return None

        # Basic linear estimation
        basic_estimate = (elapsed_time / completed_agents) * total_agents

        # Factor in agent complexity (some agents take longer than others)
        if self.current_state:
            # Flight and hotel agents typically take longer
            remaining_agents = self.current_state.get("agent_dependencies", {}).keys()
            complexity_factor = 1.0

            if "flight" in remaining_agents:
                complexity_factor += 0.2  # 20% longer for flight search
            if "hotel" in remaining_agents:
                complexity_factor += 0.15  # 15% longer for hotel search
            if len(remaining_agents) > 3:
                complexity_factor += 0.1  # 10% longer for complex workflows

            adjusted_estimate = basic_estimate * complexity_factor
        else:
            adjusted_estimate = basic_estimate

        # Add current time to get absolute completion time
        return time.time() + (adjusted_estimate - elapsed_time)

    # Additional helper methods for backward compatibility

    async def create_manual_checkpoint(self, state: TripPlanningWorkflowState, description: str = "") -> str:
        """Create a manual checkpoint with description (backward compatibility)."""
        return await self._create_enhanced_checkpoint(
            state,
            CheckpointType.MANUAL,
            description
        )

    async def list_snapshots(self) -> list[dict[str, Any]]:
        """List all available snapshots for this workflow (backward compatibility)."""
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
                    "age_seconds": time.time() - snapshot["timestamp"],
                    "description": snapshot.get("description", "")
                }
                for snapshot in snapshots
            ]

        except Exception as e:
            workflow_logger.log_snapshot_listing_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )
            return []

    async def get_workflow_progress(self) -> dict[str, Any]:
        """Get workflow progress information (backward compatibility)."""
        return await self.get_comprehensive_progress()

    async def persist_state(
        self,
        state: TripPlanningWorkflowState,
        checkpoint_type: str = "automatic"
    ) -> bool:
        """Persist workflow state (backward compatibility)."""
        # Convert string checkpoint_type to enum
        checkpoint_enum = CheckpointType.AUTOMATIC
        if checkpoint_type == "manual":
            checkpoint_enum = CheckpointType.MANUAL
        elif checkpoint_type == "error":
            checkpoint_enum = CheckpointType.ERROR
        elif checkpoint_type == "completion":
            checkpoint_enum = CheckpointType.COMPLETION

        return await self.persist_state_with_progress(state, checkpoint_enum)

    async def restore_state(self, snapshot_id: str | None = None) -> TripPlanningWorkflowState | None:
        """Restore workflow state (backward compatibility)."""
        restored_data = await self.restore_workflow_state(snapshot_id, include_progress=False)
        return restored_data["state"] if restored_data else None


# Create backward compatibility alias
WorkflowStateManager = EnhancedWorkflowStateManager

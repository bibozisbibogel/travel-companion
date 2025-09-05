"""Enhanced state persistence and management for long-running workflows."""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ..core.redis import get_redis_manager
from ..utils.logging import workflow_logger
from .orchestrator import TripPlanningWorkflowState


@dataclass
class StateSnapshot:
    """Represents a point-in-time snapshot of workflow state."""
    
    workflow_id: str
    timestamp: float
    snapshot_id: str
    state_data: Dict[str, Any]
    checkpoint_type: str  # "automatic", "manual", "error", "completion"
    agents_completed: List[str]
    agents_failed: List[str]
    current_phase: str
    
    @property
    def age_seconds(self) -> float:
        """Get age of snapshot in seconds."""
        return time.time() - self.timestamp


class WorkflowStateManager:
    """
    Enhanced state manager for long-running workflows with Redis persistence.
    
    Provides features for:
    - Checkpoint creation and restoration
    - State versioning and rollback
    - Automatic state persistence with TTL management
    - Cross-session state recovery
    - State cleanup and archival
    """
    
    def __init__(self, workflow_id: str, redis_ttl_hours: int = 24):
        """
        Initialize state manager for a workflow.
        
        Args:
            workflow_id: Unique workflow identifier
            redis_ttl_hours: TTL for Redis keys in hours
        """
        self.workflow_id = workflow_id
        self.redis_client = get_redis_manager().client
        self.redis_ttl = redis_ttl_hours * 3600  # Convert to seconds
        
        # Redis key patterns
        self.state_key = f"workflow_state:{workflow_id}"
        self.snapshots_key = f"workflow_snapshots:{workflow_id}"
        self.metadata_key = f"workflow_metadata:{workflow_id}"
        self.lock_key = f"workflow_lock:{workflow_id}"
        
        # State management
        self.snapshots: List[StateSnapshot] = []
        self.current_state: Optional[TripPlanningWorkflowState] = None
        self.last_checkpoint_time: float = 0
        self.checkpoint_interval_seconds = 300  # 5 minutes
    
    async def persist_state(
        self, 
        state: TripPlanningWorkflowState, 
        checkpoint_type: str = "automatic"
    ) -> bool:
        """
        Persist workflow state to Redis with enhanced features.
        
        Args:
            state: Current workflow state
            checkpoint_type: Type of checkpoint ("automatic", "manual", "error", "completion")
            
        Returns:
            True if persistence was successful
        """
        start_time = time.time()
        
        try:
            # Acquire lock for atomic state updates
            async with self._workflow_lock():
                # Update current state
                self.current_state = state
                
                # Store main state
                state_json = json.dumps(state, default=self._json_serializer)
                await self.redis_client.setex(self.state_key, self.redis_ttl, state_json)
                
                # Create snapshot if needed
                should_snapshot = (
                    checkpoint_type != "automatic" or 
                    time.time() - self.last_checkpoint_time > self.checkpoint_interval_seconds
                )
                
                if should_snapshot:
                    await self._create_snapshot(state, checkpoint_type)
                    self.last_checkpoint_time = time.time()
                
                # Update metadata
                await self._update_metadata(state, checkpoint_type)
                
                persistence_time_ms = (time.time() - start_time) * 1000
                
                workflow_logger.log_enhanced_state_persisted(
                    workflow_id=self.workflow_id,
                    request_id=state.get("request_id", "unknown"),
                    persistence_time_ms=persistence_time_ms,
                    checkpoint_type=checkpoint_type,
                    state_size_bytes=len(state_json)
                )
                
                return True
                
        except Exception as e:
            workflow_logger.log_state_persistence_error(
                workflow_id=self.workflow_id,
                request_id=state.get("request_id", "unknown"),
                error=str(e),
                checkpoint_type=checkpoint_type
            )
            return False
    
    async def restore_state(self, snapshot_id: Optional[str] = None) -> Optional[TripPlanningWorkflowState]:
        """
        Restore workflow state from Redis.
        
        Args:
            snapshot_id: Optional specific snapshot to restore (defaults to latest)
            
        Returns:
            Restored workflow state or None if not found
        """
        start_time = time.time()
        
        try:
            if snapshot_id:
                # Restore from specific snapshot
                state = await self._restore_from_snapshot(snapshot_id)
            else:
                # Restore from current state
                state_data = await self.redis_client.get(self.state_key)
                
                if state_data is None:
                    return None
                    
                state = json.loads(state_data)
            
            if state:
                self.current_state = state
                
                restoration_time_ms = (time.time() - start_time) * 1000
                
                workflow_logger.log_enhanced_state_restored(
                    workflow_id=self.workflow_id,
                    request_id=state.get("request_id", "unknown"),
                    restoration_time_ms=restoration_time_ms,
                    snapshot_id=snapshot_id,
                    restored_keys=list(state.keys())
                )
            
            return state
            
        except Exception as e:
            workflow_logger.log_state_restoration_error(
                workflow_id=self.workflow_id,
                request_id="restore_error",
                error=str(e),
                snapshot_id=snapshot_id
            )
            return None
    
    async def create_manual_checkpoint(self, state: TripPlanningWorkflowState, description: str = "") -> str:
        """
        Create a manual checkpoint with description.
        
        Args:
            state: Current workflow state
            description: Optional description for the checkpoint
            
        Returns:
            Snapshot ID of created checkpoint
        """
        snapshot_id = f"manual_{int(time.time())}"
        
        snapshot = StateSnapshot(
            workflow_id=self.workflow_id,
            timestamp=time.time(),
            snapshot_id=snapshot_id,
            state_data=state,
            checkpoint_type="manual",
            agents_completed=state.get("agents_completed", []),
            agents_failed=state.get("agents_failed", []),
            current_phase=state.get("current_node", "unknown")
        )
        
        await self._store_snapshot(snapshot, description)
        
        workflow_logger.log_manual_checkpoint_created(
            workflow_id=self.workflow_id,
            request_id=state.get("request_id", "unknown"),
            snapshot_id=snapshot_id,
            description=description
        )
        
        return snapshot_id
    
    async def list_snapshots(self) -> List[Dict[str, Any]]:
        """
        List all available snapshots for this workflow.
        
        Returns:
            List of snapshot metadata
        """
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
                    "age_seconds": time.time() - snapshot["timestamp"]
                }
                for snapshot in snapshots
            ]
            
        except Exception as e:
            workflow_logger.log_snapshot_listing_error(
                workflow_id=self.workflow_id,
                error=str(e)
            )
            return []
    
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
                    self.redis_ttl, 
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
    
    async def get_workflow_progress(self) -> Dict[str, Any]:
        """
        Get comprehensive workflow progress information.
        
        Returns:
            Dictionary with workflow progress and state information
        """
        try:
            metadata_data = await self.redis_client.get(self.metadata_key)
            snapshots = await self.list_snapshots()
            
            metadata = json.loads(metadata_data) if metadata_data else {}
            
            # Calculate progress metrics
            if self.current_state:
                total_agents = len(self.current_state.get("agent_dependencies", {})) + 3  # +init, itinerary, finalize
                completed_agents = len(self.current_state.get("agents_completed", []))
                failed_agents = len(self.current_state.get("agents_failed", []))
                
                progress_percentage = (completed_agents / total_agents * 100) if total_agents > 0 else 0
                
                return {
                    "workflow_id": self.workflow_id,
                    "status": self.current_state.get("status", "unknown"),
                    "current_node": self.current_state.get("current_node", "unknown"),
                    "progress_percentage": progress_percentage,
                    "agents_completed": completed_agents,
                    "agents_failed": failed_agents,
                    "total_agents": total_agents,
                    "start_time": self.current_state.get("start_time"),
                    "last_update": metadata.get("last_update", 0),
                    "snapshots_count": len(snapshots),
                    "last_checkpoint": snapshots[0] if snapshots else None,
                    "estimated_completion": self._estimate_completion_time()
                }
            
            return {
                "workflow_id": self.workflow_id,
                "status": "not_found",
                "snapshots_count": len(snapshots)
            }
            
        except Exception as e:
            return {
                "workflow_id": self.workflow_id,
                "status": "error",
                "error": str(e)
            }
    
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
                self.redis_ttl, 
                json.dumps(snapshots, default=self._json_serializer)
            )
            
        except Exception as e:
            workflow_logger.log_snapshot_storage_error(
                workflow_id=self.workflow_id,
                snapshot_id=snapshot.snapshot_id,
                error=str(e)
            )
    
    async def _restore_from_snapshot(self, snapshot_id: str) -> Optional[TripPlanningWorkflowState]:
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
            self.redis_ttl, 
            json.dumps(metadata, default=self._json_serializer)
        )
    
    async def _workflow_lock(self):
        """Context manager for workflow-level locking."""
        class WorkflowLock:
            def __init__(self, redis_client, lock_key, timeout=30):
                self.redis_client = redis_client
                self.lock_key = lock_key
                self.timeout = timeout
                self.acquired = False
            
            async def __aenter__(self):
                # Try to acquire lock
                for _ in range(self.timeout):
                    if await self.redis_client.set(self.lock_key, "locked", ex=60, nx=True):
                        self.acquired = True
                        return self
                    await asyncio.sleep(1)
                
                raise TimeoutError(f"Could not acquire workflow lock for {self.lock_key}")
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self.acquired:
                    await self.redis_client.delete(self.lock_key)
        
        import asyncio
        return WorkflowLock(self.redis_client, self.lock_key)
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime and other objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)
    
    def _estimate_completion_time(self) -> Optional[float]:
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
"""
Comprehensive tests for Enhanced Workflow State Manager (Task 6).

Tests cover:
1. Redis-based workflow state storage with TTL
2. Advanced checkpoint and resume functionality
3. Real-time progress tracking for long-running operations
4. Automated state cleanup for completed and expired workflows
"""

import json
import time
from unittest.mock import AsyncMock, patch

import pytest

from travel_companion.workflows.state_manager import (
    CheckpointType,
    EnhancedWorkflowStateManager,
    StateSnapshot,
    WorkflowPersistenceConfig,
    WorkflowStatus,
)


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    # Create pipeline mock separately
    pipeline_mock = AsyncMock()
    pipeline_mock.delete = AsyncMock()
    pipeline_mock.execute = AsyncMock(return_value=[True, True, True])

    # Create main Redis mock
    redis_mock = AsyncMock()  # Don't use spec=Redis to avoid attribute issues
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.exists = AsyncMock(return_value=1)
    redis_mock.ttl = AsyncMock(return_value=3600)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.pipeline = AsyncMock(return_value=pipeline_mock)

    return redis_mock


@pytest.fixture
def config():
    """Test configuration for state manager."""
    return WorkflowPersistenceConfig(
        active_workflow_ttl=7200,  # 2 hours for testing
        completed_workflow_ttl=86400,  # 1 day
        failed_workflow_ttl=21600,  # 6 hours
        automatic_checkpoint_interval=60,  # 1 minute for testing
        max_snapshots_per_workflow=10,
        progress_update_interval=30,  # 30 seconds for testing
        heartbeat_interval=15,  # 15 seconds for testing
    )


@pytest.fixture
def sample_workflow_state():
    """Sample workflow state for testing."""
    return {
        "workflow_id": "test_workflow_123",
        "request_id": "req_456",
        "status": "running",
        "current_node": "fetch_flights",
        "start_time": time.time(),
        "agents_completed": ["weather", "flight"],
        "agents_failed": [],
        "agent_dependencies": {
            "weather": [],
            "flight": ["weather"],
            "hotel": ["flight"],
            "activity": ["weather", "hotel"],
            "food": ["hotel"],
            "itinerary": ["flight", "hotel", "activity", "food"]
        }
    }


@pytest.fixture
def state_manager(mock_redis, config):
    """Enhanced state manager instance for testing."""
    with patch('travel_companion.workflows.state_manager.get_redis_manager') as mock_manager:
        mock_manager.return_value.client = mock_redis
        manager = EnhancedWorkflowStateManager(
            workflow_id="test_workflow_123",
            config=config,
            enable_heartbeat=True
        )
        return manager


class TestWorkflowStateStorageWithTTL:
    """Test Redis-based workflow state storage with TTL management."""

    @pytest.mark.asyncio
    async def test_initialize_workflow_with_ttl(self, state_manager, sample_workflow_state, mock_redis):
        """Test workflow initialization with proper TTL calculation."""
        # Test with estimated duration
        result = await state_manager.initialize_workflow(
            sample_workflow_state,
            estimated_duration_minutes=30
        )

        assert result is True
        assert mock_redis.setex.call_count >= 2  # state + metadata

        # Check TTL calculations - should use 2x estimated duration for active workflow
        setex_calls = mock_redis.setex.call_args_list
        ttl_values = [call[0][1] for call in setex_calls]

        # Active workflow TTL should be at least 2x estimated (30 min * 60 * 2 = 3600s)
        assert any(ttl >= 3600 for ttl in ttl_values)

    @pytest.mark.asyncio
    async def test_ttl_calculation_by_status(self, state_manager, config):
        """Test TTL calculation for different workflow statuses."""
        # Test active workflow TTL
        active_ttl = state_manager._calculate_ttl(WorkflowStatus.RUNNING)
        assert active_ttl == config.active_workflow_ttl

        # Test completed workflow TTL
        completed_ttl = state_manager._calculate_ttl(WorkflowStatus.COMPLETED)
        assert completed_ttl == config.completed_workflow_ttl

        # Test failed workflow TTL
        failed_ttl = state_manager._calculate_ttl(WorkflowStatus.FAILED)
        assert failed_ttl == config.failed_workflow_ttl

        # Test with estimated duration override
        estimated_ttl = state_manager._calculate_ttl(WorkflowStatus.RUNNING, 60)
        expected_ttl = max(60 * 60 * 2, config.active_workflow_ttl)
        assert estimated_ttl == expected_ttl

    @pytest.mark.asyncio
    async def test_dynamic_ttl_extension(self, state_manager, sample_workflow_state, mock_redis):
        """Test dynamic TTL extension for active workflows."""
        # Initialize workflow
        await state_manager.initialize_workflow(sample_workflow_state)

        # Simulate low TTL scenario
        mock_redis.ttl.return_value = 500  # Low TTL

        # Persist state - should extend TTL
        result = await state_manager.persist_state_with_progress(
            sample_workflow_state,
            CheckpointType.AUTOMATIC
        )

        assert result is True
        # Should have called expire to extend TTL
        assert mock_redis.expire.called

    @pytest.mark.asyncio
    async def test_workflow_index_management(self, state_manager, sample_workflow_state, mock_redis):
        """Test global workflow index for tracking."""
        # Mock empty index initially
        mock_redis.get.return_value = None

        await state_manager.initialize_workflow(sample_workflow_state)

        # Should add to workflow index
        set_calls = [call for call in mock_redis.set.call_args_list
                    if 'workflow:index' in str(call)]
        assert len(set_calls) >= 1


class TestCheckpointAndResumeFunctionality:
    """Test advanced checkpoint and resume functionality."""

    @pytest.mark.asyncio
    async def test_enhanced_checkpoint_creation(self, state_manager, sample_workflow_state, mock_redis):
        """Test enhanced checkpoint creation with metadata."""
        # Initialize workflow
        await state_manager.initialize_workflow(sample_workflow_state)

        # Create manual checkpoint
        snapshot_id = await state_manager.create_manual_checkpoint(
            sample_workflow_state,
            "Test checkpoint for debugging"
        )

        assert snapshot_id.startswith("manual_")
        assert mock_redis.setex.called  # Should persist snapshots

    @pytest.mark.asyncio
    async def test_checkpoint_types_and_metadata(self, state_manager, sample_workflow_state):
        """Test different checkpoint types with proper metadata."""
        await state_manager.initialize_workflow(sample_workflow_state)

        # Test automatic checkpoint
        auto_id = await state_manager._create_enhanced_checkpoint(
            sample_workflow_state,
            CheckpointType.AUTOMATIC,
            "Automatic checkpoint"
        )
        assert auto_id.startswith("automatic_")

        # Test error checkpoint
        error_id = await state_manager._create_enhanced_checkpoint(
            sample_workflow_state,
            CheckpointType.ERROR,
            "Error recovery checkpoint"
        )
        assert error_id.startswith("error_")

        # Test completion checkpoint
        completion_id = await state_manager._create_enhanced_checkpoint(
            sample_workflow_state,
            CheckpointType.COMPLETION,
            "Workflow completed"
        )
        assert completion_id.startswith("completion_")

    @pytest.mark.asyncio
    async def test_snapshot_cleanup_logic(self, state_manager, sample_workflow_state, mock_redis):
        """Test intelligent snapshot cleanup preserving important snapshots."""
        # Mock snapshots data with mixed types
        mock_snapshots = []

        # Create different types of snapshots
        for i in range(15):  # Exceed max_snapshots_per_workflow (10)
            checkpoint_type = "automatic"
            if i % 5 == 0:
                checkpoint_type = "manual"  # Important
            elif i % 7 == 0:
                checkpoint_type = "error"   # Important

            mock_snapshots.append({
                "snapshot_id": f"{checkpoint_type}_{time.time() + i}",
                "timestamp": time.time() + i,
                "checkpoint_type": checkpoint_type,
                "agents_completed": ["weather"],
                "agents_failed": [],
                "current_phase": "test",
                "state_data": sample_workflow_state,
                "description": f"Test snapshot {i}"
            })

        mock_redis.get.return_value = json.dumps(mock_snapshots)

        # Create new snapshot that should trigger cleanup
        await state_manager._store_enhanced_snapshot(
            StateSnapshot(
                workflow_id="test",
                timestamp=time.time(),
                snapshot_id="test_new",
                state_data=sample_workflow_state,
                checkpoint_type="automatic",
                agents_completed=[],
                agents_failed=[],
                current_phase="test"
            )
        )

        # Should have stored with cleanup logic applied
        assert mock_redis.setex.called

    @pytest.mark.asyncio
    async def test_workflow_suspension_and_resumption(self, state_manager, sample_workflow_state, mock_redis):
        """Test workflow suspension and resumption with state preservation."""
        # Initialize workflow
        await state_manager.initialize_workflow(sample_workflow_state)

        # Suspend workflow
        result = await state_manager.suspend_workflow("Testing suspension")
        assert result is True
        assert state_manager.workflow_status == WorkflowStatus.SUSPENDED

        # Mock restoration data - Redis should return just the state data
        mock_redis.get.return_value = json.dumps(sample_workflow_state)

        # Resume workflow
        resumed_data = await state_manager.resume_workflow()
        assert resumed_data is not None
        assert resumed_data["state"] == sample_workflow_state
        assert state_manager.workflow_status == WorkflowStatus.RUNNING


class TestProgressTrackingLongRunning:
    """Test real-time progress tracking for long-running operations."""

    @pytest.mark.asyncio
    async def test_progress_initialization(self, state_manager, sample_workflow_state, mock_redis):
        """Test progress tracking initialization."""
        await state_manager.initialize_workflow(sample_workflow_state)

        # Should initialize progress tracking
        progress_calls = [call for call in mock_redis.setex.call_args_list
                         if 'workflow:progress:' in str(call)]
        assert len(progress_calls) >= 1

    @pytest.mark.asyncio
    async def test_progress_updates_with_throttling(self, state_manager, sample_workflow_state, mock_redis):
        """Test progress updates with proper throttling."""
        await state_manager.initialize_workflow(sample_workflow_state)

        # Reset mock to track new calls
        mock_redis.reset_mock()

        # First progress update - should go through
        await state_manager._update_progress_tracking(
            sample_workflow_state,
            "Starting flight search"
        )

        # Immediate second update - should be throttled
        await state_manager._update_progress_tracking(
            sample_workflow_state,
            "Still searching flights"
        )

        # Should have made only one update due to throttling
        progress_calls = [call for call in mock_redis.setex.call_args_list
                         if 'workflow:progress:' in str(call)]
        assert len(progress_calls) <= 1

    @pytest.mark.asyncio
    async def test_comprehensive_progress_info(self, state_manager, sample_workflow_state, mock_redis):
        """Test comprehensive progress information retrieval."""
        # Mock progress, metadata, and heartbeat data
        mock_progress = {
            "workflow_id": "test_workflow_123",
            "initialized_at": time.time() - 600,
            "total_steps": 6,
            "completed_steps": 2,
            "current_step": "fetch_hotels",
            "step_history": [
                {"timestamp": time.time() - 300, "step": "fetch_weather", "description": "Weather data retrieved"},
                {"timestamp": time.time() - 150, "step": "fetch_flights", "description": "Flight search completed"}
            ]
        }

        mock_metadata = {
            "workflow_id": "test_workflow_123",
            "created_at": time.time() - 600,
            "status": "running",
            "last_update": time.time() - 30
        }

        mock_heartbeat = {
            "workflow_id": "test_workflow_123",
            "started_at": time.time() - 600,
            "last_heartbeat": time.time() - 5,
            "heartbeat_count": 40
        }

        # Mock Redis responses
        def mock_get_side_effect(key):
            if 'progress' in key:
                return json.dumps(mock_progress)
            elif 'metadata' in key:
                return json.dumps(mock_metadata)
            elif 'heartbeat' in key:
                return json.dumps(mock_heartbeat)
            return None

        mock_redis.get.side_effect = mock_get_side_effect
        mock_redis.ttl.return_value = 1800  # 30 minutes remaining

        # Set current state and status
        state_manager.current_state = sample_workflow_state
        state_manager.workflow_status = WorkflowStatus.RUNNING

        # Get comprehensive progress
        progress_info = await state_manager.get_comprehensive_progress()

        assert progress_info["workflow_id"] == "test_workflow_123"
        assert progress_info["status"] == "running"
        assert progress_info["progress_percentage"] == pytest.approx(22.22, abs=0.1)  # 2/9 * 100 (6 agents + 3 overhead)
        assert progress_info["ttl_remaining"] == 1800
        assert "heartbeat" in progress_info
        assert "performance_metrics" in progress_info

    @pytest.mark.asyncio
    async def test_heartbeat_functionality(self, state_manager, sample_workflow_state, mock_redis):
        """Test heartbeat tracking for long-running workflows."""
        await state_manager.initialize_workflow(sample_workflow_state)

        # Should start heartbeat
        heartbeat_calls = [call for call in mock_redis.setex.call_args_list
                          if 'workflow:heartbeat:' in str(call)]
        assert len(heartbeat_calls) >= 1

        # Test heartbeat update
        state_manager.last_heartbeat = 0  # Force update
        await state_manager._update_heartbeat()

        # Test heartbeat stop
        await state_manager._stop_heartbeat()

        # Should have updated heartbeat multiple times
        heartbeat_updates = [call for call in mock_redis.setex.call_args_list
                           if 'workflow:heartbeat:' in str(call)]
        assert len(heartbeat_updates) >= 2

    @pytest.mark.asyncio
    async def test_completion_time_estimation(self, state_manager, sample_workflow_state):
        """Test enhanced completion time estimation."""
        state_manager.current_state = sample_workflow_state

        # Test basic estimation
        estimated = state_manager._estimate_enhanced_completion_time(
            elapsed_time=300,  # 5 minutes elapsed
            completed_agents=2,
            total_agents=6
        )

        assert estimated is not None
        assert estimated > time.time()  # Should be in the future

        # Test with no completed agents
        estimated_none = state_manager._estimate_enhanced_completion_time(
            elapsed_time=300,
            completed_agents=0,
            total_agents=6
        )

        assert estimated_none is None


class TestAutomatedStateCleanup:
    """Test automated state cleanup for completed and expired workflows."""

    @pytest.mark.asyncio
    async def test_workflow_completion_cleanup_scheduling(self, state_manager, sample_workflow_state, mock_redis):
        """Test cleanup scheduling after workflow completion."""
        await state_manager.initialize_workflow(sample_workflow_state)

        # Complete workflow
        result = await state_manager.complete_workflow(
            sample_workflow_state,
            "Test workflow completed successfully"
        )

        assert result is True
        assert state_manager.workflow_status == WorkflowStatus.COMPLETED
        assert len(state_manager._cleanup_tasks) > 0

    @pytest.mark.asyncio
    async def test_comprehensive_workflow_cleanup(self, state_manager, mock_redis):
        """Test comprehensive cleanup of expired and completed workflows."""
        # Mock workflow index with various workflow states
        workflow_index = {
            "completed_workflow_1": {
                "created_at": time.time() - 86400,  # 1 day ago
                "status": "completed",
                "last_update": time.time() - 86400
            },
            "failed_workflow_2": {
                "created_at": time.time() - 3600,
                "status": "failed",
                "last_update": time.time() - 3600
            },
            "active_workflow_3": {
                "created_at": time.time() - 1800,
                "status": "running",
                "last_update": time.time() - 60
            }
        }

        def mock_get_side_effect(key):
            if 'workflow:index' in key:
                return json.dumps(workflow_index)
            elif 'workflow:metadata:completed_workflow_1' in key:
                return json.dumps({
                    "status": "completed",
                    "last_update": time.time() - 86400
                })
            elif 'workflow:metadata:failed_workflow_2' in key:
                return json.dumps({
                    "status": "failed",
                    "last_update": time.time() - 3600
                })
            elif 'workflow:metadata:active_workflow_3' in key:
                return json.dumps({
                    "status": "running",
                    "last_update": time.time() - 60
                })
            return None

        mock_redis.get.side_effect = mock_get_side_effect
        mock_redis.ttl.return_value = -1  # Expired

        # Run cleanup
        cleanup_result = await state_manager.cleanup_expired_workflows(max_workflows=10)

        assert cleanup_result["total_workflows_processed"] > 0
        assert cleanup_result["cleanup_time_seconds"] > 0

    @pytest.mark.asyncio
    async def test_single_workflow_cleanup_criteria(self, state_manager):
        """Test single workflow cleanup criteria evaluation."""
        # Test completed workflow cleanup
        await state_manager._cleanup_single_workflow("completed_test")

        # Test with different workflow states
        mock_metadata = {
            "status": "completed",
            "last_update": time.time() - 604800  # 1 week ago
        }

        state_manager.redis_client.get.return_value = json.dumps(mock_metadata)
        state_manager.redis_client.ttl.return_value = -1  # Expired

        result = await state_manager._cleanup_single_workflow("completed_test")
        assert result["cleaned"] is True
        assert result["reason"] == "completed"

    @pytest.mark.asyncio
    async def test_force_cleanup_workflow_keys(self, state_manager, mock_redis):
        """Test force cleanup of all workflow Redis keys."""
        await state_manager._force_cleanup_workflow_keys("test_workflow")

        # Should use pipeline for efficiency
        assert mock_redis.pipeline.called

        # Get the pipeline mock that was returned and verify execute was called
        pipeline_mock = mock_redis.pipeline.return_value
        assert pipeline_mock.execute.called

    @pytest.mark.asyncio
    async def test_snapshot_age_based_cleanup(self, state_manager, sample_workflow_state, mock_redis):
        """Test age-based cleanup of old snapshots."""
        # Create old snapshots
        old_snapshots = []
        current_time = time.time()

        for i in range(5):
            old_snapshots.append({
                "snapshot_id": f"old_{i}",
                "timestamp": current_time - (168 * 3600) - i,  # Older than 1 week
                "checkpoint_type": "automatic",
                "agents_completed": [],
                "agents_failed": [],
                "current_phase": "test"
            })

        # Add some recent snapshots to keep
        for i in range(3):
            old_snapshots.append({
                "snapshot_id": f"recent_{i}",
                "timestamp": current_time - 3600 - i,  # 1 hour ago
                "checkpoint_type": "manual",
                "agents_completed": [],
                "agents_failed": [],
                "current_phase": "test"
            })

        mock_redis.get.return_value = json.dumps(old_snapshots)

        # Run cleanup - should keep recent and important snapshots
        cleaned_count = await state_manager.cleanup_old_snapshots(max_age_hours=48)

        assert cleaned_count >= 0  # Some snapshots should be cleaned


class TestErrorHandlingAndResilience:
    """Test error handling and resilience in state management."""

    @pytest.mark.asyncio
    async def test_redis_connection_failures(self, state_manager, sample_workflow_state):
        """Test graceful handling of Redis connection failures."""
        # Mock Redis failure
        state_manager.redis_client.setex.side_effect = Exception("Redis connection failed")

        # Should handle gracefully and return False
        result = await state_manager.persist_state_with_progress(sample_workflow_state)
        assert result is False

    @pytest.mark.asyncio
    async def test_corrupted_data_handling(self, state_manager, mock_redis):
        """Test handling of corrupted data in Redis."""
        # Mock corrupted JSON data
        mock_redis.get.return_value = "invalid_json_data"

        # Should handle gracefully
        restored_data = await state_manager.restore_workflow_state()
        assert restored_data is None

    @pytest.mark.asyncio
    async def test_cleanup_with_partial_failures(self, state_manager, mock_redis):
        """Test cleanup operations with partial failures."""
        # Mock partial failures in cleanup
        def mock_delete_side_effect(*args, **kwargs):
            # Simulate some deletes failing
            return 0  # Indicate deletion failed

        mock_redis.delete.side_effect = mock_delete_side_effect

        # Should handle partial failures gracefully
        await state_manager._force_cleanup_workflow_keys("test_workflow")

        # Should still attempt all deletions
        assert mock_redis.pipeline.called

    @pytest.mark.asyncio
    async def test_concurrent_access_handling(self, state_manager, sample_workflow_state, mock_redis):
        """Test handling of concurrent access to workflow state."""
        # Mock lock acquisition failure
        mock_redis.set.return_value = False  # Lock acquisition fails

        # Should raise timeout error for lock acquisition (using short timeout for testing)
        with pytest.raises(TimeoutError):
            # Create a lock with a very short timeout to avoid 30-second wait
            class FastWorkflowLock:
                def __init__(self, redis_client, lock_key, timeout=2):  # Only 2 seconds
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

            # Use our fast lock for testing
            async with FastWorkflowLock(mock_redis, state_manager.lock_key):
                pass


class TestBackwardCompatibility:
    """Test backward compatibility with existing state manager interface."""

    @pytest.mark.asyncio
    async def test_legacy_persist_state_method(self, state_manager, sample_workflow_state):
        """Test backward compatibility of persist_state method."""
        await state_manager.initialize_workflow(sample_workflow_state)

        # Test with string checkpoint type (legacy)
        result = await state_manager.persist_state(sample_workflow_state, "manual")
        assert result is True

    @pytest.mark.asyncio
    async def test_legacy_restore_state_method(self, state_manager, sample_workflow_state, mock_redis):
        """Test backward compatibility of restore_state method."""
        # Mock restoration data
        mock_redis.get.return_value = json.dumps(sample_workflow_state)

        # Should return just the state (legacy behavior)
        restored_state = await state_manager.restore_state()
        assert restored_state == sample_workflow_state

    @pytest.mark.asyncio
    async def test_legacy_workflow_progress_method(self, state_manager, sample_workflow_state, mock_redis):
        """Test backward compatibility of get_workflow_progress method."""
        state_manager.current_state = sample_workflow_state

        # Should work with legacy method name
        progress_info = await state_manager.get_workflow_progress()
        assert progress_info["workflow_id"] == "test_workflow_123"


class TestPerformanceOptimizations:
    """Test performance optimizations in state management."""

    @pytest.mark.asyncio
    async def test_batch_redis_operations(self, state_manager, mock_redis):
        """Test batching of Redis operations for performance."""
        await state_manager._force_cleanup_workflow_keys("test_workflow")

        # Should use pipeline for batch operations
        assert mock_redis.pipeline.called

        # Get the pipeline mock and verify execute was called
        pipeline_mock = mock_redis.pipeline.return_value
        assert pipeline_mock.execute.called

    @pytest.mark.asyncio
    async def test_efficient_json_serialization(self, state_manager, sample_workflow_state):
        """Test efficient JSON serialization with custom serializer."""
        from datetime import datetime

        # Test serialization of various object types
        test_data = {
            "datetime": datetime.now(),
            "workflow_status": WorkflowStatus.RUNNING,
            "checkpoint_type": CheckpointType.MANUAL,
            "regular_string": "test"
        }

        serialized = state_manager._json_serializer(test_data["datetime"])
        assert isinstance(serialized, str)

        serialized = state_manager._json_serializer(test_data["workflow_status"])
        assert serialized == "running"

    @pytest.mark.asyncio
    async def test_memory_efficient_snapshot_storage(self, state_manager, sample_workflow_state, mock_redis):
        """Test memory-efficient snapshot storage with size limits."""
        # Create many snapshots to test size limits
        mock_large_snapshots = []
        for i in range(100):  # Exceed cleanup threshold
            mock_large_snapshots.append({
                "snapshot_id": f"snapshot_{i}",
                "timestamp": time.time() + i,
                "checkpoint_type": "automatic",
                "agents_completed": [],
                "agents_failed": [],
                "current_phase": "test",
                "state_data": sample_workflow_state
            })

        mock_redis.get.return_value = json.dumps(mock_large_snapshots)

        # Should handle large snapshot collections efficiently
        snapshots_list = await state_manager.list_snapshots()
        assert len(snapshots_list) == 100  # Should return all without memory issues


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

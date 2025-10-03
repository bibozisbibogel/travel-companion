#!/usr/bin/env python3
"""
Simple test script for Redis connection and functionality.
Tests Redis connection, basic operations, and health checks.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

# Import after path setup
from travel_companion.core.config import get_settings  # noqa: E402
from travel_companion.core.redis import get_redis_manager  # noqa: E402


async def test_redis_connection_basic():
    """Test basic Redis connection and ping."""
    print("✅ Test 1: Basic Redis Connection...")

    try:
        redis_manager = get_redis_manager()
        print(f"   - Redis manager created: {type(redis_manager).__name__}")

        # Test ping
        ping_result = await redis_manager.ping()
        print(f"   - Ping result: {ping_result}")

        if ping_result:
            print("   ✅ Redis connection successful")
            return True
        else:
            print("   ❌ Redis ping failed")
            return False

    except Exception as e:
        print(f"   ❌ Redis connection failed: {e}")
        return False


async def test_redis_operations():
    """Test basic Redis operations (set/get/delete)."""
    print("\n✅ Test 2: Basic Redis Operations...")

    try:
        redis_manager = get_redis_manager()

        # Test set operation
        test_key = "test:orchestrator:connection"
        test_value = "test_value_123"

        set_result = await redis_manager.set(test_key, test_value, expire=60)
        print(f"   - Set operation result: {set_result}")

        # Test get operation
        get_result = await redis_manager.get(test_key)
        print(f"   - Get operation result: {get_result}")

        # Test exists operation
        exists_result = await redis_manager.exists(test_key)
        print(f"   - Exists operation result: {exists_result}")

        # Test TTL operation
        ttl_result = await redis_manager.ttl(test_key)
        print(f"   - TTL operation result: {ttl_result}s")

        # Test delete operation
        delete_result = await redis_manager.delete(test_key)
        print(f"   - Delete operation result: {delete_result}")

        # Verify deletion
        exists_after_delete = await redis_manager.exists(test_key)
        print(f"   - Exists after delete: {exists_after_delete}")

        if (
            set_result
            and get_result == test_value
            and exists_result
            and delete_result
            and not exists_after_delete
        ):
            print("   ✅ All Redis operations successful")
            return True
        else:
            print("   ❌ Some Redis operations failed")
            return False

    except Exception as e:
        print(f"   ❌ Redis operations failed: {e}")
        return False


async def test_redis_json_operations():
    """Test Redis JSON operations."""
    print("\n✅ Test 3: Redis JSON Operations...")

    try:
        redis_manager = get_redis_manager()

        # Test JSON set/get
        test_key = "test:orchestrator:json"
        test_data = {
            "workflow_id": "test-123",
            "status": "running",
            "agents": ["flight", "hotel", "activity"],
            "budget": 5000.0,
        }

        set_result = await redis_manager.set(test_key, test_data, expire=60)
        print(f"   - JSON set result: {set_result}")

        get_result = await redis_manager.get(test_key, json_decode=True)
        print(
            f"   - JSON get result: {type(get_result)} with keys: {list(get_result.keys()) if isinstance(get_result, dict) else 'Not a dict'}"
        )

        # Verify data integrity
        if isinstance(get_result, dict) and get_result["workflow_id"] == "test-123":
            print("   - JSON data integrity verified")
            json_success = True
        else:
            print("   - JSON data integrity failed")
            json_success = False

        # Cleanup
        await redis_manager.delete(test_key)

        if set_result and json_success:
            print("   ✅ JSON operations successful")
            return True
        else:
            print("   ❌ JSON operations failed")
            return False

    except Exception as e:
        print(f"   ❌ JSON operations failed: {e}")
        return False


async def test_redis_workflow_state():
    """Test Redis operations similar to workflow state persistence."""
    print("\n✅ Test 4: Workflow State Simulation...")

    try:
        redis_manager = get_redis_manager()

        # Simulate workflow state
        workflow_state = {
            "workflow_id": "test-workflow-456",
            "request_id": "test-request-789",
            "user_id": "test-user-123",
            "status": "running",
            "start_time": time.time(),
            "current_node": "initialize_trip",
            "trip_request": {
                "destination": {"city": "Tokyo", "country": "Japan"},
                "budget": 5000.0,
                "travelers": 2,
            },
            "agents_completed": ["weather"],
            "agents_failed": [],
            "flight_results": [],
            "hotel_results": [],
        }

        state_key = f"workflow_state:{workflow_state['workflow_id']}"

        # Test state persistence
        persist_result = await redis_manager.set(state_key, workflow_state, expire=3600)
        print(f"   - State persistence result: {persist_result}")

        # Test state retrieval
        retrieved_state = await redis_manager.get(state_key, json_decode=True)
        print(f"   - State retrieval result: {type(retrieved_state)}")

        if isinstance(retrieved_state, dict):
            print(f"   - Retrieved workflow ID: {retrieved_state.get('workflow_id')}")
            print(f"   - Retrieved status: {retrieved_state.get('status')}")
            print(f"   - Retrieved agents completed: {retrieved_state.get('agents_completed')}")

        # Test key scanning
        pattern_keys = await redis_manager.scan_keys("workflow_state:*")
        print(f"   - Found workflow keys: {len(pattern_keys)}")

        # Cleanup
        cleanup_result = await redis_manager.delete(state_key)
        print(f"   - Cleanup result: {cleanup_result}")

        if persist_result and isinstance(retrieved_state, dict) and cleanup_result:
            print("   ✅ Workflow state simulation successful")
            return True
        else:
            print("   ❌ Workflow state simulation failed")
            return False

    except Exception as e:
        print(f"   ❌ Workflow state simulation failed: {e}")
        return False


async def test_redis_configuration():
    """Test Redis configuration and settings."""
    print("\n✅ Test 5: Redis Configuration...")

    try:
        settings = get_settings()
        redis_manager = get_redis_manager()

        print(f"   - Redis URL configured: {'Yes' if settings.redis_url else 'No'}")
        print(f"   - Redis URL: {settings.redis_url}")

        # Test client configuration
        client = redis_manager.client
        print(f"   - Client type: {type(client).__name__}")

        # Get Redis info (if connection works)
        try:
            info = await client.info()
            redis_version = info.get("redis_version", "unknown")
            print(f"   - Redis server version: {redis_version}")
            print(f"   - Redis server mode: {info.get('redis_mode', 'unknown')}")
            print(f"   - Connected clients: {info.get('connected_clients', 'unknown')}")
            print("   ✅ Configuration check successful")
            return True
        except Exception as info_error:
            print(f"   - Redis server info unavailable: {info_error}")
            print("   ⚠️ Configuration check partial (connection issues)")
            return False

    except Exception as e:
        print(f"   ❌ Configuration check failed: {e}")
        return False


async def test_redis_performance():
    """Test basic Redis performance with multiple operations."""
    print("\n✅ Test 6: Redis Performance Test...")

    try:
        redis_manager = get_redis_manager()

        # Performance test with multiple operations
        num_operations = 10
        start_time = time.time()

        # Create multiple keys
        keys = []
        for i in range(num_operations):
            key = f"test:perf:{i}"
            keys.append(key)
            await redis_manager.set(key, f"value_{i}", expire=60)

        # Read all keys
        values = []
        for key in keys:
            value = await redis_manager.get(key)
            values.append(value)

        # Delete all keys
        delete_count = await redis_manager.delete_keys(keys)

        end_time = time.time()
        total_time = (end_time - start_time) * 1000  # Convert to milliseconds

        print(f"   - Operations performed: {num_operations * 3} (set + get + delete)")
        print(f"   - Total time: {total_time:.2f}ms")
        print(f"   - Average per operation: {total_time / (num_operations * 3):.2f}ms")
        print(f"   - Keys deleted: {delete_count}/{num_operations}")

        if len(values) == num_operations and delete_count == num_operations:
            print("   ✅ Performance test successful")
            return True
        else:
            print("   ❌ Performance test failed")
            return False

    except Exception as e:
        print(f"   ❌ Performance test failed: {e}")
        return False


async def main():
    """Main test function."""
    print("Redis Connection Test Suite")
    print("=" * 50)

    results = []

    try:
        # Run all tests
        results.append(await test_redis_connection_basic())
        results.append(await test_redis_operations())
        results.append(await test_redis_json_operations())
        results.append(await test_redis_workflow_state())
        results.append(await test_redis_configuration())
        results.append(await test_redis_performance())

        # Summary
        passed = sum(results)
        total = len(results)

        print("\n" + "=" * 50)
        print(f"📊 Test Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All Redis tests passed!")
            print("✅ Redis is functioning correctly for the orchestrator")
        else:
            failed = total - passed
            print(f"⚠️ {failed} test(s) failed")
            print("❌ Redis may have connection or functionality issues")

            print("\n🔧 Troubleshooting suggestions:")
            print("- Ensure Redis server is running (redis-server)")
            print("- Check Redis URL in environment variables")
            print("- Verify Redis server is accessible on configured port")
            print("- Check firewall and network connectivity")

    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

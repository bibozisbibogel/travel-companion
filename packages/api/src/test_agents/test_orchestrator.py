#!/usr/bin/env python3
"""
Simple test script for TripPlanningWorkflow orchestrator.
Tests the instantiation and basic functionality without pytest.
"""

import asyncio
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

# Import after path setup
from travel_companion.models.trip import (  # noqa: E402
    AccommodationType,
    TravelClass,
    TripDestination,
    TripPlanRequest,
    TripRequirements,
)
from travel_companion.workflows.orchestrator import TripPlanningWorkflow  # noqa: E402


def create_test_trip_request() -> TripPlanRequest:
    """Create a test trip request for Tokyo."""
    destination = TripDestination(
        city="Tokyo",
        country="Japan",
        country_code="JP",
        airport_code="NRT",
        latitude=35.6762,
        longitude=139.6503,
    )

    requirements = TripRequirements(
        budget=Decimal("5000.00"),
        currency="USD",
        start_date=date(2024, 6, 15),
        end_date=date(2024, 6, 22),
        travelers=2,
        travel_class=TravelClass.ECONOMY,
        accommodation_type=AccommodationType.HOTEL,
    )

    preferences = {
        "food_preferences": ["japanese", "vegetarian"],
        "activity_types": ["cultural", "sightseeing"],
        "budget_priorities": ["accommodation", "activities"],
        "language": "en",
    }

    return TripPlanRequest(
        destination=destination,
        requirements=requirements,
        preferences=preferences,
    )


async def test_workflow_instantiation():
    """Test TripPlanningWorkflow instantiation and basic methods."""
    print("🚀 Starting TripPlanningWorkflow Test")
    print("=" * 50)

    # Test 1: Basic instantiation
    print("✅ Test 1: Instantiating TripPlanningWorkflow...")
    try:
        workflow = TripPlanningWorkflow()
        print(f"   - Workflow type: {workflow.workflow_type}")
        print(f"   - State class: {workflow.get_state_class().__name__}")
        print(f"   - Entry point: {workflow.get_entry_point()}")
        print("   ✅ Instantiation successful")
    except Exception as e:
        print(f"   ❌ Instantiation failed: {e}")
        return False

    # Test 2: Graph building
    print("\n✅ Test 2: Building workflow graph...")
    try:
        graph = workflow.build_graph()
        print(f"   - Graph type: {type(graph).__name__}")
        print(f"   - Nodes defined: {len(workflow._nodes)}")
        print(f"   - Edges defined: {len(workflow._edges)}")
        print("   ✅ Graph building successful")
    except Exception as e:
        print(f"   ❌ Graph building failed: {e}")
        return False

    # Test 3: Health status
    print("\n✅ Test 3: Checking workflow health...")
    try:
        health_status = workflow.get_health_status()
        print(f"   - Status: {health_status.get('status')}")
        print(f"   - Graph built: {health_status.get('graph_built')}")
        print(f"   - Redis connected: {health_status.get('redis_connected')}")
        print(f"   - Node count: {health_status.get('node_count')}")
        print("   ✅ Health check successful")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False

    # Test 4: Create initial state
    print("\n✅ Test 4: Creating initial trip state...")
    try:
        trip_request = create_test_trip_request()
        initial_state = workflow.create_initial_state(
            trip_request=trip_request, user_id="test_user_123", request_id="test_request_456"
        )

        print(f"   - Workflow ID: {initial_state['workflow_id']}")
        print(f"   - User ID: {initial_state['user_id']}")
        print(f"   - Status: {initial_state['status']}")
        print(f"   - Current node: {initial_state['current_node']}")
        print(f"   - Trip destination: {initial_state['trip_request'].destination.city}")
        print(f"   - Budget: {initial_state['budget_tracking']['total_budget']}")
        print("   ✅ Initial state creation successful")
    except Exception as e:
        print(f"   ❌ Initial state creation failed: {e}")
        return False

    # Test 5: Execute trip planning (this will likely fail due to missing dependencies)
    print("\n✅ Test 5: Testing trip planning execution...")
    try:
        result = await workflow.execute_trip_planning(
            trip_request=trip_request, user_id="test_user_123", request_id="test_request_789"
        )

        print(f"   - Execution result type: {type(result)}")
        print(
            f"   - Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
        )
        print("   ✅ Trip planning execution successful")

    except Exception as e:
        print(f"   ⚠️ Trip planning execution failed: {e}")

    return True


async def main():
    """Main test function."""
    print("TripPlanningWorkflow Test Suite")
    print("=" * 50)

    try:
        success = await test_workflow_instantiation()

        if success:
            print("\n🎉 Basic workflow tests completed successfully!")
            print("The workflow can be instantiated and basic methods work.")
            print("\nNote: Full execution may require:")
            print("- Redis server running")
            print("- Proper environment configuration")
            print("- Agent implementations in nodes.py")
        else:
            print("\n❌ Some tests failed")

    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

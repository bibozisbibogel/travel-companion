"""Simple test script for Activity Agent functionality."""

import asyncio
from datetime import datetime, timedelta

from travel_companion.agents.activity_agent import ActivityAgent


async def test_activity_agent():
    """Test basic activity agent functionality."""

    print("=" * 60)
    print("Activity Agent Test Script")
    print("=" * 60)

    # Initialize the agent
    print("\n1. Initializing Activity Agent...")
    agent = ActivityAgent()
    print(f"   ✓ Agent initialized: {agent.agent_name} v{agent.agent_version}")

    # Create a test request
    print("\n2. Creating test search request...")
    activity_date = datetime.now() + timedelta(days=14)

    request_data = {
        "location": "Rome, Italy",
        "date": activity_date.isoformat(),
        "guest_count": 2,
        "category": "cultural",  # Options: cultural, adventure, food, entertainment, nature, shopping, relaxation, nightlife
        "duration_hours": 4.0,
        "min_price": 25.0,
        "max_price": 150.0,
        "min_rating": 4.0,
        "accessibility_required": False,
        "child_friendly": False,
        "sort_by": "rating",
        "limit": 5,
    }

    print(f"   Location: {request_data['location']}")
    print(f"   Date: {activity_date.date()}")
    print(f"   Guests: {request_data['guest_count']}")
    print(f"   Category: {request_data['category']}")
    print(f"   Duration: {request_data['duration_hours']} hours")
    print(f"   Price range: ${request_data['min_price']}-${request_data['max_price']}")
    print(f"   Min rating: {request_data['min_rating']}")

    # Process the request
    print("\n3. Searching for activities...")
    try:
        response = await agent.process(request_data)

        print("\n4. Results Summary:")
        print(f"   ✓ Found {response.total_results} activities")
        print(f"   ✓ Search completed in {response.search_time_ms}ms")
        print(f"   ✓ Cached: {response.cached}")

        if response.activities:
            print(f"\n5. Top {min(5, len(response.activities))} Activities:")
            print("-" * 60)

            for i, activity in enumerate(response.activities[:5], 1):
                print(f"\n   Activity #{i}:")
                print(f"   Name: {activity.name}")
                print(f"   Category: {activity.category}")
                print(f"   Price: ${activity.price}/person")
                print(f"   Rating: {activity.rating}/5.0")
                if activity.review_count:
                    print(f"   Reviews: {activity.review_count}")
                if activity.duration_minutes:
                    print(f"   Duration: {activity.duration_minutes} minutes")
                print(f"   Location: {activity.location}")
                if activity.description:
                    desc = (
                        activity.description[:100] + "..."
                        if len(activity.description) > 100
                        else activity.description
                    )
                    print(f"   Description: {desc}")
                # Note: 'included' field may not be available from all providers
                print(f"   Provider: {activity.provider}")
        else:
            print("\n   ⚠ No activities found matching criteria")

        # Test search metadata
        if response.search_metadata:
            print("\n6. Search Metadata:")
            for key, value in response.search_metadata.items():
                print(f"   {key}: {value}")

        print("\n✅ Test completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)


async def test_different_categories():
    """Test activity search with different categories."""

    print("\n" + "=" * 60)
    print("Testing Different Activity Categories")
    print("=" * 60)

    agent = ActivityAgent()
    base_date = datetime.now() + timedelta(days=7)

    categories = ["cultural", "adventure", "food", "entertainment", "nature"]

    for category in categories:
        print(f"\n Testing category: {category.upper()}")
        print("-" * 30)

        request_data = {
            "location": "Paris, France",
            "date": base_date.isoformat(),
            "guest_count": 2,
            "category": category,
            "duration_hours": 3.0,
            "min_price": 20.0,
            "max_price": 200.0,
            "min_rating": 3.5,
        }

        try:
            response = await agent.process(request_data)
            print(f"   ✓ Found {response.total_results} {category} activities")

            if response.activities and len(response.activities) > 0:
                top_activity = response.activities[0]
                print(f"   Top result: {top_activity.name}")
                print(f"   Price: ${top_activity.price}/person")
                print(f"   Rating: {top_activity.rating}/5.0")
        except Exception as e:
            print(f"   ✗ Failed: {e}")

    print("\n✅ Category tests completed!")
    print("=" * 60)


async def test_error_handling():
    """Test error handling scenarios."""

    print("\n" + "=" * 60)
    print("Testing Error Handling")
    print("=" * 60)

    agent = ActivityAgent()

    # Test with invalid date
    print("\n1. Testing past date...")
    past_request = {
        "location": "London",
        "date": (datetime.now() - timedelta(days=1)).isoformat(),
        "guest_count": 2,
        "category": "cultural",
    }

    try:
        response = await agent.process(past_request)
        print(f"   Response: {response}")
    except Exception as e:
        print(f"   ✓ Caught expected error: {e}")

    # Test with missing required fields
    print("\n2. Testing missing required fields...")
    incomplete_request = {"location": "London"}

    try:
        response = await agent.process(incomplete_request)
        print(f"   Response: {response}")
    except Exception as e:
        print(f"   ✓ Caught expected error: {e}")

    # Test with invalid category
    print("\n3. Testing invalid category...")
    invalid_category_request = {
        "location": "London",
        "date": (datetime.now() + timedelta(days=1)).isoformat(),
        "guest_count": 2,
        "category": "invalid_category",
    }

    try:
        response = await agent.process(invalid_category_request)
        print(f"   Response: {response}")
    except Exception as e:
        print(f"   ✓ Caught expected error: {e}")

    # Test with invalid price range
    print("\n4. Testing invalid price range...")
    invalid_price_request = {
        "location": "London",
        "date": (datetime.now() + timedelta(days=1)).isoformat(),
        "guest_count": 2,
        "category": "cultural",
        "min_price": 200.0,
        "max_price": 50.0,  # Max less than min
    }

    try:
        response = await agent.process(invalid_price_request)
        print(f"   Response: {response}")
    except Exception as e:
        print(f"   ✓ Caught expected error: {e}")

    print("\n✅ Error handling tests completed!")
    print("=" * 60)


async def main():
    """Main test runner."""
    print("\nStarting Activity Agent Tests\n")

    # Run basic functionality test
    await test_activity_agent()

    # Run category tests
    # await test_different_categories()

    # Run error handling tests
    # await test_error_handling()

    print("\n🎉 All tests completed!\n")


if __name__ == "__main__":
    # Run the tests
    asyncio.run(main())

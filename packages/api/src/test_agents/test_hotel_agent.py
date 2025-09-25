"""Simple test script for Hotel Agent functionality."""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

from travel_companion.agents.hotel_agent import HotelAgent
from travel_companion.models.external import HotelSearchRequest, HotelSearchResponse


async def test_hotel_agent():
    """Test basic hotel agent functionality."""

    print("=" * 60)
    print("Hotel Agent Test Script")
    print("=" * 60)

    # Initialize the agent
    print("\n1. Initializing Hotel Agent...")
    agent = HotelAgent()
    print(f"   ✓ Agent initialized: {agent.agent_name} v{agent.agent_version}")

    # Create a test request
    print("\n2. Creating test search request...")
    check_in = datetime.now() + timedelta(days=7)
    check_out = check_in + timedelta(days=3)

    request_data = {
        "location": "Paris, France",
        "check_in_date": check_in.isoformat(),
        "check_out_date": check_out.isoformat(),
        "guest_count": 2,
        "room_count": 1,
        "budget": 200.0,  # Use budget instead of min/max price
        "currency": "USD",
        "max_results": 5
    }

    print(f"   Location: {request_data['location']}")
    print(f"   Check-in: {check_in.date()}")
    print(f"   Check-out: {check_out.date()}")
    print(f"   Guests: {request_data['guest_count']}")
    print(f"   Rooms: {request_data['room_count']}")
    print(f"   Max budget: ${request_data['budget']}/night")
    print(f"   Currency: {request_data['currency']}")
    print(f"   Max results: {request_data['max_results']}")

    # Process the request
    print("\n3. Searching for hotels...")
    try:
        response = await agent.process(request_data)

        print(f"\n4. Results Summary:")
        print(f"   ✓ Found {response.total_results} hotels")
        print(f"   ✓ Search completed in {response.search_time_ms}ms")

        if response.hotels:
            print(f"\n5. Top {min(5, len(response.hotels))} Hotels:")
            print("-" * 60)

            for i, hotel in enumerate(response.hotels[:5], 1):
                print(f"\n   Hotel #{i}:")
                print(f"   Name: {hotel.name}")
                print(f"   Price: ${hotel.price_per_night}/night ({hotel.currency})")
                if hotel.rating:
                    print(f"   Rating: {hotel.rating}/5.0")
                else:
                    print(f"   Rating: Not available")
                if hotel.location and hotel.location.address:
                    print(f"   Address: {hotel.location.address}")
                elif hotel.location:
                    print(f"   Location: {hotel.location.latitude}, {hotel.location.longitude}")
                if hotel.amenities:
                    print(f"   Amenities: {', '.join(hotel.amenities[:5])}")
                print(f"   External ID: {hotel.external_id}")
                if hotel.booking_url:
                    print(f"   Booking URL available: Yes")
        else:
            print("\n   ⚠ No hotels found matching criteria")

        # Display search metadata (new structure)
        if hasattr(response, 'search_metadata') and response.search_metadata:
            print(f"\n6. Search Metadata:")
            metadata = response.search_metadata
            if 'successful_api' in metadata:
                print(f"   Successful API: {metadata['successful_api']}")
            if 'apis_attempted' in metadata:
                print(f"   APIs attempted: {', '.join(metadata['apis_attempted'])}")
            if 'google_places_results' in metadata:
                print(f"   Google Places results: {metadata['google_places_results']}")
            if 'api_errors' in metadata and metadata['api_errors']:
                print(f"   API errors: {list(metadata['api_errors'].keys())}")

        # Show cache status
        if hasattr(response, 'cached'):
            print(f"\n7. Cache Information:")
            print(f"   Cached result: {'Yes' if response.cached else 'No'}")
            if hasattr(response, 'cache_expires_at') and response.cache_expires_at:
                print(f"   Cache expires at: {response.cache_expires_at}")

        print(f"\n✅ Test completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)


async def test_error_handling():
    """Test error handling scenarios."""

    print("\n" + "=" * 60)
    print("Testing Error Handling")
    print("=" * 60)

    agent = HotelAgent()

    # Test with invalid dates
    print("\n1. Testing invalid date range...")
    invalid_request = {
        "location": "Paris",
        "check_in_date": datetime.now().isoformat(),
        "check_out_date": (datetime.now() - timedelta(days=1)).isoformat(),
        "guest_count": 2
    }

    try:
        response = await agent.process(invalid_request)
        print(f"   Response: {response}")
    except Exception as e:
        print(f"   ✓ Caught expected error: {e}")

    # Test with missing required fields
    print("\n2. Testing missing required fields...")
    incomplete_request = {
        "location": "Paris"
    }

    try:
        response = await agent.process(incomplete_request)
        print(f"   Response: {response}")
    except Exception as e:
        print(f"   ✓ Caught expected error: {e}")

    print("\n✅ Error handling tests completed!")
    print("=" * 60)


async def main():
    """Main test runner."""
    print("\nStarting Hotel Agent Tests\n")

    # Run basic functionality test
    await test_hotel_agent()

    # Run error handling tests
    #await test_error_handling()

    print("\n🎉 All tests completed!\n")


if __name__ == "__main__":
    # Run the tests
    asyncio.run(main())
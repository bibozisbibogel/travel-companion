#!/usr/bin/env python3
"""
Live test for RapidAPI Booking client with real API key.

This test uses the provided RapidAPI key to test the actual API integration.
Only run this if you want to make real API calls.

Usage:
    python test_rapidapi_live.py
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from travel_companion.services.external_apis.rapidapibooking import (
    RapidAPIBookingClient,
    RapidAPIDestinationSearchParams,
    RapidAPIHotelSearchParams
)


async def test_rapidapi_live():
    """Test RapidAPI with real API calls."""
    
    print("🔧 Testing RapidAPI Booking Client with Live API")
    print("=" * 50)
    
    # Client will automatically get API key from environment via settings
    client = RapidAPIBookingClient()
    
    try:
        # Test 1: Search for destination
        print("\n📍 Test 1: Searching for destination 'New York'...")
        
        dest_params = RapidAPIDestinationSearchParams(query="New York")
        dest_response = await client.search_destination(dest_params)
        
        print(f"✅ Found {len(dest_response.destinations)} destinations")
        if dest_response.destinations:
            dest = dest_response.destinations[0]
            print(f"   First result: {dest.name} (ID: {dest.dest_id})")
            
            # Test 2: Search hotels for the destination
            print(f"\n🏨 Test 2: Searching hotels for {dest.name}...")
            
            hotel_params = RapidAPIHotelSearchParams(
                dest_id=dest.dest_id,
                arrival_date="2025-09-21",
                departure_date="2025-09-27",
                adults=1,
                room_qty=1
            )
            
            hotel_response = await client.search_hotels(hotel_params)
            
            print(f"✅ Found {len(hotel_response.hotels)} hotels")
            print(f"   Total results: {hotel_response.total_results}")
            print(f"   Response time: {hotel_response.api_response_time_ms}ms")
            
            # Show first few hotels
            for i, hotel in enumerate(hotel_response.hotels[:3], 1):
                print(f"\n   Hotel {i}: {hotel.name}")
                print(f"      Price: ${hotel.price_per_night}/night ({hotel.currency})")
                print(f"      Rating: {hotel.rating}/5.0")
                print(f"      Location: {hotel.address}")
                print(f"      Amenities: {len(hotel.amenities)}")
        else:
            print("❌ No destinations found")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()
    
    print("\n🏁 Live API test completed")


async def test_hotel_agent_integration():
    """Test HotelAgent integration with RapidAPI."""
    
    from travel_companion.agents.hotel_agent import HotelAgent
    
    print("\n🏨 Testing HotelAgent with RapidAPI Integration")
    print("=" * 50)
    
    # Create mock dependencies
    from travel_companion.core.config import get_settings
    
    # Use real settings to get API key from environment
    real_settings = get_settings()
    
    class MockDatabase:
        async def health_check(self): return True
        async def close(self): pass
    
    class MockRedis:
        def __init__(self):
            self._cache = {}
        async def ping(self): return True
        async def get(self, key, json_decode=False): return self._cache.get(key)
        async def set(self, key, value, expire=None): 
            self._cache[key] = value
            return True
        async def delete(self, key): return self._cache.pop(key, None) is not None
        async def close(self): pass
    
    database = MockDatabase()
    redis = MockRedis()
    
    agent = HotelAgent(settings=real_settings, database=database, redis=redis)
    
    try:
        print("\n🔍 Searching for hotels in Paris...")
        
        response = await agent.search_hotels_by_location(
            location="Paris, France",
            check_in_date="2025-10-15",
            check_out_date="2025-10-18",
            guest_count=2,
            budget=200.0,
            max_results=5
        )
        
        print(f"✅ Search completed!")
        print(f"   Hotels found: {len(response.hotels)}")
        print(f"   Search time: {response.search_time_ms}ms")
        print(f"   API used: {response.search_metadata.get('successful_api', 'Unknown')}")
        print(f"   Cached: {response.cached}")
        
        if response.hotels:
            print(f"\n   Top hotel: {response.hotels[0].name}")
            print(f"   Price: ${response.hotels[0].price_per_night}/night")
            print(f"   Rating: {response.hotels[0].rating}/5.0")
        
    except Exception as e:
        print(f"❌ HotelAgent test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await agent.cleanup()
        await redis.close()
        await database.close()


def main():
    """Main entry point."""
    import sys
    
    # Skip confirmation if --no-confirm flag is passed
    if "--no-confirm" not in sys.argv:
        print("WARNING: This will make real API calls to RapidAPI!")
        print("Press Ctrl+C to cancel, or Enter to continue...")
        print("(Use --no-confirm to skip this prompt)")
        
        try:
            input()
        except KeyboardInterrupt:
            print("\nTest cancelled.")
            return
    
    # Run tests
    asyncio.run(test_rapidapi_live())
    asyncio.run(test_hotel_agent_integration())


if __name__ == "__main__":
    main()
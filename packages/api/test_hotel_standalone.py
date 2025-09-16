#!/usr/bin/env python3
"""Standalone HotelAgent test script.

This is a self-contained script that creates and tests the HotelAgent
without complex import dependencies. Perfect for quick testing and debugging.

Usage:
    cd packages/api
    python test_hotel_standalone.py
"""

import asyncio
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from travel_companion.agents.hotel_agent import HotelAgent
    from travel_companion.core.config import Settings
    from travel_companion.models.external import (
        HotelOption,
        HotelLocation,
        HotelSearchResponse
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the packages/api directory")
    sys.exit(1)


class TestSettings:
    """Simple test settings class."""
    def __init__(self):
        self.hotel_cache_ttl_seconds = 1800
        self.hotel_max_results = 20
        self.hotel_api_timeout_seconds = 30
        # Mock API configurations to prevent real API calls
        # self.booking_api_key = "mock_key"
        # self.expedia_api_key = "mock_key"
        # self.airbnb_api_key = "mock_key"


class MockDatabase:
    """Mock database for testing."""
    async def health_check(self):
        return True
    
    async def close(self):
        pass


class MockRedis:
    """Mock Redis for testing that matches the real RedisManager interface."""
    def __init__(self):
        self._cache = {}
    
    async def ping(self):
        return True
    
    async def get(self, key, json_decode=False):
        """Mock get method matching RedisManager interface."""
        value = self._cache.get(key)
        if value is None:
            return None
        if json_decode and isinstance(value, str):
            try:
                import json
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value
    
    async def set(self, key, value, expire=None):
        """Mock set method matching RedisManager interface."""
        if isinstance(value, (dict, list)):
            import json
            value = json.dumps(value)
        self._cache[key] = value
        return True
    
    async def delete(self, key):
        return self._cache.pop(key, None) is not None
    
    async def close(self):
        pass


def print_hotel_results(response, title="Hotel Search Results"):
    """Print formatted hotel search results."""
    print(f"\n{'='*60}")
    print(f"{title.upper()}")
    print(f"{'='*60}")
    
    if not response.hotels:
        print("No hotels found.")
        return
    
    print(f"Total Hotels: {len(response.hotels)}")
    print(f"Search Time: {response.search_time_ms}ms")
    print(f"API Used: {response.search_metadata.get('successful_api', 'Mock')}")
    print(f"Cached: {response.cached}")
    
    print(f"\nTop Hotels:")
    for i, hotel in enumerate(response.hotels[:5], 1):
        print(f"\n{i}. {hotel.name}")
        print(f"   💰 Price: ${hotel.price_per_night}/night ({hotel.currency})")
        print(f"   ⭐ Rating: {hotel.rating}/5.0")
        print(f"   📍 Address: {hotel.location.address or 'Not specified'}")
        print(f"   🏨 Amenities: {len(hotel.amenities)}")
        if hotel.amenities:
            amenities_preview = ', '.join(hotel.amenities[:3])
            if len(hotel.amenities) > 3:
                amenities_preview += f" (+{len(hotel.amenities)-3} more)"
            print(f"      {amenities_preview}")


async def test_hotel_search():
    """Test basic hotel search functionality."""
    print("🏨 Starting HotelAgent Standalone Test")
    
    # Create test dependencies
    settings = TestSettings()
    database = MockDatabase()
    redis = MockRedis()
    
    # Create HotelAgent instance
    print("✅ Creating HotelAgent instance...")
    agent = HotelAgent(settings=settings, database=database, redis=redis)
    
    # Test search parameters
    location = "Paris, France"
    check_in = datetime.now() + timedelta(days=30)
    check_out = check_in + timedelta(days=3)
    guests = 2
    budget = 150.0
    
    print(f"📋 Search Parameters:")
    print(f"   Location: {location}")
    print(f"   Check-in: {check_in.strftime('%Y-%m-%d')}")
    print(f"   Check-out: {check_out.strftime('%Y-%m-%d')}")
    print(f"   Guests: {guests}")
    print(f"   Budget: ${budget}/night")
    
    try:
        # Test 1: Basic search
        print("\n🔍 Running hotel search...")
        response = await agent.search_hotels_by_location(
            location=location,
            check_in_date=check_in.strftime('%Y-%m-%d'),
            check_out_date=check_out.strftime('%Y-%m-%d'),
            guest_count=guests,
            budget=budget,
            max_results=10
        )
        
        print_hotel_results(response, "Hotel Search Results")
        
        # Test 2: Hotel ranking (if we found hotels)
        if response.hotels:
            print("\n🏆 Testing hotel ranking...")
            ranked_hotels = agent.rank_hotels(
                hotels=response.hotels,
                search_location=location,
                preferences={
                    "price_weight": 0.3,
                    "rating_weight": 0.4,
                    "location_weight": 0.2,
                    "amenities_weight": 0.1
                }
            )
            
            print(f"\nTop 3 Ranked Hotels:")
            for i, result in enumerate(ranked_hotels[:3], 1):
                print(f"\n#{i} {result.hotel.name}")
                print(f"   🏆 Score: {result.score:.1f}/100")
                print(f"   💰 Price Rank: #{result.price_rank}")
                print(f"   ⭐ Rating Rank: #{result.rating_rank}")
                print(f"   📍 Location Rank: #{result.location_rank}")
                print(f"   💎 Value: {result.value_score:.3f}")
        
        # Test 3: Filtering
        if response.hotels:
            print("\n🔍 Testing hotel filtering...")
            filtered = agent.filter_hotels_by_criteria(
                hotels=response.hotels,
                budget_max=Decimal(str(budget * 0.8)),
                min_rating=4.0
            )
            
            print(f"Hotels under ${budget * 0.8}/night with 4+ stars: {len(filtered)}")
            for hotel in filtered[:2]:
                print(f"   • {hotel.name}: ${hotel.price_per_night}/night, {hotel.rating}⭐")
        
        # Test 4: Direct process method
        print("\n🔧 Testing process method directly...")
        process_data = {
            "location": "Tokyo, Japan",
            "check_in_date": (datetime.now() + timedelta(days=45)).strftime('%Y-%m-%d'),
            "check_out_date": (datetime.now() + timedelta(days=47)).strftime('%Y-%m-%d'),
            "guest_count": 1,
            "budget": 100.0,
            "max_results": 5
        }
        
        process_response = await agent.process(process_data)
        print(f"Process method results: {len(process_response.hotels)} hotels found")
        
        print("\n✅ All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        await redis.close()
        await database.close()


async def interactive_search():
    """Interactive hotel search."""
    print("🏨 Interactive Hotel Search")
    print("=" * 40)
    
    # Get user input
    location = input("Enter location: ").strip() or "New York, NY"
    
    try:
        days_ahead = int(input("Days from now for check-in (30): ") or "30")
    except ValueError:
        days_ahead = 30
    
    try:
        nights = int(input("Number of nights (3): ") or "3")
    except ValueError:
        nights = 3
    
    try:
        guests = int(input("Number of guests (2): ") or "2")
    except ValueError:
        guests = 2
    
    try:
        budget = float(input("Budget per night USD (200): ") or "200")
    except ValueError:
        budget = 200
    
    # Setup
    settings = TestSettings()
    database = MockDatabase()
    redis = MockRedis()
    agent = HotelAgent(settings=settings, database=database, redis=redis)
    
    # Calculate dates
    check_in = datetime.now() + timedelta(days=days_ahead)
    check_out = check_in + timedelta(days=nights)
    
    try:
        print(f"\n🔍 Searching hotels in {location}...")
        
        response = await agent.search_hotels_by_location(
            location=location,
            check_in_date=check_in.strftime('%Y-%m-%d'),
            check_out_date=check_out.strftime('%Y-%m-%d'),
            guest_count=guests,
            budget=budget,
            max_results=15
        )
        
        print_hotel_results(response)
        
        if response.hotels:
            show_ranking = input("\nShow ranked results? (y/n): ").lower().startswith('y')
            if show_ranking:
                ranked = agent.rank_hotels(hotels=response.hotels, search_location=location)
                print(f"\n🏆 TOP RANKED HOTELS:")
                for i, result in enumerate(ranked[:5], 1):
                    print(f"{i}. {result.hotel.name} - Score: {result.score:.1f}/100")
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
    finally:
        await redis.close()
        await database.close()


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        asyncio.run(interactive_search())
    else:
        success = asyncio.run(test_hotel_search())
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
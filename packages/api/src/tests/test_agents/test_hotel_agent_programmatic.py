#!/usr/bin/env python3
"""Programmatic test for HotelAgent - Direct instance testing and real API calls.

This script creates a HotelAgent instance and calls it directly to fetch
hotels for a specific location. Useful for manual testing and debugging.

Usage:
    python test_hotel_agent_programmatic.py
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from travel_companion.agents.hotel_agent import HotelAgent
from travel_companion.core.config import Settings
from travel_companion.core.database import DatabaseManager
from travel_companion.core.redis import RedisManager


# Configure logging for better visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockDatabaseManager:
    """Mock database manager for programmatic testing."""
    
    def __init__(self):
        self.connected = True
    
    async def health_check(self) -> bool:
        """Mock health check."""
        return True
    
    async def close(self):
        """Mock close."""
        pass


class MockRedisManager:
    """Mock Redis manager for programmatic testing."""
    
    def __init__(self):
        self.connected = True
        self._cache = {}
    
    async def ping(self) -> bool:
        """Mock ping."""
        return True
    
    async def get(self, key: str) -> bytes | None:
        """Mock get."""
        return self._cache.get(key)
    
    async def set(self, key: str, value: bytes, ttl: int = None) -> bool:
        """Mock set."""
        self._cache[key] = value
        return True
    
    async def delete(self, key: str) -> bool:
        """Mock delete."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    async def close(self):
        """Mock close."""
        pass


class MockSettings:
    """Mock settings for programmatic testing."""
    
    def __init__(self):
        # Set default values
        self.hotel_cache_ttl_seconds = 1800
        self.hotel_max_results = 20  # Smaller number for testing
        self.hotel_api_timeout_seconds = 30
        self.database_url = "mock://localhost"
        self.redis_url = "mock://localhost:6379"
        self.environment = "test"
        # API keys (empty for mock)
        self.rapidapi_booking_api_key = ""
        self.booking_api_key = ""
        self.expedia_api_key = ""
        self.expedia_secret_key = ""
        self.airbnb_api_key = ""
        # Other required fields
        self.app_name = "Travel Companion API"
        self.debug = False
        self.version = "0.1.0"


async def test_hotel_agent_search():
    """Test HotelAgent hotel search functionality programmatically."""
    logger.info("=== Starting HotelAgent Programmatic Test ===")
    
    # Initialize mock dependencies
    settings = MockSettings()
    database = MockDatabaseManager()
    redis = MockRedisManager()
    
    # Create HotelAgent instance
    logger.info("Creating HotelAgent instance...")
    hotel_agent = HotelAgent(
        settings=settings,
        database=database,
        redis=redis
    )
    
    # Test data
    test_location = "New York, NY"
    check_in_date = datetime.now() + timedelta(days=30)
    check_out_date = check_in_date + timedelta(days=3)
    guest_count = 2
    budget = 200.0  # $200 per night budget
    
    logger.info(f"Test Parameters:")
    logger.info(f"  Location: {test_location}")
    logger.info(f"  Check-in: {check_in_date.strftime('%Y-%m-%d')}")
    logger.info(f"  Check-out: {check_out_date.strftime('%Y-%m-%d')}")
    logger.info(f"  Guests: {guest_count}")
    logger.info(f"  Budget: ${budget}/night")
    
    try:
        # Test 1: Basic hotel search using the convenience method
        logger.info("\n--- Test 1: Basic Hotel Search ---")
        
        response = await hotel_agent.search_hotels_by_location(
            location=test_location,
            check_in_date=check_in_date.strftime('%Y-%m-%d'),
            check_out_date=check_out_date.strftime('%Y-%m-%d'),
            guest_count=guest_count,
            budget=budget,
            max_results=10
        )
        
        logger.info(f"Search Results:")
        logger.info(f"  Total hotels found: {len(response.hotels)}")
        logger.info(f"  Search time: {response.search_time_ms}ms")
        logger.info(f"  Cached: {response.cached}")
        logger.info(f"  API used: {response.search_metadata.get('successful_api', 'None')}")
        
        # Display first few results
        for i, hotel in enumerate(response.hotels[:3]):
            logger.info(f"  Hotel {i+1}: {hotel.name}")
            logger.info(f"    Price: ${hotel.price_per_night}/night ({hotel.currency})")
            logger.info(f"    Rating: {hotel.rating}/5.0")
            logger.info(f"    Amenities: {len(hotel.amenities)} total")
            if hotel.location.address:
                logger.info(f"    Address: {hotel.location.address}")
        
        # Test 2: Hotel ranking and comparison
        if response.hotels:
            logger.info("\n--- Test 2: Hotel Ranking ---")
            
            ranked_hotels = hotel_agent.rank_hotels(
                hotels=response.hotels,
                search_location=test_location,
                budget_filter=Decimal(str(budget)),
                preferences={
                    "price_weight": 0.4,    # Emphasize price more
                    "rating_weight": 0.3,   # Moderate rating weight
                    "location_weight": 0.2, # Location proximity
                    "amenities_weight": 0.1  # Amenities count
                }
            )
            
            logger.info(f"Ranked Results (top 3):")
            for i, result in enumerate(ranked_hotels[:3]):
                logger.info(f"  Rank {i+1}: {result.hotel.name}")
                logger.info(f"    Overall Score: {result.score:.1f}/100")
                logger.info(f"    Price Rank: #{result.price_rank}")
                logger.info(f"    Rating Rank: #{result.rating_rank}")
                logger.info(f"    Location Rank: #{result.location_rank}")
                logger.info(f"    Value Score: {result.value_score:.3f}")
                logger.info(f"    Reasons: {', '.join(result.reasons)}")
        
        # Test 3: Hotel filtering
        if response.hotels:
            logger.info("\n--- Test 3: Hotel Filtering ---")
            
            # Filter for budget-friendly hotels with good ratings
            filtered_hotels = hotel_agent.filter_hotels_by_criteria(
                hotels=response.hotels,
                budget_max=Decimal(str(budget * 0.8)),  # 80% of budget
                min_rating=4.0,  # 4+ star rating
                required_amenities=["WiFi", "Air conditioning"]
            )
            
            logger.info(f"Filtered Results:")
            logger.info(f"  Hotels matching criteria: {len(filtered_hotels)}")
            for hotel in filtered_hotels[:2]:
                logger.info(f"    {hotel.name}: ${hotel.price_per_night}/night, {hotel.rating}★")
        
        # Test 4: Pagination
        if response.hotels:
            logger.info("\n--- Test 4: Results Pagination ---")
            
            paginated_results, pagination_meta = hotel_agent.paginate_results(
                results=response.hotels,
                page=1,
                per_page=5
            )
            
            logger.info(f"Pagination Info:")
            logger.info(f"  Page: {pagination_meta['page']}")
            logger.info(f"  Per page: {pagination_meta['per_page']}")
            logger.info(f"  Total results: {pagination_meta['total']}")
            logger.info(f"  Total pages: {pagination_meta['pages']}")
            logger.info(f"  Has next: {pagination_meta['has_next']}")
            
        # Test 5: Cache functionality
        logger.info("\n--- Test 5: Cache Functionality ---")
        
        # Second identical search should be cached
        cache_start_time = datetime.now()
        cached_response = await hotel_agent.search_hotels_by_location(
            location=test_location,
            check_in_date=check_in_date.strftime('%Y-%m-%d'),
            check_out_date=check_out_date.strftime('%Y-%m-%d'),
            guest_count=guest_count,
            budget=budget,
            max_results=10
        )
        cache_end_time = datetime.now()
        cache_duration_ms = int((cache_end_time - cache_start_time).total_seconds() * 1000)
        
        logger.info(f"Second Search (should be cached):")
        logger.info(f"  Cached: {cached_response.cached}")
        logger.info(f"  Response time: {cache_duration_ms}ms")
        logger.info(f"  Hotels found: {len(cached_response.hotels)}")
        
        # Test 6: Process method with raw request data
        logger.info("\n--- Test 6: Raw Process Method ---")
        
        raw_request_data = {
            "location": "San Francisco, CA",
            "check_in_date": (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d'),
            "check_out_date": (datetime.now() + timedelta(days=17)).strftime('%Y-%m-%d'),
            "guest_count": 1,
            "budget": 150.0,
            "currency": "USD",
            "max_results": 5
        }
        
        logger.info(f"Raw request data: {raw_request_data}")
        
        raw_response = await hotel_agent.process(raw_request_data)
        logger.info(f"Raw response results: {len(raw_response.hotels)} hotels")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        logger.exception("Full traceback:")
        return False
    
    finally:
        # Cleanup
        if redis:
            await redis.close()
        if database:
            await database.close()
    
    logger.info("\n=== HotelAgent Programmatic Test Completed Successfully ===")
    return True


def print_results_summary(results):
    """Print a formatted summary of hotel search results."""
    if not results or not results.hotels:
        print("No hotel results to display")
        return
    
    print(f"\n{'='*60}")
    print(f"HOTEL SEARCH RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Total Hotels Found: {len(results.hotels)}")
    print(f"Search Time: {results.search_time_ms}ms")
    print(f"API Used: {results.search_metadata.get('successful_api', 'Unknown')}")
    print(f"Cached Result: {results.cached}")
    print(f"{'='*60}")
    
    for i, hotel in enumerate(results.hotels[:5], 1):  # Show top 5
        print(f"\n#{i} {hotel.name}")
        print(f"   Price: ${hotel.price_per_night}/night ({hotel.currency})")
        print(f"   Rating: {hotel.rating}/5.0 stars")
        print(f"   Location: {hotel.location.address}")
        print(f"   Amenities: {len(hotel.amenities)} available")
        if hotel.booking_url:
            print(f"   Booking: {hotel.booking_url}")
        print(f"   ID: {hotel.external_id}")


async def interactive_test():
    """Interactive test mode - prompt user for search parameters."""
    print("=== Interactive HotelAgent Test ===")
    print("Enter your hotel search preferences:")
    
    # Get user input
    location = input("Enter location (e.g., 'New York, NY'): ").strip()
    if not location:
        location = "New York, NY"
        
    days_ahead = input("Check-in days from now (default: 30): ").strip()
    try:
        days_ahead = int(days_ahead) if days_ahead else 30
    except ValueError:
        days_ahead = 30
        
    nights = input("Number of nights (default: 3): ").strip()
    try:
        nights = int(nights) if nights else 3
    except ValueError:
        nights = 3
        
    guests = input("Number of guests (default: 2): ").strip()
    try:
        guests = int(guests) if guests else 2
    except ValueError:
        guests = 2
        
    budget_input = input("Budget per night in USD (default: 200): ").strip()
    try:
        budget = float(budget_input) if budget_input else 200.0
    except ValueError:
        budget = 200.0
    
    # Calculate dates
    check_in = datetime.now() + timedelta(days=days_ahead)
    check_out = check_in + timedelta(days=nights)
    
    # Initialize agent
    settings = MockSettings()
    database = MockDatabaseManager()
    redis = MockRedisManager()
    hotel_agent = HotelAgent(settings=settings, database=database, redis=redis)
    
    try:
        print(f"\nSearching for hotels in {location}...")
        print(f"Check-in: {check_in.strftime('%Y-%m-%d')}")
        print(f"Check-out: {check_out.strftime('%Y-%m-%d')}")
        print(f"Guests: {guests}")
        print(f"Budget: ${budget}/night")
        
        # Perform search
        results = await hotel_agent.search_hotels_by_location(
            location=location,
            check_in_date=check_in.strftime('%Y-%m-%d'),
            check_out_date=check_out.strftime('%Y-%m-%d'),
            guest_count=guests,
            budget=budget,
            max_results=10
        )
        
        # Display results
        print_results_summary(results)
        
        # Ask if user wants to see ranking
        if results.hotels and input("\nRank hotels by value? (y/n): ").lower().startswith('y'):
            ranked = hotel_agent.rank_hotels(
                hotels=results.hotels,
                search_location=location,
                budget_filter=Decimal(str(budget))
            )
            
            print(f"\n{'='*60}")
            print("RANKED RESULTS (Top 3)")
            print(f"{'='*60}")
            
            for i, result in enumerate(ranked[:3], 1):
                print(f"\n#{i} {result.hotel.name}")
                print(f"   Overall Score: {result.score:.1f}/100")
                print(f"   Price: ${result.hotel.price_per_night}/night")
                print(f"   Rating: {result.hotel.rating}/5.0")
                print(f"   Value Score: {result.value_score:.3f}")
                print(f"   Ranking Factors: {', '.join(result.reasons)}")
        
    except Exception as e:
        print(f"Error during search: {e}")
    finally:
        await redis.close()
        await database.close()


def main():
    """Main entry point for programmatic testing."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        # Interactive mode
        asyncio.run(interactive_test())
    else:
        # Automated test mode
        success = asyncio.run(test_hotel_agent_search())
        if success:
            print("\n✅ All tests passed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)


if __name__ == "__main__":
    main()
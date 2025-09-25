"""
Standalone test for Google Places API (New) integration.
Run with: python test_google_places.py
"""

import asyncio
import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the src directory to the Python path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from travel_companion.services.external_apis.google_places import GooglePlacesNewAPI


async def test_google_places_api():
    """Test Google Places API with real API calls."""

    # Get API key from environment
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not api_key:
        print("❌ GOOGLE_PLACES_API_KEY not found in environment variables")
        print("Please set it in your .env file or environment")
        return

    print("Starting Google Places API tests...\n")

    async with GooglePlacesNewAPI(api_key=api_key) as client:

        # Test 1: Text Search
        print("1. Testing text search for 'coffee shops in San Francisco'...")
        try:
            places = await client.text_search(
                text_query="coffee shops in San Francisco",
                max_result_count=5
            )
            print(f"✅ Found {len(places)} places")
            if places:
                first_place = places[0]
                print(f"   First result: {first_place.display_name.get('text', 'Unknown')}")
                print(f"   Address: {first_place.formatted_address}")
                print(f"   Rating: {first_place.rating}")
        except Exception as e:
            print(f"❌ Text search failed: {e}")

        print()

        # Test 2: Nearby Search
        print("2. Testing nearby search around Times Square, NY...")
        try:
            # Times Square coordinates
            places = await client.nearby_search(
                location=(40.7580, -73.9855),
                radius=500,
                included_types=["restaurant"],
                max_result_count=5
            )
            print(f"✅ Found {len(places)} nearby restaurants")
            if places:
                for i, place in enumerate(places[:3], 1):
                    print(f"   {i}. {place.display_name.get('text', 'Unknown')} - Rating: {place.rating}")
        except Exception as e:
            print(f"❌ Nearby search failed: {e}")

        print()

        # Test 3: Get Place Details
        print("3. Testing place details retrieval...")
        try:
            # First, search for a place to get its ID
            search_results = await client.text_search(
                text_query="Empire State Building",
                max_result_count=1
            )

            if search_results:
                place_id = search_results[0].id
                print(f"   Getting details for place ID: {place_id[:20]}...")

                place_details = await client.get_place(place_id)
                print(f"✅ Retrieved details for: {place_details.display_name.get('text', 'Unknown')}")
                print(f"   Address: {place_details.formatted_address}")
                print(f"   Phone: {place_details.international_phone_number}")
                print(f"   Website: {place_details.website_uri}")
                print(f"   Google Maps: {place_details.google_maps_uri}")
                print(f"   Number of reviews: {len(place_details.reviews)}")
                print(f"   Number of photos: {len(place_details.photos)}")

                # Test photo URL generation
                if place_details.photos:
                    photo_url = client.get_photo_url(
                        place_details.photos[0].name,
                        max_width=800,
                        max_height=600
                    )
                    print(f"   Sample photo URL: {photo_url}")
            else:
                print("❌ No place found to test details")

        except Exception as e:
            print(f"❌ Place details retrieval failed: {e}")

        print()

        # Test 4: Search with filters
        print("4. Testing search with filters (high-rated, inexpensive restaurants)...")
        try:
            places = await client.text_search(
                text_query="restaurants in Boston",
                min_rating=4.0,
                price_levels=["PRICE_LEVEL_INEXPENSIVE"],
                max_result_count=5
            )
            print(f"✅ Found {len(places)} filtered places")
            for place in places[:3]:
                print(f"   - {place.display_name.get('text', 'Unknown')}")
                print(f"     Rating: {place.rating}, Price: {place.price_level}")
        except Exception as e:
            print(f"❌ Filtered search failed: {e}")

    print("\n✨ Google Places API tests completed!")


if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_google_places_api())
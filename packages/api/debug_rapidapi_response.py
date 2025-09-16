#!/usr/bin/env python3
"""Debug script to inspect RapidAPI response structure."""

import asyncio
import json
from pathlib import Path
import sys

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from travel_companion.services.external_apis.rapidapibooking import RapidAPIBookingClient
import httpx


async def debug_api_response():
    """Debug the actual API response structure."""
    
    client = RapidAPIBookingClient()
    
    # Make raw request to see actual response
    headers = {
        'x-rapidapi-key': client.api_key,
        'x-rapidapi-host': client.host
    }
    
    async with httpx.AsyncClient() as http_client:
        # Test destination search
        print("🔍 Testing Destination Search...")
        dest_response = await http_client.get(
            f"https://{client.host}/api/v1/hotels/searchDestination",
            headers=headers,
            params={"query": "New York"}
        )
        
        print(f"Status: {dest_response.status_code}")
        dest_data = dest_response.json()
        print(f"Response keys: {dest_data.keys() if isinstance(dest_data, dict) else 'Not a dict'}")
        
        if isinstance(dest_data, dict) and "data" in dest_data:
            print(f"Data length: {len(dest_data['data']) if isinstance(dest_data['data'], list) else 'Not a list'}")
            if dest_data['data']:
                print(f"First destination: {json.dumps(dest_data['data'][0], indent=2)}")
        
        # Get first destination ID
        dest_id = None
        if isinstance(dest_data, dict) and "data" in dest_data and dest_data["data"]:
            dest_id = dest_data["data"][0].get("dest_id")
            print(f"\n✅ Got destination ID: {dest_id}")
        
        if dest_id:
            print("\n🏨 Testing Hotel Search...")
            hotel_response = await http_client.get(
                f"https://{client.host}/api/v1/hotels/searchHotels",
                headers=headers,
                params={
                    "dest_id": dest_id,
                    "search_type": "CITY",
                    "arrival_date": "2025-09-21",
                    "departure_date": "2025-09-27",
                    "adults": "1",
                    "room_qty": "1",
                    "page_number": "1",
                    "units": "metric",
                    "temperature_unit": "c",
                    "languagecode": "en-us",
                    "currency_code": "USD"
                }
            )
            
            print(f"Status: {hotel_response.status_code}")
            hotel_data = hotel_response.json()
            print(f"Response keys: {hotel_data.keys() if isinstance(hotel_data, dict) else 'Not a dict'}")
            
            # Save full response for analysis
            with open("rapidapi_hotel_response.json", "w") as f:
                json.dump(hotel_data, f, indent=2)
            print("📄 Full response saved to rapidapi_hotel_response.json")
            
            # Analyze structure
            if isinstance(hotel_data, dict):
                if "data" in hotel_data:
                    data = hotel_data["data"]
                    print(f"\nData type: {type(data)}")
                    if isinstance(data, dict):
                        print(f"Data keys: {data.keys()}")
                        if "hotels" in data:
                            hotels = data["hotels"]
                            print(f"Hotels type: {type(hotels)}")
                            if isinstance(hotels, list) and hotels:
                                print(f"Number of hotels: {len(hotels)}")
                                print(f"\nFirst hotel structure:")
                                print(json.dumps(hotels[0], indent=2)[:1000] + "...")
                    elif isinstance(data, list):
                        print(f"Data is a list with {len(data)} items")
                        if data:
                            print(f"\nFirst item structure:")
                            print(json.dumps(data[0], indent=2)[:1000] + "...")
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(debug_api_response())
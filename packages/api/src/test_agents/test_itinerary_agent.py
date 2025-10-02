"""
Interactive test for ItineraryAgent with pre-fetched flight and weather data.

This test simulates workflow mode where:
- Flight data is pre-fetched (provided)
- Weather data is pre-fetched (provided)
- Hotel, Activity, and Food agents are called by ItineraryAgent

This demonstrates the workflow mode behavior we implemented.
"""

import asyncio
from datetime import datetime
from decimal import Decimal

from dotenv import load_dotenv

from travel_companion.agents.itinerary_agent import ItineraryAgent


def get_prefetched_flight_data():
    """Pre-fetched flight data (simulating workflow mode)."""
    return [
        {
            "flight_number": "AZ610",
            "airline": "ITA Airways",
            "origin": "JFK",
            "destination": "FCO",
            "departure_time": datetime(2024, 6, 15, 18, 30, 0),
            "arrival_time": datetime(2024, 6, 16, 8, 45, 0),
            "duration_minutes": 495,
            "price": Decimal("520.00"),
            "travel_class": "economy",
            "external_id": "az610_jfk_fco",
        },
        {
            "flight_number": "AZ611",
            "airline": "ITA Airways",
            "origin": "FCO",
            "destination": "JFK",
            "departure_time": datetime(2024, 6, 20, 10, 30, 0),
            "arrival_time": datetime(2024, 6, 20, 14, 15, 0),
            "duration_minutes": 525,
            "price": Decimal("520.00"),
            "travel_class": "economy",
            "external_id": "az611_fco_jfk",
        },
    ]


def get_prefetched_weather_data():
    """Pre-fetched weather data (simulating workflow mode)."""
    return {
        "location": "Rome, Italy",
        "latitude": 41.9028,
        "longitude": 12.4964,
        "forecasts": [
            {
                "date": "2024-06-15",
                "temperature_high": 28.0,
                "temperature_low": 18.0,
                "condition": "sunny",
                "description": "Sunny and warm",
                "precipitation_chance": 10,
                "humidity": 55,
                "wind_speed": 12,
            },
            {
                "date": "2024-06-16",
                "temperature_high": 30.0,
                "temperature_low": 20.0,
                "condition": "sunny",
                "description": "Hot and sunny",
                "precipitation_chance": 5,
                "humidity": 50,
                "wind_speed": 10,
            },
            {
                "date": "2024-06-17",
                "temperature_high": 29.0,
                "temperature_low": 19.0,
                "condition": "partly_cloudy",
                "description": "Partly cloudy and pleasant",
                "precipitation_chance": 15,
                "humidity": 58,
                "wind_speed": 14,
            },
            {
                "date": "2024-06-18",
                "temperature_high": 27.0,
                "temperature_low": 18.0,
                "condition": "partly_cloudy",
                "description": "Mild with some clouds",
                "precipitation_chance": 20,
                "humidity": 60,
                "wind_speed": 15,
            },
            {
                "date": "2024-06-19",
                "temperature_high": 31.0,
                "temperature_low": 21.0,
                "condition": "sunny",
                "description": "Beautiful sunny day",
                "precipitation_chance": 5,
                "humidity": 48,
                "wind_speed": 8,
            },
            {
                "date": "2024-06-20",
                "temperature_high": 30.0,
                "temperature_low": 20.0,
                "condition": "sunny",
                "description": "Clear and warm",
                "precipitation_chance": 10,
                "humidity": 52,
                "wind_speed": 10,
            },
        ],
    }


async def main():
    """Test ItineraryAgent with pre-fetched data (workflow mode)."""
    load_dotenv()

    print("=" * 70)
    print("ITINERARY AGENT TEST - WORKFLOW MODE")
    print("=" * 70)
    print("\nThis test simulates workflow mode where:")
    print("  ✅ Flight data: PRE-FETCHED (provided)")
    print("  ✅ Weather data: PRE-FETCHED (provided)")
    print("  🔄 Hotel agent: WILL BE CALLED (via Google Places API)")
    print("  🔄 Activity agent: WILL BE CALLED (via Google Places API)")
    print("  🔄 Food agent: WILL BE CALLED (via Geoapify API)")
    print("\n" + "=" * 70 + "\n")

    agent = ItineraryAgent()

    # Build workflow-style request with pre-fetched data
    itinerary_request = {
        # Trip destination fields
        "destination": "Rome",
        "country": "Italy",
        "country_code": "IT",
        "airport_code": "FCO",
        "latitude": 41.9028,
        "longitude": 12.4964,
        # Trip requirements fields
        "start_date": "2024-06-15",
        "end_date": "2024-06-20",  # Changed from 06-18 to 06-20 for 5-day trip
        "budget": 3000.00,  # Increased budget for longer trip
        "currency": "USD",
        "traveler_count": 2,
        "travel_class": "economy",
        "accommodation_type": "hotel",
        # User preferences
        "user_preferences": {
            "cuisine": ["italian", "local"],
            "activities": ["culture", "sightseeing", "historical"],
        },
        # Pre-fetched data (workflow mode indicators)
        "flight_options": get_prefetched_flight_data(),
        "weather_forecast": get_prefetched_weather_data(),
        # Empty - will trigger API calls to Google Places
        "hotel_options": [],
        "activity_options": [],
        "restaurant_options": [],
    }

    print("Calling ItineraryAgent.process()...\n")

    try:
        response = await agent.process(itinerary_request)

        print("\n" + "=" * 70)
        print("ITINERARY GENERATION SUCCESSFUL")
        print("=" * 70)

        # Print summary
        print(f"\nTrip ID: {response.trip_id}")
        print(f"Total Days: {response.itinerary.total_days}")
        print(f"Total Cost: ${response.total_cost} {response.currency}")
        print(f"Budget Status: {response.budget_status}")
        print(f"Optimization Score: {response.optimization_score:.2f}")
        print(f"Conflicts Detected: {len(response.conflicts)}")

        # Print daily breakdown
        print("\n" + "-" * 70)
        print("DAILY ITINERARY BREAKDOWN")
        print("-" * 70)

        for day in response.itinerary.days:
            print(f"\nDay {day.day_number} - {day.date.strftime('%A, %B %d, %Y')}")
            print(f"  Daily Cost: ${day.daily_cost}")
            if day.weather_summary:
                print(f"  Weather: {day.weather_summary}")
            print(f"  Activities: {len(day.items)} items")

            for item in day.items:
                time_str = item.start_time.strftime("%H:%M")
                print(f"    {time_str} - {item.item_type.upper()}: {item.name}")
                if item.cost and item.cost > 0:
                    print(f"           Cost: ${item.cost}")

        # Print conflicts if any
        if response.conflicts:
            print("\n" + "-" * 70)
            print("CONFLICTS DETECTED")
            print("-" * 70)
            for conflict in response.conflicts:
                print(f"\n  Type: {conflict.get('type', 'unknown')}")
                print(f"  Severity: {conflict.get('severity', 'unknown')}")
                print(f"  Description: {conflict.get('description', 'No description')}")

        print("\n" + "=" * 70)

    except Exception as e:
        print(f"\n❌ Error during itinerary generation: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

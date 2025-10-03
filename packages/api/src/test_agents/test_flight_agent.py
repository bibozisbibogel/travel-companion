"""
Interactive test for FlightAgent with Amadeus API integration.

This test demonstrates the FlightAgent functionality:
- Searches for flights using Amadeus API
- Falls back to mock data if API fails
- Compares and ranks flight options
- Returns optimized flight results
"""

import asyncio
import logging
from datetime import datetime, timedelta

from dotenv import load_dotenv

from travel_companion.agents.flight_agent import FlightAgent


async def main():
    """Test FlightAgent with real API integration."""
    load_dotenv()

    # Configure logging to show INFO level messages
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    print("=" * 70)
    print("FLIGHT AGENT TEST - AMADEUS API INTEGRATION")
    print("=" * 70)
    print("\nThis test demonstrates FlightAgent functionality:")
    print("  🔄 Flight search: Uses Amadeus API (falls back to mock if unavailable)")
    print("  ⚖️  Flight comparison: Ranks flights by price, duration, and convenience")
    print("  📊 Optimization: Returns best-scored flight options")
    print("\n" + "=" * 70 + "\n")

    agent = FlightAgent()

    # Build flight search request
    tomorrow = datetime.now() + timedelta(days=1)
    week_later = tomorrow + timedelta(days=7)

    flight_request = {
        "origin": "LAX",
        "destination": "JFK",
        "departure_date": tomorrow.isoformat(),
        "return_date": week_later.isoformat(),
        "passengers": 2,
        "travel_class": "economy",
        "currency": "USD",
        "max_results": 10,
    }

    print("Flight Search Parameters:")
    print(f"  Route: {flight_request['origin']} → {flight_request['destination']}")
    print(f"  Departure: {tomorrow.strftime('%Y-%m-%d')}")
    print(f"  Return: {week_later.strftime('%Y-%m-%d')}")
    print(f"  Passengers: {flight_request['passengers']}")
    print(f"  Class: {flight_request['travel_class']}")
    print(f"  Max Results: {flight_request['max_results']}")
    print("\nCalling FlightAgent.process()...\n")

    try:
        response = await agent.process(flight_request)

        print("\n" + "=" * 70)
        print("FLIGHT SEARCH SUCCESSFUL")
        print("=" * 70)

        # Print summary
        print(f"\nTotal Results: {response.total_results}")
        print(f"Search Time: {response.search_time_ms}ms")
        print(f"Cached: {response.cached}")
        if response.cache_expires_at:
            print(f"Cache Expires: {response.cache_expires_at.strftime('%Y-%m-%d %H:%M:%S')}")

        # Print flight options
        print("\n" + "-" * 70)
        print("FLIGHT OPTIONS (Ranked by Score)")
        print("-" * 70)

        for idx, flight in enumerate(response.flights, 1):
            print(f"\n#{idx} - {flight.airline} {flight.flight_number}")
            print(f"  Route: {flight.origin} → {flight.destination}")
            print(f"  Departure: {flight.departure_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"  Arrival: {flight.arrival_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"  Duration: {flight.duration_minutes // 60}h {flight.duration_minutes % 60}m")
            print(f"  Stops: {flight.stops}")
            print(f"  Price: {flight.currency} {flight.price}")
            print(f"  Class: {flight.travel_class}")

            # Print comparison metadata if available
            if response.search_metadata.get("comparison_scores"):
                flight_scores = response.search_metadata["comparison_scores"]
                flight_score = next(
                    (s for s in flight_scores if s["flight_id"] == str(flight.flight_id)), None
                )
                if flight_score:
                    print(f"  Score: {flight_score['score']:.1f}/100")
                    print(f"  Price Rank: #{flight_score['price_rank']}")
                    print(f"  Duration Rank: #{flight_score['duration_rank']}")

        # Print metadata
        if response.search_metadata:
            print("\n" + "-" * 70)
            print("SEARCH METADATA")
            print("-" * 70)

            if response.search_metadata.get("ranking_applied"):
                print("  ✓ Flight ranking applied")

            if response.search_metadata.get("error"):
                print(f"  ⚠ Error: {response.search_metadata['error']}")

            if response.search_metadata.get("search_request"):
                req = response.search_metadata["search_request"]
                print(f"  Origin: {req.get('origin')}")
                print(f"  Destination: {req.get('destination')}")
                print(f"  Passengers: {req.get('passengers')}")

        print("\n" + "=" * 70)

    except Exception as e:
        print(f"\n❌ Error during flight search: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

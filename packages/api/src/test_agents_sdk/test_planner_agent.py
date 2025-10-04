"""
Interactive test for TravelPlannerAgent using Claude Agent SDK.

This test demonstrates the agent's capabilities:
- Planning complete trips with all components
- Using Claude Agent SDK for orchestration
- Calling specialized tools for flights, hotels, activities, and restaurants
- Streaming responses during the planning process
"""

import asyncio
import logging
from datetime import date, timedelta
from decimal import Decimal

from dotenv import load_dotenv

from travel_companion.agents_sdk.travel_planner_agent import TravelPlannerAgent
from travel_companion.models.trip import (
    TripDestination,
    TripPlanRequest,
    TripRequirements,
)


async def test_plan_trip():
    """Test TravelPlannerAgent with a complete trip planning request."""
    load_dotenv()

    # Configure logging to show INFO level messages
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    print("=" * 70)
    print("TRAVEL PLANNER AGENT TEST - CLAUDE AGENT SDK")
    print("=" * 70)
    print("\nThis test demonstrates the Claude Agent SDK integration:")
    print("  🤖 Claude Agent SDK: Orchestrates the planning process")
    print("  ✈️  Flight Search: Uses Amadeus API via MCP tool")
    print("  🏨 Hotel Search: Uses Google Places API via MCP tool")
    print("  🎯 Activity Search: Uses Google Places API via MCP tool")
    print("  🍽️  Restaurant Search: Uses Geoapify API via MCP tool")
    print("\n" + "=" * 70 + "\n")

    agent = TravelPlannerAgent()

    # Create trip destination
    destination = TripDestination(
        city="Rome",
        country="Italy",
        country_code="IT",
        airport_code="FCO",
    )

    # Create trip requirements
    tomorrow = date.today() + timedelta(days=1)
    week_after = tomorrow + timedelta(days=7)
    requirements = TripRequirements(
        start_date=tomorrow,
        end_date=week_after,
        budget=Decimal("3000.00"),
        currency="USD",
        travelers=2,
    )

    # Create trip planning request
    trip_request = TripPlanRequest(
        destination=destination,
        requirements=requirements,
        preferences={
            "origin": "New York",
            "accommodation_type": "hotel",
            "activity_types": ["culture", "sightseeing", "historical"],
            "cuisine_preferences": ["italian", "local"],
        },
    )

    print("Planning trip with the following parameters:")
    print(
        f"  📍 Destination: {trip_request.destination.city}, "
        f"{trip_request.destination.country}"
    )
    print(
        f"  📅 Dates: {trip_request.requirements.start_date} to "
        f"{trip_request.requirements.end_date}"
    )
    print(f"  👥 Travelers: {trip_request.requirements.travelers}")
    print(
        f"  💰 Budget: ${trip_request.requirements.budget} "
        f"{trip_request.requirements.currency}"
    )
    print(f"  🎯 Preferences: {trip_request.preferences}")
    print("\n" + "-" * 70 + "\n")

    try:
        print("Starting trip planning (streaming responses)...\n")

        # Stream planning responses
        message_count = 0
        async for message in agent.plan_trip(trip_request):
            message_count += 1

            if message["type"] == "text":
                print(f"\n💬 Agent Response #{message_count}:")
                print("-" * 70)
                print(message["content"])
                print("-" * 70)

            elif message["type"] == "tool_use":
                print(f"\n🔧 Tool Call #{message_count}: {message['tool']}")
                print(f"    Input: {message['input']}")

            elif message["type"] == "complete":
                print(f"\n✅ Planning Complete (after {message_count} messages)")

            elif message["type"] == "error":
                print(f"\n❌ Error: {message['error']}")

            else:
                print(f"\n💬 Unknown message #{message_count}: {message}")

        print("\n" + "=" * 70)
        print("TRIP PLANNING TEST COMPLETED")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error during trip planning: {e}")
        import traceback

        traceback.print_exc()


async def test_query_agent():
    """Test TravelPlannerAgent with a freeform query."""
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    print("\n\n" + "=" * 70)
    print("TRAVEL PLANNER AGENT - FREEFORM QUERY TEST")
    print("=" * 70)
    print("\nTesting freeform query capabilities:")
    print("  💬 Query: 'Find me hotels in Paris for June 2025 under $200/night'")
    print("\n" + "=" * 70 + "\n")

    agent = TravelPlannerAgent()

    query = "Find me hotels in Paris for June 2025 under $200 per night. I prefer boutique hotels in the Marais district."

    try:
        print("Sending query to agent...\n")

        message_count = 0
        async for message in agent.query_agent(query):
            message_count += 1

            if message["type"] == "text":
                print(f"\n💬 Agent Response #{message_count}:")
                print("-" * 70)
                print(message["content"])
                print("-" * 70)

            elif message["type"] == "tool_use":
                print(f"\n🔧 Tool Call #{message_count}: {message['tool']}")
                print(f"   Input: {message['input']}")

            elif message["type"] == "complete":
                print(f"\n✅ Query Complete (after {message_count} messages)")

            elif message["type"] == "error":
                print(f"\n❌ Error: {message['error']}")

        print("\n" + "=" * 70)
        print("QUERY TEST COMPLETED")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error during query: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Run all tests."""
    # Test 1: Complete trip planning
    await test_plan_trip()

    # Test 2: Freeform query
    # Uncomment to run:
    # await test_query_agent()


if __name__ == "__main__":
    asyncio.run(main())

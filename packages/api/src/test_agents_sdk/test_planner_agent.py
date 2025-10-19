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
import sys
from datetime import date, timedelta
from decimal import Decimal

from dotenv import load_dotenv

from travel_companion.agents_sdk.travel_planner_agent import TravelPlannerAgent
from travel_companion.models.trip import (
    AccommodationType,
    TripDestination,
    TripPlanRequest,
    TripRequirements,
)


async def stream_text_output(text: str, delay: float = 0.01) -> None:
    """
    Stream text output character by character to simulate real-time streaming.
    
    Args:
        text: The text to stream
        delay: Delay between characters in seconds
    """
    for char in text:
        print(char, end='', flush=True)
        await asyncio.sleep(delay)
    print()  # New line at the end


async def test_plan_trip(enable_text_streaming: bool = True):
    """Test TravelPlannerAgent with a complete trip planning request.
    
    Args:
        enable_text_streaming: If True, simulate streaming text output character by character
    """
    load_dotenv()

    # Configure logging to show INFO level messages
    logging.basicConfig(
        level=logging.WARNING,
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
    if enable_text_streaming:
        print("  📝 Text Streaming: Agent responses will be streamed in real-time")
    else:
        print("  📝 Text Display: Agent responses will be printed instantly")
    print("\n" + "=" * 70 + "\n")

    agent = TravelPlannerAgent()

    # Create trip destination
    destination = TripDestination(
        city="Rome",
        country="Italy",
        country_code="IT",
        airport_code="FCO",
        latitude=41.9028,  # Rome's latitude
        longitude=12.4964  # Rome's longitude
    )

    # Create trip requirements
    # tomorrow = date.today() + timedelta(days=1)
    # week_after = tomorrow + timedelta(days=7)

    # Use specific dates for testing
    start_date = date(2025, 10, 18)
    end_date = date(2025, 10, 25)
    requirements = TripRequirements(
        start_date=start_date,
        end_date=end_date,
        budget=Decimal("3000.00"),
        currency="EUR",
        travelers=2,
        accommodation_type=AccommodationType.HOTEL,
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
        flight_options=None,
        weather_forecast=None,
        hotel_options=None,
        activity_options=None,
        restaurant_options=None,
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
                # Stream or print text based on configuration
                if enable_text_streaming:
                    await stream_text_output(message["content"], delay=0.005)
                else:
                    print(message["content"])
                print("-" * 70)

            elif message["type"] == "tool_use":
                print(f"\n🔧 Tool Call #{message_count}: {message['tool']}")
                print(f"    Input: {message['input']}")

            elif message["type"] == "tool_result":
                print(f"\n📊 Tool Result #{message_count}:")
                print(f"    Tool Use ID: {message.get('tool_use_id', 'Unknown')}")
                print(f"    Is Error: {message.get('is_error', False)}")
                print("    Content:")
                print("-" * 40)
                content = message.get('content', 'No content')
                print(content[:1000] + "..." if len(content) > 1000 else content)
                print("-" * 40)

            elif message["type"] == "system":
                print(f"\n🔧 System Message #{message_count}:")
                subtype = message.get('subtype', 'unknown')
                print(f"    Subtype: {subtype}")
                if subtype == 'init':
                    data = message.get('data', {})
                    print(f"    Session ID: {data.get('session_id', 'N/A')}")
                    print(f"    Model: {data.get('model', 'N/A')}")
                    print(f"    MCP Servers: {data.get('mcp_servers', [])}")
                    tools = data.get('tools', [])
                    travel_tools = [t for t in tools if t.startswith('mcp__travel__')]
                    print(f"    Travel Tools: {travel_tools}")

            elif message["type"] == "complete":
                print(f"\n✅ Planning Complete (after {message_count} messages)")

            elif message["type"] == "error":
                print(f"\n❌ Error: {message['error']}")

            else:
                print(f"\n💬 Unknown message #{message_count}: {message}")
                print(f"Message: {message}")

    except Exception as e:
        print(f"\n❌ Error during trip planning: {e}")
        import traceback

        traceback.print_exc()


async def test_query_agent(enable_text_streaming: bool = True):
    """Test TravelPlannerAgent with a freeform query.
    
    Args:
        enable_text_streaming: If True, simulate streaming text output character by character
    """
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
                # Stream or print text based on configuration
                if enable_text_streaming:
                    await stream_text_output(message["content"], delay=0.005)
                else:
                    print(message["content"])
                print("-" * 70)

            elif message["type"] == "tool_use":
                print(f"\n🔧 Tool Call #{message_count}: {message['tool']}")
                print(f"   Input: {message['input']}")

            elif message["type"] == "tool_result":
                print(f"\n📊 Tool Result #{message_count}:")
                print(f"    Tool Use ID: {message.get('tool_use_id', 'Unknown')}")
                print(f"    Is Error: {message.get('is_error', False)}")
                print("    Content:")
                print("-" * 40)
                content = message.get('content', 'No content')
                print(content[:1000] + "..." if len(content) > 1000 else content)
                print("-" * 40)

            elif message["type"] == "system":
                print(f"\n🔧 System Message #{message_count}:")
                subtype = message.get('subtype', 'unknown')
                print(f"    Subtype: {subtype}")
                if subtype == 'init':
                    data = message.get('data', {})
                    print(f"    Session ID: {data.get('session_id', 'N/A')}")
                    print(f"    Model: {data.get('model', 'N/A')}")
                    print(f"    MCP Servers: {data.get('mcp_servers', [])}")
                    tools = data.get('tools', [])
                    travel_tools = [t for t in tools if t.startswith('mcp__travel__')]
                    print(f"    Travel Tools: {travel_tools}")

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
    # Check if streaming is disabled via command line argument
    enable_streaming = "--no-streaming" not in sys.argv
    
    # Test 1: Complete trip planning
    await test_plan_trip(enable_text_streaming=enable_streaming)

    # Test 2: Freeform query
    # Uncomment to run:
    # await test_query_agent(enable_text_streaming=enable_streaming)


if __name__ == "__main__":
    # Print usage information
    if "--help" in sys.argv or "-h" in sys.argv:
        print("\nUsage: python test_planner_agent.py [options]")
        print("\nOptions:")
        print("  --no-streaming    Disable text streaming simulation (print instantly)")
        print("  --help, -h        Show this help message")
        print("\nBy default, text responses are streamed character-by-character to simulate")
        print("real-time streaming. Use --no-streaming for instant text display.")
        print()
        sys.exit(0)
    
    asyncio.run(main())

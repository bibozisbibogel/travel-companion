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
from datetime import date
from decimal import Decimal

from dotenv import load_dotenv

from travel_companion.agents_sdk.travel_planner_agent import TravelPlannerAgent
from travel_companion.core.database import get_database_manager
from travel_companion.models.trip import (
    AccommodationType,
    TripDestination,
    TripPlanRequest,
    TripRequirements,
    TripStatus,
)
from travel_companion.services.trip_service import TripService


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


async def save_trip_to_database(
    itinerary, trip_request: TripPlanRequest, user_id: str | None = None
):
    """
    Save the generated trip itinerary to the database.

    Args:
        itinerary: The ItineraryOutput object
        trip_request: The original trip request
        user_id: Optional user ID string (will create a test user if not provided)

    Returns:
        The saved TripResponse object
    """
    try:
        from uuid import UUID

        # Get database connection
        db = get_database_manager()
        trip_service = TripService(db.client)

        # Use provided user_id or create a test user ID
        if user_id is None:
            # For testing, we'll use a fixed test user ID
            # In production, this should be the actual authenticated user's ID
            user_id_str = "00000000-0000-0000-0000-000000000001"
            print(f"\n💡 Using test user_id: {user_id_str}")
            print("   (In production, this would be the authenticated user's ID)")
        else:
            user_id_str = user_id

        # Convert string to UUID
        try:
            user_uuid = UUID(user_id_str)
        except (ValueError, AttributeError) as e:
            print(f"\n❌ Invalid user_id format: {user_id_str}")
            print(f"   Error: {e}")
            print("   user_id must be a valid UUID string")
            return None

        # Create trip in database
        saved_trip = await trip_service.create_trip(
            user_id=user_uuid,
            name=f"Trip to {trip_request.destination.city}",
            description=f"AI-generated travel plan for {trip_request.destination.city}",
            destination=trip_request.destination,
            requirements=trip_request.requirements,
            plan=itinerary,
            status=TripStatus.PLANNING,
        )

        print("\n✅ Trip saved to database!")
        print(f"   Trip ID: {saved_trip.trip_id}")
        print(f"   User ID: {saved_trip.user_id}")
        print(f"   Status: {saved_trip.status}")
        print(f"   Created: {saved_trip.created_at}")
        print(
            f"\n🔗 View in Supabase: "
            f"https://app.supabase.com → Table Editor → trips → {saved_trip.trip_id}"
        )

        return saved_trip

    except Exception as e:
        print(f"\n❌ Error saving to database: {e}")
        import traceback

        traceback.print_exc()
        return None


async def test_plan_trip(
    enable_text_streaming: bool = True, save_to_db: bool = True, user_id: str | None = None
):
    """Test TravelPlannerAgent with a complete trip planning request.

    Args:
        enable_text_streaming: If True, simulate streaming text output character by character
        save_to_db: If True, save the generated itinerary to the database
        user_id: Optional user ID for database save (uses test user if not provided)
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

            elif message["type"] == "itinerary":
                print("\n📋 STRUCTURED ITINERARY RECEIVED")
                print("=" * 70)
                itinerary = message["data"]
                print(
                    f"Destination: {itinerary.trip.destination.city}, "
                    f"{itinerary.trip.destination.country}"
                )
                print(
                    f"Dates: {itinerary.trip.dates.start} to {itinerary.trip.dates.end}"
                )
                print(f"Duration: {itinerary.trip.dates.duration_days} days")
                print(f"Travelers: {itinerary.trip.travelers.count}")
                print(
                    f"Budget: {itinerary.trip.budget.total} "
                    f"{itinerary.trip.budget.currency}"
                )
                print(
                    f"Spent: {itinerary.trip.budget.spent} "
                    f"{itinerary.trip.budget.currency}"
                )
                print(
                    f"Remaining: {itinerary.trip.budget.remaining} "
                    f"{itinerary.trip.budget.currency}"
                )
                print(f"\n✈️  Flights: {itinerary.flights.total_cost}")
                print(
                    f"🏨 Accommodation: {itinerary.accommodation.name} - "
                    f"{itinerary.accommodation.total_cost} for "
                    f"{itinerary.accommodation.nights} nights"
                )
                print(f"\n📅 Daily Itinerary ({len(itinerary.itinerary)} days):")
                for day in itinerary.itinerary:
                    print(f"  Day {day.day} ({day.date}, {day.day_of_week}): {day.title}")
                    print(f"    Activities: {len(day.activities)}")
                    print(
                        f"    Daily Cost: {day.daily_cost.min}-{day.daily_cost.max} "
                        f"{day.daily_cost.currency}"
                    )
                print("=" * 70)

                # Save JSON to file
                import json

                output_path = "itinerary_output.json"
                with open(output_path, "w") as f:
                    json.dump(message["raw_json"], f, indent=2, default=str)
                print(f"\n💾 Saved structured JSON to: {output_path}")

                # Save to database (if enabled)
                if save_to_db:
                    print("\n💾 Saving trip to database...")
                    saved_trip = await save_trip_to_database(itinerary, trip_request, user_id)
                    if saved_trip:
                        print("\n🎉 Trip successfully saved to Supabase!")
                        print("   You can view it in the Supabase dashboard")
                        print(
                            f"   or retrieve it via API using trip_id: {saved_trip.trip_id}"
                        )
                else:
                    print(
                        "\n⏭️  Database save skipped (use --save-to-db flag to enable)"
                    )

            elif message["type"] == "complete":
                print(f"\n✅ Planning Complete (after {message_count} messages)")

            elif message["type"] == "error":
                print(f"\n❌ Error: {message['error']}")

            elif message["type"] == "warning":
                print(f"\n⚠️  Warning: {message.get('message', 'Unknown warning')}")

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
    # Parse command line arguments
    enable_streaming = "--no-streaming" not in sys.argv
    save_to_db = "--save-to-db" in sys.argv or "--db" in sys.argv

    # Parse user_id if provided
    user_id = None
    for arg in sys.argv:
        if arg.startswith("--user-id="):
            user_id = arg.split("=")[1]
        elif arg.startswith("--user="):
            user_id = arg.split("=")[1]

    # Test 1: Complete trip planning
    await test_plan_trip(
        enable_text_streaming=enable_streaming, save_to_db=save_to_db, user_id=user_id
    )

    # Test 2: Freeform query
    # Uncomment to run:
    # await test_query_agent(enable_text_streaming=enable_streaming)


if __name__ == "__main__":
    # Print usage information
    if "--help" in sys.argv or "-h" in sys.argv:
        print("\nUsage: python test_planner_agent.py [options]")
        print("\nOptions:")
        print("  --no-streaming       Disable text streaming simulation (print instantly)")
        print("  --save-to-db, --db   Save generated itinerary to database")
        print("  --user-id=UUID       Specify user ID for database save (default: test user)")
        print("  --user=UUID          Alias for --user-id")
        print("  --help, -h           Show this help message")
        print("\nExamples:")
        print("  # Run with text streaming (default):")
        print("  python test_planner_agent.py")
        print()
        print("  # Run and save to database:")
        print("  python test_planner_agent.py --save-to-db")
        print()
        print("  # Run with specific user ID and save to database:")
        print("  python test_planner_agent.py --save-to-db --user-id=123e4567-e89b-12d3-a456-426614174000")
        print()
        print("  # Run without streaming, save to database:")
        print("  python test_planner_agent.py --no-streaming --save-to-db")
        print()
        print("Notes:")
        print("  - By default, text responses are streamed character-by-character")
        print("  - Database save is DISABLED by default (use --save-to-db to enable)")
        print("  - Itinerary JSON is always saved to 'itinerary_output.json'")
        print("  - Make sure SUPABASE_URL and SUPABASE_KEY are set in .env")
        print()
        sys.exit(0)

    asyncio.run(main())

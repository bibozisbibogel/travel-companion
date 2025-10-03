"""Flight search tools for Claude Agent SDK."""

import json
import logging
from datetime import datetime
from typing import Any

from mcp import Tool

from travel_companion.agents.flight_agent import FlightAgent
from travel_companion.models.external import FlightSearchRequest

logger = logging.getLogger(__name__)


# Tool input schema for flight search
FLIGHT_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "origin": {
            "type": "string",
            "description": "Origin airport code or city name (e.g., 'JFK', 'New York')",
        },
        "destination": {
            "type": "string",
            "description": "Destination airport code or city name (e.g., 'LAX', 'Los Angeles')",
        },
        "departure_date": {
            "type": "string",
            "description": "Departure date in ISO format (YYYY-MM-DD)",
        },
        "return_date": {
            "type": "string",
            "description": "Optional return date in ISO format (YYYY-MM-DD)",
        },
        "passengers": {
            "type": "integer",
            "description": "Number of passengers",
            "default": 1,
        },
        "travel_class": {
            "type": "string",
            "description": "Travel class: economy, premium_economy, business, first",
            "enum": ["economy", "premium_economy", "business", "first"],
            "default": "economy",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of flight options to return",
            "default": 10,
        },
        "currency": {
            "type": "string",
            "description": "Currency code for pricing (e.g., 'USD', 'EUR')",
            "default": "USD",
        },
    },
    "required": ["origin", "destination", "departure_date"],
}


async def search_flights_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Search for flights between origin and destination.

    This tool searches for available flights using the FlightAgent,
    which integrates with AviationStack API and falls back to mock data.

    Args:
        arguments: Flight search parameters including origin, destination, dates, etc.

    Returns:
        Tool result with flight options in JSON format
    """
    logger.info(f"Executing flight search tool with arguments: {arguments}")

    try:
        # Parse and validate input
        origin = arguments.get("origin")
        destination = arguments.get("destination")
        departure_date_str = arguments.get("departure_date")
        return_date_str = arguments.get("return_date")
        passengers = arguments.get("passengers", 1)
        travel_class = arguments.get("travel_class", "economy")
        max_results = arguments.get("max_results", 10)
        currency = arguments.get("currency", "USD")

        if not origin or not destination or not departure_date_str:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "error": "Missing required fields: origin, destination, departure_date",
                                "status": "error",
                            }
                        ),
                    }
                ],
                "isError": True,
            }

        # Parse dates
        try:
            departure_date = datetime.fromisoformat(departure_date_str)
            return_date = (
                datetime.fromisoformat(return_date_str) if return_date_str else None
            )
        except ValueError as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"error": f"Invalid date format: {e}", "status": "error"}
                        ),
                    }
                ],
                "isError": True,
            }

        # Create flight search request
        search_request = FlightSearchRequest(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            passengers=passengers,
            travel_class=travel_class,
            max_results=max_results,
            currency=currency,
        )

        # Execute search using FlightAgent
        flight_agent = FlightAgent()
        search_response = await flight_agent.process(search_request.model_dump())

        # Format response
        result = {
            "status": "success",
            "total_results": search_response.total_results,
            "search_time_ms": search_response.search_time_ms,
            "cached": search_response.cached,
            "flights": [
                {
                    "flight_id": str(flight.flight_id),
                    "airline": flight.airline,
                    "flight_number": flight.flight_number,
                    "origin": flight.origin,
                    "destination": flight.destination,
                    "departure_time": flight.departure_time.isoformat(),
                    "arrival_time": flight.arrival_time.isoformat(),
                    "duration_minutes": flight.duration_minutes,
                    "stops": flight.stops,
                    "price": float(flight.price),
                    "currency": flight.currency,
                    "travel_class": flight.travel_class,
                }
                for flight in search_response.flights[:max_results]
            ],
        }

        logger.info(
            f"Flight search completed: {search_response.total_results} results "
            f"in {search_response.search_time_ms}ms"
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2),
                }
            ]
        }

    except Exception as e:
        logger.error(f"Flight search tool error: {e}", exc_info=True)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"error": str(e), "status": "error", "flights": []}
                    ),
                }
            ],
            "isError": True,
        }


# Create the tool definition for MCP server
flight_search_tool = Tool(
    name="search_flights",
    description=(
        "Search for flights between two locations. Returns available flight options "
        "with pricing, schedules, and airline information. Supports filtering by "
        "travel class, number of passengers, and maximum results."
    ),
    inputSchema=FLIGHT_SEARCH_SCHEMA,
)

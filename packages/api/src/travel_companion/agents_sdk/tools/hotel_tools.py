"""Hotel search tools for Claude Agent SDK."""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from mcp import Tool

from travel_companion.agents.hotel_agent import HotelAgent

logger = logging.getLogger(__name__)


# Tool input schema for hotel search
HOTEL_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "location": {
            "type": "string",
            "description": "City, address, or coordinates for hotel search",
        },
        "check_in_date": {
            "type": "string",
            "description": "Check-in date in ISO format (YYYY-MM-DD)",
        },
        "check_out_date": {
            "type": "string",
            "description": "Check-out date in ISO format (YYYY-MM-DD)",
        },
        "guest_count": {
            "type": "integer",
            "description": "Number of guests",
            "default": 1,
        },
        "room_count": {
            "type": "integer",
            "description": "Number of rooms needed",
            "default": 1,
        },
        "budget_per_night": {
            "type": "number",
            "description": "Maximum budget per night (optional filter)",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of hotel options to return",
            "default": 10,
        },
        "currency": {
            "type": "string",
            "description": "Currency code for pricing (e.g., 'USD', 'EUR')",
            "default": "USD",
        },
    },
    "required": ["location", "check_in_date", "check_out_date", "guest_count"],
}


async def search_hotels_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Search for hotels at a specific location.

    This tool searches for available hotels using the HotelAgent,
    which integrates with Google Places API and other hotel booking services.

    Args:
        arguments: Hotel search parameters including location, dates, guests, etc.

    Returns:
        Tool result with hotel options in JSON format
    """
    logger.info(f"Executing hotel search tool with arguments: {arguments}")

    try:
        # Parse and validate input
        location = arguments.get("location")
        check_in_date_str = arguments.get("check_in_date")
        check_out_date_str = arguments.get("check_out_date")
        guest_count = arguments.get("guest_count", 1)
        room_count = arguments.get("room_count", 1)
        budget_per_night = arguments.get("budget_per_night")
        max_results = arguments.get("max_results", 10)
        currency = arguments.get("currency", "USD")

        if not location or not check_in_date_str or not check_out_date_str:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "error": "Missing required fields: location, check_in_date, check_out_date",
                                "status": "error",
                            }
                        ),
                    }
                ],
                "isError": True,
            }

        # Parse dates
        try:
            check_in_date = datetime.fromisoformat(check_in_date_str)
            check_out_date = datetime.fromisoformat(check_out_date_str)
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

        # Create hotel search request data
        request_data = {
            "location": location,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "guest_count": guest_count,
            "room_count": room_count,
            "budget": Decimal(str(budget_per_night)) if budget_per_night else None,
            "max_results": max_results,
            "currency": currency,
        }

        # Execute search using HotelAgent
        hotel_agent = HotelAgent()
        search_response = await hotel_agent.process(request_data)

        # Calculate number of nights
        nights = (check_out_date - check_in_date).days

        # Format response
        result = {
            "status": "success",
            "total_results": search_response.total_results,
            "search_time_ms": search_response.search_time_ms,
            "cached": search_response.cached,
            "nights": nights,
            "hotels": [
                {
                    "hotel_id": str(hotel.hotel_id),
                    "external_id": hotel.external_id,
                    "name": hotel.name,
                    "location": {
                        "latitude": hotel.location.latitude,
                        "longitude": hotel.location.longitude,
                        "address": hotel.location.address,
                        "city": hotel.location.city,
                        "country": hotel.location.country,
                    },
                    "price_per_night": float(hotel.price_per_night),
                    "total_price": float(hotel.price_per_night * nights),
                    "currency": hotel.currency,
                    "rating": hotel.rating,
                    "amenities": hotel.amenities,
                    "photos": hotel.photos[:3] if hotel.photos else [],  # Limit to 3 photos
                    "booking_url": hotel.booking_url,
                }
                for hotel in search_response.hotels[:max_results]
            ],
        }

        logger.info(
            f"Hotel search completed: {search_response.total_results} results "
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
        logger.error(f"Hotel search tool error: {e}", exc_info=True)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"error": str(e), "status": "error", "hotels": []}
                    ),
                }
            ],
            "isError": True,
        }


# Create the tool definition for MCP server
hotel_search_tool = Tool(
    name="search_hotels",
    description=(
        "Search for hotels at a specific location. Returns available hotel options "
        "with pricing, ratings, amenities, and location information. Supports filtering "
        "by budget, number of guests, rooms, and maximum results."
    ),
    inputSchema=HOTEL_SEARCH_SCHEMA,
)

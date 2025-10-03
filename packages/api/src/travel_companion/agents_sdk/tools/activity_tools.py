"""Activity search tools for Claude Agent SDK."""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from mcp import Tool

from travel_companion.agents.activity_agent import ActivityAgent

logger = logging.getLogger(__name__)


# Tool input schema for activity search
ACTIVITY_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "location": {
            "type": "string",
            "description": "City or location for activity search",
        },
        "date": {
            "type": "string",
            "description": "Date for activities in ISO format (YYYY-MM-DD)",
        },
        "activity_type": {
            "type": "string",
            "description": "Type of activity: sightseeing, adventure, cultural, food, entertainment, outdoor, indoor",
            "enum": [
                "sightseeing",
                "adventure",
                "cultural",
                "food",
                "entertainment",
                "outdoor",
                "indoor",
            ],
        },
        "budget_per_activity": {
            "type": "number",
            "description": "Maximum budget per activity (optional filter)",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of activity options to return",
            "default": 10,
        },
        "currency": {
            "type": "string",
            "description": "Currency code for pricing (e.g., 'USD', 'EUR')",
            "default": "USD",
        },
    },
    "required": ["location", "date"],
}


async def search_activities_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Search for activities and attractions at a location.

    This tool searches for available activities using the ActivityAgent,
    which integrates with Google Places API and activity booking services.

    Args:
        arguments: Activity search parameters including location, date, type, etc.

    Returns:
        Tool result with activity options in JSON format
    """
    logger.info(f"Executing activity search tool with arguments: {arguments}")

    try:
        # Parse and validate input
        location = arguments.get("location")
        date_str = arguments.get("date")
        activity_type = arguments.get("activity_type")
        budget_per_activity = arguments.get("budget_per_activity")
        max_results = arguments.get("max_results", 10)
        currency = arguments.get("currency", "USD")

        if not location or not date_str:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "error": "Missing required fields: location, date",
                                "status": "error",
                            }
                        ),
                    }
                ],
                "isError": True,
            }

        # Parse date
        try:
            activity_date = datetime.fromisoformat(date_str)
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

        # Create activity search request data
        request_data = {
            "location": location,
            "date": activity_date,
            "activity_type": activity_type,
            "budget": Decimal(str(budget_per_activity)) if budget_per_activity else None,
            "max_results": max_results,
            "currency": currency,
        }

        # Execute search using ActivityAgent
        activity_agent = ActivityAgent()
        search_response = await activity_agent.process(request_data)

        # Format response
        result = {
            "status": "success",
            "total_results": search_response.total_results,
            "search_time_ms": search_response.search_time_ms,
            "cached": search_response.cached,
            "activities": [
                {
                    "activity_id": str(activity.activity_id),
                    "external_id": activity.external_id,
                    "name": activity.name,
                    "description": activity.description,
                    "location": {
                        "latitude": activity.location.latitude,
                        "longitude": activity.location.longitude,
                        "address": activity.location.address,
                        "city": activity.location.city,
                        "country": activity.location.country,
                    },
                    "activity_type": activity.activity_type,
                    "price": float(activity.price),
                    "currency": activity.currency,
                    "duration_minutes": activity.duration_minutes,
                    "rating": activity.rating,
                    "photos": activity.photos[:3] if activity.photos else [],
                    "booking_url": activity.booking_url,
                    "available_times": activity.available_times,
                }
                for activity in search_response.activities[:max_results]
            ],
        }

        logger.info(
            f"Activity search completed: {search_response.total_results} results "
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
        logger.error(f"Activity search tool error: {e}", exc_info=True)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"error": str(e), "status": "error", "activities": []}
                    ),
                }
            ],
            "isError": True,
        }


# Create the tool definition for MCP server
activity_search_tool = Tool(
    name="search_activities",
    description=(
        "Search for activities, attractions, and experiences at a specific location. "
        "Returns available activity options with pricing, ratings, duration, and booking "
        "information. Supports filtering by activity type, budget, and maximum results."
    ),
    inputSchema=ACTIVITY_SEARCH_SCHEMA,
)

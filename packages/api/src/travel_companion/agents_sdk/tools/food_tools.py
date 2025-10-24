"""Food and restaurant search tools for Claude Agent SDK."""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from claude_agent_sdk import tool

from travel_companion.agents.food_agent import FoodAgent

logger = logging.getLogger(__name__)


# Tool input schema for food/restaurant search
FOOD_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "location": {
            "type": "string",
            "description": "City or location for restaurant search",
        },
        "date": {
            "type": "string",
            "description": "Date for dining in ISO format (YYYY-MM-DD)",
        },
        "meal_type": {
            "type": "string",
            "description": "Type of meal: breakfast, lunch, dinner, snack",
            "enum": ["breakfast", "lunch", "dinner", "snack"],
        },
        "cuisine_type": {
            "type": "string",
            "description": "Preferred cuisine type (e.g., 'Italian', 'Japanese', 'Mexican')",
        },
        "budget_per_person": {
            "type": "number",
            "description": "Maximum budget per person (optional filter)",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of restaurant options to return",
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


@tool(
    "search_restaurants",
    "Search for restaurants and dining options at a specific location. "
    "Returns available restaurant options with cuisine types, pricing, ratings, "
    "and booking information. Supports filtering by meal type, cuisine, budget, "
    "and maximum results.",
    FOOD_SEARCH_SCHEMA,
)
async def search_restaurants(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Search for restaurants and dining options at a location.

    This tool searches for available restaurants using the FoodAgent,
    which integrates with Google Places API and restaurant booking services.

    Args:
        arguments: Food search parameters including location, date, meal type, etc.

    Returns:
        Tool result with restaurant options in JSON format
    """
    logger.info(f"Executing food search tool with arguments: {arguments}")

    try:
        # Parse and validate input
        location = arguments.get("location")
        date_str = arguments.get("date")
        meal_type = arguments.get("meal_type")
        cuisine_type = arguments.get("cuisine_type")
        budget_per_person = arguments.get("budget_per_person")
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
            dining_date = datetime.fromisoformat(date_str)
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

        # Create food search request data
        request_data = {
            "location": location,
            "date": dining_date,
            "meal_type": meal_type,
            "cuisine_type": cuisine_type,
            "budget": Decimal(str(budget_per_person)) if budget_per_person else None,
            "max_results": max_results,
            "currency": currency,
        }

        # Execute search using FoodAgent
        food_agent = FoodAgent()
        search_response = await food_agent.process(request_data)

        # Format response
        result = {
            "status": "success",
            "total_results": search_response.total_results,
            "search_time_ms": search_response.search_time_ms,
            "cached": search_response.cached,
            "restaurants": [
                {
                    "restaurant_id": str(restaurant.restaurant_id),
                    "external_id": restaurant.external_id,
                    "name": restaurant.name,
                    "categories": restaurant.categories,
                    "location": {
                        "latitude": restaurant.location.latitude,
                        "longitude": restaurant.location.longitude,
                        "address": restaurant.location.address,
                        "city": restaurant.location.city,
                    },
                    "formatted_address": restaurant.formatted_address,
                    "distance_meters": restaurant.distance_meters,
                    "provider": restaurant.provider,
                }
                for restaurant in search_response.restaurants[:max_results]
            ],
        }

        logger.info(
            f"Food search completed: {search_response.total_results} results "
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
        logger.error(f"Food search tool error: {e}", exc_info=True)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"error": str(e), "status": "error", "restaurants": []}),
                }
            ],
            "isError": True,
        }

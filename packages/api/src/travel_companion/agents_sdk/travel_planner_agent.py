"""Main travel planner agent using Claude Agent SDK."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, AsyncIterator

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, create_sdk_mcp_server
from travel_companion.core.config import Settings, get_settings
from travel_companion.agents_sdk.constants import TRAVEL_PLANNER_SYSTEM_PROMPT
from travel_companion.agents_sdk.tools import (
    search_activities,
    search_flights,
    search_restaurants,
    search_hotels,
)
from travel_companion.models.trip import TripPlanRequest

logger = logging.getLogger(__name__)


class TravelPlannerAgent:
    """
    Main orchestrator agent for travel planning using Claude Agent SDK.

    This agent coordinates all travel planning activities including:
    - Flight search and booking
    - Hotel accommodation search
    - Activity and attraction planning
    - Restaurant recommendations
    - Itinerary generation

    The agent uses Claude's reasoning capabilities combined with specialized
    tools to create comprehensive travel plans.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize the travel planner agent.

        Args:
            settings: Application settings instance
        """
        self.settings = settings or get_settings()

        # System prompt for travel planning
        self.system_prompt = TRAVEL_PLANNER_SYSTEM_PROMPT

        # Create MCP server with travel planning tools
        self.mcp_server = create_sdk_mcp_server(
            name="travel-planning-tools",
            version="1.0.0",
            tools=[
                search_flights,
                search_hotels,
                search_activities,
                search_restaurants,
            ],
        )

        logger.info("TravelPlannerAgent initialized with claude_agent_sdk")

    async def plan_trip(
        self, trip_request: TripPlanRequest
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Plan a complete trip based on user requirements.

        This method streams the planning process, yielding updates as each
        component of the trip is planned.

        Args:
            trip_request: Trip planning request with destination, dates, budget, etc.

        Yields:
            Planning progress updates and final trip plan

        Example:
            >>> agent = TravelPlannerAgent()
            >>> request = TripPlanRequest(
            ...     destination="Paris",
            ...     start_date=date(2025, 6, 1),
            ...     end_date=date(2025, 6, 7),
            ...     budget=Decimal("3000"),
            ...     travelers=2
            ... )
            >>> async for update in agent.plan_trip(request):
            ...     print(update)
        """
        logger.info(f"Starting trip planning for: {trip_request.destination}")

        # Convert trip request to natural language prompt
        prompt = self._create_planning_prompt(trip_request)

        # Configure Claude Agent SDK options
        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            mcp_servers={"travel": self.mcp_server},
            allowed_tools=[
                "mcp__travel__search_flights",
                "mcp__travel__search_hotels",
                "mcp__travel__search_activities",
                "mcp__travel__search_restaurants",
            ],
        )

        try:
            # Stream planning using ClaudeSDKClient
            logger.info(f"Starting query with MCP server: travel")
            async with ClaudeSDKClient(options) as client:
                await client.query(prompt)
                async for message in client.receive_response():
                    # Convert SDK message to our format
                    yield self._convert_message(message)

        except Exception as e:
            logger.error(f"Error during trip planning: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
            }

    def _create_planning_prompt(self, trip_request: TripPlanRequest) -> str:
        """
        Create a natural language prompt from trip request.

        Args:
            trip_request: Structured trip planning request

        Returns:
            Natural language prompt for Claude
        """
        prompt_parts = [
            f"I need help planning a trip to {trip_request.destination.city}, {trip_request.destination.country}.",
            f"Travel dates: {trip_request.requirements.start_date.isoformat()} to {trip_request.requirements.end_date.isoformat()}",
            f"Number of travelers: {trip_request.requirements.travelers}",
        ]

        # Calculate number of nights
        nights = (trip_request.requirements.end_date - trip_request.requirements.start_date).days
        prompt_parts.append(f"Duration: {nights} nights")

        if trip_request.requirements.budget:
            prompt_parts.append(f"Total budget: {trip_request.requirements.budget} {trip_request.requirements.currency}")

        if trip_request.preferences and trip_request.preferences.get("origin"):
            prompt_parts.append(f"Traveling from: {trip_request.preferences['origin']}")

        if trip_request.preferences:
            prefs = []
            if trip_request.preferences.get("accommodation_type"):
                prefs.append(
                    f"Accommodation preference: {trip_request.preferences['accommodation_type']}"
                )
            activity_types = trip_request.preferences.get("activity_types")
            if activity_types and isinstance(activity_types, list):
                prefs.append(
                    f"Interested in: {', '.join(activity_types)}"
                )
            cuisine_preferences = trip_request.preferences.get("cuisine_preferences")
            if cuisine_preferences and isinstance(cuisine_preferences, list):
                prefs.append(
                    f"Cuisine preferences: {', '.join(cuisine_preferences)}"
                )
            if prefs:
                prompt_parts.append("\n".join(prefs))

        prompt_parts.append(
            "\nPlease help me plan this trip by:\n"
            "1. Finding suitable flights (if origin is provided)\n"
            "2. Searching for accommodations within budget\n"
            "3. Suggesting activities and attractions\n"
            "4. Recommending restaurants for different meals\n"
            "5. Creating a day-by-day itinerary\n\n"
            "Start by searching for the main components and then create a cohesive plan."
        )

        return "\n".join(prompt_parts)

    async def query_agent(self, user_query: str) -> AsyncIterator[dict[str, Any]]:
        """
        Send a freeform query to the travel planner agent.

        This method allows for more flexible interactions where the user
        can ask questions or make requests in natural language.

        Args:
            user_query: User's question or request

        Yields:
            Agent responses and tool execution results

        Example:
            >>> agent = TravelPlannerAgent()
            >>> async for response in agent.query_agent("Find me cheap hotels in Tokyo for next month"):
            ...     print(response)
        """
        logger.info(f"Processing query: {user_query}")

        # Configure Claude Agent SDK options
        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            mcp_servers={"travel": self.mcp_server},
            allowed_tools=[
                "mcp__travel__search_flights",
                "mcp__travel__search_hotels",
                "mcp__travel__search_activities",
                "mcp__travel__search_restaurants",
            ],
        )

        try:
            # Stream query results using ClaudeSDKClient
            async with ClaudeSDKClient(options) as client:
                await client.query(user_query)
                async for message in client.receive_response():
                    yield self._convert_message(message)

        except Exception as e:
            logger.error(f"Error during query: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
            }

    def _convert_message(self, sdk_message: Any) -> dict[str, Any]:
        """
        Convert Claude Agent SDK message to our standardized format.

        Args:
            sdk_message: Message object from claude_agent_sdk

        Returns:
            Converted message dictionary
        """
        # The SDK returns Message objects with .content and .type attributes
        # We need to convert these to our format for the API

        logger.debug(f"Converting SDK message: {type(sdk_message).__name__}")

        message_dict = {
            "type": "unknown",
            "content": str(sdk_message)
        }

        try:
            # Check if it's a text message (AssistantMessage, UserMessage, etc.)
            if hasattr(sdk_message, "content"):
                logger.debug(f"Message has content: {sdk_message.content}")
                for content_block in sdk_message.content:
                    block_type = type(content_block).__name__
                    logger.debug(f"Content block type: {block_type}")

                    # Handle TextBlock
                    if block_type == "TextBlock":
                        message_dict = {
                            "type": "text",
                            "content": content_block.text if hasattr(content_block, "text") else str(content_block),
                        }

                    # Handle ToolUseBlock
                    elif block_type == "ToolUseBlock":
                        message_dict = {
                            "type": "tool_use",
                            "tool": content_block.name if hasattr(content_block, "name") else "unknown",
                            "input": content_block.input if hasattr(content_block, "input") else {},
                        }

                    # Handle ToolResultBlock
                    elif block_type == "ToolResultBlock":
                        # Extract content from ToolResultBlock
                        result_content = ""
                        if hasattr(content_block, "content"):
                            # content is typically a list of content blocks
                            if isinstance(content_block.content, list):
                                for result_item in content_block.content:
                                    if hasattr(result_item, "text"):
                                        result_content += result_item.text
                                    elif isinstance(result_item, dict) and "text" in result_item:
                                        result_content += result_item["text"]
                                    else:
                                        result_content += str(result_item)
                            else:
                                result_content = str(content_block.content)
                        
                        message_dict = {
                            "type": "tool_result",
                            "tool_use_id": content_block.tool_use_id if hasattr(content_block, "tool_use_id") else None,
                            "content": result_content,
                            "is_error": content_block.is_error if hasattr(content_block, "is_error") else None,
                        }

            # Handle ResultMessage (final completion)
            if type(sdk_message).__name__ == "ResultMessage":
                message_dict = {
                    "type": "complete",
                    "result": sdk_message.result if hasattr(sdk_message, "result") else None,
                }

            # Handle SystemMessage (initialization and system events)
            elif type(sdk_message).__name__ == "SystemMessage":
                # Extract subtype and data if available
                subtype = None
                data = None
                
                if hasattr(sdk_message, "subtype"):
                    subtype = sdk_message.subtype
                if hasattr(sdk_message, "data"):
                    data = sdk_message.data
                
                message_dict = {
                    "type": "system",
                    "subtype": subtype,
                    "data": data,
                }

        except Exception as e:
            logger.warning(f"Error converting message: {e}", exc_info=True)
            message_dict = {
                "type": "error",
                "content": str(sdk_message),
            }

        logger.debug(f"Converted message: {message_dict}")
        return message_dict

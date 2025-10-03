"""Main travel planner agent using Claude Agent SDK."""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, AsyncIterator

from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from travel_companion.agents_sdk.mcp_server import create_travel_mcp_server
from travel_companion.core.config import Settings, get_settings
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
        self.anthropic_client = Anthropic(api_key=self.settings.anthropic_api_key)

        # System prompt for travel planning
        self.system_prompt = """You are an expert travel planning assistant with access to tools for searching flights, hotels, activities, and restaurants.

Your role is to help users plan comprehensive trips by:
1. Understanding their travel requirements (destination, dates, budget, preferences)
2. Searching for suitable flights using the search_flights tool
3. Finding appropriate accommodations using the search_hotels tool
4. Discovering activities and attractions using the search_activities tool
5. Recommending restaurants using the search_restaurants tool
6. Creating a well-organized itinerary that fits their budget and preferences

When planning trips:
- Always ask for clarification if requirements are unclear
- Stay within the user's budget constraints
- Consider travel time, distances, and logistics
- Provide multiple options when appropriate
- Include practical details like booking URLs and pricing

Be proactive, helpful, and thorough in your planning."""

        logger.info("TravelPlannerAgent initialized")

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

        # Create MCP server and session
        server = create_travel_mcp_server()

        # Start MCP server in stdio mode
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "travel_companion.agents_sdk.mcp_server"],
            env=None,
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize session
                    await session.initialize()

                    # List available tools
                    tools_result = await session.list_tools()
                    available_tools = [tool.name for tool in tools_result.tools]

                    logger.info(f"Available tools: {available_tools}")

                    # Stream Claude's response with tool use
                    messages = [{"role": "user", "content": prompt}]

                    # Track conversation for multi-turn planning
                    max_turns = 10
                    turn = 0

                    while turn < max_turns:
                        turn += 1

                        # Send message to Claude
                        response = self.anthropic_client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=4096,
                            system=self.system_prompt,
                            messages=messages,
                            tools=[
                                {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "input_schema": tool.inputSchema,
                                }
                                for tool in tools_result.tools
                            ],
                        )

                        # Process response
                        assistant_message = {"role": "assistant", "content": []}

                        for content_block in response.content:
                            if content_block.type == "text":
                                # Yield text updates to user
                                yield {
                                    "type": "text",
                                    "content": content_block.text,
                                    "turn": turn,
                                }
                                assistant_message["content"].append(content_block)

                            elif content_block.type == "tool_use":
                                # Execute tool and get result
                                tool_name = content_block.name
                                tool_input = content_block.input

                                logger.info(
                                    f"Executing tool: {tool_name} with input: {tool_input}"
                                )

                                yield {
                                    "type": "tool_use",
                                    "tool": tool_name,
                                    "input": tool_input,
                                    "turn": turn,
                                }

                                # Call tool via MCP
                                tool_result = await session.call_tool(tool_name, tool_input)

                                # Add tool use to assistant message
                                assistant_message["content"].append(content_block)

                                # Add tool result to messages
                                messages.append(assistant_message)
                                messages.append(
                                    {
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "tool_result",
                                                "tool_use_id": content_block.id,
                                                "content": [
                                                    {"type": "text", "text": tc.text}
                                                    for tc in tool_result
                                                ],
                                            }
                                        ],
                                    }
                                )

                                yield {
                                    "type": "tool_result",
                                    "tool": tool_name,
                                    "result": tool_result,
                                    "turn": turn,
                                }

                                # Continue conversation
                                break

                        # Check if we're done (no more tool uses)
                        if response.stop_reason == "end_turn":
                            messages.append(assistant_message)
                            logger.info("Trip planning completed")
                            yield {
                                "type": "complete",
                                "final_response": assistant_message,
                                "total_turns": turn,
                            }
                            break

                        # Check if we hit token limit
                        if response.stop_reason == "max_tokens":
                            logger.warning("Hit max tokens, summarizing...")
                            messages.append(assistant_message)
                            # Ask Claude to summarize
                            messages.append(
                                {
                                    "role": "user",
                                    "content": "Please provide a concise summary of the trip plan.",
                                }
                            )
                            # Continue to next turn

        except Exception as e:
            logger.error(f"Error during trip planning: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
                "turn": turn,
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
            f"I need help planning a trip to {trip_request.destination}.",
            f"Travel dates: {trip_request.start_date.isoformat()} to {trip_request.end_date.isoformat()}",
            f"Number of travelers: {trip_request.travelers}",
        ]

        # Calculate number of nights
        nights = (trip_request.end_date - trip_request.start_date).days
        prompt_parts.append(f"Duration: {nights} nights")

        if trip_request.budget:
            prompt_parts.append(f"Total budget: {trip_request.budget} {trip_request.currency}")

        if trip_request.origin:
            prompt_parts.append(f"Traveling from: {trip_request.origin}")

        if trip_request.preferences:
            prefs = []
            if trip_request.preferences.get("accommodation_type"):
                prefs.append(
                    f"Accommodation preference: {trip_request.preferences['accommodation_type']}"
                )
            if trip_request.preferences.get("activity_types"):
                prefs.append(
                    f"Interested in: {', '.join(trip_request.preferences['activity_types'])}"
                )
            if trip_request.preferences.get("cuisine_preferences"):
                prefs.append(
                    f"Cuisine preferences: {', '.join(trip_request.preferences['cuisine_preferences'])}"
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

    async def query(self, prompt: str) -> AsyncIterator[dict[str, Any]]:
        """
        Send a freeform query to the travel planner agent.

        This method allows for more flexible interactions where the user
        can ask questions or make requests in natural language.

        Args:
            prompt: User's question or request

        Yields:
            Agent responses and tool execution results

        Example:
            >>> agent = TravelPlannerAgent()
            >>> async for response in agent.query("Find me cheap hotels in Tokyo for next month"):
            ...     print(response)
        """
        logger.info(f"Processing query: {prompt}")

        # Similar to plan_trip but with a direct prompt
        server = create_travel_mcp_server()
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "travel_companion.agents_sdk.mcp_server"],
            env=None,
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()

                    messages = [{"role": "user", "content": prompt}]
                    max_turns = 5
                    turn = 0

                    while turn < max_turns:
                        turn += 1

                        response = self.anthropic_client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=2048,
                            system=self.system_prompt,
                            messages=messages,
                            tools=[
                                {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "input_schema": tool.inputSchema,
                                }
                                for tool in tools_result.tools
                            ],
                        )

                        assistant_message = {"role": "assistant", "content": []}

                        for content_block in response.content:
                            if content_block.type == "text":
                                yield {
                                    "type": "text",
                                    "content": content_block.text,
                                    "turn": turn,
                                }
                                assistant_message["content"].append(content_block)

                            elif content_block.type == "tool_use":
                                tool_result = await session.call_tool(
                                    content_block.name, content_block.input
                                )
                                assistant_message["content"].append(content_block)
                                messages.append(assistant_message)
                                messages.append(
                                    {
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "tool_result",
                                                "tool_use_id": content_block.id,
                                                "content": [
                                                    {"type": "text", "text": tc.text}
                                                    for tc in tool_result
                                                ],
                                            }
                                        ],
                                    }
                                )
                                yield {
                                    "type": "tool_result",
                                    "tool": content_block.name,
                                    "result": tool_result,
                                    "turn": turn,
                                }
                                break

                        if response.stop_reason == "end_turn":
                            messages.append(assistant_message)
                            yield {
                                "type": "complete",
                                "final_response": assistant_message,
                                "total_turns": turn,
                            }
                            break

        except Exception as e:
            logger.error(f"Error during query: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
                "turn": turn,
            }

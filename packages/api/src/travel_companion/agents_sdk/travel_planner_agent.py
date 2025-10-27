"""Main travel planner agent using Claude Agent SDK."""

import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, create_sdk_mcp_server
from pydantic import ValidationError

from travel_companion.agents_sdk.constants import TRAVEL_PLANNER_SYSTEM_PROMPT
from travel_companion.agents_sdk.tools import (
    search_activities,
    search_flights,
    search_hotels,
    search_restaurants,
)
from travel_companion.core.config import Settings, get_settings
from travel_companion.models.itinerary_output import ItineraryOutput
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

    async def plan_trip(self, trip_request: TripPlanRequest) -> AsyncIterator[dict[str, Any]]:
        """
        Plan a complete trip based on user requirements.

        This method streams the planning process, yielding updates as each
        component of the trip is planned. After all streaming completes,
        it yields a final 'itinerary' message with the parsed JSON structure.

        Args:
            trip_request: Trip planning request with destination, dates, budget, etc.

        Yields:
            Planning progress updates (text, tool_use, tool_result, system)
            Final message with type='itinerary' containing TripItinerary object

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
            ...     if update["type"] == "itinerary":
            ...         itinerary = update["data"]  # TripItinerary object
            ...         print(f"Total cost: {itinerary.total_cost}")
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

        # Accumulate all text responses for final parsing
        accumulated_text = []

        try:
            # Stream planning using ClaudeSDKClient
            logger.info("Starting query with MCP server: travel")
            async with ClaudeSDKClient(options) as client:
                await client.query(prompt)
                async for message in client.receive_response():
                    # Convert SDK message to our format
                    converted = self._convert_message(message)

                    # Accumulate text messages for parsing
                    if converted["type"] == "text":
                        accumulated_text.append(converted["content"])

                    # Yield streaming updates
                    yield converted

            # After streaming completes, parse the accumulated text
            full_response = "\n".join(accumulated_text)
            logger.debug(f"Accumulated {len(accumulated_text)} text messages")

            itinerary = await self._parse_itinerary_response(full_response)

            if itinerary:
                # Yield final structured itinerary
                yield {
                    "type": "itinerary",
                    "data": itinerary,
                    "raw_json": itinerary.model_dump(mode="json"),
                }
                logger.info("Successfully yielded structured itinerary")
            else:
                logger.warning("Failed to parse itinerary from agent response")
                yield {
                    "type": "warning",
                    "message": "Could not parse structured itinerary from response",
                    "raw_text": full_response,
                }

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
            prompt_parts.append(
                f"Total budget: {trip_request.requirements.budget} {trip_request.requirements.currency}"
            )

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
                prefs.append(f"Interested in: {', '.join(activity_types)}")
            cuisine_preferences = trip_request.preferences.get("cuisine_preferences")
            if cuisine_preferences and isinstance(cuisine_preferences, list):
                prefs.append(f"Cuisine preferences: {', '.join(cuisine_preferences)}")
            if prefs:
                prompt_parts.append("\n".join(prefs))

        prompt_parts.append(
            "\nPlease help me plan this trip by:\n"
            "1. Finding suitable flights\n"
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

        message_dict: dict[str, Any] = {"type": "unknown", "content": str(sdk_message)}

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
                            "content": content_block.text
                            if hasattr(content_block, "text")
                            else str(content_block),
                        }

                    # Handle ToolUseBlock
                    elif block_type == "ToolUseBlock":
                        message_dict = {
                            "type": "tool_use",
                            "tool": content_block.name
                            if hasattr(content_block, "name")
                            else "unknown",
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
                            "tool_use_id": content_block.tool_use_id
                            if hasattr(content_block, "tool_use_id")
                            else None,
                            "content": result_content,
                            "is_error": content_block.is_error
                            if hasattr(content_block, "is_error")
                            else None,
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

    async def _parse_itinerary_response(self, accumulated_text: str) -> ItineraryOutput | None:
        """
        Parse accumulated text response to extract structured JSON itinerary.

        Looks for JSON within markdown code blocks or raw JSON in the response.
        Validates against ItineraryOutput Pydantic model.

        Args:
            accumulated_text: Full text response from the agent

        Returns:
            ItineraryOutput object if parsing succeeds, None otherwise

        Example:
            >>> text = "Here is your itinerary:\n```json\n{...}\n```"
            >>> itinerary = agent._parse_itinerary_response(text)
        """
        logger.info("Attempting to parse itinerary from accumulated response")

        # Try to extract JSON from markdown code block first
        json_match = re.search(
            r"```json\s*\n(.*?)\n```", accumulated_text, re.DOTALL | re.IGNORECASE
        )

        json_str = None
        if json_match:
            json_str = json_match.group(1).strip()
            logger.debug("Found JSON in markdown code block")
        else:
            # Try to find raw JSON object
            json_match = re.search(r"\{[\s\S]*\}", accumulated_text)
            if json_match:
                json_str = json_match.group(0).strip()
                logger.debug("Found raw JSON object")

        if not json_str:
            logger.warning("No JSON found in response text")
            return None

        try:
            # Parse JSON string to dict
            data = json.loads(json_str)
            logger.debug(f"Successfully parsed JSON with keys: {data.keys()}")

            # Validate and convert to ItineraryOutput model
            itinerary = ItineraryOutput(**data)
            logger.info(
                f"Successfully validated itinerary: {len(itinerary.itinerary)} days of activities"
            )

            # Geocode all locations in the itinerary (optional - non-blocking)
            # If geocoding fails for any reason, we still return the itinerary without coordinates
            try:
                logger.info("Starting geocoding for itinerary locations")

                # Check if geocoding is available (API key configured)
                from travel_companion.core.config import get_settings

                settings = get_settings()

                if not settings.google_places_api_key:
                    logger.info("Google Maps API key not configured, skipping geocoding")
                    return itinerary

                import asyncio

                from travel_companion.services.itinerary_geocoder import geocode_itinerary

                # Geocode itinerary asynchronously with timeout
                geocoded_itinerary = await asyncio.wait_for(
                    geocode_itinerary(itinerary),
                    timeout=30.0,  # 30 second timeout for geocoding
                )
                logger.info("Geocoding completed successfully")
                return geocoded_itinerary

            except TimeoutError:
                logger.warning(
                    "Geocoding timed out after 30s, returning itinerary without coordinates"
                )
                return itinerary
            except ImportError as e:
                logger.warning(f"Geocoding module not available: {e}")
                return itinerary
            except Exception as geocoding_error:
                logger.warning(
                    f"Geocoding failed: {type(geocoding_error).__name__}: {geocoding_error}",
                    exc_info=False,  # Don't print full stack trace for optional feature
                )
                # Return itinerary without geocoding if geocoding fails
                return itinerary

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}", exc_info=True)
            return None
        except ValidationError as e:
            logger.error(f"Pydantic validation failed: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing itinerary: {e}", exc_info=True)
            return None

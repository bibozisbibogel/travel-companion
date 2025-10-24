"""MCP server for travel planning tools."""

import logging
from typing import Any

from mcp import types
from mcp.server import Server

from travel_companion.agents_sdk.tools import (
    search_activities,
    search_flights,
    search_hotels,
    search_restaurants,
)

logger = logging.getLogger(__name__)


# Create MCP server for travel planning tools
travel_tools_server = Server("travel-planning-tools")


@travel_tools_server.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    List all available travel planning tools.

    Returns:
        List of tool definitions
    """
    # Convert SdkMcpTool objects to MCP Tool types
    tools = [search_flights, search_hotels, search_activities, search_restaurants]
    return [
        types.Tool(
            name=tool.name,
            description=tool.description or "",
            inputSchema=(tool.input_schema if isinstance(tool.input_schema, dict) else {}),
        )
        for tool in tools
    ]


@travel_tools_server.call_tool()
async def call_tool(
    name: str, arguments: dict[str, Any]
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Execute a travel planning tool by name.

    Args:
        name: Name of the tool to execute
        arguments: Tool arguments

    Returns:
        Tool execution results

    Raises:
        ValueError: If tool name is not recognized
    """
    logger.info(f"Calling tool: {name} with arguments: {arguments}")

    # Map tool names to handler functions
    tool_handlers = {
        "search_flights": search_flights,
        "search_hotels": search_hotels,
        "search_activities": search_activities,
        "search_restaurants": search_restaurants,
    }

    if name not in tool_handlers:
        raise ValueError(f"Unknown tool: {name}")

    # Execute the tool handler - use .handler attribute for SdkMcpTool
    result = await tool_handlers[name].handler(arguments)

    # Convert result to MCP format
    if "content" in result:
        return [
            types.TextContent(type="text", text=content["text"])
            for content in result["content"]
            if content.get("type") == "text"
        ]
    else:
        # Fallback if result doesn't have content
        import json

        return [types.TextContent(type="text", text=json.dumps(result))]


def create_travel_mcp_server() -> Server:
    """
    Create and configure the travel planning MCP server.

    Returns:
        Configured MCP server instance
    """
    logger.info("Creating travel planning MCP server")
    return travel_tools_server

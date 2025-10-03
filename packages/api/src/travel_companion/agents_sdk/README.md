# Travel Companion - Claude Agent SDK Integration

This directory contains the Claude Agent SDK integration for the Travel Companion application, providing an intelligent AI-powered travel planning system.

## Architecture Overview

### Components

```
agents_sdk/
├── __init__.py                  # Package exports
├── travel_planner_agent.py      # Main orchestrator agent
├── mcp_server.py                # MCP server for tool registration
├── hooks.py                     # Pre/post tool execution hooks
└── tools/                       # Travel planning tools
    ├── __init__.py
    ├── flight_tools.py          # Flight search tool
    ├── hotel_tools.py           # Hotel search tool
    ├── activity_tools.py        # Activity search tool
    └── food_tools.py            # Restaurant search tool
```

### Design Principles

1. **Tool-Based Architecture**: Each travel planning capability (flights, hotels, activities, food) is exposed as a Claude tool
2. **MCP Integration**: Tools are registered via Model Context Protocol (MCP) server
3. **Budget Tracking**: Built-in hooks for budget validation and allocation tracking
4. **Streaming Responses**: Real-time progress updates during trip planning
5. **Reusable Agents**: Leverages existing agent implementations (FlightAgent, HotelAgent, etc.)

## Key Features

### 1. Intelligent Trip Planning

The `TravelPlannerAgent` uses Claude's reasoning to:
- Understand natural language trip requirements
- Search for flights, hotels, activities, and restaurants
- Create coherent itineraries that fit budget constraints
- Provide multiple options with rankings

### 2. Tool Ecosystem

Four specialized tools for travel planning:

#### `search_flights`
- Search for flights between origin and destination
- Filter by travel class, passengers, and budget
- Returns ranked flight options with pricing

#### `search_hotels`
- Find accommodations at a location
- Filter by dates, guests, rooms, and budget
- Returns hotels with ratings, amenities, and photos

#### `search_activities`
- Discover activities and attractions
- Filter by activity type and budget
- Returns activities with duration, pricing, and schedules

#### `search_restaurants`
- Find dining options
- Filter by meal type, cuisine, and budget
- Returns restaurants with ratings and menu information

### 3. Budget Management

The `BudgetTracker` class provides:
- Total budget allocation across categories
- Automatic budget validation in pre-tool hooks
- Real-time spending tracking
- Budget utilization reporting

### 4. Validation Hooks

**Pre-Tool Hooks:**
- Validate required fields
- Check budget constraints
- Add budget filters automatically
- Deny execution if budget exhausted

**Post-Tool Hooks:**
- Log tool execution results
- Update budget allocations
- Track spending by category
- Generate execution metadata

## Usage

### API Endpoints

#### 1. Plan Trip (Streaming)

```bash
POST /api/v1/agent/plan
Authorization: Bearer <token>

{
  "destination": "Paris, France",
  "start_date": "2025-06-01",
  "end_date": "2025-06-07",
  "budget": 3000,
  "currency": "USD",
  "travelers": 2,
  "origin": "New York, NY",
  "preferences": {
    "accommodation_type": "hotel",
    "activity_types": ["cultural", "sightseeing", "food"],
    "cuisine_preferences": ["French", "Italian"]
  }
}
```

Returns Server-Sent Events (SSE) stream:
```json
data: {"type": "start", "status": "Planning trip..."}
data: {"type": "text", "content": "Let me search for flights...", "turn": 1}
data: {"type": "tool_use", "tool": "search_flights", "input": {...}, "turn": 1}
data: {"type": "tool_result", "tool": "search_flights", "result": {...}, "turn": 1}
data: {"type": "budget_summary", "data": {...}}
data: {"type": "done", "status": "Trip planning completed"}
```

#### 2. Freeform Query

```bash
POST /api/v1/agent/query?query=Find cheap hotels in Tokyo for next month
Authorization: Bearer <token>
```

Returns streaming response with agent's answer.

#### 3. Health Check

```bash
GET /api/v1/agent/health
```

Returns agent system status and available tools.

### Programmatic Usage

```python
from travel_companion.agents_sdk import TravelPlannerAgent
from travel_companion.models.trip import TripPlanRequest
from decimal import Decimal
from datetime import date

# Initialize agent
agent = TravelPlannerAgent()

# Create trip request
request = TripPlanRequest(
    destination="Paris",
    start_date=date(2025, 6, 1),
    end_date=date(2025, 6, 7),
    budget=Decimal("3000"),
    travelers=2,
    origin="New York"
)

# Stream trip planning
async for update in agent.plan_trip(request):
    if update["type"] == "text":
        print(update["content"])
    elif update["type"] == "tool_use":
        print(f"Executing: {update['tool']}")
    elif update["type"] == "complete":
        print("Planning complete!")
```

## Tool Implementation

Each tool follows this pattern:

```python
from mcp import Tool

# Define input schema
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "param": {"type": "string", "description": "Parameter description"},
    },
    "required": ["param"]
}

# Implement tool function
async def my_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    # 1. Validate input
    # 2. Call existing agent/service
    # 3. Format response
    return {
        "content": [
            {"type": "text", "text": json.dumps(result)}
        ]
    }

# Create tool definition
my_tool_definition = Tool(
    name="my_tool",
    description="What the tool does",
    inputSchema=TOOL_SCHEMA
)
```

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
ANTHROPIC_MODEL=claude-sonnet-4-20250514
ANTHROPIC_MAX_TOKENS=4096
```

### Budget Configuration

```python
from travel_companion.agents_sdk.hooks import BudgetTracker
from decimal import Decimal

# Initialize tracker
tracker = BudgetTracker(
    total_budget=Decimal("5000"),
    currency="USD"
)

# Use in agent context
context = {"budget_tracker": tracker}
```

## Testing

```bash
# Run all SDK tests
uv run pytest src/tests/test_agents_sdk/

# Test specific component
uv run pytest src/tests/test_agents_sdk/test_flight_tools.py
uv run pytest src/tests/test_agents_sdk/test_hooks.py

# Run with coverage
uv run pytest --cov=src/travel_companion/agents_sdk src/tests/test_agents_sdk/
```

## Migration from LangGraph

The Claude Agent SDK implementation replaces the LangGraph-based workflow orchestration:

| LangGraph | Claude Agent SDK |
|-----------|------------------|
| StateGraph with nodes | Single TravelPlannerAgent with tools |
| Manual node orchestration | Claude's reasoning for tool selection |
| Complex state management | Conversation context |
| Custom error handling | Built-in resilience |
| Tool dispatch logic | MCP tool registration |

### Benefits

✅ **Simpler Architecture**: One agent vs complex state graphs
✅ **Better Reasoning**: Claude chooses tools intelligently
✅ **Streaming Support**: Built-in progress monitoring
✅ **Easier Testing**: Test individual tools, not graph states
✅ **Flexible Validation**: Hooks for custom business logic
✅ **Reduced Code**: Less orchestration, more intelligence

## Troubleshooting

### Common Issues

**Tool not found:**
```python
# Ensure tool is registered in mcp_server.py
@travel_tools_server.call_tool()
async def call_tool(name: str, arguments: dict):
    tool_handlers = {
        "your_tool": your_tool_handler  # Add here
    }
```

**Budget validation failing:**
```python
# Check BudgetTracker initialization
tracker = BudgetTracker(total_budget=Decimal("5000"), currency="USD")

# Verify budget hasn't been exhausted
summary = tracker.get_summary()
print(f"Remaining: {summary['remaining']}")
```

**MCP connection errors:**
```python
# Ensure MCP server is properly configured
server = create_travel_mcp_server()
# Check server_params in TravelPlannerAgent
```

## Future Enhancements

- [ ] Add weather integration tool
- [ ] Implement itinerary optimization tool
- [ ] Add booking confirmation tool
- [ ] Multi-destination trip planning
- [ ] Collaborative planning (multi-user)
- [ ] Voice input/output support
- [ ] Image analysis for destination insights
- [ ] Real-time pricing alerts

## Resources

- [Claude Agent SDK Documentation](https://docs.claude.com/en/api/agent-sdk/overview)
- [Model Context Protocol (MCP)](https://github.com/anthropics/mcp)
- [Anthropic API Reference](https://docs.anthropic.com/)
- [Travel Companion API Docs](../../README.md)

## Support

For issues or questions:
1. Check the [troubleshooting section](#troubleshooting)
2. Review test cases in `src/tests/test_agents_sdk/`
3. Consult Claude Agent SDK documentation
4. Open an issue in the repository

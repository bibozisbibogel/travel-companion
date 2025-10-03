# Migration Plan: LangGraph → Claude Agent SDK

## Current State Analysis
Your travel planner currently uses:
- **LangGraph** for multi-agent orchestration
- **BaseAgent** pattern with individual agents (flight, hotel, activity, food, weather, itinerary)
- **External API integrations** (Google Places, AviationStack, etc.)
- **Redis caching** and circuit breakers
- **FastAPI** backend with workflow endpoints

## Proposed Architecture: Claude Agent SDK

### 1. **Core Agent Setup** (`src/travel_companion/agents_sdk/`)
```
agents_sdk/
  __init__.py
  travel_planner_agent.py    # Main orchestrator agent
  tools/
    __init__.py
    flight_tools.py            # @tool decorated flight search
    hotel_tools.py             # @tool decorated hotel search
    activity_tools.py          # @tool decorated activity search
    food_tools.py              # @tool decorated food search
    weather_tools.py           # @tool decorated weather lookup
```

### 2. **Tool Implementation Pattern**
Each tool will:
- Use `@tool` decorator from `claude-agent-sdk`
- Accept typed input schemas (Pydantic models)
- Call existing API clients (GooglePlacesClient, AviationStackClient, etc.)
- Return structured responses
- Include built-in caching, circuit breaking, error handling

### 3. **Main Orchestrator Agent**
Single `TravelPlannerAgent` that:
- Uses `ClaudeSDKClient` for stateful conversations
- Has access to all travel planning tools via MCP server
- Implements pre-tool hooks for budget validation
- Uses post-tool hooks for result aggregation
- Maintains conversation context across planning steps

### 4. **Integration Points**
- Keep existing FastAPI endpoints
- Replace LangGraph workflow invocation with Claude SDK `query()` 
- Preserve Redis caching layer
- Maintain external API clients unchanged
- Reuse existing Pydantic models

### 5. **Key Benefits**
✅ Simpler architecture (single agent vs complex state graphs)  
✅ Built-in streaming and progress monitoring  
✅ Better tool orchestration via Claude's reasoning  
✅ Hooks for validation, logging, and custom behavior  
✅ Easier to test and debug

### 6. **Implementation Steps**
1. Install `claude-agent-sdk` via UV
2. Create SDK MCP server with travel planning tools
3. Build main TravelPlannerAgent with hooks
4. Migrate one agent at a time (start with flight tool)
5. Update FastAPI endpoints to use SDK query pattern
6. Add comprehensive tests
7. Deprecate LangGraph orchestrator

### 7. **Example Tool Structure**
```python
@tool("search_flights", "Search for flights between cities")
async def search_flights_tool(args):
    request = FlightSearchRequest(**args)
    agent = FlightAgent()  # Reuse existing agent
    result = await agent.search_flights(request)
    return {"content": [{"type": "text", "text": json.dumps(result)}]}
```

Would you like me to proceed with this migration plan?
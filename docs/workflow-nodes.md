  Workflow Nodes for Travel Companion Agents

  # Architecture Overview

  The Travel Companion uses a LangGraph-based workflow orchestration
  system with specialized agent nodes that execute in a coordinated
  sequence. Each node represents a specific travel planning domain
  expert.

  # Workflow Execution Flow

  Sequential Phases:

  initialize_trip_context → execute_weather_agent → [parallel_agents] → 
  execute_itinerary_agent → finalize_trip_plan

  Parallel Execution Block:

  - execute_flight_agent
  - execute_hotel_agent
  - execute_activity_agent
  - execute_food_agent

  # Node Breakdown

  1. Initialize Trip Context (initialize_trip_context)

  Purpose: Bootstrap workflow state and validate input
  Key Functions:
  - Validates trip request data
  - Initializes budget allocations (40% flights, 30% hotels, 20%
  activities, 10% food)
  - Sets up user preferences context
  - Creates optimization metrics tracking
  - Establishes agent execution tracking

  2. Weather Agent Node (execute_weather_agent)

  Purpose: Gather weather forecast data for trip planning decisions
  Dependencies: Trip destination and dates
  Outputs: Weather forecast and historical data
  Graceful Degradation: Continues on API failures with degraded data
  flag

  3. Flight Agent Node (execute_flight_agent)

  Purpose: Search and rank flight options
  Parallel Execution: Runs concurrently with hotel, activity, food
  Key Features:
  - Creates FlightSearchRequest from trip requirements
  - Updates budget tracking with cheapest option
  - Handles circuit breaker patterns for API failures

  4. Hotel Agent Node (execute_hotel_agent)

  Purpose: Find accommodation options
  Parallel Execution: Runs concurrently with flight, activity, food
  Smart Features:
  - Calculates room count based on traveler count (2 per room max)
  - Uses budget allocation for price filtering
  - Considers check-in/out dates for availability

  5. Activity Agent Node (execute_activity_agent)

  Purpose: Discover activities and attractions
  Dependencies: Weather data (for weather-dependent filtering)
  Parallel Execution: Runs concurrently with flight, hotel, food
  Intelligence:
  - Maps user activity preferences to activity categories
  - Uses weather conditions for indoor/outdoor recommendations
  - Budget-aware filtering per person

  6. Food Agent Node (execute_food_agent)

  Purpose: Find restaurant recommendations
  Parallel Execution: Runs concurrently with flight, hotel, activity
  Features:
  - Maps user cuisine preferences to restaurant categories
  - Geoapify integration for location-based search
  - Fallback budget estimation when no restaurants found

  7. Itinerary Agent Node (execute_itinerary_agent)

  Purpose: Coordinate and optimize all travel components
  Dependencies: All parallel agents must complete first
  Intelligence:
  - Requires at least one critical agent (flight OR hotel) to succeed
  - Creates comprehensive itinerary request with all agent results
  - Performs budget optimization and preference alignment
  - Handles mock objects gracefully for testing

  8. Finalize Trip Plan (finalize_trip_plan)

  Purpose: Create final comprehensive output
  Advanced Features:
  - Uses AgentResultAggregator for result correlations
  - Calculates quality metrics (completeness, coherence, preference
  alignment)
  - Provides execution summary with performance metrics
  - Fallback to basic output if aggregation fails

  # Advanced Routing Logic

  Conditional Routing Functions:

  should_proceed_to_itinerary:
  - Checks if critical agents (flight + hotel) completed
  - Routes to finalization if all critical agents failed
  - Enables graceful degradation

  route_based_on_preferences:
  - Budget constraint checking
  - Critical failure detection
  - Future: User preference-based routing

  # Key Design Patterns

  ## Error Handling Strategy:

  - Recoverable Errors: API timeouts, circuit breaker opens → Continue
  with degraded data
  - Critical Errors: Validation failures, system errors → Halt workflow
  - Graceful Degradation: Continue with partial results

  ## Budget Management:

  - Real-time Tracking: Each agent updates spent/remaining budget
  - Smart Allocation: Percentage-based initial allocation
  - Cost Optimization: Selects cheapest options for budget calculation

  ## Performance Optimization:

  - Parallel Execution: 4 agents run simultaneously after weather
  - Circuit Breakers: Prevent cascade failures
  - Caching: Redis-based result caching
  - Metrics: Detailed execution timing and API call tracking

  ## State Management:

  - Comprehensive State: TripPlanningWorkflowState tracks all context
  - Redis Persistence: Workflow state persisted for recovery
  - Structured Logging: Every node entry/exit logged with metrics

  This architecture provides a robust, scalable, and fault-tolerant
  system for coordinating multiple travel planning agents while
  maintaining high performance and user experience quality.

  # Nodes

  The nodes.py file implements individual workflow node functions that are executed as part of the LangGraph trip planning workflow. Each node represents a specific step in the trip planning process.

  ## Core Purpose

  This file contains the execution logic for each agent in the trip planning workflow, handling:
  - Agent initialization and coordination
  - External API calls to travel services
  - Error handling and graceful degradation
  - State management and budget tracking
  - Structured logging and metrics

  ## Key Node Functions

  1. initialize_trip_context()

  - Purpose: Sets up initial workflow context and validates request data
  - Key Actions:
    - Validates trip request data
    - Initializes budget tracking with allocations (40% flights, 30% hotels, 20% activities, 10% food)
    - Sets up user preferences and optimization metrics
    - Creates agent execution tracking structures

  2. Agent Execution Nodes (All async functions):

  execute_weather_agent()
  - Fetches weather forecast data for the destination
  - Uses WeatherAgent with OpenWeatherMap API
  - Dependency: None (runs first)
  - Handles: Weather-dependent activity filtering

  execute_flight_agent()
  - Searches for flight options using Amadeus API
  - Updates budget tracking with cheapest flight option
  - Dependency: Can run in parallel
  - Handles: Flight search with origin/destination/dates

  execute_hotel_agent()
  - Searches for accommodation using Booking.com/Google Places APIs
  - Calculates budget per night based on allocation
  - Dependency: Can run in parallel
  - Handles: Hotel search with check-in/check-out dates

  execute_activity_agent()
  - Finds activities and attractions using Google Places API
  - Dependency: Requires weather data (depends on weather agent)
  - Handles: Weather-aware activity filtering based on conditions

  execute_food_agent()
  - Searches for restaurant recommendations using Geoapify API
  - Maps cuisine preferences to API categories
  - Dependency: Can run in parallel
  - Handles: Restaurant search with cuisine filtering

  execute_itinerary_agent()
  - Critical Final Step: Coordinates and optimizes all travel components
  - Dependencies: Requires flight, hotel, activity, and food agents
  - Handles: Creates comprehensive itinerary with daily schedules

  3. finalize_trip_plan()

  - Purpose: Creates final trip plan output with comprehensive results
  - Key Features:
    - Uses AgentResultAggregator for result correlation
    - Calculates quality metrics and optimization scores
    - Creates structured output with cost analysis
    - Handles both successful aggregation and fallback scenarios

  ## Architecture Patterns

  ### Error Handling Strategy

  try:
      # Agent execution
      agent = WeatherAgent()
      response = await agent.process(request)
  except (ExternalAPIError, CircuitBreakerOpenError) as e:
      # Graceful degradation - continue workflow
      state["weather_data"] = {"error": str(e), "degraded": True}
  except Exception as e:
      # Critical failure - stop workflow
      raise

  ### State Management

  - Each node updates the shared TripPlanningWorkflowState
  - Tracks completed/failed agents for dependency management
  - Updates budget tracking throughout execution
  - Maintains execution metrics and timing

  ### Budget Tracking

  - Initial Allocation: 40% flights, 30% hotels, 20% activities, 10% food
  - Real-time Updates: Updates spent/remaining as agents complete
  - Final Reconciliation: Aggregator provides final cost analysis

  ### Dependency Management

  - Weather → Activities: Weather data influences activity selection
  - All Core Agents → Itinerary: Itinerary agent waits for others to complete
  - Parallel Execution: Flight, hotel, food agents can run simultaneously

  ## Integration with Orchestrator

  The orchestrator (orchestrator.py) uses these nodes in its workflow definition:
  - Sequential: initialize_trip → coordinated_execution → finalize_plan
  - Parallel Optimization: The coordinated_execution node manages parallel agent execution
  - Conditional Routing: Advanced routing functions handle different execution paths

  ## Key Design Features

  1. Resilient: Continues workflow even if individual agents fail
  2. Observable: Comprehensive logging and metrics collection
  3. Budget-Aware: Real-time budget tracking and allocation management
  4. Weather-Aware: Activity selection considers forecast conditions
  5. Preference-Driven: User preferences influence all agent decisions
  6. Correlation-Aware: Final aggregation creates correlations between results

  # Agents

  ## Itinerary Agent (execute_itinerary_agent)

  ### Purpose & Role

  The Itinerary Agent Node is the coordination and optimization hub of
  the travel planning workflow. It takes all the individual agent
  results (flights, hotels, activities, food, weather) and creates a
  cohesive, optimized trip itinerary.

  ### Execution Flow

  1. Dependency Validation

  # Critical gate - requires at least one core travel component
  critical_completed = any(
      agent in completed_agents for agent in ["flight_agent",
  "hotel_agent"]
  )
  if not critical_completed:
      raise TravelCompanionError("Critical travel agents failed to 
  complete")

  Logic: Must have either flights OR hotels to proceed (graceful
  degradation)

  2. Data Aggregation

  Creates comprehensive itinerary_request dictionary combining:
  - Trip basics: destination, dates, traveler count
  - Budget constraints: current tracking state
  - Agent results: flights, hotels, activities, restaurants, weather
  - Optimization criteria: ["budget", "time", "weather"]
  - User preferences: activity types, cuisine preferences, etc.

  3. ItineraryAgent Processing

  itinerary_agent = ItineraryAgent()
  itinerary_response = await itinerary_agent.process(itinerary_request)

  The ItineraryAgent performs:
  - Multi-Agent Coordination: Uses all sub-agents with circuit breakers
  - Daily Schedule Generation: Creates time-sequenced daily plans
  - Cost Optimization: Calculates total costs and budget allocation
  - Conflict Detection: Identifies scheduling/location conflicts
  - Quality Scoring: Generates optimization scores

  4. Response Processing

  Handles both real objects and test mocks:
  if hasattr(itinerary_response, "model_dump") and
  callable(itinerary_response.model_dump):
      itinerary_data = itinerary_response.model_dump()
  else:
      # Handle mock objects for testing
      itinerary_data = extract_mock_attributes(itinerary_response)

  5. State Updates

  Updates workflow state with:
  - itinerary_data: Optimized schedules, recommendations
  - budget_tracking: Final costs, utilization, savings
  - optimization_metrics: Quality scores, recommendation counts

  ### ItineraryAgent Intelligence

  Multi-Agent Coordination:

  - Circuit Breakers: Prevents cascade failures (3 failure threshold,
  60s recovery)
  - Timeout Handling: 30-second agent timeouts
  - Retry Logic: 2 max retries per agent
  - Graceful Degradation: Continues with partial results

  Daily Schedule Generation:

  - Time-based Sequencing: Activities organized by logical time flow
  - Weather Integration: Outdoor activities scheduled for good weather
  days
  - Location Optimization: Minimizes travel time between locations
  - Rest Periods: Builds in breaks and meal times

  Cost Optimization:

  - Budget Allocation: Smart distribution across trip components
  - Alternative Selection: Picks optimal price/quality combinations
  - Savings Calculation: Tracks budget vs actual costs
  - Currency Handling: Consistent currency conversion

  Quality Metrics:

  - Optimization Score: Overall trip plan quality (0.0-1.0)
  - Completeness: Percentage of required components found
  - Coherence: Logical flow and timing consistency
  - Preference Alignment: Match to user stated preferences

  ### Error Handling Strategy

  Graceful Degradation:

  - Partial Results: Works with incomplete agent data
  - Fallback Logic: Uses defaults when agents fail
  - User Notification: Clearly marks degraded components

  Test Compatibility:

  - Mock Handling: Robust support for test mock objects
  - Flexible Response Processing: Works with various response types
  - Fallback Values: Sensible defaults (e.g., $2500 estimated cost)

  ### Output Structure

  {
      "optimized_itinerary": {...},      # Complete trip plan
      "daily_schedules": [...],          # Day-by-day schedules
      "budget_summary": {...},           # Cost breakdown
      "optimization_score": 0.85,        # Quality metric
      "recommendations": [...]           # Optimization suggestions
  }

  ### Performance Features

  - Caching: 30-minute TTL for repeated requests
  - Parallel Execution: Coordinates multiple agents concurrently
  - Metrics Tracking: Detailed execution timing
  - Resource Management: Circuit breakers prevent resource exhaustion

  The Itinerary Agent Node essentially acts as a travel planning 
  orchestrator, taking raw search results and transforming them into a
  coordinated, optimized, and realistic travel itinerary that respects
  budget constraints, user preferences, and practical considerations
  like weather and timing.
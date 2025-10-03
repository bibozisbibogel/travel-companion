"""Claude Agent SDK-based trip planning API endpoints."""

import logging
from decimal import Decimal
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from travel_companion.agents_sdk.hooks import BudgetTracker
from travel_companion.agents_sdk.travel_planner_agent import TravelPlannerAgent
from travel_companion.api.deps import get_current_user
from travel_companion.models.base import SuccessResponse
from travel_companion.models.trip import TripPlanRequest, TripResponse
from travel_companion.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/plan",
    status_code=status.HTTP_200_OK,
    summary="Generate trip plan using Claude Agent SDK",
    description="Generate a travel plan using Claude Agent SDK with streaming responses",
)
async def generate_trip_plan_sdk(
    trip_request: TripPlanRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Generate a travel plan using Claude Agent SDK.

    This endpoint:
    - Uses Claude's reasoning capabilities for intelligent trip planning
    - Streams planning progress in real-time
    - Executes tools (search_flights, search_hotels, etc.) as needed
    - Applies budget tracking and validation hooks
    - Returns a comprehensive travel plan

    Required authentication via JWT token.

    Example request:
    ```json
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

    Returns streaming JSON objects with planning updates.
    """
    logger.info(
        f"SDK trip planning request for {trip_request.destination} "
        f"from user {current_user.user_id}"
    )

    try:
        # Initialize travel planner agent
        agent = TravelPlannerAgent()

        # Create budget tracker for validation
        budget_tracker = None
        if trip_request.budget:
            budget_tracker = BudgetTracker(
                total_budget=Decimal(str(trip_request.budget)),
                currency=trip_request.currency,
            )

        # Stream generator
        async def event_stream() -> AsyncIterator[str]:
            """Generate SSE events for trip planning progress."""
            import json

            try:
                # Send initial status
                yield f"data: {json.dumps({'type': 'start', 'status': 'Planning trip...'})}\n\n"

                # Stream planning updates from agent
                async for update in agent.plan_trip(trip_request):
                    # Format update as SSE
                    yield f"data: {json.dumps(update)}\n\n"

                # Send budget summary if available
                if budget_tracker:
                    budget_summary = budget_tracker.get_summary()
                    yield f"data: {json.dumps({'type': 'budget_summary', 'data': budget_summary})}\n\n"

                # Send completion event
                yield f"data: {json.dumps({'type': 'done', 'status': 'Trip planning completed'})}\n\n"

            except Exception as e:
                logger.error(f"Error during trip planning stream: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        # Return streaming response
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    except Exception as e:
        logger.error(f"Failed to initialize trip planning: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize trip planning: {str(e)}",
        )


@router.post(
    "/query",
    status_code=status.HTTP_200_OK,
    summary="Freeform travel planning query",
    description="Ask the travel agent any question about travel planning",
)
async def travel_query_sdk(
    query: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Send a freeform query to the travel planning agent.

    This endpoint allows natural language interactions with the agent
    for tasks like:
    - "Find cheap flights to Tokyo next month"
    - "What are the best hotels in Paris under $200/night?"
    - "Suggest activities for families in Barcelona"
    - "Create a 3-day itinerary for Rome with a $1500 budget"

    Required authentication via JWT token.

    Args:
        query: Natural language question or request
        request: FastAPI request object
        current_user: Authenticated user

    Returns:
        Streaming response with agent's answer and tool results
    """
    logger.info(f"SDK travel query from user {current_user.user_id}: {query}")

    try:
        agent = TravelPlannerAgent()

        async def event_stream() -> AsyncIterator[str]:
            """Generate SSE events for query responses."""
            import json

            try:
                yield f"data: {json.dumps({'type': 'start', 'query': query})}\n\n"

                async for update in agent.query(query):
                    yield f"data: {json.dumps(update)}\n\n"

                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            except Exception as e:
                logger.error(f"Error during query stream: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error(f"Failed to process query: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}",
        )


@router.get(
    "/health",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Check agent health",
    description="Verify the Claude Agent SDK integration is working",
)
async def agent_health_check() -> SuccessResponse[dict]:
    """
    Health check for Claude Agent SDK integration.

    Returns:
        Health status of the agent system
    """
    try:
        agent = TravelPlannerAgent()

        # Basic health check - verify agent can be initialized
        health_data = {
            "status": "healthy",
            "agent_type": "TravelPlannerAgent",
            "sdk_version": "0.1.0",
            "available_tools": [
                "search_flights",
                "search_hotels",
                "search_activities",
                "search_restaurants",
            ],
        }

        return SuccessResponse(data=health_data, message="Agent system is healthy")

    except Exception as e:
        logger.error(f"Agent health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent system unhealthy: {str(e)}",
        )

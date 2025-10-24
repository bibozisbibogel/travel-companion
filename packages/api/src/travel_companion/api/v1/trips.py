"""Trip planning API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from travel_companion.agents_sdk.travel_planner_agent import TravelPlannerAgent
from travel_companion.api.deps import get_current_user
from travel_companion.core.database import DatabaseManager, get_database
from travel_companion.models.base import PaginatedResponse, PaginationMeta, SuccessResponse
from travel_companion.models.trip import (
    TripCreate,
    TripPlanRequest,
    TripResponse,
    TripStatus,
    TripUpdate,
)
from travel_companion.models.user import User
from travel_companion.services.trip_service import TripService
from travel_companion.utils.logging import get_client_ip, get_user_agent

router = APIRouter()


@router.post(
    "/plan",
    response_model=SuccessResponse[TripResponse],
    status_code=status.HTTP_200_OK,
    summary="Generate trip plan",
    description="Generate a travel plan based on destination and requirements",
)
async def generate_trip_plan(
    trip_request: TripPlanRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database),
) -> SuccessResponse[TripResponse]:
    """
    Generate a travel plan using Claude Agent SDK.

    This endpoint:
    - Validates trip requirements and destination
    - Uses TravelPlannerAgent with Claude Agent SDK for trip planning
    - Saves the generated plan to database
    - Returns a comprehensive travel plan with flights, hotels, and activities

    Required authentication via JWT token.
    """
    get_client_ip(request)
    get_user_agent(request)

    # Initialize TravelPlannerAgent
    agent = TravelPlannerAgent()

    try:
        # Stream planning responses and collect itinerary
        itinerary_data = None
        async for message in agent.plan_trip(trip_request):
            # Extract structured itinerary when received
            if message["type"] == "itinerary":
                # ItineraryOutput model instance
                itinerary_data = message["data"]
                break

        # Save trip to database with generated plan
        trip_service = TripService(db.client)
        saved_trip = await trip_service.create_trip(
            user_id=current_user.user_id,
            name=f"Trip to {trip_request.destination.city}",
            description=f"AI-generated travel plan for {trip_request.destination.city}",
            destination=trip_request.destination,
            requirements=trip_request.requirements,
            plan=itinerary_data,
            status=TripStatus.DRAFT,
        )

        return SuccessResponse[TripResponse](
            data=saved_trip, message="Trip plan generated and saved successfully"
        )

    except TimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail={
                "message": "Trip planning timed out",
                "error_code": "PLANNING_TIMEOUT",
                "details": str(e),
            },
        ) from e

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Failed to generate trip plan",
                "error_code": "TRIP_PLANNING_ERROR",
                "details": str(e),
            },
        ) from e


@router.post(
    "/",
    response_model=SuccessResponse[TripResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new trip",
    description="Create a new trip with planning requirements",
)
async def create_trip(
    trip_data: TripCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database),
) -> SuccessResponse[TripResponse]:
    """
    Create a new trip for the authenticated user.

    This endpoint:
    - Validates trip data and requirements
    - Creates a new trip in draft status
    - Returns the created trip information

    Required authentication via JWT token.
    """
    get_client_ip(request)
    get_user_agent(request)

    try:
        trip_service = TripService(db.client)
        saved_trip = await trip_service.create_trip(
            user_id=current_user.user_id,
            name=trip_data.name,
            description=trip_data.description,
            destination=trip_data.destination,
            requirements=trip_data.requirements,
            plan=None,
            status=TripStatus.DRAFT,
        )

        return SuccessResponse[TripResponse](data=saved_trip, message="Trip created successfully")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to create trip", "error_code": "TRIP_CREATION_ERROR"},
        ) from e


@router.get(
    "/",
    response_model=PaginatedResponse[list[TripResponse]],
    summary="List user trips",
    description="Retrieve a paginated list of trips for the authenticated user",
)
async def list_user_trips(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database),
) -> PaginatedResponse[list[TripResponse]]:
    """
    Get all trips for the authenticated user with pagination.

    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)

    Required authentication via JWT token.
    """
    get_client_ip(request)
    get_user_agent(request)

    # Validate pagination parameters
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Page must be greater than 0", "error_code": "INVALID_PAGE"},
        )

    if per_page < 1 or per_page > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Per page must be between 1 and 100",
                "error_code": "INVALID_PER_PAGE",
            },
        )

    try:
        trip_service = TripService(db.client)
        trips, total_count = await trip_service.list_user_trips(
            user_id=current_user.user_id, page=page, per_page=per_page
        )

        # Calculate pagination metadata
        total_pages = (total_count + per_page - 1) // per_page
        pagination_meta = PaginationMeta(
            page=page,
            per_page=per_page,
            total_items=total_count,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

        return PaginatedResponse[list[TripResponse]](
            data=trips, pagination=pagination_meta, message="Trips retrieved successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to retrieve trips", "error_code": "TRIP_RETRIEVAL_ERROR"},
        ) from e


@router.get(
    "/{trip_id}",
    response_model=SuccessResponse[TripResponse],
    summary="Get trip details",
    description="Retrieve detailed information about a specific trip",
)
async def get_trip(
    trip_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database),
) -> SuccessResponse[TripResponse]:
    """
    Get detailed information about a specific trip.

    The trip must belong to the authenticated user.
    Required authentication via JWT token.
    """
    get_client_ip(request)
    get_user_agent(request)

    try:
        trip_service = TripService(db.client)
        trip = await trip_service.get_trip_by_id(trip_id=trip_id, user_id=current_user.user_id)

        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Trip not found", "error_code": "TRIP_NOT_FOUND"},
            )

        return SuccessResponse[TripResponse](data=trip, message="Trip retrieved successfully")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to retrieve trip", "error_code": "TRIP_RETRIEVAL_ERROR"},
        ) from e


@router.put(
    "/{trip_id}",
    response_model=SuccessResponse[TripResponse],
    summary="Update trip",
    description="Update trip details and requirements",
)
async def update_trip(
    trip_id: UUID,
    trip_update: TripUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database),
) -> SuccessResponse[TripResponse]:
    """
    Update an existing trip.

    The trip must belong to the authenticated user.
    Only non-null fields in the update request will be modified.
    Required authentication via JWT token.
    """
    get_client_ip(request)
    get_user_agent(request)

    try:
        trip_service = TripService(db.client)
        updated_trip = await trip_service.update_trip(
            trip_id=trip_id, user_id=current_user.user_id, update_data=trip_update
        )

        if not updated_trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Trip not found", "error_code": "TRIP_NOT_FOUND"},
            )

        return SuccessResponse[TripResponse](data=updated_trip, message="Trip updated successfully")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to update trip", "error_code": "TRIP_UPDATE_ERROR"},
        ) from e


@router.delete(
    "/{trip_id}",
    response_model=SuccessResponse[dict[str, str]],
    summary="Delete trip",
    description="Delete a trip and all associated data",
)
async def delete_trip(
    trip_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database),
) -> SuccessResponse[dict[str, str]]:
    """
    Delete an existing trip.

    The trip must belong to the authenticated user.
    This operation cannot be undone.
    Required authentication via JWT token.
    """
    get_client_ip(request)
    get_user_agent(request)

    try:
        trip_service = TripService(db.client)
        deleted = await trip_service.delete_trip(trip_id=trip_id, user_id=current_user.user_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Trip not found", "error_code": "TRIP_NOT_FOUND"},
            )

        return SuccessResponse[dict[str, str]](
            data={"trip_id": str(trip_id)}, message="Trip deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to delete trip", "error_code": "TRIP_DELETION_ERROR"},
        ) from e

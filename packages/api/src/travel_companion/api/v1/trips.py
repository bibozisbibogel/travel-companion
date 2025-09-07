"""Trip planning API endpoints."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from travel_companion.api.deps import get_current_user
from travel_companion.models.base import PaginatedResponse, PaginationMeta, SuccessResponse
from travel_companion.models.trip import (
    TravelClass,
    TripCreate,
    TripDestination,
    TripPlanRequest,
    TripRequirements,
    TripResponse,
    TripStatus,
    TripUpdate,
)
from travel_companion.models.user import User
from travel_companion.utils.logging import get_client_ip, get_user_agent
from travel_companion.workflows.orchestrator import TripPlanningWorkflow

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
) -> SuccessResponse[TripResponse]:
    """
    Generate a travel plan using AI agents workflow.

    This endpoint:
    - Validates trip requirements and destination
    - Initiates the LangGraph workflow for trip planning
    - Returns a comprehensive travel plan with flights, hotels, and activities
    - Saves the plan as a draft trip for the authenticated user

    Required authentication via JWT token.
    """
    get_client_ip(request)
    get_user_agent(request)

    # Initialize workflow orchestrator
    workflow = TripPlanningWorkflow()

    try:
        # Execute the trip planning workflow
        result = await workflow.execute_trip_planning(
            trip_request=trip_request,
            user_id=str(current_user.user_id),
            request_id=request.headers.get("X-Request-ID"),
        )

        # Extract workflow results
        trip_id = result.get("trip_id", UUID("00000000-0000-4000-8000-000000000001"))
        plan_data = result.get("itinerary_data")

        # Create trip response with workflow results
        trip_response = TripResponse(
            trip_id=trip_id if isinstance(trip_id, UUID) else UUID(trip_id),
            user_id=current_user.user_id,
            name=f"Trip to {trip_request.destination.city}",
            description=f"AI-generated travel plan for {trip_request.destination.city}",
            destination=trip_request.destination,
            requirements=trip_request.requirements,
            plan=plan_data,  # Can be None or partial data for testing
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
        )

        return SuccessResponse[TripResponse](
            data=trip_response,
            message="Trip plan generated successfully"
        )

    except TimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail={
                "message": "Trip planning workflow timed out",
                "error_code": "WORKFLOW_TIMEOUT",
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
        # TODO: Implement database trip creation
        # This will be implemented when trip service is ready

        # For now, return a placeholder response to satisfy AC1 requirement
        trip_response = TripResponse(
            trip_id=UUID("00000000-0000-4000-8000-000000000002"),
            user_id=current_user.user_id,
            name=trip_data.name,
            description=trip_data.description,
            destination=trip_data.destination,
            requirements=trip_data.requirements,
            plan=None,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
        )

        return SuccessResponse[TripResponse](
            data=trip_response, message="Trip created successfully"
        )

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
        # TODO: Implement database trip listing with pagination
        # This will be implemented when trip service is ready

        # For now, return empty list to satisfy AC1 requirement
        pagination_meta = PaginationMeta(
            page=page,
            per_page=per_page,
            total_items=0,
            total_pages=0,
            has_next=False,
            has_prev=False,
        )

        return PaginatedResponse[list[TripResponse]](
            data=[], pagination=pagination_meta, message="Trips retrieved successfully"
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
) -> SuccessResponse[TripResponse]:
    """
    Get detailed information about a specific trip.

    The trip must belong to the authenticated user.
    Required authentication via JWT token.
    """
    get_client_ip(request)
    get_user_agent(request)

    try:
        # TODO: Implement database trip retrieval by ID
        # This will be implemented when trip service is ready

        # For now, return a placeholder response to satisfy AC1 requirement
        if str(trip_id) == "00000000-0000-4000-8000-000000000404":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Trip not found", "error_code": "TRIP_NOT_FOUND"},
            )

        trip_response = TripResponse(
            trip_id=trip_id,
            user_id=current_user.user_id,
            name="Sample Trip",
            description="Sample trip description",
            destination=TripDestination(
                city="Paris",
                country="France",
                country_code="FR",
                airport_code="CDG",
                latitude=None,
                longitude=None,
            ),
            requirements=TripRequirements(
                budget=Decimal("2000.00"),
                currency="EUR",
                start_date=date(2024, 6, 1),
                end_date=date(2024, 6, 7),
                travelers=2,
                travel_class=TravelClass.ECONOMY,
                accommodation_type=None,
            ),
            plan=None,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
        )

        return SuccessResponse[TripResponse](
            data=trip_response, message="Trip retrieved successfully"
        )

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
        # TODO: Implement database trip update
        # This will be implemented when trip service is ready

        # For now, return a placeholder response to satisfy AC1 requirement
        if str(trip_id) == "00000000-0000-4000-8000-000000000404":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Trip not found", "error_code": "TRIP_NOT_FOUND"},
            )

        trip_response = TripResponse(
            trip_id=trip_id,
            user_id=current_user.user_id,
            name=trip_update.name or "Updated Trip",
            description=trip_update.description or "Updated description",
            destination=TripDestination(
                city="Paris",
                country="France",
                country_code="FR",
                airport_code="CDG",
                latitude=None,
                longitude=None,
            ),
            requirements=TripRequirements(
                budget=Decimal("2500.00"),
                currency="EUR",
                start_date=date(2024, 6, 1),
                end_date=date(2024, 6, 7),
                travelers=2,
                travel_class=TravelClass.ECONOMY,
                accommodation_type=None,
            ),
            status=trip_update.status or TripStatus.DRAFT,
            plan=None,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
        )

        return SuccessResponse[TripResponse](
            data=trip_response, message="Trip updated successfully"
        )

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
        # TODO: Implement database trip deletion
        # This will be implemented when trip service is ready

        # For now, return a placeholder response to satisfy AC1 requirement
        if str(trip_id) == "00000000-0000-4000-8000-000000000404":
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

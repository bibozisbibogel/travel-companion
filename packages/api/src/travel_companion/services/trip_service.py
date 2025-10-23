"""Trip service for handling trip operations."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from supabase import Client

from travel_companion.models.itinerary_output import ItineraryOutput
from travel_companion.models.trip import (
    TripDestination,
    TripRequirements,
    TripResponse,
    TripStatus,
    TripUpdate,
)
from travel_companion.utils.errors import DatabaseError


class TripService:
    """Service for trip operations."""

    def __init__(self, client: Client):
        self.client = client

    async def create_trip(
        self,
        user_id: UUID,
        name: str,
        destination: TripDestination,
        requirements: TripRequirements,
        plan: ItineraryOutput | None = None,
        description: str | None = None,
        status: TripStatus = TripStatus.DRAFT,
    ) -> TripResponse:
        """
        Create a new trip with destination, requirements, and optional plan.

        Args:
            user_id: User ID who owns the trip
            name: Trip name
            destination: Trip destination details
            requirements: Trip requirements (budget, dates, travelers, etc)
            plan: Optional generated trip plan (itinerary)
            description: Optional trip description
            status: Trip status (default: DRAFT)

        Returns:
            TripResponse with created trip data

        Raises:
            DatabaseError: If database operation fails
        """
        now = datetime.now(UTC)

        # Prepare trip data for database
        trip_dict: dict[str, Any] = {
            "user_id": str(user_id),
            "name": name,
            "description": description,
            "destination": destination.city,
            "start_date": requirements.start_date.isoformat(),
            "end_date": requirements.end_date.isoformat(),
            "total_budget": float(requirements.budget),
            "traveler_count": requirements.travelers,
            "status": status.value,
            "preferences": {
                "travel_class": requirements.travel_class.value,
                "accommodation_type": (
                    requirements.accommodation_type.value
                    if requirements.accommodation_type
                    else None
                ),
                "currency": requirements.currency,
                "destination_details": destination.model_dump(),
            },
            "itinerary_data": plan.model_dump(mode="json") if plan else {},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        try:
            result = self.client.table("trips").insert(trip_dict).execute()

            if not result.data:
                raise DatabaseError("Failed to create trip - no data returned from database")

            # Convert database record to TripResponse
            db_record = result.data[0]
            return self._db_record_to_response(db_record)

        except Exception as e:
            raise DatabaseError(f"Database error during trip creation: {str(e)}") from e

    async def get_trip_by_id(self, trip_id: UUID, user_id: UUID) -> TripResponse | None:
        """
        Get trip by ID for a specific user.

        Args:
            trip_id: Trip ID
            user_id: User ID who owns the trip

        Returns:
            TripResponse if found, None otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            result = (
                self.client.table("trips")
                .select("*")
                .eq("trip_id", str(trip_id))
                .eq("user_id", str(user_id))
                .execute()
            )

            if not result.data:
                return None

            return self._db_record_to_response(result.data[0])

        except Exception as e:
            raise DatabaseError(f"Database error retrieving trip by ID: {str(e)}") from e

    async def list_user_trips(
        self, user_id: UUID, page: int = 1, per_page: int = 20
    ) -> tuple[list[TripResponse], int]:
        """
        List all trips for a user with pagination.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Tuple of (list of trips, total count)

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            # Calculate offset
            offset = (page - 1) * per_page

            # Get total count
            count_result = (
                self.client.table("trips")
                .select("*", count="exact")
                .eq("user_id", str(user_id))
                .execute()
            )
            total_count = count_result.count or 0

            # Get paginated results
            result = (
                self.client.table("trips")
                .select("*")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .range(offset, offset + per_page - 1)
                .execute()
            )

            trips = [self._db_record_to_response(record) for record in result.data]

            return trips, total_count

        except Exception as e:
            raise DatabaseError(f"Database error listing user trips: {str(e)}") from e

    async def update_trip(
        self, trip_id: UUID, user_id: UUID, update_data: TripUpdate
    ) -> TripResponse | None:
        """
        Update trip information.

        Args:
            trip_id: Trip ID
            user_id: User ID who owns the trip
            update_data: Fields to update

        Returns:
            Updated TripResponse if found, None otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            # Build update dictionary with only provided fields
            update_dict: dict[str, Any] = {"updated_at": datetime.now(UTC).isoformat()}

            if update_data.name is not None:
                update_dict["name"] = update_data.name

            if update_data.description is not None:
                update_dict["description"] = update_data.description

            if update_data.status is not None:
                update_dict["status"] = update_data.status.value

            if update_data.requirements is not None:
                update_dict["start_date"] = update_data.requirements.start_date.isoformat()
                update_dict["end_date"] = update_data.requirements.end_date.isoformat()
                update_dict["total_budget"] = float(update_data.requirements.budget)
                update_dict["traveler_count"] = update_data.requirements.travelers

                # Update preferences
                existing_trip = await self.get_trip_by_id(trip_id, user_id)
                if existing_trip:
                    preferences = existing_trip.model_dump().get("preferences", {})
                    preferences.update(
                        {
                            "travel_class": update_data.requirements.travel_class.value,
                            "accommodation_type": (
                                update_data.requirements.accommodation_type.value
                                if update_data.requirements.accommodation_type
                                else None
                            ),
                            "currency": update_data.requirements.currency,
                        }
                    )
                    update_dict["preferences"] = preferences

            # Update trip in database
            result = (
                self.client.table("trips")
                .update(update_dict)
                .eq("trip_id", str(trip_id))
                .eq("user_id", str(user_id))
                .execute()
            )

            if not result.data:
                return None

            return self._db_record_to_response(result.data[0])

        except Exception as e:
            raise DatabaseError(f"Database error updating trip: {str(e)}") from e

    async def delete_trip(self, trip_id: UUID, user_id: UUID) -> bool:
        """
        Delete a trip.

        Args:
            trip_id: Trip ID
            user_id: User ID who owns the trip

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            result = (
                self.client.table("trips")
                .delete()
                .eq("trip_id", str(trip_id))
                .eq("user_id", str(user_id))
                .execute()
            )

            return len(result.data) > 0

        except Exception as e:
            raise DatabaseError(f"Database error deleting trip: {str(e)}") from e

    def _db_record_to_response(self, record: dict[str, Any]) -> TripResponse:
        """
        Convert database record to TripResponse model.

        Args:
            record: Database record dictionary

        Returns:
            TripResponse model instance
        """
        # Extract preferences and destination details
        preferences = record.get("preferences", {})
        destination_details = preferences.get("destination_details", {})

        # Build destination object
        destination = TripDestination(
            city=destination_details.get("city", record.get("destination", "")),
            country=destination_details.get("country", ""),
            country_code=destination_details.get("country_code", ""),
            airport_code=destination_details.get("airport_code"),
            latitude=destination_details.get("latitude"),
            longitude=destination_details.get("longitude"),
        )

        # Build requirements object
        requirements = TripRequirements(
            budget=record.get("total_budget", 0),
            currency=preferences.get("currency", "USD"),
            start_date=record.get("start_date"),
            end_date=record.get("end_date"),
            travelers=record.get("traveler_count", 1),
            travel_class=preferences.get("travel_class", "economy"),
            accommodation_type=preferences.get("accommodation_type"),
        )

        # Parse itinerary data if present
        itinerary_data = record.get("itinerary_data", {})
        plan = None
        if itinerary_data and isinstance(itinerary_data, dict) and itinerary_data:
            try:
                plan = ItineraryOutput(**itinerary_data)
            except Exception:
                # If parsing fails, leave plan as None
                pass

        # Build TripResponse
        return TripResponse(
            trip_id=UUID(record["trip_id"]),
            user_id=UUID(record["user_id"]),
            name=record.get("name", ""),
            description=record.get("description"),
            destination=destination,
            requirements=requirements,
            status=TripStatus(record.get("status", "draft")),
            plan=plan,
            created_at=datetime.fromisoformat(record["created_at"]),
            updated_at=datetime.fromisoformat(record["updated_at"]),
        )

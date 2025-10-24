"""Tests for TripService."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from travel_companion.models.itinerary_output import ItineraryOutput
from travel_companion.models.trip import (
    AccommodationType,
    TravelClass,
    TripDestination,
    TripRequirements,
    TripUpdate,
)
from travel_companion.services.trip_service import TripService
from travel_companion.utils.errors import DatabaseError


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    return MagicMock()


@pytest.fixture
def trip_service(mock_supabase_client):
    """Create TripService instance with mock client."""
    return TripService(mock_supabase_client)


@pytest.fixture
def sample_destination():
    """Sample trip destination."""
    return TripDestination(
        city="Paris",
        country="France",
        country_code="FR",
        airport_code="CDG",
        latitude=48.8566,
        longitude=2.3522,
    )


@pytest.fixture
def sample_requirements():
    """Sample trip requirements."""
    return TripRequirements(
        budget=Decimal("2000.00"),
        currency="EUR",
        start_date=date(2024, 6, 1),
        end_date=date(2024, 6, 7),
        travelers=2,
        travel_class=TravelClass.ECONOMY,
        accommodation_type=AccommodationType.HOTEL,
    )


@pytest.fixture
def sample_db_record():
    """Sample database record for a trip."""
    return {
        "trip_id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Trip to Paris",
        "description": "AI-generated travel plan",
        "destination": "Paris",
        "start_date": "2024-06-01",
        "end_date": "2024-06-07",
        "total_budget": 2000.00,
        "traveler_count": 2,
        "status": "draft",
        "preferences": {
            "travel_class": "economy",
            "accommodation_type": "hotel",
            "currency": "EUR",
            "destination_details": {
                "city": "Paris",
                "country": "France",
                "country_code": "FR",
                "airport_code": "CDG",
                "latitude": 48.8566,
                "longitude": 2.3522,
            },
        },
        "itinerary_data": {},
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    }


class TestTripServiceCreate:
    """Tests for trip creation."""

    async def test_create_trip_success(
        self, trip_service, mock_supabase_client, sample_destination, sample_requirements
    ):
        """Test successful trip creation."""
        user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        mock_result = MagicMock()
        mock_result.data = [
            {
                "trip_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": str(user_id),
                "name": "Trip to Paris",
                "description": "Test trip",
                "destination": "Paris",
                "start_date": "2024-06-01",
                "end_date": "2024-06-07",
                "total_budget": 2000.00,
                "traveler_count": 2,
                "status": "draft",
                "preferences": {
                    "travel_class": "economy",
                    "accommodation_type": "hotel",
                    "currency": "EUR",
                    "destination_details": sample_destination.model_dump(),
                },
                "itinerary_data": {},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
        ]

        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = mock_result
        mock_supabase_client.table.return_value = mock_table

        result = await trip_service.create_trip(
            user_id=user_id,
            name="Trip to Paris",
            destination=sample_destination,
            requirements=sample_requirements,
            description="Test trip",
        )

        assert result.trip_id == UUID("550e8400-e29b-41d4-a716-446655440000")
        assert result.user_id == user_id
        assert result.name == "Trip to Paris"
        assert result.destination.city == "Paris"
        mock_supabase_client.table.assert_called_once_with("trips")

    async def test_create_trip_with_plan(
        self, trip_service, mock_supabase_client, sample_destination, sample_requirements
    ):
        """Test trip creation with itinerary plan."""
        from travel_companion.models.itinerary_output import (
            AccommodationInfo,
            Address,
            BudgetBreakdown,
            BudgetCategoryRange,
            BudgetInfo,
            DailyCost,
            DateRange,
            DayItinerary,
            Destination,
            FlightDetails,
            FlightInfo,
            RouteInfo,
            TimeInfo,
            TravelerInfo,
            TripInfo,
        )

        user_id = uuid4()

        # Create a minimal valid ItineraryOutput
        plan = ItineraryOutput(
            trip=TripInfo(
                destination=Destination(city="Paris", country="France"),
                dates=DateRange(start=date(2024, 6, 1), end=date(2024, 6, 7), duration_days=7),
                travelers=TravelerInfo(count=2),
                budget=BudgetInfo(
                    total=Decimal("2000.00"),
                    currency="EUR",
                    spent=Decimal("1800.00"),
                    remaining=Decimal("200.00"),
                ),
            ),
            flights=FlightInfo(
                outbound=FlightDetails(
                    airline="Air France",
                    flight_number="AF123",
                    route=RouteInfo(from_airport="JFK", to_airport="CDG"),
                    departure=TimeInfo(time="10:00", timezone="America/New_York"),
                    price_per_person=Decimal("250.00"),
                    total_price=Decimal("500.00"),
                ),
                total_cost=Decimal("500.00"),
            ),
            accommodation=AccommodationInfo(
                name="Hotel Paris",
                address=Address(city="Paris", country="France"),
                price_per_night=Decimal("150.00"),
                nights=6,
                total_cost=Decimal("900.00"),
            ),
            itinerary=[
                DayItinerary(
                    day=1,
                    date=date(2024, 6, 1),
                    day_of_week="Saturday",
                    title="Arrival Day",
                    daily_cost=DailyCost(
                        min=Decimal("50.00"), max=Decimal("100.00"), currency="EUR"
                    ),
                )
            ],
            budget_breakdown=BudgetBreakdown(
                flights=Decimal("500.00"),
                accommodation=Decimal("900.00"),
                total=BudgetCategoryRange(min=Decimal("1800.00"), max=Decimal("2000.00")),
            ),
        )

        mock_result = MagicMock()
        mock_result.data = [
            {
                "trip_id": str(uuid4()),
                "user_id": str(user_id),
                "name": "Trip to Paris",
                "description": None,
                "destination": "Paris",
                "start_date": "2024-06-01",
                "end_date": "2024-06-07",
                "total_budget": 2000.00,
                "traveler_count": 2,
                "status": "draft",
                "preferences": {
                    "travel_class": "economy",
                    "accommodation_type": "hotel",
                    "currency": "EUR",
                    "destination_details": sample_destination.model_dump(),
                },
                "itinerary_data": plan.model_dump(mode="json"),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
        ]

        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = mock_result
        mock_supabase_client.table.return_value = mock_table

        result = await trip_service.create_trip(
            user_id=user_id,
            name="Trip to Paris",
            destination=sample_destination,
            requirements=sample_requirements,
            plan=plan,
        )

        assert result.plan is not None
        assert result.plan.trip.destination.city == "Paris"

    async def test_create_trip_database_error(
        self, trip_service, mock_supabase_client, sample_destination, sample_requirements
    ):
        """Test trip creation with database error."""
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.side_effect = Exception("Database error")
        mock_supabase_client.table.return_value = mock_table

        with pytest.raises(DatabaseError) as exc_info:
            await trip_service.create_trip(
                user_id=uuid4(),
                name="Trip to Paris",
                destination=sample_destination,
                requirements=sample_requirements,
            )

        assert "Database error during trip creation" in str(exc_info.value)


class TestTripServiceGet:
    """Tests for trip retrieval."""

    async def test_get_trip_by_id_success(
        self, trip_service, mock_supabase_client, sample_db_record
    ):
        """Test successful trip retrieval by ID."""
        trip_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        user_id = UUID("123e4567-e89b-12d3-a456-426614174000")

        mock_result = MagicMock()
        mock_result.data = [sample_db_record]

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = (
            mock_result
        )
        mock_supabase_client.table.return_value = mock_table

        result = await trip_service.get_trip_by_id(trip_id=trip_id, user_id=user_id)

        assert result is not None
        assert result.trip_id == trip_id
        assert result.name == "Trip to Paris"
        assert result.destination.city == "Paris"

    async def test_get_trip_by_id_not_found(self, trip_service, mock_supabase_client):
        """Test trip retrieval when trip doesn't exist."""
        mock_result = MagicMock()
        mock_result.data = []

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = (
            mock_result
        )
        mock_supabase_client.table.return_value = mock_table

        result = await trip_service.get_trip_by_id(trip_id=uuid4(), user_id=uuid4())

        assert result is None


class TestTripServiceList:
    """Tests for listing trips."""

    async def test_list_user_trips_success(
        self, trip_service, mock_supabase_client, sample_db_record
    ):
        """Test successful listing of user trips."""
        user_id = UUID("123e4567-e89b-12d3-a456-426614174000")

        # Mock count result
        mock_count_result = MagicMock()
        mock_count_result.count = 1

        # Mock trips result
        mock_trips_result = MagicMock()
        mock_trips_result.data = [sample_db_record]

        mock_table = MagicMock()

        # First call for count
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_count_result

        # Second call for trips
        (
            mock_table.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value
        ) = mock_trips_result

        mock_supabase_client.table.return_value = mock_table

        trips, total_count = await trip_service.list_user_trips(
            user_id=user_id, page=1, per_page=20
        )

        assert total_count == 1
        assert len(trips) == 1
        assert trips[0].name == "Trip to Paris"

    async def test_list_user_trips_empty(self, trip_service, mock_supabase_client):
        """Test listing trips when user has no trips."""
        mock_count_result = MagicMock()
        mock_count_result.count = 0

        mock_trips_result = MagicMock()
        mock_trips_result.data = []

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_count_result
        (
            mock_table.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value
        ) = mock_trips_result

        mock_supabase_client.table.return_value = mock_table

        trips, total_count = await trip_service.list_user_trips(user_id=uuid4())

        assert total_count == 0
        assert len(trips) == 0


class TestTripServiceUpdate:
    """Tests for trip updates."""

    async def test_update_trip_success(self, trip_service, mock_supabase_client, sample_db_record):
        """Test successful trip update."""
        trip_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        user_id = UUID("123e4567-e89b-12d3-a456-426614174000")

        update_data = TripUpdate(name="Updated Trip Name", description="Updated description")

        # Mock get_trip_by_id
        mock_get_result = MagicMock()
        mock_get_result.data = [sample_db_record]

        # Mock update result
        updated_record = sample_db_record.copy()
        updated_record["name"] = "Updated Trip Name"
        updated_record["description"] = "Updated description"
        mock_update_result = MagicMock()
        mock_update_result.data = [updated_record]

        mock_table = MagicMock()

        # Setup for get_trip_by_id call
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = (
            mock_get_result
        )

        # Setup for update call
        (
            mock_table.update.return_value.eq.return_value.eq.return_value.execute.return_value
        ) = mock_update_result

        mock_supabase_client.table.return_value = mock_table

        result = await trip_service.update_trip(
            trip_id=trip_id, user_id=user_id, update_data=update_data
        )

        assert result is not None
        assert result.name == "Updated Trip Name"
        assert result.description == "Updated description"

    async def test_update_trip_not_found(self, trip_service, mock_supabase_client):
        """Test updating non-existent trip."""
        mock_result = MagicMock()
        mock_result.data = []

        mock_table = MagicMock()
        (
            mock_table.update.return_value.eq.return_value.eq.return_value.execute.return_value
        ) = mock_result
        mock_supabase_client.table.return_value = mock_table

        update_data = TripUpdate(name="Updated Trip")
        result = await trip_service.update_trip(
            trip_id=uuid4(), user_id=uuid4(), update_data=update_data
        )

        assert result is None


class TestTripServiceDelete:
    """Tests for trip deletion."""

    async def test_delete_trip_success(self, trip_service, mock_supabase_client):
        """Test successful trip deletion."""
        trip_id = uuid4()
        user_id = uuid4()

        mock_result = MagicMock()
        mock_result.data = [{"trip_id": str(trip_id)}]

        mock_table = MagicMock()
        (
            mock_table.delete.return_value.eq.return_value.eq.return_value.execute.return_value
        ) = mock_result
        mock_supabase_client.table.return_value = mock_table

        result = await trip_service.delete_trip(trip_id=trip_id, user_id=user_id)

        assert result is True

    async def test_delete_trip_not_found(self, trip_service, mock_supabase_client):
        """Test deleting non-existent trip."""
        mock_result = MagicMock()
        mock_result.data = []

        mock_table = MagicMock()
        (
            mock_table.delete.return_value.eq.return_value.eq.return_value.execute.return_value
        ) = mock_result
        mock_supabase_client.table.return_value = mock_table

        result = await trip_service.delete_trip(trip_id=uuid4(), user_id=uuid4())

        assert result is False

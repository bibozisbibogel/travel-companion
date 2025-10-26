"""Tests for itinerary geocoding helper."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from travel_companion.models.itinerary_output import (
    AccommodationInfo,
    Address,
    BudgetBreakdown,
    BudgetCategoryRange,
    BudgetInfo,
    DateRange,
    Destination,
    FlightDetails,
    FlightInfo,
    ItineraryActivity,
    ItineraryOutput,
    RouteInfo,
    TimeInfo,
    TravelerInfo,
    TripInfo,
    ActivityCategory,
)
from travel_companion.services.geocoding_service import GeocodeResult
from travel_companion.services.itinerary_geocoder import ItineraryGeocoder, geocode_itinerary


@pytest.fixture
def mock_geocoding_service():
    """Mock geocoding service."""
    with patch(
        "travel_companion.services.itinerary_geocoder.get_geocoding_service"
    ) as mock_get:
        service = Mock()
        service.geocode_location = AsyncMock()
        mock_get.return_value = service
        yield service


@pytest.fixture
def sample_itinerary():
    """Create a sample itinerary for testing."""
    return ItineraryOutput(
        trip=TripInfo(
            destination=Destination(city="Rome", country="Italy"),
            dates=DateRange(
                start=date(2024, 6, 1), end=date(2024, 6, 5), duration_days=5
            ),
            travelers=TravelerInfo(count=2, type="adults"),
            budget=BudgetInfo(
                total=Decimal("2000"), currency="USD", spent=Decimal("0"), remaining=Decimal("2000")
            ),
        ),
        flights=FlightInfo(
            outbound=FlightDetails(
                airline="United",
                flight_number="UA123",
                route=RouteInfo(from_airport="JFK", to_airport="FCO"),
                departure=TimeInfo(time="10:00", timezone="America/New_York"),
                arrival=TimeInfo(time="22:00", timezone="Europe/Rome"),
                price_per_person=Decimal("500"),
                total_price=Decimal("1000"),
            ),
            total_cost=Decimal("1000"),
        ),
        accommodation=AccommodationInfo(
            name="Hotel Roma",
            address=Address(
                street="Via Nazionale 7", city="Rome", region=None, country="Italy"
            ),
            price_per_night=Decimal("100"),
            nights=4,
            total_cost=Decimal("400"),
        ),
        itinerary=[],
        budget_breakdown=BudgetBreakdown(
            flights=Decimal("1000"),
            accommodation=Decimal("400"),
            total=BudgetCategoryRange(min=Decimal("1400"), max=Decimal("1600")),
        ),
    )


class TestItineraryGeocoder:
    """Tests for ItineraryGeocoder."""

    @pytest.mark.asyncio
    async def test_geocode_destination_success(self, mock_geocoding_service, sample_itinerary):
        """Test successful destination geocoding."""
        # Mock successful geocoding
        mock_geocoding_service.geocode_location.return_value = GeocodeResult(
            status="success",
            latitude=41.9028,
            longitude=12.4964,
            formatted_address="Rome, Italy",
        )

        geocoder = ItineraryGeocoder()
        await geocoder._geocode_destination(sample_itinerary.trip.destination)

        # Verify coordinates were added
        assert sample_itinerary.trip.destination.coordinates is not None
        assert sample_itinerary.trip.destination.coordinates.latitude == 41.9028
        assert sample_itinerary.trip.destination.coordinates.longitude == 12.4964
        assert sample_itinerary.trip.destination.coordinates.geocoding_status == "success"

        # Verify geocoding service was called
        mock_geocoding_service.geocode_location.assert_called_once_with("Rome, Italy")

    @pytest.mark.asyncio
    async def test_geocode_destination_failure(self, mock_geocoding_service, sample_itinerary):
        """Test destination geocoding failure."""
        # Mock failed geocoding
        mock_geocoding_service.geocode_location.return_value = GeocodeResult(
            status="failed",
            error_message="No results found",
        )

        geocoder = ItineraryGeocoder()
        await geocoder._geocode_destination(sample_itinerary.trip.destination)

        # Verify coordinates reflect failure
        assert sample_itinerary.trip.destination.coordinates is not None
        assert sample_itinerary.trip.destination.coordinates.geocoding_status == "failed"
        assert sample_itinerary.trip.destination.coordinates.geocoding_error_message == (
            "No results found"
        )

    @pytest.mark.asyncio
    async def test_geocode_accommodation_success(self, mock_geocoding_service, sample_itinerary):
        """Test successful accommodation geocoding."""
        mock_geocoding_service.geocode_location.return_value = GeocodeResult(
            status="success",
            latitude=41.9010,
            longitude=12.4926,
            formatted_address="Via Nazionale 7, Rome, Italy",
        )

        geocoder = ItineraryGeocoder()
        await geocoder._geocode_accommodation(sample_itinerary.accommodation)

        # Verify coordinates were added
        assert sample_itinerary.accommodation.coordinates is not None
        assert sample_itinerary.accommodation.coordinates.latitude == 41.9010
        assert sample_itinerary.accommodation.coordinates.longitude == 12.4926
        assert sample_itinerary.accommodation.coordinates.geocoding_status == "success"

    @pytest.mark.asyncio
    async def test_geocode_activity_success(self, mock_geocoding_service):
        """Test successful activity geocoding."""
        activity = ItineraryActivity(
            category=ActivityCategory.ATTRACTION,
            title="Visit Trevi Fountain",
            location="Trevi Fountain, Rome, Italy",
        )

        mock_geocoding_service.geocode_location.return_value = GeocodeResult(
            status="success",
            latitude=41.9009,
            longitude=12.4833,
            formatted_address="Trevi Fountain, Rome, Italy",
        )

        geocoder = ItineraryGeocoder()
        await geocoder._geocode_activity(activity)

        # Verify coordinates were added
        assert activity.coordinates is not None
        assert activity.coordinates.latitude == 41.9009
        assert activity.coordinates.longitude == 12.4833
        assert activity.coordinates.geocoding_status == "success"

    @pytest.mark.asyncio
    async def test_geocode_activity_no_location(self, mock_geocoding_service):
        """Test activity geocoding skips when no location."""
        activity = ItineraryActivity(
            category=ActivityCategory.DINING,
            title="Free Morning",
            location=None,
        )

        geocoder = ItineraryGeocoder()
        await geocoder._geocode_activity(activity)

        # Verify geocoding service was not called
        mock_geocoding_service.geocode_location.assert_not_called()

        # Verify no coordinates were added
        assert activity.coordinates is None

    @pytest.mark.asyncio
    async def test_geocode_airport_success(self, mock_geocoding_service, sample_itinerary):
        """Test successful airport geocoding."""
        mock_geocoding_service.geocode_location.return_value = GeocodeResult(
            status="success",
            latitude=40.6413,
            longitude=-73.7781,
            formatted_address="JFK Airport, New York",
        )

        geocoder = ItineraryGeocoder()
        await geocoder._geocode_airport(
            "JFK", is_departure=True, flight=sample_itinerary.flights.outbound
        )

        # Verify departure coordinates were added
        assert sample_itinerary.flights.outbound.departure_coordinates is not None
        assert sample_itinerary.flights.outbound.departure_coordinates.latitude == 40.6413
        assert sample_itinerary.flights.outbound.departure_coordinates.longitude == -73.7781
        assert (
            sample_itinerary.flights.outbound.departure_coordinates.geocoding_status
            == "success"
        )

        # Verify geocoding service was called with airport search string
        mock_geocoding_service.geocode_location.assert_called_once_with("JFK Airport")

    @pytest.mark.asyncio
    async def test_geocode_itinerary_full(self, mock_geocoding_service, sample_itinerary):
        """Test geocoding complete itinerary."""
        # Mock all geocoding calls to succeed
        mock_geocoding_service.geocode_location.return_value = GeocodeResult(
            status="success",
            latitude=41.9,
            longitude=12.5,
            formatted_address="Rome, Italy",
        )

        geocoder = ItineraryGeocoder()
        result = await geocoder.geocode_itinerary(sample_itinerary)

        # Verify itinerary is returned
        assert result == sample_itinerary

        # Verify destination was geocoded
        assert result.trip.destination.coordinates is not None
        assert result.trip.destination.coordinates.geocoding_status == "success"

        # Verify accommodation was geocoded
        assert result.accommodation.coordinates is not None
        assert result.accommodation.coordinates.geocoding_status == "success"

        # Verify flight airports were geocoded
        assert result.flights.outbound.departure_coordinates is not None
        assert result.flights.outbound.arrival_coordinates is not None

    @pytest.mark.asyncio
    async def test_geocode_itinerary_convenience_function(
        self, mock_geocoding_service, sample_itinerary
    ):
        """Test convenience function for geocoding."""
        mock_geocoding_service.geocode_location.return_value = GeocodeResult(
            status="success",
            latitude=41.9,
            longitude=12.5,
        )

        result = await geocode_itinerary(sample_itinerary)

        # Verify geocoding was performed
        assert result.trip.destination.coordinates is not None
        assert result.accommodation.coordinates is not None

    @pytest.mark.asyncio
    async def test_geocode_handles_exceptions(self, mock_geocoding_service, sample_itinerary):
        """Test that geocoding handles exceptions gracefully."""
        # Mock geocoding to raise exception
        mock_geocoding_service.geocode_location.side_effect = Exception("API Error")

        geocoder = ItineraryGeocoder()
        await geocoder._geocode_destination(sample_itinerary.trip.destination)

        # Verify coordinates reflect exception
        assert sample_itinerary.trip.destination.coordinates is not None
        assert sample_itinerary.trip.destination.coordinates.geocoding_status == "failed"
        assert "Exception during geocoding" in (
            sample_itinerary.trip.destination.coordinates.geocoding_error_message or ""
        )

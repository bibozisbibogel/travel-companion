"""
Unit tests for AviationStack API client.

Tests core functionality without complex HTTP mocking.
"""

from unittest.mock import patch

import pytest

from travel_companion.services.external_apis.aviationstack import (
    AviationStackClient,
    AviationStackFlight,
    FlightSearchParams,
)
from travel_companion.utils.errors import ExternalAPIError


class TestFlightSearchParams:
    """Test flight search parameters validation."""

    def test_valid_search_params(self):
        """Test valid flight search parameters."""
        params = FlightSearchParams(
            origin="NYC",
            destination="LAX",
            departure_date="2024-12-25",
            adults=2,
        )
        assert params.origin == "NYC"
        assert params.destination == "LAX"
        assert params.departure_date == "2024-12-25"
        assert params.adults == 2
        assert params.children == 0
        assert params.currency == "USD"

    def test_invalid_origin_code(self):
        """Test invalid origin airport code."""
        with pytest.raises(ValueError):
            FlightSearchParams(
                origin="INVALID",
                destination="LAX",
                departure_date="2024-12-25",
            )

    def test_invalid_adult_count(self):
        """Test invalid adult passenger count."""
        with pytest.raises(ValueError):
            FlightSearchParams(
                origin="NYC",
                destination="LAX",
                departure_date="2024-12-25",
                adults=0,  # Invalid: must be at least 1
            )


@pytest.fixture
def aviationstack_client():
    """Create AviationStack client for testing."""
    return AviationStackClient(
        api_key="test_api_key",
        base_url="http://test-api.aviationstack.com/v1",
        timeout=10.0,
        rate_limit_per_second=5,
    )


@pytest.fixture
def mock_flight_data():
    """Create mock flight data."""
    return {
        "flight_date": "2024-12-25",
        "flight_status": "active",
        "departure": {
            "airport": "John F Kennedy International Airport",
            "timezone": "America/New_York",
            "iata": "JFK",
            "icao": "KJFK",
            "terminal": "4",
            "gate": "A12",
            "delay": None,
            "scheduled": "2024-12-25T10:00:00+00:00",
            "estimated": "2024-12-25T10:00:00+00:00",
            "actual": None,
        },
        "arrival": {
            "airport": "Los Angeles International Airport",
            "timezone": "America/Los_Angeles",
            "iata": "LAX",
            "icao": "KLAX",
            "terminal": "7",
            "gate": "B15",
            "baggage": "3",
            "delay": None,
            "scheduled": "2024-12-25T13:30:00+00:00",
            "estimated": "2024-12-25T13:30:00+00:00",
            "actual": None,
        },
        "airline": {"name": "American Airlines", "iata": "AA", "icao": "AAL"},
        "flight": {"number": "123", "iata": "AA123", "icao": "AAL123", "codeshared": None},
        "aircraft": {"registration": "N12345", "iata": "B738", "icao": "B738", "icao24": "A12345"},
        "live": {
            "updated": "2024-12-25T09:45:00+00:00",
            "latitude": 40.6413,
            "longitude": -73.7781,
            "altitude": 35000,
            "direction": 270,
            "speed_horizontal": 900,
            "speed_vertical": 0,
            "is_ground": False,
        },
    }


@pytest.fixture
def mock_route_data():
    """Create mock route data."""
    return {
        "airline_name": "American Airlines",
        "airline_iata": "AA",
        "airline_icao": "AAL",
        "departure_airport": "John F Kennedy International Airport",
        "departure_iata": "JFK",
        "departure_icao": "KJFK",
        "arrival_airport": "Los Angeles International Airport",
        "arrival_iata": "LAX",
        "arrival_icao": "KLAX",
    }


class TestAviationStackClient:
    """Test AviationStack API client functionality."""

    def test_client_initialization(self, aviationstack_client):
        """Test client initialization."""
        assert aviationstack_client.api_key == "test_api_key"
        assert aviationstack_client.base_url == "http://test-api.aviationstack.com/v1"
        assert aviationstack_client.timeout == 10.0
        assert aviationstack_client.rate_limit_per_second == 5

    def test_get_auth_params(self, aviationstack_client):
        """Test authentication parameters generation."""
        auth_params = aviationstack_client._get_auth_params()
        assert auth_params == {"access_key": "test_api_key"}

    def test_get_auth_params_no_key(self):
        """Test authentication parameters without API key."""
        client = AviationStackClient(api_key="")
        with pytest.raises(ExternalAPIError) as exc_info:
            client._get_auth_params()
        assert "AviationStack API key not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_context_manager_usage(self, aviationstack_client):
        """Test async context manager usage."""
        async with aviationstack_client as client:
            assert client is aviationstack_client
            assert aviationstack_client._client is not None

    @pytest.mark.asyncio
    @patch(
        "travel_companion.services.external_apis.aviationstack.AviationStackClient._make_authenticated_request"
    )
    async def test_search_flights_success(
        self, mock_request, aviationstack_client, mock_flight_data
    ):
        """Test successful flight search."""
        # Mock the API response
        mock_request.return_value = {"data": [mock_flight_data]}

        search_params = FlightSearchParams(
            origin="JFK",
            destination="LAX",
            departure_date="2024-12-25",
            adults=1,
        )

        async with aviationstack_client:
            flights = await aviationstack_client.search_flights(search_params)

            assert len(flights) == 1
            assert isinstance(flights[0], AviationStackFlight)
            assert flights[0].flight_status == "active"
            assert flights[0].airline["name"] == "American Airlines"
            assert flights[0].flight["number"] == "123"

            # Verify the request was made with correct parameters
            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/flights",
                params={
                    "dep_iata": "JFK",
                    "arr_iata": "LAX",
                    "flight_date": "2024-12-25",
                    "limit": 100,
                },
            )

    @pytest.mark.asyncio
    @patch(
        "travel_companion.services.external_apis.aviationstack.AviationStackClient._make_authenticated_request"
    )
    async def test_search_flights_error(self, mock_request, aviationstack_client):
        """Test flight search error handling."""
        mock_request.side_effect = ExternalAPIError("API request failed")

        search_params = FlightSearchParams(
            origin="JFK",
            destination="LAX",
            departure_date="2024-12-25",
            adults=1,
        )

        async with aviationstack_client:
            with pytest.raises(ExternalAPIError) as exc_info:
                await aviationstack_client.search_flights(search_params)
            assert "Flight search failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch(
        "travel_companion.services.external_apis.aviationstack.AviationStackClient._make_authenticated_request"
    )
    async def test_get_routes_success(self, mock_request, aviationstack_client, mock_route_data):
        """Test successful route retrieval."""
        mock_request.return_value = {"data": [mock_route_data]}

        async with aviationstack_client:
            routes = await aviationstack_client.get_routes("JFK", "LAX")
            assert len(routes) == 1
            assert routes[0].airline_name == "American Airlines"
            assert routes[0].departure_iata == "JFK"
            assert routes[0].arrival_iata == "LAX"

            # Verify the request was made with correct parameters
            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/routes",
                params={
                    "dep_iata": "JFK",
                    "arr_iata": "LAX",
                },
            )

    @pytest.mark.asyncio
    @patch(
        "travel_companion.services.external_apis.aviationstack.AviationStackClient._make_authenticated_request"
    )
    async def test_get_airport_info_success(self, mock_request, aviationstack_client):
        """Test successful airport information retrieval."""
        mock_airport_data = {
            "airport_name": "Los Angeles International Airport",
            "iata_code": "LAX",
            "icao_code": "KLAX",
            "country_name": "United States",
            "city": "Los Angeles",
            "timezone": "America/Los_Angeles",
            "gmt": "-8",
            "coordinates": {"latitude": 33.94254, "longitude": -118.40807},
        }
        mock_request.return_value = {"data": [mock_airport_data]}

        async with aviationstack_client:
            airport_info = await aviationstack_client.get_airport_info("LAX")
            assert airport_info["iata_code"] == "LAX"
            assert airport_info["airport_name"] == "Los Angeles International Airport"

    @pytest.mark.asyncio
    @patch(
        "travel_companion.services.external_apis.aviationstack.AviationStackClient._make_authenticated_request"
    )
    async def test_get_airport_info_not_found(self, mock_request, aviationstack_client):
        """Test airport information not found."""
        mock_request.return_value = {"data": []}

        async with aviationstack_client:
            with pytest.raises(ExternalAPIError) as exc_info:
                await aviationstack_client.get_airport_info("INVALID")
            assert "Airport not found" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch(
        "travel_companion.services.external_apis.aviationstack.AviationStackClient._make_authenticated_request"
    )
    async def test_health_check_success(self, mock_request, aviationstack_client):
        """Test successful health check."""
        mock_request.return_value = {"data": [{"airport_name": "Test Airport"}]}

        async with aviationstack_client:
            is_healthy = await aviationstack_client.health_check()
            assert is_healthy is True

    @pytest.mark.asyncio
    @patch(
        "travel_companion.services.external_apis.aviationstack.AviationStackClient._make_authenticated_request"
    )
    async def test_health_check_failure(self, mock_request, aviationstack_client):
        """Test health check failure."""
        mock_request.side_effect = ExternalAPIError("API request failed")

        async with aviationstack_client:
            is_healthy = await aviationstack_client.health_check()
            assert is_healthy is False

    def test_flight_data_model_validation(self, mock_flight_data):
        """Test AviationStackFlight model validation."""
        flight = AviationStackFlight(**mock_flight_data)
        assert flight.flight_status == "active"
        assert flight.airline["name"] == "American Airlines"
        assert flight.flight["number"] == "123"
        assert flight.departure["iata"] == "JFK"
        assert flight.arrival["iata"] == "LAX"

    @pytest.mark.asyncio
    async def test_rate_limiting(self, aviationstack_client):
        """Test rate limiting mechanism."""
        # Set a very low rate limit for testing
        aviationstack_client.rate_limit_per_second = 2

        async with aviationstack_client:
            import time

            start_time = time.time()

            # Make two rate-limited calls
            await aviationstack_client._rate_limit()
            await aviationstack_client._rate_limit()

            end_time = time.time()
            elapsed = end_time - start_time

            # Should take at least 0.5 seconds due to rate limiting (1/2 per second)
            assert elapsed >= 0.4  # Allow for some timing variance

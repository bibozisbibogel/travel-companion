"""
Simplified unit tests for Amadeus API client.

Tests core functionality without complex HTTP mocking.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from travel_companion.services.external_apis.amadeus import (
    AmadeusAuthToken,
    AmadeusClient,
    AmadeusFlightOffer,
    FlightSearchParams,
)
from travel_companion.utils.errors import ExternalAPIError


class TestAmadeusAuthToken:
    """Test Amadeus authentication token model."""

    def test_token_initialization(self):
        """Test token model initialization."""
        token = AmadeusAuthToken(
            access_token="test_token",
            token_type="Bearer",
            expires_in=1800,
        )
        assert token.access_token == "test_token"
        assert token.token_type == "Bearer"
        assert token.expires_in == 1800

    def test_token_expiration_check_not_expired(self):
        """Test token expiration check when not expired."""
        token = AmadeusAuthToken(
            access_token="test_token",
            token_type="Bearer",
            expires_in=1800,
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        assert not token.is_expired

    def test_token_expiration_check_expired(self):
        """Test token expiration check when expired."""
        token = AmadeusAuthToken(
            access_token="test_token",
            token_type="Bearer",
            expires_in=1800,
            expires_at=datetime.utcnow() - timedelta(minutes=10),
        )
        assert token.is_expired


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
def amadeus_client():
    """Create Amadeus client for testing."""
    return AmadeusClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        base_url="https://test.amadeus.com",
        timeout=10.0,
        rate_limit_per_second=5,
    )


@pytest.fixture
def mock_flight_offer():
    """Create mock flight offer data."""
    return {
        "id": "test_offer_1",
        "source": "GDS",
        "instant_ticketing_required": False,
        "non_homogeneous": False,
        "one_way": False,
        "last_ticketing_date": "2024-12-20",
        "price": {
            "currency": "USD",
            "total": "350.00",
            "base": "300.00",
        },
        "itineraries": [
            {
                "duration": "PT5H30M",
                "segments": [
                    {
                        "departure": {
                            "iataCode": "NYC",
                            "terminal": "4",
                            "at": "2024-12-25T10:00:00",
                        },
                        "arrival": {
                            "iataCode": "LAX",
                            "terminal": "7",
                            "at": "2024-12-25T13:30:00",
                        },
                        "carrierCode": "AA",
                        "number": "123",
                    }
                ],
            }
        ],
        "pricing_options": {"fareType": ["PUBLISHED"]},
        "validating_airline_codes": ["AA"],
        "traveler_pricings": [
            {
                "travelerId": "1",
                "fareOption": "STANDARD",
                "travelerType": "ADULT",
                "price": {"currency": "USD", "total": "350.00", "base": "300.00"},
            }
        ],
    }


class TestAmadeusClient:
    """Test Amadeus API client functionality."""

    def test_client_initialization(self, amadeus_client):
        """Test client initialization."""
        assert amadeus_client.client_id == "test_client_id"
        assert amadeus_client.client_secret == "test_client_secret"
        assert amadeus_client.base_url == "https://test.amadeus.com"
        assert amadeus_client.timeout == 10.0
        assert amadeus_client.rate_limit_per_second == 5

    @pytest.mark.asyncio
    async def test_context_manager_usage(self, amadeus_client):
        """Test async context manager usage."""
        async with amadeus_client as client:
            assert client is amadeus_client
            assert amadeus_client._client is not None

    @pytest.mark.asyncio
    @patch("travel_companion.services.external_apis.amadeus.AmadeusClient._make_authenticated_request")
    async def test_search_flights_success(self, mock_request, amadeus_client, mock_flight_offer):
        """Test successful flight search."""
        # Mock the API response
        mock_request.return_value = {"data": [mock_flight_offer]}

        search_params = FlightSearchParams(
            origin="NYC",
            destination="LAX",
            departure_date="2024-12-25",
            adults=1,
        )

        async with amadeus_client:
            offers = await amadeus_client.search_flights(search_params)

            assert len(offers) == 1
            assert isinstance(offers[0], AmadeusFlightOffer)
            assert offers[0].id == "test_offer_1"
            assert offers[0].price["currency"] == "USD"
            assert offers[0].price["total"] == "350.00"

            # Verify the request was made with correct parameters
            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/v2/shopping/flight-offers",
                params={
                    "originLocationCode": "NYC",
                    "destinationLocationCode": "LAX",
                    "departureDate": "2024-12-25",
                    "adults": 1,
                    "max": 100,
                    "currencyCode": "USD",
                },
            )

    @pytest.mark.asyncio
    @patch("travel_companion.services.external_apis.amadeus.AmadeusClient._make_authenticated_request")
    async def test_search_flights_with_return_date(self, mock_request, amadeus_client, mock_flight_offer):
        """Test flight search with return date."""
        mock_request.return_value = {"data": [mock_flight_offer]}

        search_params = FlightSearchParams(
            origin="NYC",
            destination="LAX",
            departure_date="2024-12-25",
            return_date="2025-01-02",
            adults=2,
            children=1,
        )

        async with amadeus_client:
            offers = await amadeus_client.search_flights(search_params)
            assert len(offers) == 1

            # Check that return date and passenger counts were included
            call_args = mock_request.call_args
            params = call_args.kwargs["params"]
            assert params["returnDate"] == "2025-01-02"
            assert params["adults"] == 2
            assert params["children"] == 1

    @pytest.mark.asyncio
    @patch("travel_companion.services.external_apis.amadeus.AmadeusClient._make_authenticated_request")
    async def test_search_flights_error(self, mock_request, amadeus_client):
        """Test flight search error handling."""
        mock_request.side_effect = ExternalAPIError("API request failed")

        search_params = FlightSearchParams(
            origin="NYC",
            destination="LAX",
            departure_date="2024-12-25",
            adults=1,
        )

        async with amadeus_client:
            with pytest.raises(ExternalAPIError) as exc_info:
                await amadeus_client.search_flights(search_params)
            assert "Flight search failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("travel_companion.services.external_apis.amadeus.AmadeusClient._make_authenticated_request")
    async def test_get_airport_info_success(self, mock_request, amadeus_client):
        """Test successful airport information retrieval."""
        mock_airport_data = {
            "type": "location",
            "subType": "AIRPORT",
            "name": "Los Angeles International Airport",
            "iataCode": "LAX",
            "geoCode": {"latitude": 33.94254, "longitude": -118.40807},
        }
        mock_request.return_value = {"data": [mock_airport_data]}

        async with amadeus_client:
            airport_info = await amadeus_client.get_airport_info("LAX")
            assert airport_info["iataCode"] == "LAX"
            assert airport_info["name"] == "Los Angeles International Airport"

    @pytest.mark.asyncio
    @patch("travel_companion.services.external_apis.amadeus.AmadeusClient._make_authenticated_request")
    async def test_get_airport_info_not_found(self, mock_request, amadeus_client):
        """Test airport information not found."""
        mock_request.return_value = {"data": []}

        async with amadeus_client:
            with pytest.raises(ExternalAPIError) as exc_info:
                await amadeus_client.get_airport_info("INVALID")
            assert "Airport not found" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("travel_companion.services.external_apis.amadeus.AmadeusClient._get_access_token")
    async def test_health_check_success(self, mock_get_token, amadeus_client):
        """Test successful health check."""
        mock_get_token.return_value = "test_token"

        async with amadeus_client:
            is_healthy = await amadeus_client.health_check()
            assert is_healthy is True

    @pytest.mark.asyncio
    @patch("travel_companion.services.external_apis.amadeus.AmadeusClient._get_access_token")
    async def test_health_check_failure(self, mock_get_token, amadeus_client):
        """Test health check failure."""
        mock_get_token.side_effect = ExternalAPIError("Authentication failed")

        async with amadeus_client:
            is_healthy = await amadeus_client.health_check()
            assert is_healthy is False

    def test_flight_offer_model_validation(self, mock_flight_offer):
        """Test AmadeusFlightOffer model validation."""
        offer = AmadeusFlightOffer(**mock_flight_offer)
        assert offer.id == "test_offer_1"
        assert offer.source == "GDS"
        assert offer.price["currency"] == "USD"
        assert offer.price["total"] == "350.00"
        assert len(offer.itineraries) == 1
        assert len(offer.traveler_pricings) == 1

    @pytest.mark.asyncio
    async def test_rate_limiting(self, amadeus_client):
        """Test rate limiting mechanism."""
        # Set a very low rate limit for testing
        amadeus_client.rate_limit_per_second = 2

        async with amadeus_client:
            import time
            start_time = time.time()

            # Make two rate-limited calls
            await amadeus_client._rate_limit()
            await amadeus_client._rate_limit()

            end_time = time.time()
            elapsed = end_time - start_time

            # Should take at least 0.5 seconds due to rate limiting (1/2 per second)
            assert elapsed >= 0.4  # Allow for some timing variance

"""Comprehensive tests for FlightAgent functionality with resilience and API integration."""

import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from travel_companion.agents.flight_agent import FlightAgent
from travel_companion.models.external import (
    FlightComparisonResult,
    FlightOption,
    FlightSearchRequest,
    FlightSearchResponse,
)
from travel_companion.models.trip import TravelClass
from travel_companion.services.external_apis.amadeus import AmadeusFlightOffer
from travel_companion.utils.errors import ExternalAPIError


class TestFlightAgentComprehensive:
    """Comprehensive test cases for FlightAgent with API integration and resilience."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        from travel_companion.core.config import Settings

        return Settings(
            app_name="Test Travel Companion API",
            debug=True,
            database_url="test://localhost",
            redis_url="redis://localhost:6379/1",
            secret_key="test-secret",
            amadeus_client_id="test_client_id",
            amadeus_client_secret="test_client_secret",
        )

    @pytest.fixture
    def mock_database(self):
        """Create mock database manager for testing."""
        from travel_companion.core.database import DatabaseManager

        mock_db = Mock(spec=DatabaseManager)
        mock_db.health_check = AsyncMock(return_value=True)
        return mock_db

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis manager for testing."""
        from travel_companion.core.redis import RedisManager

        mock_redis = Mock(spec=RedisManager)
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)
        return mock_redis

    @pytest.fixture
    def flight_agent(self, mock_settings, mock_database, mock_redis):
        """Create FlightAgent instance for testing."""
        with patch("travel_companion.core.config.get_settings", return_value=mock_settings):
            agent = FlightAgent(
                settings=mock_settings,
                database=mock_database,
                redis=mock_redis,
            )
            return agent

    @pytest.fixture
    def sample_flight_request(self):
        """Create a sample flight search request."""
        return FlightSearchRequest(
            origin="JFK",
            destination="LAX",
            departure_date=datetime(2024, 12, 15),
            passengers=1,
            travel_class=TravelClass.ECONOMY,
            currency="USD",
            max_results=10,
        )

    @pytest.fixture
    def flight_fixtures(self):
        """Load flight test fixtures."""
        fixtures_path = Path(__file__).parent.parent / "fixtures" / "flight_data.json"
        with open(fixtures_path) as f:
            return json.load(f)

    @pytest.fixture
    def mock_amadeus_offers(self, flight_fixtures):
        """Create mock Amadeus flight offers."""
        offers_data = flight_fixtures["amadeus_flight_response"]["data"]
        return [AmadeusFlightOffer(**offer) for offer in offers_data]

    @pytest.mark.asyncio
    async def test_flight_search_with_amadeus_success(
        self, flight_agent, sample_flight_request, mock_amadeus_offers
    ):
        """Test successful flight search using Amadeus API."""
        # Mock the Amadeus client
        mock_amadeus_client = Mock()
        mock_amadeus_client.__aenter__ = AsyncMock(return_value=mock_amadeus_client)
        mock_amadeus_client.__aexit__ = AsyncMock(return_value=None)
        mock_amadeus_client.search_flights = AsyncMock(return_value=mock_amadeus_offers)

        with patch.object(flight_agent, "_get_amadeus_client", return_value=mock_amadeus_client):
            flights = await flight_agent.search_flights(sample_flight_request)

        # Verify results
        assert len(flights) == 3
        assert all(isinstance(flight, FlightOption) for flight in flights)

        # Verify first flight details
        first_flight = flights[0]
        assert first_flight.external_id == "1"
        assert first_flight.airline == "AA"
        assert first_flight.origin == "JFK"
        assert first_flight.destination == "LAX"
        assert first_flight.price == Decimal("299.99")
        assert first_flight.stops == 0

    @pytest.mark.asyncio
    async def test_flight_search_fallback_to_mock(self, flight_agent, sample_flight_request):
        """Test fallback to mock data when Amadeus API fails."""
        # Mock Amadeus client to raise exception
        mock_amadeus_client = Mock()
        mock_amadeus_client.__aenter__ = AsyncMock(side_effect=ExternalAPIError("API unavailable"))

        with patch.object(flight_agent, "_get_amadeus_client", return_value=mock_amadeus_client):
            flights = await flight_agent.search_flights(sample_flight_request)

        # Should fall back to mock data
        assert len(flights) > 0
        assert all(isinstance(flight, FlightOption) for flight in flights)
        assert all(flight.external_id.startswith("mock_") for flight in flights)

    @pytest.mark.asyncio
    async def test_flight_search_timeout_handling(self, flight_agent, sample_flight_request):
        """Test timeout handling in flight search."""

        # Mock Amadeus client that times out - use shorter timeout to prevent test hanging
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(2)  # Shorter sleep to prevent hanging tests
            return []

        mock_amadeus_client = Mock()
        mock_amadeus_client.__aenter__ = AsyncMock(return_value=mock_amadeus_client)
        mock_amadeus_client.__aexit__ = AsyncMock(return_value=None)
        mock_amadeus_client.search_flights = slow_search

        # Patch the timeout to be very short for testing
        with patch("asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = TimeoutError("Test timeout")

            with patch.object(flight_agent, "_get_amadeus_client", return_value=mock_amadeus_client):
                flights = await flight_agent.search_flights(sample_flight_request)

        # Should fall back to mock data due to timeout
        assert len(flights) > 0
        assert all(flight.external_id.startswith("mock_") for flight in flights)

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_fallback(self, flight_agent, sample_flight_request):
        """Test fallback when circuit breaker is open."""
        # Force circuit breaker to open state
        flight_agent._amadeus_circuit_breaker.state = "open"
        flight_agent._amadeus_circuit_breaker.next_attempt_time = datetime.now() + timedelta(
            minutes=5
        )

        flights = await flight_agent.search_flights(sample_flight_request)

        # Should fall back to mock data
        assert len(flights) > 0
        assert all(flight.external_id.startswith("mock_") for flight in flights)

    @pytest.mark.asyncio
    async def test_flight_comparison_and_ranking(self, flight_agent):
        """Test flight comparison and ranking logic."""
        # Create test flights with different characteristics
        test_flights = [
            FlightOption(
                flight_id=uuid4(),
                external_id="test1",
                airline="Airline A",
                flight_number="AA123",
                origin="JFK",
                destination="LAX",
                departure_time=datetime(2024, 12, 15, 8, 0),  # Morning flight
                arrival_time=datetime(2024, 12, 15, 11, 30),
                duration_minutes=210,
                stops=0,
                price=Decimal("300.00"),
                currency="USD",
            ),
            FlightOption(
                flight_id=uuid4(),
                external_id="test2",
                airline="Airline B",
                flight_number="BB456",
                origin="JFK",
                destination="LAX",
                departure_time=datetime(2024, 12, 15, 14, 0),  # Afternoon flight
                arrival_time=datetime(2024, 12, 15, 17, 0),
                duration_minutes=180,  # Shorter duration
                stops=1,  # Has stops
                price=Decimal("200.00"),  # Cheaper
                currency="USD",
            ),
            FlightOption(
                flight_id=uuid4(),
                external_id="test3",
                airline="Airline C",
                flight_number="CC789",
                origin="JFK",
                destination="LAX",
                departure_time=datetime(2024, 12, 15, 23, 0),  # Late night
                arrival_time=datetime(2024, 12, 16, 2, 0),
                duration_minutes=300,  # Longer duration
                stops=0,
                price=Decimal("150.00"),  # Cheapest
                currency="USD",
            ),
        ]

        results = await flight_agent.compare_flights(test_flights)

        # Verify all flights are returned with comparison results
        assert len(results) == 3
        assert all(isinstance(result, FlightComparisonResult) for result in results)

        # Verify sorting by score (highest first)
        scores = [result.score for result in results]
        assert scores == sorted(scores, reverse=True)

        # Verify price rankings
        for result in results:
            assert result.price_rank >= 1
            assert result.duration_rank >= 1
            assert 0 <= result.departure_preference_score <= 1

    @pytest.mark.asyncio
    async def test_amadeus_offer_conversion(
        self, flight_agent, sample_flight_request, mock_amadeus_offers
    ):
        """Test conversion of Amadeus offers to FlightOption models."""
        flights = flight_agent._convert_amadeus_offers_to_flights(
            mock_amadeus_offers, sample_flight_request
        )

        assert len(flights) == 3

        # Test first flight conversion
        first_flight = flights[0]
        assert first_flight.external_id == "1"
        assert first_flight.airline == "AA"
        assert first_flight.flight_number == "AA123"
        assert first_flight.price == Decimal("299.99")
        assert first_flight.currency == "USD"
        assert first_flight.stops == 0
        assert first_flight.duration_minutes == 330  # 5h30m

        # Test flight with stops
        second_flight = flights[1]
        assert second_flight.external_id == "2"
        assert second_flight.stops == 1  # Has 2 segments, so 1 stop

    @pytest.mark.asyncio
    async def test_process_method_end_to_end(
        self, flight_agent, sample_flight_request, mock_amadeus_offers
    ):
        """Test the complete process method end-to-end."""

        # Mock the Amadeus client with small delay to simulate real API
        async def mock_search_flights(*args, **kwargs):
            await asyncio.sleep(0.01)  # Small delay to simulate API call
            return mock_amadeus_offers

        mock_amadeus_client = Mock()
        mock_amadeus_client.__aenter__ = AsyncMock(return_value=mock_amadeus_client)
        mock_amadeus_client.__aexit__ = AsyncMock(return_value=None)
        mock_amadeus_client.search_flights = mock_search_flights

        with patch.object(flight_agent, "_get_amadeus_client", return_value=mock_amadeus_client):
            response = await flight_agent.process(sample_flight_request.model_dump())

        # Verify response structure
        assert isinstance(response, FlightSearchResponse)
        assert len(response.flights) == 3
        assert response.total_results == 3
        assert response.search_time_ms > 0
        assert not response.cached
        assert response.cache_expires_at is not None

        # Verify metadata includes ranking information
        assert "ranking_applied" in response.search_metadata
        assert response.search_metadata["ranking_applied"] is True
        assert "comparison_scores" in response.search_metadata
        assert len(response.search_metadata["comparison_scores"]) == 3

    @pytest.mark.asyncio
    async def test_caching_functionality(self, flight_agent, sample_flight_request, mock_redis):
        """Test flight search result caching."""
        # Mock cached result
        cached_response = FlightSearchResponse(
            flights=[],
            total_results=0,
            cached=True,
        )
        mock_redis.get = AsyncMock(return_value=cached_response.model_dump())

        response = await flight_agent.process(sample_flight_request.model_dump())

        # Should return cached result
        assert response.cached is True
        assert response.total_results == 0

    @pytest.mark.asyncio
    async def test_invalid_request_handling(self, flight_agent):
        """Test handling of invalid flight search requests."""
        invalid_request = {
            "origin": "X",  # Too short
            "destination": "Y",  # Too short
            "passengers": 0,  # Invalid passenger count
        }

        with pytest.raises(ValueError, match="Invalid flight search request"):
            await flight_agent.process(invalid_request)

    @pytest.mark.asyncio
    async def test_mock_data_generation(self, flight_agent, sample_flight_request):
        """Test mock flight data generation."""
        mock_flights = await flight_agent._get_mock_flight_data(sample_flight_request)

        assert len(mock_flights) <= sample_flight_request.max_results
        assert len(mock_flights) > 0

        for flight in mock_flights:
            assert flight.origin == sample_flight_request.origin
            assert flight.destination == sample_flight_request.destination
            assert flight.currency == sample_flight_request.currency
            assert flight.travel_class == sample_flight_request.travel_class
            assert flight.price > 0
            assert flight.duration_minutes > 0
            assert flight.external_id.startswith("mock_")

    @pytest.mark.asyncio
    async def test_resilience_error_scenarios(self, flight_agent, sample_flight_request):
        """Test various error scenarios and resilience patterns."""
        test_cases = [
            (ExternalAPIError("Service unavailable"), "API error"),
            (TimeoutError(), "Timeout"),
            (Exception("Unexpected error"), "Generic error"),
        ]

        for exception, test_name in test_cases:
            # Mock Amadeus client to raise specific exception
            mock_amadeus_client = Mock()
            mock_amadeus_client.__aenter__ = AsyncMock(side_effect=exception)

            with patch.object(
                flight_agent, "_get_amadeus_client", return_value=mock_amadeus_client
            ):
                flights = await flight_agent.search_flights(sample_flight_request)

            # Should always fall back to mock data
            assert len(flights) > 0, f"Failed for {test_name}"
            assert all(flight.external_id.startswith("mock_") for flight in flights), (
                f"Failed for {test_name}"
            )

    def test_agent_properties(self, flight_agent):
        """Test agent identification properties."""
        assert flight_agent.agent_name == "FlightAgent"
        assert flight_agent.agent_version == "1.0.0"

    @pytest.mark.asyncio
    async def test_circuit_breaker_configuration(self, flight_agent):
        """Test circuit breaker is properly configured."""
        circuit_breaker = flight_agent._amadeus_circuit_breaker

        assert circuit_breaker.failure_threshold == 3
        assert circuit_breaker.recovery_timeout == 30
        assert circuit_breaker.name == "AmadeusAPI"
        assert circuit_breaker.is_closed  # Should start in closed state

    @pytest.mark.asyncio
    async def test_performance_requirements(
        self, flight_agent, sample_flight_request, mock_amadeus_offers
    ):
        """Test that flight search meets performance requirements."""

        # Mock the Amadeus client with small delay to simulate real API
        async def mock_search_flights(*args, **kwargs):
            await asyncio.sleep(0.01)  # Small delay to simulate API call
            return mock_amadeus_offers

        mock_amadeus_client = Mock()
        mock_amadeus_client.__aenter__ = AsyncMock(return_value=mock_amadeus_client)
        mock_amadeus_client.__aexit__ = AsyncMock(return_value=None)
        mock_amadeus_client.search_flights = mock_search_flights

        start_time = datetime.now()

        with patch.object(flight_agent, "_get_amadeus_client", return_value=mock_amadeus_client):
            response = await flight_agent.process(sample_flight_request.model_dump())

        end_time = datetime.now()
        actual_time_ms = (end_time - start_time).total_seconds() * 1000

        # Should complete within 30 seconds (30,000ms) and reported time should be reasonable
        assert actual_time_ms < 30000
        assert response.search_time_ms > 0
        assert response.search_time_ms < 30000

"""Tests for FlightAgent functionality."""

from datetime import datetime, timedelta
from decimal import Decimal
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


class TestFlightAgent:
    """Test cases for FlightAgent."""

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
        """Create a FlightAgent instance for testing."""
        return FlightAgent(
            settings=mock_settings,
            database=mock_database,
            redis=mock_redis,
        )

    @pytest.fixture
    def sample_flight_request(self):
        """Create a sample flight search request."""
        return {
            "origin": "NYC",
            "destination": "LAX",
            "departure_date": "2024-06-15T10:00:00",
            "passengers": 1,
            "travel_class": "economy",
            "currency": "USD",
            "max_results": 20,
        }

    @pytest.fixture
    def sample_flights(self):
        """Create sample flight options for testing."""
        base_time = datetime(2024, 6, 15, 10, 0, 0)
        flights = []

        for i in range(3):
            flight = FlightOption(
                flight_id=uuid4(),
                external_id=f"test_{i}",
                airline=f"Airline {i}",
                flight_number=f"FL{100 + i}",
                origin="NYC",
                destination="LAX",
                departure_time=base_time + timedelta(hours=i * 2),
                arrival_time=base_time + timedelta(hours=i * 2 + 5),
                duration_minutes=300 + i * 30,
                stops=i % 2,
                price=Decimal(str(300 + i * 50)),
                currency="USD",
                travel_class=TravelClass.ECONOMY,
            )
            flights.append(flight)

        return flights

    def test_agent_properties(self, flight_agent):
        """Test FlightAgent properties."""
        assert flight_agent.agent_name == "FlightAgent"
        assert flight_agent.agent_version == "1.0.0"

    @pytest.mark.asyncio
    async def test_process_valid_request(self, flight_agent, sample_flight_request, sample_flights):
        """Test processing a valid flight search request."""
        with (
            patch.object(flight_agent, "search_flights", new_callable=AsyncMock) as mock_search,
            patch.object(flight_agent, "compare_flights", new_callable=AsyncMock) as mock_compare,
            patch.object(
                flight_agent, "_get_cached_result", new_callable=AsyncMock
            ) as mock_cache_get,
            patch.object(
                flight_agent, "_set_cached_result", new_callable=AsyncMock
            ) as mock_cache_set,
        ):
            mock_cache_get.return_value = None
            mock_search.return_value = sample_flights

            # Create comparison results
            comparison_results = [
                FlightComparisonResult(
                    flight=flight,
                    score=80 - i * 10,
                    price_rank=i + 1,
                    duration_rank=i + 1,
                    departure_preference_score=0.8,
                    reasons=[f"Reason {i}"],
                )
                for i, flight in enumerate(sample_flights)
            ]
            mock_compare.return_value = comparison_results

            result = await flight_agent.process(sample_flight_request)

            assert isinstance(result, FlightSearchResponse)
            assert len(result.flights) == 3
            assert result.total_results == 3
            assert result.cached is False
            assert result.search_time_ms >= 0

            # Verify flights are returned in the order from comparison
            assert result.flights[0] == sample_flights[0]

            mock_search.assert_called_once()
            mock_compare.assert_called_once_with(sample_flights)
            mock_cache_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_cached_result(self, flight_agent, sample_flight_request):
        """Test processing request with cached result."""
        cached_response = FlightSearchResponse(
            flights=[],
            total_results=0,
            cached=True,
        )

        with patch.object(
            flight_agent, "_get_cached_result", new_callable=AsyncMock
        ) as mock_cache_get:
            mock_cache_get.return_value = cached_response.model_dump()

            result = await flight_agent.process(sample_flight_request)

            assert isinstance(result, FlightSearchResponse)
            assert result.cached is True
            mock_cache_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_invalid_request(self, flight_agent):
        """Test processing an invalid request."""
        invalid_request = {"origin": ""}  # Missing required fields

        with pytest.raises(ValueError, match="Invalid flight search request"):
            await flight_agent.process(invalid_request)

    @pytest.mark.asyncio
    async def test_process_search_failure(self, flight_agent, sample_flight_request):
        """Test processing request when search fails."""
        with (
            patch.object(flight_agent, "search_flights", new_callable=AsyncMock) as mock_search,
            patch.object(
                flight_agent, "_get_cached_result", new_callable=AsyncMock
            ) as mock_cache_get,
        ):
            mock_cache_get.return_value = None
            mock_search.side_effect = Exception("API Error")

            result = await flight_agent.process(sample_flight_request)

            assert isinstance(result, FlightSearchResponse)
            assert len(result.flights) == 0
            assert result.total_results == 0
            assert "error" in result.search_metadata

    @pytest.mark.asyncio
    async def test_search_flights(self, flight_agent, sample_flight_request, sample_flights):
        """Test flight search functionality."""
        request = FlightSearchRequest(**sample_flight_request)

        with (
            patch.object(
                flight_agent, "_search_flights_with_resilience", new_callable=AsyncMock
            ) as mock_api,
            patch.object(
                flight_agent, "_get_mock_flight_data", new_callable=AsyncMock
            ) as mock_data,
        ):
            # Make API call fail to trigger fallback to mock data
            from travel_companion.utils.errors import ExternalAPIError

            mock_api.side_effect = ExternalAPIError("API unavailable")
            mock_data.return_value = sample_flights

            result = await flight_agent.search_flights(request)

            assert result == sample_flights
            assert len(result) == 3
            mock_data.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_compare_flights_empty_list(self, flight_agent):
        """Test flight comparison with empty list."""
        result = await flight_agent.compare_flights([])
        assert result == []

    @pytest.mark.asyncio
    async def test_compare_flights_ranking(self, flight_agent, sample_flights):
        """Test flight comparison and ranking logic."""
        result = await flight_agent.compare_flights(sample_flights)

        assert len(result) == 3
        assert all(isinstance(r, FlightComparisonResult) for r in result)

        # Results should be sorted by score (highest first)
        scores = [r.score for r in result]
        assert scores == sorted(scores, reverse=True)

        # Check price rankings
        price_ranks = [r.price_rank for r in result]
        assert set(price_ranks) == {1, 2, 3}

        # Check duration rankings
        duration_ranks = [r.duration_rank for r in result]
        assert set(duration_ranks) == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_compare_flights_direct_flight_bonus(self, flight_agent):
        """Test that direct flights get preference in comparison."""
        base_time = datetime(2024, 6, 15, 10, 0, 0)

        # Create flights with same price and duration, but different stops
        direct_flight = FlightOption(
            flight_id=uuid4(),
            external_id="direct",
            airline="Direct Airlines",
            flight_number="DR001",
            origin="NYC",
            destination="LAX",
            departure_time=base_time,
            arrival_time=base_time + timedelta(hours=5),
            duration_minutes=300,
            stops=0,  # Direct flight
            price=Decimal("400.00"),
            currency="USD",
            travel_class=TravelClass.ECONOMY,
        )

        connecting_flight = FlightOption(
            flight_id=uuid4(),
            external_id="connecting",
            airline="Connect Airlines",
            flight_number="CN001",
            origin="NYC",
            destination="LAX",
            departure_time=base_time,
            arrival_time=base_time + timedelta(hours=5),
            duration_minutes=300,
            stops=1,  # One stop
            price=Decimal("400.00"),
            currency="USD",
            travel_class=TravelClass.ECONOMY,
        )

        # Test with direct flight first to avoid price/duration rank influence
        result = await flight_agent.compare_flights([direct_flight, connecting_flight])

        # Direct flight should get direct flight bonus
        direct_result = next(r for r in result if r.flight.stops == 0)
        connecting_result = next(r for r in result if r.flight.stops == 1)

        # Direct flight should score higher in the stops component
        # Direct: (100 - 0*20) * 0.1 = 10.0, Connecting: (100 - 1*20) * 0.1 = 8.0
        # Since they have same price/duration/departure time,
        # the 2-point difference should make direct flight win
        assert direct_result.score > connecting_result.score, (
            f"Direct flight score ({direct_result.score}) should be higher "
            f"than connecting ({connecting_result.score})"
        )
        assert "Direct flight" in direct_result.reasons

    @pytest.mark.asyncio
    async def test_departure_time_preference(self, flight_agent):
        """Test departure time preference scoring."""
        base_time = datetime(2024, 6, 15, 8, 0, 0)  # 8 AM - preferred morning time

        morning_flight = FlightOption(
            flight_id=uuid4(),
            external_id="morning",
            airline="Morning Airlines",
            flight_number="MR001",
            origin="NYC",
            destination="LAX",
            departure_time=base_time,
            arrival_time=base_time + timedelta(hours=5),
            duration_minutes=300,
            stops=0,
            price=Decimal("400.00"),
            currency="USD",
            travel_class=TravelClass.ECONOMY,
        )

        late_night_flight = FlightOption(
            flight_id=uuid4(),
            external_id="late",
            airline="Night Airlines",
            flight_number="NT001",
            origin="NYC",
            destination="LAX",
            departure_time=base_time.replace(hour=2),  # 2 AM - less preferred
            arrival_time=base_time.replace(hour=7),
            duration_minutes=300,
            stops=0,
            price=Decimal("400.00"),
            currency="USD",
            travel_class=TravelClass.ECONOMY,
        )

        result = await flight_agent.compare_flights([late_night_flight, morning_flight])

        morning_result = next(r for r in result if r.flight.departure_time.hour == 8)
        late_result = next(r for r in result if r.flight.departure_time.hour == 2)

        assert morning_result.departure_preference_score > late_result.departure_preference_score
        assert morning_result.score > late_result.score

    @pytest.mark.asyncio
    async def test_get_mock_flight_data(self, flight_agent, sample_flight_request):
        """Test mock flight data generation."""
        request = FlightSearchRequest(**sample_flight_request)

        result = await flight_agent._get_mock_flight_data(request)

        assert len(result) <= request.max_results
        assert len(result) > 0

        for flight in result:
            assert isinstance(flight, FlightOption)
            assert flight.origin == request.origin
            assert flight.destination == request.destination
            assert flight.currency == request.currency
            assert flight.travel_class == request.travel_class
            assert flight.departure_time.date() == request.departure_date.date()
            assert flight.price > 0
            assert flight.duration_minutes > 0

    @pytest.mark.asyncio
    async def test_get_mock_flight_data_limited_results(self, flight_agent):
        """Test mock flight data with limited max results."""
        request_data = {
            "origin": "NYC",
            "destination": "LAX",
            "departure_date": "2024-06-15T10:00:00",
            "passengers": 1,
            "travel_class": "economy",
            "currency": "USD",
            "max_results": 5,  # Limited to 5 results
        }
        request = FlightSearchRequest(**request_data)

        result = await flight_agent._get_mock_flight_data(request)

        assert len(result) == 5

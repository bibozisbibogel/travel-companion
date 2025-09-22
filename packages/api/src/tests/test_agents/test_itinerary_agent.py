"""Comprehensive unit and integration tests for ItineraryAgent."""

import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from travel_companion.agents.itinerary_agent import ItineraryAgent, ItineraryAgentResponse
from travel_companion.models.external import (
    ActivityOption,
    ActivitySearchRequest,
    ActivitySearchResponse,
    FlightOption,
    FlightSearchRequest,
    FlightSearchResponse,
    HotelOption,
    HotelSearchRequest,
    HotelSearchResponse,
    RestaurantOption,
    RestaurantSearchRequest,
    WeatherSearchRequest,
)
from travel_companion.models.trip import (
    AccommodationType,
    DailyItinerary,
    ItineraryItem,
    TravelClass,
    TripDestination,
    TripItinerary,
    TripPlanRequest,
    TripRequirements,
)


class TestItineraryAgent:
    """Test suite for ItineraryAgent functionality."""

    @pytest.fixture
    def sample_trip_request(self) -> TripPlanRequest:
        """Create a sample trip request for testing."""
        destination = TripDestination(
            city="Paris",
            country="France",
            country_code="FR",
            airport_code="CDG",
            latitude=48.8566,
            longitude=2.3522,
        )

        requirements = TripRequirements(
            budget=Decimal("2000.00"),
            currency="USD",
            start_date=date(2024, 6, 15),
            end_date=date(2024, 6, 18),
            travelers=2,
            travel_class=TravelClass.ECONOMY,
            accommodation_type=AccommodationType.HOTEL,
        )

        return TripPlanRequest(
            destination=destination,
            requirements=requirements,
            preferences={"cuisine": ["french", "local"], "activities": ["culture", "sightseeing"]},
        )

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock base dependencies for ItineraryAgent."""
        return {"settings": Mock(), "database": Mock(), "redis": AsyncMock()}

    @pytest.fixture
    async def itinerary_agent(self, mock_dependencies) -> ItineraryAgent:
        """Create an ItineraryAgent instance with mocked dependencies."""
        with (
            patch("travel_companion.agents.itinerary_agent.CircuitBreaker"),
            patch("travel_companion.agents.itinerary_agent.FlightAgent"),
            patch("travel_companion.agents.itinerary_agent.HotelAgent"),
            patch("travel_companion.agents.itinerary_agent.ActivityAgent"),
            patch("travel_companion.agents.itinerary_agent.WeatherAgent"),
            patch("travel_companion.agents.itinerary_agent.FoodAgent"),
        ):
            agent = ItineraryAgent(**mock_dependencies)

            # Mock the individual agents after initialization
            agent.flight_agent = AsyncMock()
            agent.hotel_agent = AsyncMock()
            agent.activity_agent = AsyncMock()
            agent.weather_agent = AsyncMock()
            agent.food_agent = AsyncMock()

            return agent

    @pytest.fixture
    def sample_agent_results(self) -> dict[str, Any]:
        """Create sample agent results for testing."""
        # Sample flight data
        flight_response = FlightSearchResponse(
            flights=[
                FlightOption(
                    external_id="AF001_20240615",
                    airline="Air France",
                    flight_number="AF001",
                    origin="JFK",
                    destination="CDG",
                    departure_time=datetime(2024, 6, 15, 8, 0),
                    arrival_time=datetime(2024, 6, 15, 14, 0),
                    duration_minutes=360,
                    price=Decimal("450.00"),
                    currency="USD",
                    travel_class=TravelClass.ECONOMY,
                    stops=0,
                ),
                FlightOption(
                    external_id="AF002_20240618",
                    airline="Air France",
                    flight_number="AF002",
                    origin="CDG",
                    destination="JFK",
                    departure_time=datetime(2024, 6, 18, 16, 0),
                    arrival_time=datetime(2024, 6, 18, 22, 0),
                    duration_minutes=420,
                    price=Decimal("450.00"),
                    currency="USD",
                    travel_class=TravelClass.ECONOMY,
                    stops=0,
                ),
            ]
        )

        # Sample hotel data
        from travel_companion.models.external import HotelLocation

        hotel_response = HotelSearchResponse(
            hotels=[
                HotelOption(
                    external_id="hotel_paris_123",
                    name="Hotel de Paris",
                    location=HotelLocation(
                        latitude=48.8566, longitude=2.3522, address="123 Champs Elysees, Paris"
                    ),
                    price_per_night=Decimal("150.00"),
                    currency="USD",
                    rating=4.5,
                    amenities=["WiFi", "Breakfast", "Gym"],
                )
            ]
        )

        # Sample activity data
        from travel_companion.models.external import ActivityCategory, ActivityLocation

        activity_response = ActivitySearchResponse(
            activities=[
                ActivityOption(
                    external_id="louvre_001",
                    name="Louvre Museum Visit",
                    description="Explore the world's largest art museum",
                    category=ActivityCategory.CULTURAL,
                    duration_minutes=180,
                    price=Decimal("25.00"),
                    currency="USD",
                    location=ActivityLocation(
                        latitude=48.8606, longitude=2.3376, address="Louvre, Paris"
                    ),
                    rating=4.6,
                    provider="test_provider",
                ),
                ActivityOption(
                    external_id="eiffel_001",
                    name="Eiffel Tower Tour",
                    description="Visit the iconic Eiffel Tower",
                    category=ActivityCategory.CULTURAL,
                    duration_minutes=120,
                    price=Decimal("30.00"),
                    currency="USD",
                    location=ActivityLocation(
                        latitude=48.8584, longitude=2.2945, address="Eiffel Tower, Paris"
                    ),
                    rating=4.4,
                    provider="test_provider",
                ),
            ]
        )

        # Sample restaurant data
        from travel_companion.models.external import (
            GeoapifyCateringCategory,
            RestaurantLocation,
            RestaurantSearchResponse,
        )

        restaurant_data = RestaurantSearchResponse(
            restaurants=[
                RestaurantOption(
                    external_id="jules_verne_001",
                    name="Le Jules Verne",
                    categories=[GeoapifyCateringCategory.RESTAURANT_FRENCH.value],
                    location=RestaurantLocation(
                        latitude=48.8584, longitude=2.2945, address="Eiffel Tower, Paris"
                    ),
                    distance_meters=300,
                    provider="geoapify",
                ),
                RestaurantOption(
                    external_id="cafe_flore_001",
                    name="Cafe de Flore",
                    categories=[GeoapifyCateringCategory.RESTAURANT_FRENCH.value],
                    location=RestaurantLocation(
                        latitude=48.8532, longitude=2.3332, address="172 Bd Saint-Germain, Paris"
                    ),
                    distance_meters=800,
                    provider="geoapify",
                ),
            ]
        )

        # Sample weather data
        weather_data = {
            "location": "Paris",
            "forecast": "Partly cloudy with mild temperatures",
            "temperature_range": "18-24°C",
            "conditions": "Pleasant",
            "recommendations": ["Light jacket for evenings", "Comfortable walking shoes"],
        }

        return {
            "flights": {"status": "success", "data": flight_response},
            "hotels": {"status": "success", "data": hotel_response},
            "activities": {"status": "success", "data": activity_response},
            "restaurants": {"status": "success", "data": restaurant_data},
            "weather": {"status": "success", "data": weather_data},
        }

    # Test Agent Properties
    def test_agent_properties(self, itinerary_agent):
        """Test agent name and version properties."""
        assert itinerary_agent.agent_name == "itinerary_agent"
        assert itinerary_agent.agent_version == "1.0.0"

    # Test Request Preparation
    def test_prepare_flight_request(self, itinerary_agent, sample_trip_request):
        """Test flight request preparation."""
        flight_request = itinerary_agent._prepare_flight_request(sample_trip_request)

        assert isinstance(flight_request, FlightSearchRequest)
        assert flight_request.destination == "CDG"
        assert flight_request.departure_date.date() == sample_trip_request.requirements.start_date
        assert flight_request.return_date.date() == sample_trip_request.requirements.end_date
        assert flight_request.passengers == sample_trip_request.requirements.travelers

    def test_prepare_hotel_request(self, itinerary_agent, sample_trip_request):
        """Test hotel request preparation."""
        hotel_request = itinerary_agent._prepare_hotel_request(sample_trip_request)

        assert isinstance(hotel_request, HotelSearchRequest)
        assert hotel_request.location == "Paris"
        assert hotel_request.check_in_date.date() == sample_trip_request.requirements.start_date
        assert hotel_request.check_out_date.date() == sample_trip_request.requirements.end_date
        assert hotel_request.guest_count == sample_trip_request.requirements.travelers

    def test_prepare_activity_request(self, itinerary_agent, sample_trip_request):
        """Test activity request preparation."""
        activity_request = itinerary_agent._prepare_activity_request(sample_trip_request)

        assert isinstance(activity_request, ActivitySearchRequest)
        assert activity_request.location == "Paris"
        assert activity_request.guest_count == sample_trip_request.requirements.travelers

    def test_prepare_weather_request(self, itinerary_agent, sample_trip_request):
        """Test weather request preparation."""
        weather_request = itinerary_agent._prepare_weather_request(sample_trip_request)

        assert isinstance(weather_request, WeatherSearchRequest)
        assert weather_request.location == "Paris"
        assert weather_request.start_date.date() == sample_trip_request.requirements.start_date

    def test_prepare_food_request(self, itinerary_agent, sample_trip_request):
        """Test food request preparation."""
        food_request = itinerary_agent._prepare_food_request(sample_trip_request)

        assert isinstance(food_request, RestaurantSearchRequest)
        assert food_request.location == "Paris"
        # party_size field removed from RestaurantSearchRequest in Geoapify version
        assert food_request.max_results == 15  # Check max_results instead

    # Test Budget Calculations
    @pytest.mark.asyncio
    async def test_calculate_total_cost_success(self, itinerary_agent, sample_agent_results):
        """Test successful total cost calculation."""
        total_cost, currency = await itinerary_agent._calculate_total_cost(sample_agent_results)

        assert isinstance(total_cost, Decimal)
        assert total_cost > Decimal("0.00")
        assert currency == "USD"

    @pytest.mark.asyncio
    async def test_calculate_total_cost_with_missing_agents(self, itinerary_agent):
        """Test cost calculation with missing agent data."""
        incomplete_results = {
            "flights": {"status": "success", "data": Mock()},
            "hotels": {"status": "failed", "error": "API unavailable"},
        }

        total_cost, currency = await itinerary_agent._calculate_total_cost(incomplete_results)

        assert isinstance(total_cost, Decimal)
        assert currency == "USD"

    @pytest.mark.asyncio
    async def test_check_budget_status_within_budget(self, itinerary_agent):
        """Test budget status check when within budget."""
        status = await itinerary_agent._check_budget_status(Decimal("1500.00"), Decimal("2000.00"))
        assert status == "well_within_budget"

    @pytest.mark.asyncio
    async def test_check_budget_status_over_budget(self, itinerary_agent):
        """Test budget status check when over budget."""
        status = await itinerary_agent._check_budget_status(Decimal("2200.00"), Decimal("2000.00"))
        assert status == "slightly_over_budget"

    @pytest.mark.asyncio
    async def test_check_budget_status_significantly_over(self, itinerary_agent):
        """Test budget status check when significantly over budget."""
        status = await itinerary_agent._check_budget_status(Decimal("3000.00"), Decimal("2000.00"))
        assert status == "significantly_over_budget"

    # Test Conflict Detection
    @pytest.mark.asyncio
    async def test_detect_conflicts_no_conflicts(self, itinerary_agent):
        """Test conflict detection with no conflicts."""
        # Create a well-structured itinerary
        itinerary = TripItinerary(
            trip_id="test-trip",
            days=[],
            total_days=3,
            total_cost=Decimal("1500.00"),
            currency="USD",
            optimization_score=0.85,
            budget_status="within_budget",
        )

        conflicts = await itinerary_agent._detect_conflicts(itinerary, {})
        assert isinstance(conflicts, list)
        assert len(conflicts) == 0

    @pytest.mark.asyncio
    async def test_detect_daily_timeline_conflicts_overlap(self, itinerary_agent):
        """Test detection of overlapping activities."""
        # Create overlapping items
        item1 = ItineraryItem(
            item_id="item1",
            item_type="activity",
            name="Museum Visit",
            start_time=datetime(2024, 6, 15, 10, 0),
            end_time=datetime(2024, 6, 15, 12, 30),
            duration_minutes=150,
            cost=Decimal("25.00"),
        )

        item2 = ItineraryItem(
            item_id="item2",
            item_type="activity",
            name="City Tour",
            start_time=datetime(2024, 6, 15, 12, 0),  # Overlaps with item1
            end_time=datetime(2024, 6, 15, 14, 0),
            duration_minutes=120,
            cost=Decimal("30.00"),
        )

        day = DailyItinerary(
            date=date(2024, 6, 15), day_number=1, items=[item1, item2], daily_cost=Decimal("55.00")
        )

        conflicts = await itinerary_agent._detect_daily_timeline_conflicts(day)
        assert len(conflicts) > 0
        assert conflicts[0]["type"] == "timeline_overlap"
        assert conflicts[0]["severity"] == "high"

    # Test Geographic Optimization
    def test_calculate_haversine_distance(self, itinerary_agent):
        """Test Haversine distance calculation."""
        # Test distance between Paris and London (approximate)
        distance = itinerary_agent._calculate_haversine_distance(
            48.8566,
            2.3522,  # Paris
            51.5074,
            -0.1278,  # London
        )

        # Should be approximately 344 km
        assert 340 <= distance <= 350

    def test_calculate_haversine_distance_same_point(self, itinerary_agent):
        """Test Haversine distance for same point."""
        distance = itinerary_agent._calculate_haversine_distance(
            48.8566,
            2.3522,  # Paris
            48.8566,
            2.3522,  # Same Paris coordinates
        )

        assert distance == 0.0

    # Test Export Functionality
    @pytest.mark.asyncio
    async def test_export_json(self, itinerary_agent):
        """Test JSON export functionality."""
        from travel_companion.models.trip import TripItinerary, TripSummary

        # Create minimal trip summary
        itinerary = TripItinerary(
            trip_id="test-trip",
            days=[],
            total_days=3,
            total_cost=Decimal("1500.00"),
            currency="USD",
            optimization_score=0.85,
            budget_status="within_budget",
        )

        trip_summary = TripSummary(
            trip_id="test-trip",
            trip_name="Test Trip",
            destination="Paris, France",
            start_date=date(2024, 6, 15),
            end_date=date(2024, 6, 18),
            total_days=3,
            travelers=2,
            itinerary=itinerary,
            total_cost=Decimal("1500.00"),
            currency="USD",
        )

        export_result = await itinerary_agent._export_json(trip_summary)

        assert export_result["format"] == "json"
        assert "data" in export_result
        assert "generated_at" in export_result
        assert "version" in export_result

    @pytest.mark.asyncio
    async def test_export_pdf_structure(self, itinerary_agent):
        """Test PDF structure export functionality."""
        from travel_companion.models.trip import TripItinerary, TripSummary

        itinerary = TripItinerary(
            trip_id="test-trip",
            days=[],
            total_days=3,
            total_cost=Decimal("1500.00"),
            currency="USD",
            optimization_score=0.85,
            budget_status="within_budget",
        )

        trip_summary = TripSummary(
            trip_id="test-trip",
            trip_name="Test Trip",
            destination="Paris, France",
            start_date=date(2024, 6, 15),
            end_date=date(2024, 6, 18),
            total_days=3,
            travelers=2,
            itinerary=itinerary,
            total_cost=Decimal("1500.00"),
            currency="USD",
        )

        export_result = await itinerary_agent._export_pdf(trip_summary)

        assert export_result["format"] == "pdf"
        assert "pdf_structure" in export_result
        assert export_result["pdf_structure"]["title"] == "Test Trip"

    @pytest.mark.asyncio
    async def test_export_icalendar(self, itinerary_agent):
        """Test iCalendar export functionality."""
        from travel_companion.models.trip import (
            DailyItinerary,
            ItineraryItem,
            TripItinerary,
            TripSummary,
        )

        # Create itinerary with items
        item = ItineraryItem(
            item_id="test-item",
            item_type="activity",
            name="Test Activity",
            start_time=datetime(2024, 6, 15, 10, 0),
            end_time=datetime(2024, 6, 15, 12, 0),
            duration_minutes=120,
            cost=Decimal("25.00"),
            address="Test Location",
        )

        day = DailyItinerary(
            date=date(2024, 6, 15), day_number=1, items=[item], daily_cost=Decimal("25.00")
        )

        itinerary = TripItinerary(
            trip_id="test-trip",
            days=[day],
            total_days=1,
            total_cost=Decimal("25.00"),
            currency="USD",
            optimization_score=0.85,
            budget_status="within_budget",
        )

        trip_summary = TripSummary(
            trip_id="test-trip",
            trip_name="Test Trip",
            destination="Paris, France",
            start_date=date(2024, 6, 15),
            end_date=date(2024, 6, 15),
            total_days=1,
            travelers=2,
            itinerary=itinerary,
            total_cost=Decimal("25.00"),
            currency="USD",
        )

        export_result = await itinerary_agent._export_icalendar(trip_summary)

        assert export_result["format"] == "icalendar"
        assert "icalendar_content" in export_result
        assert "BEGIN:VCALENDAR" in export_result["icalendar_content"]
        assert "END:VCALENDAR" in export_result["icalendar_content"]
        assert export_result["mime_type"] == "text/calendar"

    # Test Agent Coordination with Fallbacks
    @pytest.mark.asyncio
    async def test_graceful_degradation_flight_fallback(self, itinerary_agent, sample_trip_request):
        """Test graceful degradation with flight agent fallback."""
        failed_results = {
            "flights": {"status": "failed", "error": "API unavailable"},
            "hotels": {"status": "success", "data": Mock()},
            "activities": {"status": "success", "data": Mock()},
            "weather": {"status": "success", "data": Mock()},
            "restaurants": {"status": "success", "data": Mock()},
        }

        degraded_results = await itinerary_agent._apply_graceful_degradation(
            failed_results, sample_trip_request
        )

        assert "flights" in degraded_results
        assert degraded_results["flights"]["status"] == "success"
        assert degraded_results["flights"]["fallback_used"] is True

    @pytest.mark.asyncio
    async def test_create_fallback_flight_data(self, itinerary_agent, sample_trip_request):
        """Test fallback flight data creation."""
        fallback_data = itinerary_agent._create_fallback_flight_data(sample_trip_request)

        assert hasattr(fallback_data, "flights")
        assert len(fallback_data.flights) >= 2  # Should have departure and return
        assert fallback_data.flights[0].airline == "TBD"

    @pytest.mark.asyncio
    async def test_create_fallback_hotel_data(self, itinerary_agent, sample_trip_request):
        """Test fallback hotel data creation."""
        fallback_data = itinerary_agent._create_fallback_hotel_data(sample_trip_request)

        assert hasattr(fallback_data, "hotels")
        assert len(fallback_data.hotels) > 0
        assert "Paris" in fallback_data.hotels[0].name

    @pytest.mark.asyncio
    async def test_create_fallback_activity_data(self, itinerary_agent, sample_trip_request):
        """Test fallback activity data creation."""
        fallback_data = itinerary_agent._create_fallback_activity_data(sample_trip_request)

        assert hasattr(fallback_data, "activities")
        assert len(fallback_data.activities) >= 2
        assert "Paris" in fallback_data.activities[0].name

    def test_create_fallback_weather_data(self, itinerary_agent, sample_trip_request):
        """Test fallback weather data creation."""
        fallback_data = itinerary_agent._create_fallback_weather_data(sample_trip_request)

        assert fallback_data["location"] == "Paris"
        assert fallback_data["fallback"] is True
        assert "recommendations" in fallback_data

    def test_create_fallback_restaurant_data(self, itinerary_agent, sample_trip_request):
        """Test fallback restaurant data creation."""
        fallback_data = itinerary_agent._create_fallback_restaurant_data(sample_trip_request)

        assert hasattr(fallback_data, "restaurants")
        assert len(fallback_data.restaurants) > 0
        assert "Paris" in fallback_data.restaurants[0].name

    # Test Error Handling
    @pytest.mark.asyncio
    async def test_agent_coordination_with_timeouts(self, itinerary_agent, sample_trip_request):
        """Test agent coordination handles timeouts gracefully."""
        # Mock agents to raise timeout
        itinerary_agent.flight_agent.process = AsyncMock(side_effect=TimeoutError("Timeout"))
        itinerary_agent.hotel_agent.process = AsyncMock(side_effect=TimeoutError("Timeout"))
        itinerary_agent.activity_agent.process = AsyncMock(side_effect=TimeoutError("Timeout"))
        itinerary_agent.weather_agent.process = AsyncMock(side_effect=TimeoutError("Timeout"))
        itinerary_agent.food_agent.process = AsyncMock(side_effect=TimeoutError("Timeout"))

        # Mock circuit breaker to allow calls
        with patch("travel_companion.agents.itinerary_agent.CircuitBreaker") as mock_circuit:
            mock_circuit.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_circuit.return_value.__aexit__ = AsyncMock(return_value=None)

            agent_results = await itinerary_agent._coordinate_agents(sample_trip_request)

            # Should handle timeouts and provide fallbacks
            assert len(agent_results) == 5
            for agent_name in ["flights", "hotels", "activities", "weather", "restaurants"]:
                assert agent_name in agent_results

    @pytest.mark.asyncio
    async def test_qr_code_generation(self, itinerary_agent):
        """Test QR code data generation."""
        itinerary = TripItinerary(
            trip_id="test-trip",
            days=[],
            total_days=3,
            total_cost=Decimal("1500.00"),
            currency="USD",
            optimization_score=0.85,
            budget_status="within_budget",
        )

        qr_data = await itinerary_agent.generate_qr_code_data(itinerary)

        assert isinstance(qr_data, str)
        assert "test-trip" in qr_data
        assert "1500.0" in qr_data

    # Integration Tests
    @pytest.mark.asyncio
    async def test_full_itinerary_generation_integration(
        self, itinerary_agent, sample_trip_request, sample_agent_results
    ):
        """Integration test for complete itinerary generation."""
        # Mock all agent calls to return sample data
        itinerary_agent.flight_agent.process = AsyncMock(
            return_value=sample_agent_results["flights"]["data"]
        )
        itinerary_agent.hotel_agent.process = AsyncMock(
            return_value=sample_agent_results["hotels"]["data"]
        )
        itinerary_agent.activity_agent.process = AsyncMock(
            return_value=sample_agent_results["activities"]["data"]
        )
        itinerary_agent.weather_agent.process = AsyncMock(
            return_value=sample_agent_results["weather"]["data"]
        )
        itinerary_agent.food_agent.process = AsyncMock(
            return_value=sample_agent_results["restaurants"]["data"]
        )

        # Mock Redis for caching
        itinerary_agent.redis.get = AsyncMock(return_value=None)
        itinerary_agent.redis.set = AsyncMock(return_value=True)

        # Mock circuit breakers
        with patch("travel_companion.agents.itinerary_agent.CircuitBreaker") as mock_circuit:
            mock_circuit.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_circuit.return_value.__aexit__ = AsyncMock(return_value=None)

            # Execute the full process
            response = await itinerary_agent.process(sample_trip_request.model_dump())

            # Verify response structure
            assert isinstance(response, ItineraryAgentResponse)
            assert response.trip_id is not None
            assert isinstance(response.itinerary, TripItinerary)
            assert response.total_cost > Decimal("0.00")
            assert response.currency == "USD"
            assert response.budget_status in [
                "well_within_budget",
                "within_budget",
                "slightly_over_budget",
                "over_budget",
                "significantly_over_budget",
            ]
            assert isinstance(response.conflicts, list)
            assert 0.0 <= response.optimization_score <= 1.0
            assert isinstance(response.generated_at, datetime)

    @pytest.mark.asyncio
    async def test_process_error_handling(self, itinerary_agent, sample_trip_request):
        """Test process method error handling."""
        # Mock all agents to fail
        itinerary_agent.flight_agent.process = AsyncMock(side_effect=Exception("API Error"))
        itinerary_agent.hotel_agent.process = AsyncMock(side_effect=Exception("API Error"))
        itinerary_agent.activity_agent.process = AsyncMock(side_effect=Exception("API Error"))
        itinerary_agent.weather_agent.process = AsyncMock(side_effect=Exception("API Error"))
        itinerary_agent.food_agent.process = AsyncMock(side_effect=Exception("API Error"))

        # Mock Redis
        itinerary_agent.redis.get = AsyncMock(return_value=None)
        itinerary_agent.redis.set = AsyncMock(return_value=True)

        # Mock circuit breakers
        with patch("travel_companion.agents.itinerary_agent.CircuitBreaker") as mock_circuit:
            mock_circuit.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_circuit.return_value.__aexit__ = AsyncMock(return_value=None)

            # Should still generate response using fallbacks
            response = await itinerary_agent.process(sample_trip_request.model_dump())

            assert isinstance(response, ItineraryAgentResponse)
            assert response.trip_id is not None

    # Performance and Load Tests
    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self, itinerary_agent, sample_trip_request):
        """Test handling multiple concurrent requests."""
        # Mock quick responses
        itinerary_agent.flight_agent.process = AsyncMock(return_value=Mock())
        itinerary_agent.hotel_agent.process = AsyncMock(return_value=Mock())
        itinerary_agent.activity_agent.process = AsyncMock(return_value=Mock())
        itinerary_agent.weather_agent.process = AsyncMock(return_value=Mock())
        itinerary_agent.food_agent.process = AsyncMock(return_value=Mock())
        itinerary_agent.redis.get = AsyncMock(return_value=None)
        itinerary_agent.redis.set = AsyncMock(return_value=True)

        with patch("travel_companion.agents.itinerary_agent.CircuitBreaker") as mock_circuit:
            mock_circuit.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_circuit.return_value.__aexit__ = AsyncMock(return_value=None)

            # Execute multiple concurrent requests
            tasks = [itinerary_agent.process(sample_trip_request.model_dump()) for _ in range(5)]

            responses = await asyncio.gather(*tasks)

            assert len(responses) == 5
            for response in responses:
                assert isinstance(response, ItineraryAgentResponse)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

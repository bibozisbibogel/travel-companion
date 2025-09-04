"""Unit tests for FoodAgent."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from travel_companion.agents.food_agent import FoodAgent
from travel_companion.models.external import (
    CuisineType,
    DietaryRestriction,
    PriceRange,
    RestaurantLocation,
    RestaurantOption,
    RestaurantSearchRequest,
    RestaurantSearchResponse,
)
from travel_companion.utils.errors import ExternalAPIError


@pytest.fixture
def mock_settings():
    """Mock settings with API keys."""
    settings = MagicMock()
    settings.yelp_api_key = "test_yelp_key"
    settings.google_places_api_key = "test_google_key"
    settings.zomato_api_key = "test_zomato_key"
    return settings


@pytest.fixture
def mock_database():
    """Mock database manager."""
    db_manager = AsyncMock()
    db_manager.health_check.return_value = True
    return db_manager


@pytest.fixture
def mock_redis():
    """Mock Redis manager."""
    redis_manager = AsyncMock()
    redis_manager.ping.return_value = True
    redis_manager.get.return_value = None
    redis_manager.set.return_value = True
    return redis_manager


@pytest.fixture
def food_agent(mock_settings, mock_database, mock_redis):
    """Create FoodAgent instance with mocked dependencies."""
    with (
        patch("travel_companion.agents.food_agent.YelpClient"),
        patch("travel_companion.agents.food_agent.GooglePlacesClient"),
        patch("travel_companion.agents.food_agent.ZomatoClient"),
        patch("travel_companion.agents.food_agent.CircuitBreaker"),
    ):
        agent = FoodAgent(settings=mock_settings, database=mock_database, redis=mock_redis)
        return agent


@pytest.fixture
def sample_restaurant_request():
    """Sample restaurant search request."""
    return RestaurantSearchRequest(
        location="New York, NY",
        latitude=40.7128,
        longitude=-74.0060,
        cuisine_type=CuisineType.ITALIAN,
        price_range=PriceRange.MODERATE,
        dietary_restrictions=[DietaryRestriction.VEGETARIAN],
        party_size=4,
        max_results=20,
    )


@pytest.fixture
def sample_restaurant_option():
    """Sample restaurant option."""
    return RestaurantOption(
        external_id="test_restaurant_1",
        name="Test Italian Restaurant",
        cuisine_type=CuisineType.ITALIAN,
        location=RestaurantLocation(
            latitude=40.7128,
            longitude=-74.0060,
            address="123 Main St",
            city="New York",
            state="NY",
            country="US",
        ),
        rating=4.5,
        review_count=150,
        price_range=PriceRange.MODERATE,
        average_cost_per_person=Decimal("25.00"),
        dietary_accommodations=[DietaryRestriction.VEGETARIAN],
        provider="yelp",
    )


class TestFoodAgentBasics:
    """Test basic FoodAgent functionality."""

    def test_agent_properties(self, food_agent):
        """Test agent name and version properties."""
        assert food_agent.agent_name == "food_agent"
        assert food_agent.agent_version == "1.0.0"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, food_agent):
        """Test health check with healthy dependencies."""
        status = await food_agent.health_check()

        assert status["agent"] == "food_agent"
        assert status["version"] == "1.0.0"
        assert status["status"] in ["healthy", "degraded"]  # APIs might be circuit open
        assert "dependencies" in status
        assert "database" in status["dependencies"]
        assert "redis" in status["dependencies"]
        assert "apis" in status["dependencies"]

    @pytest.mark.asyncio
    async def test_health_check_with_database_error(self, food_agent):
        """Test health check with database error."""
        food_agent.database.health_check.return_value = False

        status = await food_agent.health_check()

        assert status["status"] == "degraded"
        assert status["dependencies"]["database"] == "unhealthy"


class TestRestaurantSearch:
    """Test restaurant search functionality."""

    @pytest.mark.asyncio
    async def test_process_successful_search(
        self, food_agent, sample_restaurant_request, sample_restaurant_option
    ):
        """Test successful restaurant search."""
        # Mock API responses
        food_agent._search_yelp = AsyncMock(return_value=[sample_restaurant_option])
        food_agent._search_google_places = AsyncMock(return_value=[])
        food_agent._search_zomato = AsyncMock(return_value=[])

        # Mock caching
        food_agent._get_cached_result = AsyncMock(return_value=None)
        food_agent._set_cached_result = AsyncMock()
        food_agent._cache_key = AsyncMock(return_value="test_cache_key")

        result = await food_agent.process(sample_restaurant_request.model_dump())

        assert isinstance(result, RestaurantSearchResponse)
        assert len(result.restaurants) == 1
        assert result.restaurants[0].name == "Test Italian Restaurant"
        assert result.total_results == 1
        assert not result.cached

    @pytest.mark.asyncio
    async def test_process_cached_result(
        self, food_agent, sample_restaurant_request, sample_restaurant_option
    ):
        """Test returning cached restaurant search results."""
        cached_response = RestaurantSearchResponse(
            restaurants=[sample_restaurant_option], total_results=1, cached=True
        )

        food_agent._get_cached_result = AsyncMock(return_value=cached_response)
        food_agent._cache_key = AsyncMock(return_value="test_cache_key")

        result = await food_agent.process(sample_restaurant_request.model_dump())

        assert isinstance(result, RestaurantSearchResponse)
        assert result.cached
        assert len(result.restaurants) == 1

    @pytest.mark.asyncio
    async def test_process_with_api_failures(self, food_agent, sample_restaurant_request):
        """Test handling API failures gracefully."""
        # Mock all APIs to fail
        food_agent._search_yelp = AsyncMock(side_effect=Exception("Yelp API error"))
        food_agent._search_google_places = AsyncMock(side_effect=Exception("Google API error"))
        food_agent._search_zomato = AsyncMock(side_effect=Exception("Zomato API error"))

        food_agent._get_cached_result = AsyncMock(return_value=None)
        food_agent._set_cached_result = AsyncMock()
        food_agent._cache_key = AsyncMock(return_value="test_cache_key")

        result = await food_agent.process(sample_restaurant_request.model_dump())

        assert isinstance(result, RestaurantSearchResponse)
        assert len(result.restaurants) == 0
        assert result.total_results == 0

    @pytest.mark.asyncio
    async def test_process_invalid_request(self, food_agent):
        """Test handling invalid request data."""
        invalid_request = {"invalid": "data"}

        with pytest.raises(ExternalAPIError):
            await food_agent.process(invalid_request)


class TestRestaurantDeduplication:
    """Test restaurant deduplication logic."""

    def test_deduplicate_restaurants_removes_duplicates(self, food_agent):
        """Test that duplicate restaurants are removed."""
        restaurant1 = RestaurantOption(
            external_id="1",
            name="Pizza Palace",
            cuisine_type=CuisineType.PIZZA,
            location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
            price_range=PriceRange.MODERATE,
            provider="yelp",
        )

        restaurant2 = RestaurantOption(
            external_id="2",
            name="Pizza Palace",  # Same name
            cuisine_type=CuisineType.PIZZA,
            location=RestaurantLocation(
                latitude=40.7130, longitude=-74.0062
            ),  # Very close location
            price_range=PriceRange.MODERATE,
            provider="google_places",
        )

        restaurant3 = RestaurantOption(
            external_id="3",
            name="Burger Joint",  # Different name
            cuisine_type=CuisineType.AMERICAN,
            location=RestaurantLocation(latitude=40.7200, longitude=-74.0100),  # Different location
            price_range=PriceRange.BUDGET,
            provider="zomato",
        )

        restaurants = [restaurant1, restaurant2, restaurant3]
        deduplicated = food_agent._deduplicate_restaurants(restaurants)

        assert len(deduplicated) == 2
        names = [r.name for r in deduplicated]
        assert "Pizza Palace" in names
        assert "Burger Joint" in names

    def test_calculate_distance(self, food_agent):
        """Test distance calculation between coordinates."""
        # Distance between NYC and Philadelphia (approximately 130km)
        nyc_lat, nyc_lon = 40.7128, -74.0060
        philly_lat, philly_lon = 39.9526, -75.1652

        distance = food_agent._calculate_distance(nyc_lat, nyc_lon, philly_lat, philly_lon)

        assert 120 < distance < 140  # Approximate distance

    def test_names_similar(self, food_agent):
        """Test restaurant name similarity detection."""
        assert food_agent._names_similar("pizzapalace", "pizzapalace")
        assert food_agent._names_similar("pizzapalace", "pizza palace")
        assert food_agent._names_similar("joes pizza", "joespizza")
        assert not food_agent._names_similar("pizza", "burger")


class TestRestaurantRanking:
    """Test restaurant ranking and scoring."""

    def test_calculate_restaurant_score(self, food_agent, sample_restaurant_request):
        """Test restaurant scoring algorithm."""
        restaurant = RestaurantOption(
            external_id="test_1",
            name="High Rated Italian",
            cuisine_type=CuisineType.ITALIAN,  # Matches request
            location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
            rating=4.8,  # High rating
            review_count=500,  # Many reviews
            price_range=PriceRange.MODERATE,  # Matches request
            dietary_accommodations=[DietaryRestriction.VEGETARIAN],  # Matches request
            average_cost_per_person=Decimal("25.00"),
            provider="yelp",
            distance_km=2.0,  # Close
        )

        score = food_agent._calculate_restaurant_score(restaurant, sample_restaurant_request)

        # Score should be high due to multiple matching factors
        assert score > 80  # High score expected
        assert score <= 100  # Score capped at 100

    def test_rank_restaurants_orders_correctly(self, food_agent, sample_restaurant_request):
        """Test that restaurants are ranked in correct order."""
        high_scored = RestaurantOption(
            external_id="high",
            name="Excellent Italian",
            cuisine_type=CuisineType.ITALIAN,
            location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
            rating=4.9,
            review_count=1000,
            price_range=PriceRange.MODERATE,
            dietary_accommodations=[DietaryRestriction.VEGETARIAN],
            provider="yelp",
        )

        low_scored = RestaurantOption(
            external_id="low",
            name="Poor Chinese",
            cuisine_type=CuisineType.CHINESE,  # Doesn't match Italian request
            location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
            rating=2.0,
            review_count=5,
            price_range=PriceRange.EXPENSIVE,  # Doesn't match moderate request
            dietary_accommodations=[],  # No dietary accommodations
            provider="zomato",
        )

        restaurants = [low_scored, high_scored]  # Intentionally wrong order
        ranked = food_agent._rank_restaurants(restaurants, sample_restaurant_request)

        assert ranked[0].external_id == "high"  # High scored should be first
        assert ranked[1].external_id == "low"  # Low scored should be second


class TestLocalSpecialties:
    """Test local specialty search functionality."""

    @pytest.mark.asyncio
    async def test_search_local_specialties(self, food_agent):
        """Test local specialty search."""
        # Mock API calls
        specialty_restaurant = RestaurantOption(
            external_id="specialty_1",
            name="Famous NYC Deli",
            cuisine_type=CuisineType.AMERICAN,
            location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
            rating=4.5,
            review_count=800,
            price_range=PriceRange.MODERATE,
            provider="yelp",
        )

        food_agent._search_yelp = AsyncMock(return_value=[specialty_restaurant])
        food_agent._search_google_places = AsyncMock(return_value=[])

        # Mock specialty detection
        food_agent._is_local_specialty = MagicMock(return_value=True)
        food_agent._enhance_with_local_dishes = AsyncMock(return_value=specialty_restaurant)

        results = await food_agent.search_local_specialties("New York, NY")

        assert len(results) == 1
        assert results[0].name == "Famous NYC Deli"

    def test_is_local_specialty_detection(self, food_agent):
        """Test local specialty detection logic."""
        ny_deli = RestaurantOption(
            external_id="1",
            name="Classic NYC Deli",
            cuisine_type=CuisineType.AMERICAN,
            location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
            rating=4.2,
            review_count=200,
            price_range=PriceRange.MODERATE,
            provider="yelp",
        )

        # Should detect NYC deli as local specialty
        assert food_agent._is_local_specialty(ny_deli, "New York, NY")

        # Should not detect for different location
        assert not food_agent._is_local_specialty(ny_deli, "Los Angeles, CA")

    def test_get_local_dish_suggestions(self, food_agent):
        """Test local dish suggestion generation."""
        dishes = food_agent._get_local_dish_suggestions("New York, NY", CuisineType.AMERICAN)

        assert len(dishes) > 0
        dish_names = [d.name for d in dishes]
        assert any("Pizza" in name for name in dish_names)
        assert all(dish.is_specialty for dish in dishes)


class TestDietaryFiltering:
    """Test dietary restriction filtering."""

    @pytest.mark.asyncio
    async def test_filter_by_dietary_restrictions(self, food_agent):
        """Test filtering restaurants by dietary restrictions."""
        vegetarian_restaurant = RestaurantOption(
            external_id="veg_1",
            name="Green Garden",
            cuisine_type=CuisineType.VEGETARIAN,
            location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
            rating=4.3,
            review_count=100,
            price_range=PriceRange.MODERATE,
            dietary_accommodations=[DietaryRestriction.VEGETARIAN, DietaryRestriction.VEGAN],
            provider="yelp",
        )

        meat_restaurant = RestaurantOption(
            external_id="meat_1",
            name="Steakhouse Prime",
            cuisine_type=CuisineType.STEAKHOUSE,
            location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
            rating=4.5,
            review_count=300,
            price_range=PriceRange.EXPENSIVE,
            dietary_accommodations=[],
            provider="google_places",
        )

        restaurants = [vegetarian_restaurant, meat_restaurant]
        filtered = await food_agent.filter_by_dietary_restrictions(restaurants, ["vegetarian"])

        assert len(filtered) == 1
        assert filtered[0].name == "Green Garden"

    def test_restaurant_accommodates_restriction(self, food_agent):
        """Test dietary restriction accommodation checking."""
        restaurant = RestaurantOption(
            external_id="test",
            name="Test Restaurant",
            cuisine_type=CuisineType.ITALIAN,
            location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
            rating=4.0,
            review_count=50,
            price_range=PriceRange.MODERATE,
            dietary_accommodations=[DietaryRestriction.VEGETARIAN, DietaryRestriction.GLUTEN_FREE],
            provider="yelp",
        )

        assert food_agent._restaurant_accommodates_restriction(restaurant, "vegetarian")
        assert food_agent._restaurant_accommodates_restriction(restaurant, "gluten_free")
        assert not food_agent._restaurant_accommodates_restriction(restaurant, "vegan")

    def test_cuisine_compatible_with_restriction(self, food_agent):
        """Test cuisine type compatibility with dietary restrictions."""
        assert food_agent._cuisine_compatible_with_restriction(CuisineType.VEGETARIAN, "vegetarian")
        assert food_agent._cuisine_compatible_with_restriction(CuisineType.VEGAN, "vegan")
        assert food_agent._cuisine_compatible_with_restriction(CuisineType.INDIAN, "vegetarian")
        assert not food_agent._cuisine_compatible_with_restriction(
            CuisineType.STEAKHOUSE, "vegetarian"
        )


class TestCircuitBreakers:
    """Test circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_api_circuit_breaker_integration(self, food_agent):
        """Test that circuit breakers are properly integrated."""
        # Check that circuit breakers are created
        assert hasattr(food_agent, "yelp_circuit_breaker")
        assert hasattr(food_agent, "google_circuit_breaker")
        assert hasattr(food_agent, "zomato_circuit_breaker")

        # Mock circuit breaker behavior with proper mock objects
        food_agent.yelp_circuit_breaker = MagicMock()
        food_agent.google_circuit_breaker = MagicMock()
        food_agent.zomato_circuit_breaker = MagicMock()

        food_agent.yelp_circuit_breaker.is_closed = True
        food_agent.google_circuit_breaker.is_closed = False  # Circuit open
        food_agent.zomato_circuit_breaker.is_closed = True

        health_status = await food_agent.health_check()

        # Should show degraded status due to Google circuit being open
        assert health_status["dependencies"]["apis"]["google_places"] == "circuit_open"
        assert health_status["status"] == "degraded"


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_process_handles_validation_error(self, food_agent):
        """Test handling of validation errors in request."""
        invalid_request = {
            "location": "",  # Empty location should fail validation
            "max_results": -1,  # Negative max_results should fail
        }

        with pytest.raises(ExternalAPIError):
            await food_agent.process(invalid_request)

    @pytest.mark.asyncio
    async def test_api_timeout_handling(self, food_agent, sample_restaurant_request):
        """Test handling of API timeouts."""
        # Mock timeout errors
        food_agent._search_yelp = AsyncMock(side_effect=TimeoutError())
        food_agent._search_google_places = AsyncMock(return_value=[])
        food_agent._search_zomato = AsyncMock(return_value=[])

        food_agent._get_cached_result = AsyncMock(return_value=None)
        food_agent._set_cached_result = AsyncMock()
        food_agent._cache_key = AsyncMock(return_value="test_cache_key")

        # Should not raise exception, but return empty results
        result = await food_agent.process(sample_restaurant_request.model_dump())

        assert isinstance(result, RestaurantSearchResponse)
        assert len(result.restaurants) == 0

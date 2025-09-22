"""Unit tests for FoodAgent with Geoapify integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from travel_companion.agents.food_agent import FoodAgent
from travel_companion.models.external import (
    GeoapifyCateringCategory,
    RestaurantComparisonResult,
    RestaurantLocation,
    RestaurantOption,
    RestaurantSearchRequest,
    RestaurantSearchResponse,
)
from travel_companion.utils.errors import ExternalAPIError


@pytest.fixture
def mock_settings():
    """Mock settings with Geoapify API key."""
    settings = MagicMock()
    settings.geoapify_api_key = "test_geoapify_key"
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
def mock_geoapify_client():
    """Mock Geoapify client."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    return client


@pytest.fixture
def food_agent(mock_settings, mock_database, mock_redis, mock_geoapify_client):
    """Create FoodAgent instance with mocked dependencies."""
    with (
        patch(
            "travel_companion.agents.food_agent.GeoapifyClient", return_value=mock_geoapify_client
        ),
        patch("travel_companion.agents.food_agent.CircuitBreaker"),
    ):
        agent = FoodAgent(settings=mock_settings, database=mock_database, redis=mock_redis)
        agent.geoapify_client = mock_geoapify_client
        return agent


@pytest.fixture
def sample_restaurant_request():
    """Sample restaurant search request for Geoapify."""
    return RestaurantSearchRequest(
        location="New York, NY",
        latitude=40.7128,
        longitude=-74.0060,
        categories=[GeoapifyCateringCategory.RESTAURANT_ITALIAN.value],
        radius_meters=5000,
        max_results=20,
    )


@pytest.fixture
def sample_restaurant_option():
    """Sample restaurant option from Geoapify."""
    return RestaurantOption(
        external_id="geoapify_place_1",
        name="Test Italian Restaurant",
        categories=["catering.restaurant.italian", "catering.restaurant"],
        location=RestaurantLocation(
            latitude=40.7128,
            longitude=-74.0060,
            address="123 Main St",
            city="New York",
            country="US",
        ),
        formatted_address="123 Main St, New York, NY 10001, USA",
        distance_meters=500,
        provider="geoapify",
    )


@pytest.fixture
def sample_restaurant_response(sample_restaurant_option):
    """Sample restaurant search response."""
    return RestaurantSearchResponse(
        restaurants=[sample_restaurant_option],
        total_results=1,
        search_time_ms=150,
        cached=False,
        search_metadata={"provider": "geoapify"},
    )


class TestFoodAgentBasics:
    """Test basic FoodAgent functionality."""

    def test_agent_properties(self, food_agent):
        """Test agent name and version properties."""
        assert food_agent.agent_name == "food_agent"
        assert food_agent.agent_version == "2.0.0"  # Updated for Geoapify

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, food_agent):
        """Test health check with healthy dependencies."""
        food_agent.geoapify_circuit_breaker = MagicMock()
        food_agent.geoapify_circuit_breaker.is_closed = True

        status = await food_agent.health_check()

        assert status["agent"] == "food_agent"
        assert status["version"] == "2.0.0"
        assert status["status"] in ["healthy", "degraded"]
        assert "dependencies" in status
        assert "database" in status["dependencies"]
        assert "redis" in status["dependencies"]
        assert "apis" in status["dependencies"]
        assert status["dependencies"]["apis"]["geoapify"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_with_circuit_open(self, food_agent):
        """Test health check with circuit breaker open."""
        food_agent.geoapify_circuit_breaker = MagicMock()
        food_agent.geoapify_circuit_breaker.is_closed = False

        status = await food_agent.health_check()

        assert status["status"] == "degraded"
        assert status["dependencies"]["apis"]["geoapify"] == "circuit_open"


class TestRestaurantSearch:
    """Test restaurant search functionality with Geoapify."""

    @pytest.mark.asyncio
    async def test_process_successful_search(
        self, food_agent, sample_restaurant_request, sample_restaurant_response
    ):
        """Test successful restaurant search."""
        food_agent.geoapify_client.search_restaurants = AsyncMock(
            return_value=sample_restaurant_response
        )

        result = await food_agent.process(sample_restaurant_request.model_dump())

        assert isinstance(result, RestaurantSearchResponse)
        assert len(result.restaurants) == 1
        assert result.restaurants[0].name == "Test Italian Restaurant"
        assert result.total_results == 1

    @pytest.mark.asyncio
    async def test_process_sorts_by_distance(self, food_agent, sample_restaurant_request):
        """Test that results are sorted by distance."""
        restaurant1 = RestaurantOption(
            external_id="place_1",
            name="Far Restaurant",
            categories=["catering.restaurant"],
            location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
            distance_meters=2000,
            provider="geoapify",
        )
        restaurant2 = RestaurantOption(
            external_id="place_2",
            name="Near Restaurant",
            categories=["catering.restaurant"],
            location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
            distance_meters=500,
            provider="geoapify",
        )

        response = RestaurantSearchResponse(
            restaurants=[restaurant1, restaurant2],  # Far one first
            total_results=2,
            search_time_ms=100,
            cached=False,
        )

        food_agent.geoapify_client.search_restaurants = AsyncMock(return_value=response)

        result = await food_agent.process(sample_restaurant_request.model_dump())

        # Should be sorted by distance
        assert result.restaurants[0].name == "Near Restaurant"
        assert result.restaurants[1].name == "Far Restaurant"

    @pytest.mark.asyncio
    async def test_process_with_api_error(self, food_agent, sample_restaurant_request):
        """Test handling API errors."""
        food_agent.geoapify_client.search_restaurants = AsyncMock(
            side_effect=ExternalAPIError("API error")
        )

        with pytest.raises(ExternalAPIError):
            await food_agent.process(sample_restaurant_request.model_dump())

    @pytest.mark.asyncio
    async def test_process_invalid_request(self, food_agent):
        """Test handling invalid request data."""
        # Test with completely invalid data that should fail Pydantic validation
        invalid_request = {
            "categories": "invalid_type",  # Should be list, not string
            "radius_meters": "not_a_number",  # Should be int, not string
            "max_results": -5,  # Should be positive
        }

        with pytest.raises(ExternalAPIError):
            await food_agent.process(invalid_request)


class TestCuisineSearch:
    """Test cuisine-specific search functionality."""

    @pytest.mark.asyncio
    async def test_search_by_cuisine(self, food_agent):
        """Test searching by specific cuisine category."""
        expected_response = RestaurantSearchResponse(
            restaurants=[
                RestaurantOption(
                    external_id="thai_1",
                    name="Thai Palace",
                    categories=["catering.restaurant.thai"],
                    location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
                    distance_meters=800,
                    provider="geoapify",
                )
            ],
            total_results=1,
            search_time_ms=100,
            cached=False,
        )

        food_agent.geoapify_client.search_restaurants = AsyncMock(return_value=expected_response)

        result = await food_agent.search_by_cuisine(
            latitude=40.7128,
            longitude=-74.0060,
            cuisine_category=GeoapifyCateringCategory.RESTAURANT_THAI,
        )

        assert len(result.restaurants) == 1
        assert result.restaurants[0].name == "Thai Palace"
        assert "catering.restaurant.thai" in result.restaurants[0].categories

        # Verify the correct category was passed
        call_args = food_agent.geoapify_client.search_restaurants.call_args[0][0]
        assert GeoapifyCateringCategory.RESTAURANT_THAI.value in call_args.categories

    @pytest.mark.asyncio
    async def test_search_by_cuisine_string(self, food_agent):
        """Test searching by cuisine category as string."""
        expected_response = RestaurantSearchResponse(
            restaurants=[],
            total_results=0,
            search_time_ms=50,
            cached=False,
        )

        food_agent.geoapify_client.search_restaurants = AsyncMock(return_value=expected_response)

        await food_agent.search_by_cuisine(
            location="Tokyo",
            cuisine_category="catering.restaurant.sushi",  # String instead of enum
        )

        # Verify string category was used
        call_args = food_agent.geoapify_client.search_restaurants.call_args[0][0]
        assert "catering.restaurant.sushi" in call_args.categories


class TestLocalSpecialties:
    """Test local specialty search functionality."""

    @pytest.mark.asyncio
    async def test_search_local_specialties_italy(self, food_agent):
        """Test local specialty search for Italian location."""
        italian_restaurants = [
            RestaurantOption(
                external_id="italian_1",
                name="Authentic Pizza",
                categories=["catering.restaurant.italian", "catering.restaurant.pizza"],
                location=RestaurantLocation(latitude=41.9028, longitude=12.4964),
                distance_meters=200,
                provider="geoapify",
            )
        ]

        expected_response = RestaurantSearchResponse(
            restaurants=italian_restaurants,
            total_results=1,
            search_time_ms=100,
            cached=False,
        )

        food_agent.geoapify_client.search_restaurants = AsyncMock(return_value=expected_response)

        result = await food_agent.search_local_specialties(location="Rome, Italy")

        assert len(result.restaurants) == 1
        assert "catering.restaurant.italian" in result.restaurants[0].categories
        assert result.search_metadata["search_type"] == "local_specialties"

        # Verify Italian category was searched
        call_args = food_agent.geoapify_client.search_restaurants.call_args[0][0]
        assert GeoapifyCateringCategory.RESTAURANT_ITALIAN.value in call_args.categories

    @pytest.mark.asyncio
    async def test_search_local_specialties_japan(self, food_agent):
        """Test local specialty search for Japanese location."""
        food_agent.geoapify_client.search_restaurants = AsyncMock(
            return_value=RestaurantSearchResponse(
                restaurants=[],
                total_results=0,
                search_time_ms=100,
                cached=False,
            )
        )

        await food_agent.search_local_specialties(location="Tokyo, Japan")

        # Verify Japanese categories were searched
        call_args = food_agent.geoapify_client.search_restaurants.call_args[0][0]
        assert GeoapifyCateringCategory.RESTAURANT_JAPANESE.value in call_args.categories
        assert any("sushi" in cat or "ramen" in cat for cat in call_args.categories)

    def test_get_local_cuisine_categories(self, food_agent):
        """Test local cuisine category mapping."""
        # Test Italy
        italy_categories = food_agent._get_local_cuisine_categories("Rome, Italy")
        assert GeoapifyCateringCategory.RESTAURANT_ITALIAN.value in italy_categories

        # Test Mexico
        mexico_categories = food_agent._get_local_cuisine_categories("Mexico City")
        assert GeoapifyCateringCategory.RESTAURANT_MEXICAN.value in mexico_categories

        # Test Texas (BBQ and Tex-Mex)
        texas_categories = food_agent._get_local_cuisine_categories("Austin, Texas")
        assert GeoapifyCateringCategory.RESTAURANT_TEX_MEX.value in texas_categories
        assert GeoapifyCateringCategory.RESTAURANT_BARBECUE.value in texas_categories

        # Test unknown location
        unknown_categories = food_agent._get_local_cuisine_categories("Unknown Place")
        assert len(unknown_categories) == 0


class TestRestaurantComparison:
    """Test restaurant comparison and ranking."""

    @pytest.mark.asyncio
    async def test_compare_restaurants(self, food_agent):
        """Test restaurant comparison with scoring."""
        restaurants = [
            RestaurantOption(
                external_id="far_generic",
                name="Generic Restaurant",
                categories=["catering.restaurant"],  # Generic category
                location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
                distance_meters=4000,  # Far away
                provider="geoapify",
            ),
            RestaurantOption(
                external_id="near_specific",
                name="Authentic Italian Trattoria",  # Longer name (established)
                categories=["catering.restaurant.italian"],  # Specific cuisine
                location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
                distance_meters=500,  # Close
                provider="geoapify",
            ),
        ]

        preferred_categories = ["catering.restaurant.italian"]

        results = await food_agent.compare_restaurants(restaurants, preferred_categories)

        assert len(results) == 2
        assert isinstance(results[0], RestaurantComparisonResult)

        # The near, specific Italian restaurant should score higher
        assert results[0].restaurant.external_id == "near_specific"
        assert results[0].score > results[1].score
        assert results[0].distance_rank == 1
        assert results[0].category_match_score == 1.0

        # The far, generic restaurant should score lower
        assert results[1].restaurant.external_id == "far_generic"
        assert results[1].distance_rank == 2
        assert results[1].category_match_score == 0.0

    @pytest.mark.asyncio
    async def test_compare_restaurants_no_preferences(self, food_agent):
        """Test restaurant comparison without preferences."""
        restaurants = [
            RestaurantOption(
                external_id="rest_1",
                name="Restaurant One",
                categories=["catering.restaurant"],
                location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
                distance_meters=1000,
                provider="geoapify",
            ),
        ]

        results = await food_agent.compare_restaurants(restaurants, None)

        assert len(results) == 1
        assert results[0].category_match_score == 0.0  # No preferences to match


class TestCategoryFiltering:
    """Test category-based filtering."""

    def test_filter_by_category_type(self, food_agent):
        """Test filtering restaurants by category type."""
        restaurants = [
            RestaurantOption(
                external_id="cafe_1",
                name="Coffee Shop",
                categories=["catering.cafe.coffee", "catering.cafe"],
                location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
                provider="geoapify",
            ),
            RestaurantOption(
                external_id="restaurant_1",
                name="Italian Place",
                categories=["catering.restaurant.italian"],
                location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
                provider="geoapify",
            ),
            RestaurantOption(
                external_id="fast_food_1",
                name="Burger Joint",
                categories=["catering.fast_food.burger"],
                location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
                provider="geoapify",
            ),
        ]

        # Filter for cafes
        cafes = food_agent.filter_by_category_type(restaurants, "cafe")
        assert len(cafes) == 1
        assert cafes[0].name == "Coffee Shop"

        # Filter for fast food
        fast_food = food_agent.filter_by_category_type(restaurants, "fast_food")
        assert len(fast_food) == 1
        assert fast_food[0].name == "Burger Joint"

        # Filter for restaurants
        restaurant_only = food_agent.filter_by_category_type(restaurants, "restaurant")
        assert len(restaurant_only) == 1
        assert restaurant_only[0].name == "Italian Place"


class TestConvenienceMethods:
    """Test convenience methods for specific searches."""

    @pytest.mark.asyncio
    async def test_get_nearby_cafes(self, food_agent):
        """Test nearby cafe search."""
        cafe_response = RestaurantSearchResponse(
            restaurants=[
                RestaurantOption(
                    external_id="cafe_1",
                    name="Local Coffee",
                    categories=["catering.cafe.coffee"],
                    location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
                    distance_meters=200,
                    provider="geoapify",
                )
            ],
            total_results=1,
            search_time_ms=50,
            cached=False,
        )

        food_agent.geoapify_client.search_restaurants = AsyncMock(return_value=cafe_response)

        result = await food_agent.get_nearby_cafes(
            latitude=40.7128,
            longitude=-74.0060,
            radius_meters=500,
        )

        assert len(result.restaurants) == 1
        assert "cafe" in result.restaurants[0].categories[0]

        # Verify cafe categories were used
        call_args = food_agent.geoapify_client.search_restaurants.call_args[0][0]
        assert GeoapifyCateringCategory.CAFE.value in call_args.categories

    @pytest.mark.asyncio
    async def test_get_fast_food_options(self, food_agent):
        """Test fast food search."""
        fast_food_response = RestaurantSearchResponse(
            restaurants=[
                RestaurantOption(
                    external_id="ff_1",
                    name="Quick Burger",
                    categories=["catering.fast_food.burger"],
                    location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
                    distance_meters=1000,
                    provider="geoapify",
                ),
                RestaurantOption(
                    external_id="ff_2",
                    name="Pizza Express",
                    categories=["catering.fast_food.pizza"],
                    location=RestaurantLocation(latitude=40.7128, longitude=-74.0060),
                    distance_meters=1500,
                    provider="geoapify",
                ),
            ],
            total_results=2,
            search_time_ms=75,
            cached=False,
        )

        food_agent.geoapify_client.search_restaurants = AsyncMock(return_value=fast_food_response)

        result = await food_agent.get_fast_food_options(
            latitude=40.7128,
            longitude=-74.0060,
        )

        assert len(result.restaurants) == 2
        assert all("fast_food" in r.categories[0] for r in result.restaurants)

        # Verify fast food categories were used
        call_args = food_agent.geoapify_client.search_restaurants.call_args[0][0]
        assert GeoapifyCateringCategory.FAST_FOOD.value in call_args.categories


class TestCircuitBreaker:
    """Test circuit breaker integration with Geoapify."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_protection(self, food_agent, sample_restaurant_request):
        """Test that circuit breaker protects API calls."""
        food_agent.geoapify_circuit_breaker = MagicMock()
        food_agent.geoapify_circuit_breaker.__aenter__ = AsyncMock()
        food_agent.geoapify_circuit_breaker.__aexit__ = AsyncMock()

        food_agent.geoapify_client.search_restaurants = AsyncMock(
            return_value=RestaurantSearchResponse(
                restaurants=[],
                total_results=0,
                search_time_ms=100,
                cached=False,
            )
        )

        await food_agent.process(sample_restaurant_request.model_dump())

        # Verify circuit breaker was used
        food_agent.geoapify_circuit_breaker.__aenter__.assert_called_once()


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_search_local_specialties_error_handling(self, food_agent):
        """Test local specialty search handles errors gracefully."""
        food_agent.geoapify_client.search_restaurants = AsyncMock(
            side_effect=Exception("API Error")
        )

        # Should return empty results instead of raising
        result = await food_agent.search_local_specialties(location="Rome, Italy")

        assert isinstance(result, RestaurantSearchResponse)
        assert len(result.restaurants) == 0
        assert "error" in result.search_metadata

    @pytest.mark.asyncio
    async def test_search_by_cuisine_error_propagation(self, food_agent):
        """Test cuisine search propagates errors."""
        food_agent.geoapify_client.search_restaurants = AsyncMock(
            side_effect=ExternalAPIError("API Error")
        )

        with pytest.raises(ExternalAPIError):
            await food_agent.search_by_cuisine(
                location="Tokyo",
                cuisine_category=GeoapifyCateringCategory.RESTAURANT_JAPANESE,
            )


class TestContextManager:
    """Test async context manager support."""

    @pytest.mark.asyncio
    async def test_context_manager_usage(self, mock_settings, mock_database, mock_redis):
        """Test FoodAgent can be used as async context manager."""
        with patch("travel_companion.agents.food_agent.GeoapifyClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock()
            MockClient.return_value = mock_client_instance

            with patch("travel_companion.agents.food_agent.CircuitBreaker"):
                agent = FoodAgent(settings=mock_settings, database=mock_database, redis=mock_redis)

                async with agent as context_agent:
                    assert context_agent is agent
                    mock_client_instance.__aenter__.assert_called_once()

                mock_client_instance.__aexit__.assert_called_once()

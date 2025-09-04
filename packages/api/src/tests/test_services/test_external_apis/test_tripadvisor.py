"""Tests for TripAdvisor API client."""

from decimal import Decimal
from unittest.mock import Mock, patch

import httpx
import pytest

from travel_companion.models.external import ActivityCategory, ActivitySearchRequest
from travel_companion.services.external_apis.tripadvisor import TripAdvisorAPIClient


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.tripadvisor_api_key = "test_api_key_123"
    return settings


@pytest.fixture
def tripadvisor_client():
    """Create TripAdvisor client for testing."""
    with patch(
        "travel_companion.services.external_apis.tripadvisor.get_settings"
    ) as mock_get_settings:
        mock_get_settings.return_value = Mock()
        mock_get_settings.return_value.tripadvisor_api_key = "test_key"
        return TripAdvisorAPIClient()


@pytest.fixture
def sample_activity_request():
    """Sample activity search request."""
    return ActivitySearchRequest(
        location="Paris, France",
        category=ActivityCategory.CULTURAL,
        guest_count=2,
        max_results=10,
    )


@pytest.fixture
def mock_location_response():
    """Mock TripAdvisor location search response."""
    return {
        "data": [
            {
                "location_id": "187147",
                "name": "Paris",
                "address_obj": {
                    "address_string": "Paris, France",
                    "city": "Paris",
                    "country": "France",
                },
                "latitude": "48.856614",
                "longitude": "2.3522219",
            }
        ]
    }


@pytest.fixture
def mock_attractions_response():
    """Mock TripAdvisor attractions response."""
    return {
        "data": [
            {
                "location_id": "188679",
                "name": "Louvre Museum",
                "description": "World's largest art museum",
                "category": {"name": "Museums"},
                "subcategory": [{"name": "Art Museums"}],
                "address_obj": {
                    "address_string": "Rue de Rivoli, 75001 Paris, France",
                    "city": "Paris",
                    "country": "France",
                },
                "latitude": "48.8606",
                "longitude": "2.3376",
                "rating": "4.5",
                "num_reviews": "89,234",
                "photo": {
                    "images": [
                        {"url": "https://example.com/louvre1.jpg"},
                        {"url": "https://example.com/louvre2.jpg"},
                    ]
                },
                "web_url": "https://www.tripadvisor.com/Attraction_Review-g187147-d188679",
            }
        ]
    }


class TestTripAdvisorAPIClient:
    """Test cases for TripAdvisor API client."""

    def test_client_initialization(self, tripadvisor_client):
        """Test client initialization."""
        assert tripadvisor_client.base_url == "https://api.content.tripadvisor.com/api/v1"
        assert tripadvisor_client.failure_count == 0
        assert not tripadvisor_client.circuit_open

    @pytest.mark.asyncio
    async def test_search_activities_success(
        self,
        tripadvisor_client,
        sample_activity_request,
        mock_location_response,
        mock_attractions_response,
    ):
        """Test successful activity search."""
        # Mock the client methods directly instead of httpx
        from travel_companion.services.external_apis.tripadvisor import TripAdvisorAttraction

        mock_attraction = TripAdvisorAttraction(
            location_id="188679",
            name="Louvre Museum",
            description="World's largest art museum",
            category={"name": "Museums"},
            address_obj={
                "address_string": "Rue de Rivoli, 75001 Paris, France",
                "city": "Paris",
                "country": "France",
            },
            latitude="48.8606",
            longitude="2.3376",
            rating="4.5",
            num_reviews="89234",
        )

        with (
            patch.object(tripadvisor_client, "_search_location", return_value="187147"),
            patch.object(tripadvisor_client, "_search_attractions", return_value=[mock_attraction]),
        ):
            activities = await tripadvisor_client.search_activities(sample_activity_request)

            assert len(activities) == 1
            assert activities[0].name == "Louvre Museum"
            assert activities[0].provider == "tripadvisor"
            assert activities[0].external_id == "188679"
            assert activities[0].category == ActivityCategory.CULTURAL

    @pytest.mark.asyncio
    async def test_search_activities_no_location_found(
        self, tripadvisor_client, sample_activity_request
    ):
        """Test activity search when no location is found."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": []}  # Empty location results

            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            activities = await tripadvisor_client.search_activities(sample_activity_request)

            assert activities == []

    @pytest.mark.asyncio
    async def test_search_activities_api_error(self, tripadvisor_client, sample_activity_request):
        """Test activity search with API error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.RequestError(
                "API Error"
            )

            activities = await tripadvisor_client.search_activities(sample_activity_request)

            assert activities == []
            assert tripadvisor_client.failure_count == 1

    @pytest.mark.asyncio
    async def test_search_activities_rate_limited(
        self, tripadvisor_client, sample_activity_request
    ):
        """Test handling of rate limit responses."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "10"}

            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            with patch("asyncio.sleep") as mock_sleep:
                activities = await tripadvisor_client.search_activities(sample_activity_request)

                assert activities == []
                mock_sleep.assert_called()

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(
        self, tripadvisor_client, sample_activity_request
    ):
        """Test circuit breaker opens after repeated failures."""
        # Trigger 3 failures to open circuit breaker
        for _ in range(3):
            await tripadvisor_client._handle_api_failure()

        assert tripadvisor_client.circuit_open

        # Now search should be skipped
        activities = await tripadvisor_client.search_activities(sample_activity_request)
        assert activities == []

    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self, tripadvisor_client):
        """Test circuit breaker reset after success."""
        # Simulate some failures
        tripadvisor_client.failure_count = 2

        # Reset on success
        tripadvisor_client._reset_circuit_breaker()

        assert tripadvisor_client.failure_count == 0

    def test_map_category_to_tripadvisor(self, tripadvisor_client):
        """Test category mapping to TripAdvisor categories."""
        assert (
            tripadvisor_client._map_category_to_tripadvisor(ActivityCategory.CULTURAL) == "museums"
        )
        assert (
            tripadvisor_client._map_category_to_tripadvisor(ActivityCategory.ADVENTURE) == "outdoor"
        )
        assert tripadvisor_client._map_category_to_tripadvisor(ActivityCategory.FOOD) == "food"

    def test_map_tripadvisor_category_to_internal(self, tripadvisor_client):
        """Test mapping TripAdvisor categories to internal categories."""
        from travel_companion.services.external_apis.tripadvisor import TripAdvisorAttraction

        # Museum attraction
        museum_attraction = TripAdvisorAttraction(
            location_id="123",
            name="Test Museum",
            category={"name": "Museums"},
            subcategory=[{"name": "Art Museums"}],
        )

        category = tripadvisor_client._map_tripadvisor_category_to_internal(museum_attraction)
        assert category == ActivityCategory.CULTURAL

        # Adventure attraction
        adventure_attraction = TripAdvisorAttraction(
            location_id="456",
            name="Hiking Tour",
            category={"name": "Outdoor Activities"},
            subcategory=[{"name": "Adventure"}],
        )

        category = tripadvisor_client._map_tripadvisor_category_to_internal(adventure_attraction)
        assert category == ActivityCategory.ADVENTURE

    def test_estimate_activity_price(self, tripadvisor_client):
        """Test activity price estimation based on category."""
        cultural_price = tripadvisor_client._estimate_activity_price(ActivityCategory.CULTURAL)
        assert cultural_price == Decimal("15.00")

        adventure_price = tripadvisor_client._estimate_activity_price(ActivityCategory.ADVENTURE)
        assert adventure_price == Decimal("75.00")

        nature_price = tripadvisor_client._estimate_activity_price(ActivityCategory.NATURE)
        assert nature_price == Decimal("0.00")  # Often free

    def test_estimate_duration(self, tripadvisor_client):
        """Test activity duration estimation based on category."""
        cultural_duration = tripadvisor_client._estimate_duration(ActivityCategory.CULTURAL)
        assert cultural_duration == 120  # 2 hours

        adventure_duration = tripadvisor_client._estimate_duration(ActivityCategory.ADVENTURE)
        assert adventure_duration == 240  # 4 hours

    @pytest.mark.asyncio
    async def test_convert_to_activity(self, tripadvisor_client):
        """Test conversion of TripAdvisor attraction to ActivityOption."""
        from travel_companion.services.external_apis.tripadvisor import TripAdvisorAttraction

        attraction = TripAdvisorAttraction(
            location_id="188679",
            name="Louvre Museum",
            description="World's largest art museum",
            category={"name": "Museums"},
            subcategory=[{"name": "Art Museums"}],
            address_obj={
                "address_string": "Rue de Rivoli, 75001 Paris, France",
                "city": "Paris",
                "country": "France",
            },
            latitude="48.8606",
            longitude="2.3376",
            rating="4.5",
            num_reviews="1,250",
            photo={"images": [{"url": "https://example.com/louvre.jpg"}]},
            web_url="https://www.tripadvisor.com/attraction",
        )

        activity = await tripadvisor_client._convert_to_activity(attraction)

        assert activity is not None
        assert activity.name == "Louvre Museum"
        assert activity.external_id == "188679"
        assert activity.category == ActivityCategory.CULTURAL
        assert activity.location.latitude == 48.8606
        assert activity.location.longitude == 2.3376
        assert activity.rating == 4.5
        assert activity.review_count == 1250
        assert len(activity.images) == 1
        assert activity.provider == "tripadvisor"

    @pytest.mark.asyncio
    async def test_convert_to_activity_with_invalid_data(self, tripadvisor_client):
        """Test conversion handling of invalid attraction data."""
        from travel_companion.services.external_apis.tripadvisor import TripAdvisorAttraction

        # Attraction with invalid rating
        attraction = TripAdvisorAttraction(
            location_id="123",
            name="Test Attraction",
            rating="invalid_rating",  # Invalid rating
            num_reviews="not_a_number",  # Invalid review count
        )

        activity = await tripadvisor_client._convert_to_activity(attraction)

        assert activity is not None
        assert activity.rating is None  # Should handle invalid rating gracefully
        assert activity.review_count is None  # Should handle invalid count gracefully

    @pytest.mark.asyncio
    async def test_rate_limiting(self, tripadvisor_client):
        """Test rate limiting functionality."""
        import time

        # Reset rate limit state
        tripadvisor_client.request_count = 0
        tripadvisor_client.rate_limit_reset_time = time.time() + 3600

        # Make requests up to limit
        for _ in range(20):
            await tripadvisor_client._check_rate_limit()

        assert tripadvisor_client.request_count == 20

        # Next request should trigger waiting
        with patch("asyncio.sleep") as mock_sleep:
            await tripadvisor_client._check_rate_limit()
            mock_sleep.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_handle_rate_limit_response(self, tripadvisor_client):
        """Test handling of rate limit HTTP response."""
        mock_response = Mock()
        mock_response.headers = {"Retry-After": "30"}

        with patch("asyncio.sleep") as mock_sleep:
            await tripadvisor_client._handle_rate_limit(mock_response)
            mock_sleep.assert_called_once_with(30)

        # Test with no Retry-After header
        mock_response.headers = {}
        with patch("asyncio.sleep") as mock_sleep:
            await tripadvisor_client._handle_rate_limit(mock_response)
            mock_sleep.assert_called_once_with(60)  # Default wait time

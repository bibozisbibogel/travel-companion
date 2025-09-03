"""Tests for Booking.com API client implementation."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from travel_companion.services.external_apis.booking import (
    BookingApiResponse,
    BookingClient,
    BookingCredentials,
    BookingHotelResult,
    HotelSearchParams,
)
from travel_companion.utils.errors import ExternalAPIError, RateLimitError


class TestBookingClient:
    """Test suite for BookingClient class."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings for testing."""
        settings = MagicMock()
        settings.booking_username = "test_user"
        settings.booking_password = "test_pass"
        return settings

    @pytest.fixture
    def booking_client(self) -> BookingClient:
        """Create BookingClient instance for testing."""
        return BookingClient(
            username="test_user",
            password="test_pass",
            timeout=5.0,
        )

    @pytest.fixture
    def hotel_search_params(self) -> HotelSearchParams:
        """Create hotel search parameters for testing."""
        return HotelSearchParams(
            location="New York",
            check_in="2024-06-15",
            check_out="2024-06-17",
            guest_count=2,
            room_count=1,
            max_results=10,
        )

    @pytest.fixture
    def sample_xml_response(self) -> str:
        """Create sample XML response for testing."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<response>
    <total_results>2</total_results>
    <hotel hotel_id="12345">
        <name>Test Hotel</name>
        <address>123 Test Street, New York</address>
        <location>
            <latitude>40.7128</latitude>
            <longitude>-74.0060</longitude>
        </location>
        <price>150.00</price>
        <currency>USD</currency>
        <rating>4.5</rating>
        <review_score>8.5</review_score>
        <amenities>
            <amenity>WiFi</amenity>
            <amenity>Pool</amenity>
        </amenities>
        <photos>
            <photo>https://example.com/photo1.jpg</photo>
        </photos>
        <description>A lovely test hotel</description>
        <booking_url>https://booking.com/hotel/12345</booking_url>
    </hotel>
    <hotel hotel_id="67890">
        <name>Another Hotel</name>
        <price>200.00</price>
        <currency>USD</currency>
    </hotel>
</response>"""

    def test_booking_client_initialization(self, booking_client):
        """Test BookingClient initializes correctly."""
        assert booking_client.username == "test_user"
        assert booking_client.password == "test_pass"
        assert booking_client.base_url == "https://distribution-xml.booking.com"
        assert booking_client.timeout == 5.0
        assert booking_client.rate_limit_per_minute == 100

    def test_booking_client_initialization_no_credentials(self):
        """Test BookingClient initializes with warning when no credentials."""
        client = BookingClient()
        assert client.username is None
        assert client.password is None

    @pytest.mark.asyncio
    async def test_booking_client_context_manager(self):
        """Test BookingClient works as async context manager."""
        async with BookingClient(username="test", password="test") as client:
            assert client is not None
        # Client should be closed after context

    def test_credentials_model(self):
        """Test BookingCredentials model validation."""
        credentials = BookingCredentials(username="test", password="secret")
        assert credentials.username == "test"
        assert credentials.password == "secret"

    def test_hotel_search_params_validation(self):
        """Test HotelSearchParams model validation."""
        params = HotelSearchParams(
            location="Paris",
            check_in="2024-07-01",
            check_out="2024-07-03",
            guest_count=4,
        )
        assert params.location == "Paris"
        assert params.guest_count == 4
        assert params.room_count == 1  # Default value
        assert params.currency == "USD"  # Default value

    def test_hotel_search_params_invalid_guest_count(self):
        """Test HotelSearchParams validates guest count limits."""
        with pytest.raises(ValueError):
            HotelSearchParams(
                location="Paris",
                check_in="2024-07-01",
                check_out="2024-07-03",
                guest_count=25,  # Exceeds maximum
            )

    def test_booking_hotel_result_model(self):
        """Test BookingHotelResult model creation."""
        hotel = BookingHotelResult(
            hotel_id="12345",
            name="Test Hotel",
            price_per_night=150.0,
            currency="USD",
        )
        assert hotel.hotel_id == "12345"
        assert hotel.name == "Test Hotel"
        assert hotel.price_per_night == 150.0
        assert hotel.amenities == []  # Default empty list

    def test_create_hotel_search_xml(self, booking_client, hotel_search_params):
        """Test XML payload creation for hotel search."""
        xml_payload = booking_client._create_hotel_search_xml(hotel_search_params)

        assert "test_user" in xml_payload
        assert "test_pass" in xml_payload
        assert "New York" in xml_payload
        assert "2024-06-15" in xml_payload
        assert "2024-06-17" in xml_payload
        assert "<guests>2</guests>" in xml_payload
        assert "<num_rooms>1</num_rooms>" in xml_payload

    def test_parse_hotel_response(self, booking_client, sample_xml_response):
        """Test XML response parsing."""
        response = booking_client._parse_hotel_response(sample_xml_response)

        assert isinstance(response, BookingApiResponse)
        assert response.total_results == 2
        assert len(response.hotels) == 2

        # Check first hotel
        first_hotel = response.hotels[0]
        assert first_hotel.hotel_id == "12345"
        assert first_hotel.name == "Test Hotel"
        assert first_hotel.address == "123 Test Street, New York"
        assert first_hotel.latitude == 40.7128
        assert first_hotel.longitude == -74.0060
        assert first_hotel.price_per_night == 150.0
        assert first_hotel.currency == "USD"
        assert first_hotel.rating == 4.5
        assert first_hotel.review_score == 8.5
        assert "WiFi" in first_hotel.amenities
        assert "Pool" in first_hotel.amenities
        assert "https://example.com/photo1.jpg" in first_hotel.photos
        assert first_hotel.description == "A lovely test hotel"
        assert first_hotel.booking_url == "https://booking.com/hotel/12345"

        # Check second hotel (minimal data)
        second_hotel = response.hotels[1]
        assert second_hotel.hotel_id == "67890"
        assert second_hotel.name == "Another Hotel"
        assert second_hotel.price_per_night == 200.0

    def test_parse_hotel_response_invalid_xml(self, booking_client):
        """Test XML response parsing handles invalid XML."""
        invalid_xml = "Not valid XML at all"

        with pytest.raises(ExternalAPIError, match="Failed to parse Booking.com response"):
            booking_client._parse_hotel_response(invalid_xml)

    def test_parse_hotel_response_malformed_hotel(self, booking_client):
        """Test XML response parsing handles malformed hotel elements gracefully."""
        malformed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<response>
    <hotel hotel_id="12345">
        <name>Valid Hotel</name>
        <price>150.00</price>
        <currency>USD</currency>
    </hotel>
    <hotel hotel_id="invalid">
        <name>Broken Hotel</name>
        <price>not-a-number</price>
    </hotel>
</response>"""

        response = booking_client._parse_hotel_response(malformed_xml)

        # Should only parse the valid hotel
        assert len(response.hotels) == 1
        assert response.hotels[0].name == "Valid Hotel"

    @pytest.mark.asyncio
    async def test_rate_limiting(self, booking_client):
        """Test rate limiting mechanism."""
        # Mock the semaphore and timing
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.side_effect = [
                0.0,
                0.3,
                0.3,
                1.0,
            ]  # Simulate time progression

            # First call should not sleep
            await booking_client._rate_limit()

            # Second call should sleep due to rate limiting
            with patch("asyncio.sleep") as mock_sleep:
                await booking_client._rate_limit()
                mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_api_request_success(self, booking_client):
        """Test successful API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<response>success</response>"

        with patch.object(booking_client.client, "post", return_value=mock_response):
            result = await booking_client._make_api_request("/test", "<request/>")
            assert result == "<response>success</response>"

    @pytest.mark.asyncio
    async def test_make_api_request_rate_limit(self, booking_client):
        """Test API request handles rate limiting."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}

        with patch.object(booking_client.client, "post", return_value=mock_response):
            with pytest.raises(RateLimitError) as exc_info:
                await booking_client._make_api_request("/test", "<request/>")

            assert exc_info.value.details["retry_after"] == 60

    @pytest.mark.asyncio
    async def test_make_api_request_http_error(self, booking_client):
        """Test API request handles HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(booking_client.client, "post", return_value=mock_response):
            with pytest.raises(ExternalAPIError) as exc_info:
                await booking_client._make_api_request("/test", "<request/>")

            assert exc_info.value.details["status_code"] == 500

    @pytest.mark.asyncio
    async def test_make_api_request_network_error(self, booking_client):
        """Test API request handles network errors."""
        with patch.object(
            booking_client.client, "post", side_effect=httpx.RequestError("Network error")
        ):
            with pytest.raises(ExternalAPIError, match="Failed to connect to Booking.com API"):
                await booking_client._make_api_request("/test", "<request/>")

    @pytest.mark.asyncio
    async def test_search_hotels_no_credentials(self):
        """Test hotel search fails without credentials."""
        client = BookingClient()  # No credentials
        params = HotelSearchParams(
            location="Paris",
            check_in="2024-07-01",
            check_out="2024-07-03",
            guest_count=2,
        )

        with pytest.raises(ExternalAPIError, match="credentials not configured"):
            await client.search_hotels(params)

    @pytest.mark.asyncio
    async def test_search_hotels_invalid_dates(self, booking_client):
        """Test hotel search validates date formats."""
        params = HotelSearchParams(
            location="Paris",
            check_in="invalid-date",
            check_out="2024-07-03",
            guest_count=2,
        )

        with pytest.raises(ValueError, match="Invalid date format"):
            await booking_client.search_hotels(params)

    @pytest.mark.asyncio
    async def test_search_hotels_success(
        self, booking_client, hotel_search_params, sample_xml_response
    ):
        """Test successful hotel search."""
        with patch.object(booking_client, "_rate_limit", return_value=None):
            with patch.object(booking_client._circuit_breaker, "call") as mock_circuit:
                mock_circuit.return_value = sample_xml_response

                result = await booking_client.search_hotels(hotel_search_params)

                assert isinstance(result, BookingApiResponse)
                assert len(result.hotels) == 2
                assert result.total_results == 2

                # Verify circuit breaker was called with correct arguments
                mock_circuit.assert_called_once()
                args = mock_circuit.call_args[0]
                assert args[0] == booking_client._make_api_request
                assert args[1] == "/json/bookings.getHotelAvailabilityV2"

    @pytest.mark.asyncio
    async def test_get_hotel_details_success(self, booking_client, sample_xml_response):
        """Test successful hotel details retrieval."""
        hotel_id = "12345"

        with patch.object(booking_client, "_rate_limit", return_value=None):
            with patch.object(booking_client._circuit_breaker, "call") as mock_circuit:
                mock_circuit.return_value = sample_xml_response

                result = await booking_client.get_hotel_details(hotel_id)

                assert isinstance(result, BookingHotelResult)
                assert result.hotel_id == "12345"
                assert result.name == "Test Hotel"

    @pytest.mark.asyncio
    async def test_get_hotel_details_not_found(self, booking_client):
        """Test hotel details retrieval when hotel not found."""
        empty_response = """<?xml version="1.0" encoding="UTF-8"?>
<response>
    <total_results>0</total_results>
</response>"""

        with patch.object(booking_client, "_rate_limit", return_value=None):
            with patch.object(booking_client._circuit_breaker, "call") as mock_circuit:
                mock_circuit.return_value = empty_response

                result = await booking_client.get_hotel_details("nonexistent")

                assert result is None

    @pytest.mark.asyncio
    async def test_get_hotel_details_error(self, booking_client):
        """Test hotel details retrieval handles errors gracefully."""
        with patch.object(booking_client, "_rate_limit", return_value=None):
            with patch.object(booking_client._circuit_breaker, "call") as mock_circuit:
                mock_circuit.side_effect = ExternalAPIError("API error")

                result = await booking_client.get_hotel_details("12345")

                assert result is None

    def test_get_health_status_with_credentials(self, booking_client):
        """Test health status with configured credentials."""
        status = booking_client.get_health_status()

        assert status["service"] == "booking"
        assert status["status"] == "healthy"
        assert status["credentials_configured"] is True
        assert "circuit_breaker" in status
        assert status["rate_limit_per_minute"] == 100

    def test_get_health_status_no_credentials(self):
        """Test health status without configured credentials."""
        client = BookingClient()
        status = client.get_health_status()

        assert status["service"] == "booking"
        assert status["status"] == "degraded"
        assert status["credentials_configured"] is False

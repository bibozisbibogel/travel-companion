"""Tests for OpenWeatherMap API client with mock responses."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from travel_companion.models.external import (
    WeatherCondition,
    WeatherSearchRequest,
    WeatherSeverity,
)
from travel_companion.services.external_apis.openweather import OpenWeatherMapAPIClient


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.openweather_api_key = "test_api_key_12345"
    return settings


@pytest.fixture
def openweather_client(mock_settings):
    """Create OpenWeatherMap client with mocked settings."""
    with patch(
        "travel_companion.services.external_apis.openweather.get_settings",
        return_value=mock_settings,
    ):
        client = OpenWeatherMapAPIClient()
        return client


@pytest.fixture
def sample_weather_request():
    """Sample weather search request."""
    return WeatherSearchRequest(
        location="Paris, France",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        include_alerts=True,
        include_historical=False,
    )


@pytest.fixture
def mock_geocode_response():
    """Mock geocoding API response from OpenWeatherMap."""
    return [
        {
            "name": "Paris",
            "local_names": {"en": "Paris", "fr": "Paris"},
            "lat": 48.8566,
            "lon": 2.3522,
            "country": "FR",
            "state": "Île-de-France",
        }
    ]


@pytest.fixture
def mock_onecall_response():
    """Mock One Call API response from OpenWeatherMap."""
    current_time = int(datetime.now(UTC).timestamp())
    return {
        "lat": 48.8566,
        "lon": 2.3522,
        "timezone": "Europe/Paris",
        "timezone_offset": 3600,
        "current": {
            "dt": current_time,
            "sunrise": current_time - 3600,
            "sunset": current_time + 7200,
            "temp": 20.5,
            "feels_like": 22.1,
            "pressure": 1013,
            "humidity": 65,
            "dew_point": 14.2,
            "uvi": 5.5,
            "clouds": 25,
            "visibility": 10000,
            "wind_speed": 4.2,
            "wind_deg": 180,
            "weather": [{"id": 801, "main": "Clouds", "description": "few clouds", "icon": "02d"}],
        },
        "hourly": [
            {
                "dt": current_time + 3600,
                "temp": 18.5,
                "feels_like": 19.2,
                "pressure": 1015,
                "humidity": 70,
                "dew_point": 13.1,
                "uvi": 3.2,
                "clouds": 40,
                "visibility": 10000,
                "wind_speed": 3.8,
                "wind_deg": 200,
                "weather": [
                    {"id": 500, "main": "Rain", "description": "light rain", "icon": "10d"}
                ],
                "pop": 0.65,
                "rain": {"1h": 0.8},
            }
        ],
        "daily": [
            {
                "dt": current_time,
                "sunrise": current_time - 3600,
                "sunset": current_time + 7200,
                "moonrise": current_time + 10800,
                "moonset": current_time - 10800,
                "temp": {
                    "day": 22.5,
                    "min": 15.2,
                    "max": 25.1,
                    "night": 17.8,
                    "eve": 20.9,
                    "morn": 16.4,
                },
                "feels_like": {"day": 23.2, "night": 18.5, "eve": 21.6, "morn": 17.1},
                "pressure": 1015,
                "humidity": 68,
                "dew_point": 16.3,
                "wind_speed": 4.5,
                "wind_deg": 210,
                "weather": [
                    {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
                ],
                "clouds": 15,
                "pop": 0.2,
                "uvi": 6.8,
            }
        ],
        "alerts": [
            {
                "sender_name": "Météo-France",
                "event": "Wind Advisory",
                "start": current_time + 7200,
                "end": current_time + 14400,
                "description": "Strong winds expected with gusts up to 60 km/h",
                "tags": ["wind", "advisory"],
            }
        ],
    }


class TestOpenWeatherMapAPIClient:
    """Test cases for OpenWeatherMap API client."""

    def test_client_initialization(self, openweather_client):
        """Test client initializes with correct configuration."""
        assert openweather_client.base_url == "https://api.openweathermap.org/data/2.5"
        assert openweather_client.api_key == "test_api_key_12345"
        assert openweather_client.timeout == 30.0
        assert openweather_client.max_retries == 3

    @pytest.mark.asyncio
    async def test_get_weather_forecast_success(
        self,
        openweather_client,
        sample_weather_request,
        mock_geocode_response,
        mock_onecall_response,
    ):
        """Test successful weather forecast retrieval."""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock the context manager and responses
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Mock geocoding response
            geocode_response = Mock()
            geocode_response.json.return_value = mock_geocode_response
            geocode_response.raise_for_status = Mock()

            # Mock One Call API response
            onecall_response = Mock()
            onecall_response.json.return_value = mock_onecall_response
            onecall_response.raise_for_status = Mock()

            # Set up the mock to return different responses for different URLs
            def mock_get(url, **kwargs):
                if "geo/1.0/direct" in url:
                    return geocode_response
                elif "onecall" in url:
                    return onecall_response
                else:
                    raise ValueError(f"Unexpected URL: {url}")

            mock_client_instance.get = AsyncMock(side_effect=mock_get)

            # Execute the test
            result = await openweather_client.get_weather_forecast(sample_weather_request)

            # Verify the result
            assert result.location.name == "Paris, France"
            assert result.location.latitude == 48.8566
            assert result.location.longitude == 2.3522
            assert result.location.timezone == "Europe/Paris"

            # Verify current weather
            assert result.current is not None
            assert result.current.temperature == 20.5
            assert result.current.feels_like == 22.1
            assert result.current.humidity == 65
            assert result.current.condition == WeatherCondition.CLOUDY

            # Verify hourly forecast
            assert len(result.hourly) == 1
            hourly = result.hourly[0]
            assert hourly.temperature == 18.5
            assert hourly.precipitation_probability == 0.65
            assert hourly.condition == WeatherCondition.RAIN

            # Verify daily forecast
            assert len(result.daily) == 1
            daily = result.daily[0]
            assert daily.temperature == 22.5  # day temperature
            assert daily.condition == WeatherCondition.CLEAR

            # Verify alerts
            assert len(result.alerts) == 1
            alert = result.alerts[0]
            assert alert.title == "Wind Advisory"
            assert alert.severity == WeatherSeverity.MODERATE
            assert "Strong winds" in alert.description

    @pytest.mark.asyncio
    async def test_get_weather_forecast_with_coordinates(
        self, openweather_client, mock_onecall_response
    ):
        """Test weather forecast with provided coordinates (skip geocoding)."""
        request = WeatherSearchRequest(
            location="Custom Location",
            latitude=48.8566,
            longitude=2.3522,
            start_date=datetime.now(UTC),
            end_date=datetime.now(UTC),
            include_alerts=True,
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            onecall_response = Mock()
            onecall_response.json.return_value = mock_onecall_response
            onecall_response.raise_for_status = Mock()

            mock_client_instance.get = AsyncMock(return_value=onecall_response)

            await openweather_client.get_weather_forecast(request)

            # Should not call geocoding API
            assert mock_client_instance.get.call_count == 1

            # Verify coordinates are used correctly
            call_args = mock_client_instance.get.call_args
            params = call_args.kwargs["params"]
            assert params["lat"] == 48.8566
            assert params["lon"] == 2.3522

    @pytest.mark.asyncio
    async def test_geocode_location_not_found(self, openweather_client):
        """Test geocoding when location is not found."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Mock empty geocoding response
            geocode_response = Mock()
            geocode_response.json.return_value = []  # Empty array
            geocode_response.raise_for_status = Mock()

            mock_client_instance.get = AsyncMock(return_value=geocode_response)

            with pytest.raises(ValueError) as exc_info:
                await openweather_client._geocode_location("Unknown Location")

            assert "Location not found: Unknown Location" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_api_request_failure_with_retry(self, openweather_client):
        """Test API request failure handling with retries in One Call API."""
        # Test retry logic directly on the One Call API method
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            # Mock HTTP error that should trigger retries
            mock_client_instance.get = AsyncMock(side_effect=httpx.HTTPError("API Error"))

            with pytest.raises(httpx.HTTPError):
                await openweather_client._get_onecall_data(48.8566, 2.3522, True)

            # Should have retried 3 times
            assert mock_client_instance.get.call_count == 3

    @pytest.mark.asyncio
    async def test_exclude_alerts_parameter(self, openweather_client, mock_onecall_response):
        """Test that alerts can be excluded from API request."""
        request = WeatherSearchRequest(
            location="Test Location",
            latitude=48.8566,
            longitude=2.3522,
            start_date=datetime.now(UTC),
            end_date=datetime.now(UTC),
            include_alerts=False,  # Exclude alerts
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            onecall_response = Mock()
            onecall_response.json.return_value = mock_onecall_response
            onecall_response.raise_for_status = Mock()

            mock_client_instance.get = AsyncMock(return_value=onecall_response)

            await openweather_client.get_weather_forecast(request)

            # Check that alerts were excluded in the API call
            call_args = mock_client_instance.get.call_args
            params = call_args.kwargs["params"]
            assert "alerts" in params["exclude"]

    def test_weather_condition_mapping(self, openweather_client):
        """Test weather condition mapping from OpenWeatherMap to internal format."""
        test_cases = [
            ("Clear", WeatherCondition.CLEAR),
            ("Clouds", WeatherCondition.CLOUDY),
            ("Rain", WeatherCondition.RAIN),
            ("Drizzle", WeatherCondition.LIGHT_RAIN),
            ("Thunderstorm", WeatherCondition.THUNDERSTORM),
            ("Snow", WeatherCondition.SNOW),
            ("Mist", WeatherCondition.MIST),
            ("Fog", WeatherCondition.FOG),
            ("Unknown", WeatherCondition.UNKNOWN),
        ]

        for owm_condition, expected_condition in test_cases:
            result = openweather_client._map_weather_condition(owm_condition)
            assert result == expected_condition

    def test_alert_severity_mapping(self, openweather_client):
        """Test alert severity mapping from event types."""
        test_cases = [
            ("hurricane warning", WeatherSeverity.EXTREME),
            ("tornado watch", WeatherSeverity.EXTREME),
            ("severe thunderstorm warning", WeatherSeverity.HIGH),
            ("flood warning", WeatherSeverity.HIGH),
            ("wind advisory", WeatherSeverity.MODERATE),
            ("frost caution", WeatherSeverity.MODERATE),
            ("general weather statement", WeatherSeverity.LOW),
        ]

        for event, expected_severity in test_cases:
            result = openweather_client._map_alert_severity(event)
            assert result == expected_severity

    def test_precipitation_amount_calculation(self, openweather_client):
        """Test precipitation amount calculation from rain and snow data."""
        # Test with rain only
        rain_data = {"1h": 2.5}
        result = openweather_client._get_precipitation_amount(rain_data, None)
        assert result == 2.5

        # Test with snow only
        snow_data = {"1h": 1.2}
        result = openweather_client._get_precipitation_amount(None, snow_data)
        assert result == 1.2

        # Test with both rain and snow
        result = openweather_client._get_precipitation_amount(rain_data, snow_data)
        assert result == 3.7  # 2.5 + 1.2

        # Test with no precipitation
        result = openweather_client._get_precipitation_amount(None, None)
        assert result == 0.0

    def test_unit_conversions(self, openweather_client):
        """Test unit conversions in weather data processing."""
        from travel_companion.services.external_apis.openweather import OpenWeatherMapCurrent

        # Create mock current weather data
        current_data = OpenWeatherMapCurrent(
            dt=int(datetime.now(UTC).timestamp()),
            temp=20.0,
            feels_like=22.0,
            pressure=1013,
            humidity=65,
            clouds=25,
            visibility=5000,  # meters
            wind_speed=10.0,  # m/s
            wind_deg=180,
            weather=[{"main": "Clear", "description": "clear sky"}],
        )

        result = openweather_client._convert_current_weather(current_data)

        # Test visibility conversion (m to km)
        assert result.visibility == 5.0  # 5000m -> 5km

        # Test wind speed conversion (m/s to km/h)
        assert result.wind_speed == 36.0  # 10 m/s -> 36 km/h

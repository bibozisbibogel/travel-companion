"""Tests for WeatherAgent with mock API responses."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from travel_companion.agents.weather_agent import WeatherAgent
from travel_companion.models.external import (
    WeatherAlert,
    WeatherCondition,
    WeatherData,
    WeatherForecast,
    WeatherLocation,
    WeatherSearchRequest,
    WeatherSearchResponse,
    WeatherSeverity,
)


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.openweather_api_key = "test_api_key"
    return settings


@pytest.fixture
def mock_database():
    """Mock database manager for testing."""
    return Mock()


@pytest.fixture
def mock_redis():
    """Mock Redis manager for testing."""
    return Mock()


@pytest.fixture
def weather_agent(mock_settings, mock_database, mock_redis):
    """Create WeatherAgent with mocked dependencies."""
    with patch(
        "travel_companion.services.external_apis.openweather.get_settings",
        return_value=mock_settings,
    ):
        agent = WeatherAgent(settings=mock_settings, database=mock_database, redis=mock_redis)
        return agent


@pytest.fixture
def sample_weather_request():
    """Sample weather search request."""
    return WeatherSearchRequest(
        location="Paris, France",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=5),
        include_alerts=True,
        include_historical=False,
    )


@pytest.fixture
def sample_weather_data():
    """Sample weather data points."""
    base_time = datetime.now(UTC)
    return [
        WeatherData(
            timestamp=base_time,
            temperature=20.0,
            feels_like=22.0,
            humidity=65.0,
            pressure=1013.0,
            visibility=10.0,
            wind_speed=15.0,
            wind_direction=180,
            precipitation=0.0,
            precipitation_probability=0.1,
            condition=WeatherCondition.CLEAR,
            condition_description="Clear sky",
            uv_index=6.0,
        ),
        WeatherData(
            timestamp=base_time + timedelta(hours=6),
            temperature=15.0,
            feels_like=13.0,
            humidity=80.0,
            pressure=1010.0,
            visibility=5.0,
            wind_speed=25.0,
            wind_direction=270,
            precipitation=2.5,
            precipitation_probability=0.8,
            condition=WeatherCondition.RAIN,
            condition_description="Light rain",
            uv_index=2.0,
        ),
    ]


@pytest.fixture
def sample_weather_forecast():
    """Sample weather forecast."""
    location = WeatherLocation(
        name="Paris, France",
        latitude=48.8566,
        longitude=2.3522,
        country="France",
        timezone="Europe/Paris",
    )

    current = WeatherData(
        timestamp=datetime.now(UTC),
        temperature=18.0,
        feels_like=20.0,
        humidity=70.0,
        pressure=1015.0,
        visibility=10.0,
        wind_speed=12.0,
        wind_direction=200,
        precipitation=0.0,
        precipitation_probability=0.2,
        condition=WeatherCondition.PARTLY_CLOUDY,
        condition_description="Partly cloudy",
        uv_index=5.0,
    )

    alerts = [
        WeatherAlert(
            title="Wind Advisory",
            description="Strong winds expected",
            severity=WeatherSeverity.MODERATE,
            start_time=datetime.now(UTC) + timedelta(hours=12),
            end_time=datetime.now(UTC) + timedelta(hours=18),
            regions=["Paris"],
        )
    ]

    return WeatherForecast(location=location, current=current, hourly=[], daily=[], alerts=alerts)


class TestWeatherAgent:
    """Test cases for WeatherAgent."""

    def test_agent_properties(self, weather_agent):
        """Test agent name and version properties."""
        assert weather_agent.agent_name == "weather_agent"
        assert weather_agent.agent_version == "1.0.0"

    @pytest.mark.asyncio
    async def test_process_weather_request_success(
        self, weather_agent, sample_weather_request, sample_weather_forecast
    ):
        """Test successful weather request processing."""
        # Mock the OpenWeatherMap client
        with patch.object(
            weather_agent.openweather_client,
            "get_weather_forecast",
            return_value=sample_weather_forecast,
        ) as mock_forecast:
            request_data = sample_weather_request.model_dump()
            result = await weather_agent.process(request_data)

            assert isinstance(result, WeatherSearchResponse)
            assert result.forecast == sample_weather_forecast
            assert result.data_source == "OpenWeatherMap"
            assert result.search_time_ms >= 0
            assert len(result.forecast.alerts) == 1

            mock_forecast.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_weather_request_api_failure(self, weather_agent, sample_weather_request):
        """Test weather request processing with API failure."""
        # Mock API failure
        with patch.object(
            weather_agent.openweather_client,
            "get_weather_forecast",
            side_effect=Exception("API Error"),
        ):
            request_data = sample_weather_request.model_dump()

            with pytest.raises(Exception) as exc_info:
                await weather_agent.process(request_data)

            assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_invalid_request_data(self, weather_agent):
        """Test processing with invalid request data."""
        invalid_request = {
            "location": "",  # Invalid empty location
            "start_date": "invalid-date",  # Invalid date format
            "end_date": datetime.now(UTC) - timedelta(days=1),  # End before start
        }

        with pytest.raises(Exception):
            await weather_agent.process(invalid_request)

    @pytest.mark.asyncio
    async def test_process_weather_request_with_historical(
        self, weather_agent, sample_weather_request, sample_weather_forecast
    ):
        """Test weather request processing with historical data."""
        # Mock both forecast and historical data
        with patch.object(
            weather_agent.openweather_client,
            "get_weather_forecast",
            return_value=sample_weather_forecast,
        ) as mock_forecast:
            with patch.object(
                weather_agent.openweather_client,
                "get_historical_weather",
                return_value=[
                    WeatherData(
                        timestamp=datetime.now(UTC) - timedelta(days=1),
                        temperature=18.0,
                        feels_like=20.0,
                        humidity=75.0,
                        pressure=1012.0,
                        visibility=10.0,
                        wind_speed=12.0,
                        wind_direction=180,
                        precipitation=0.0,
                        precipitation_probability=0.3,
                        condition=WeatherCondition.CLEAR,
                        condition_description="Clear sky",
                        uv_index=5.0,
                    )
                ],
            ) as mock_historical:
                # Enable historical data in request
                request_data = sample_weather_request.model_dump()
                request_data["include_historical"] = True

                result = await weather_agent.process(request_data)

                assert isinstance(result, WeatherSearchResponse)
                assert result.forecast == sample_weather_forecast
                assert len(result.historical_data) == 1
                assert result.historical_data[0].temperature == 18.0
                assert result.search_metadata["include_historical"] is True

                mock_forecast.assert_called_once()
                mock_historical.assert_called_once()

    @pytest.mark.asyncio
    async def test_weather_caching(
        self, weather_agent, sample_weather_request, sample_weather_forecast
    ):
        """Test weather response caching."""
        # Mock the API client
        with patch.object(
            weather_agent.openweather_client,
            "get_weather_forecast",
            return_value=sample_weather_forecast,
        ) as mock_forecast:
            with patch.object(
                weather_agent.cache_manager, "get_weather_cache", return_value=None
            ) as mock_get_cache:
                with patch.object(
                    weather_agent.cache_manager, "set_weather_cache", return_value=True
                ) as mock_set_cache:
                    request_data = sample_weather_request.model_dump()
                    result = await weather_agent.process(request_data)

                    # Verify API was called
                    mock_forecast.assert_called_once()

                    # Verify cache was checked
                    mock_get_cache.assert_called_once()

                    # Verify cache was set with correct TTL
                    mock_set_cache.assert_called_once()
                    call_args = mock_set_cache.call_args
                    assert call_args[0][1] == result  # Response object
                    # TTL should be 30 minutes (1800s) due to weather alerts in sample forecast
                    assert call_args[0][2] == 1800

    @pytest.mark.asyncio
    async def test_weather_cache_hit(self, weather_agent, sample_weather_request):
        """Test weather cache hit scenario."""
        cached_response = WeatherSearchResponse(
            forecast=WeatherForecast(
                location=WeatherLocation(
                    name="Paris, France",
                    latitude=48.8566,
                    longitude=2.3522,
                    timezone="Europe/Paris",
                ),
                current=None,
                hourly=[],
                daily=[],
                alerts=[],
            ),
            historical_data=[],
            search_time_ms=50,
            cached=True,
            data_source="OpenWeatherMap",
        )

        with patch.object(
            weather_agent.cache_manager, "get_weather_cache", return_value=cached_response
        ) as mock_get_cache:
            with patch.object(
                weather_agent.openweather_client, "get_weather_forecast"
            ) as mock_forecast:
                request_data = sample_weather_request.model_dump()
                result = await weather_agent.process(request_data)

                # Verify cached result was returned
                assert result == cached_response
                assert result.cached is True

                # Verify API was not called
                mock_forecast.assert_not_called()

                # Verify cache was checked
                mock_get_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_activity_recommendations_default(self, weather_agent, sample_weather_data):
        """Test activity recommendations with default activity types."""
        recommendations = await weather_agent.get_activity_recommendations(sample_weather_data)

        assert len(recommendations) > 0
        assert all(hasattr(rec, "activity_type") for rec in recommendations)
        assert all(hasattr(rec, "suitability_score") for rec in recommendations)
        assert all(hasattr(rec, "recommendation") for rec in recommendations)
        assert all(0 <= rec.suitability_score <= 1 for rec in recommendations)

        # Check that recommendations are sorted by score
        scores = [rec.suitability_score for rec in recommendations]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_get_activity_recommendations_specific_types(
        self, weather_agent, sample_weather_data
    ):
        """Test activity recommendations with specific activity types."""
        activity_types = ["museums_indoor", "outdoor_sightseeing"]

        recommendations = await weather_agent.get_activity_recommendations(
            sample_weather_data, activity_types
        )

        assert len(recommendations) == 2
        activity_names = [rec.activity_type for rec in recommendations]
        assert "museums_indoor" in activity_names
        assert "outdoor_sightseeing" in activity_names

    @pytest.mark.asyncio
    async def test_get_activity_recommendations_empty_weather_data(self, weather_agent):
        """Test activity recommendations with empty weather data."""
        recommendations = await weather_agent.get_activity_recommendations([])

        # Should return recommendations but with 0 suitability scores
        assert len(recommendations) > 0
        assert all(rec.suitability_score == 0 for rec in recommendations)

    @pytest.mark.asyncio
    async def test_assess_travel_impact_low_risk(self, weather_agent):
        """Test travel impact assessment with good weather."""
        good_weather = [
            WeatherData(
                timestamp=datetime.now(UTC),
                temperature=22.0,
                feels_like=24.0,
                humidity=60.0,
                pressure=1015.0,
                visibility=15.0,
                wind_speed=10.0,
                wind_direction=90,
                precipitation=0.0,
                precipitation_probability=0.1,
                condition=WeatherCondition.CLEAR,
                condition_description="Clear sky",
                uv_index=5.0,
            )
        ]

        impact = await weather_agent.assess_travel_impact(good_weather)

        assert impact["overall_impact"] == "low"
        assert len(impact["risk_factors"]) == 0
        assert len(impact["critical_periods"]) == 0

    @pytest.mark.asyncio
    async def test_assess_travel_impact_high_risk(self, weather_agent):
        """Test travel impact assessment with extreme weather."""
        extreme_weather = [
            WeatherData(
                timestamp=datetime.now(UTC),
                temperature=-15.0,  # Extreme cold
                feels_like=-20.0,
                humidity=90.0,
                pressure=980.0,
                visibility=1.0,  # Poor visibility
                wind_speed=80.0,  # Strong winds
                wind_direction=270,
                precipitation=10.0,
                precipitation_probability=0.95,
                condition=WeatherCondition.HEAVY_SNOW,
                condition_description="Heavy snow",
                uv_index=0.0,
            )
        ]

        impact = await weather_agent.assess_travel_impact(extreme_weather)

        assert impact["overall_impact"] == "high"
        assert len(impact["risk_factors"]) > 0
        assert len(impact["critical_periods"]) > 0
        assert len(impact["recommendations"]) > 0
        assert "indoor activities" in " ".join(impact["recommendations"]).lower()

    @pytest.mark.asyncio
    async def test_assess_travel_impact_moderate_risk(self, weather_agent):
        """Test travel impact assessment with challenging weather."""
        challenging_weather = [
            WeatherData(
                timestamp=datetime.now(UTC),
                temperature=2.0,  # Cold but not extreme
                feels_like=-1.0,
                humidity=85.0,
                pressure=1005.0,
                visibility=3.0,
                wind_speed=45.0,  # Moderate winds
                wind_direction=180,
                precipitation=5.0,
                precipitation_probability=0.8,
                condition=WeatherCondition.RAIN,
                condition_description="Rain",
                uv_index=1.0,
            )
        ]

        impact = await weather_agent.assess_travel_impact(challenging_weather)

        assert impact["overall_impact"] == "moderate"
        assert len(impact["risk_factors"]) > 0

    def test_calculate_activity_suitability_outdoor(self, weather_agent):
        """Test activity suitability calculation for outdoor activities."""
        good_weather = WeatherData(
            timestamp=datetime.now(UTC),
            temperature=20.0,  # Ideal temperature
            feels_like=22.0,
            humidity=65.0,
            pressure=1015.0,
            visibility=15.0,
            wind_speed=10.0,  # Light wind
            wind_direction=90,
            precipitation=0.0,
            precipitation_probability=0.1,  # Low rain chance
            condition=WeatherCondition.CLEAR,
            condition_description="Clear sky",
            uv_index=5.0,
        )

        score, factors = weather_agent._calculate_activity_suitability(
            "outdoor_sightseeing", good_weather
        )

        assert 0.8 <= score <= 1.0  # Should be high score
        assert "ideal_temperature" in factors
        assert "low_rain_chance" in factors

    def test_calculate_activity_suitability_indoor(self, weather_agent):
        """Test activity suitability calculation for indoor activities."""
        rainy_weather = WeatherData(
            timestamp=datetime.now(UTC),
            temperature=10.0,
            feels_like=8.0,
            humidity=90.0,
            pressure=1005.0,
            visibility=5.0,
            wind_speed=30.0,
            wind_direction=270,
            precipitation=8.0,
            precipitation_probability=0.9,  # High rain chance
            condition=WeatherCondition.HEAVY_RAIN,
            condition_description="Heavy rain",
            uv_index=1.0,
        )

        score, factors = weather_agent._calculate_activity_suitability(
            "museums_indoor", rainy_weather
        )

        assert score >= 0.8  # Indoor activities should score well in bad weather
        assert "rain_makes_indoor_attractive" in factors

    def test_calculate_activity_suitability_beach(self, weather_agent):
        """Test activity suitability calculation for beach activities."""
        perfect_beach_weather = WeatherData(
            timestamp=datetime.now(UTC),
            temperature=28.0,  # Perfect beach temperature
            feels_like=30.0,
            humidity=70.0,
            pressure=1018.0,
            visibility=15.0,
            wind_speed=15.0,
            wind_direction=120,
            precipitation=0.0,
            precipitation_probability=0.05,
            condition=WeatherCondition.CLEAR,
            condition_description="Clear sky",
            uv_index=7.0,
        )

        score, factors = weather_agent._calculate_activity_suitability(
            "beach_activities", perfect_beach_weather
        )

        assert score >= 0.8  # Should be excellent for beach
        assert "ideal_beach_temperature" in factors
        assert "good_beach_weather" in factors

    def test_is_extreme_weather_conditions(self, weather_agent):
        """Test extreme weather detection."""
        extreme_weather_cases = [
            WeatherData(
                timestamp=datetime.now(UTC),
                temperature=45.0,  # Extreme heat
                feels_like=50.0,
                humidity=30.0,
                pressure=1020.0,
                visibility=10.0,
                wind_speed=20.0,
                wind_direction=90,
                precipitation=0.0,
                precipitation_probability=0.0,
                condition=WeatherCondition.CLEAR,
                condition_description="Extreme heat",
                uv_index=11.0,
            ),
            WeatherData(
                timestamp=datetime.now(UTC),
                temperature=5.0,
                feels_like=2.0,
                humidity=95.0,
                pressure=950.0,
                visibility=0.5,
                wind_speed=100.0,  # Extreme winds
                wind_direction=270,
                precipitation=20.0,
                precipitation_probability=1.0,
                condition=WeatherCondition.THUNDERSTORM,
                condition_description="Severe thunderstorm",
                uv_index=0.0,
            ),
        ]

        for weather in extreme_weather_cases:
            assert weather_agent._is_extreme_weather(weather) is True

    def test_is_challenging_weather_conditions(self, weather_agent):
        """Test challenging weather detection."""
        challenging_weather = WeatherData(
            timestamp=datetime.now(UTC),
            temperature=-2.0,  # Cold but not extreme
            feels_like=-5.0,
            humidity=85.0,
            pressure=1000.0,
            visibility=2.0,
            wind_speed=50.0,  # Strong but not extreme winds
            wind_direction=180,
            precipitation=5.0,
            precipitation_probability=0.8,
            condition=WeatherCondition.SNOW,
            condition_description="Snow",
            uv_index=0.0,
        )

        assert weather_agent._is_challenging_weather(challenging_weather) is True
        assert weather_agent._is_extreme_weather(challenging_weather) is False

    def test_generate_recommendation_text(self, weather_agent):
        """Test recommendation text generation."""
        # Test excellent conditions
        excellent_text = weather_agent._generate_recommendation_text(
            "outdoor_sightseeing", 0.9, ["ideal_temperature", "low_rain_chance"]
        )
        assert "Excellent conditions" in excellent_text
        assert "Outdoor Sightseeing" in excellent_text
        assert "ideal temperature" in excellent_text

        # Test challenging conditions
        poor_text = weather_agent._generate_recommendation_text(
            "hiking", 0.2, ["extreme_temperature", "high_rain_chance"]
        )
        assert "Challenging conditions" in poor_text
        assert "Hiking" in poor_text

"""OpenWeatherMap API client for weather data."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from travel_companion.core.config import get_settings
from travel_companion.models.external import (
    WeatherAlert,
    WeatherCondition,
    WeatherData,
    WeatherForecast,
    WeatherLocation,
    WeatherSearchRequest,
    WeatherSeverity,
)


class OpenWeatherMapCurrent(BaseModel):
    """OpenWeatherMap current weather response model."""

    dt: int = Field(..., description="Timestamp")
    sunrise: int | None = Field(None, description="Sunrise timestamp")
    sunset: int | None = Field(None, description="Sunset timestamp")
    temp: float = Field(..., description="Temperature")
    feels_like: float = Field(..., description="Feels like temperature")
    pressure: int = Field(..., description="Atmospheric pressure")
    humidity: int = Field(..., description="Humidity percentage")
    dew_point: float | None = Field(None, description="Dew point")
    uvi: float | None = Field(None, description="UV index")
    clouds: int = Field(..., description="Cloud coverage percentage")
    visibility: int | None = Field(None, description="Visibility in meters")
    wind_speed: float = Field(..., description="Wind speed")
    wind_deg: int | None = Field(None, description="Wind direction")
    rain: dict[str, float] | None = Field(None, description="Rain data")
    snow: dict[str, float] | None = Field(None, description="Snow data")
    weather: list[dict[str, Any]] = Field(..., description="Weather conditions")


class OpenWeatherMapHourly(BaseModel):
    """OpenWeatherMap hourly forecast model."""

    dt: int = Field(..., description="Timestamp")
    temp: float = Field(..., description="Temperature")
    feels_like: float = Field(..., description="Feels like temperature")
    pressure: int = Field(..., description="Atmospheric pressure")
    humidity: int = Field(..., description="Humidity percentage")
    dew_point: float = Field(..., description="Dew point")
    uvi: float = Field(..., description="UV index")
    clouds: int = Field(..., description="Cloud coverage percentage")
    visibility: int | None = Field(None, description="Visibility in meters")
    wind_speed: float = Field(..., description="Wind speed")
    wind_deg: int | None = Field(None, description="Wind direction")
    rain: dict[str, float] | None = Field(None, description="Rain data")
    snow: dict[str, float] | None = Field(None, description="Snow data")
    weather: list[dict[str, Any]] = Field(..., description="Weather conditions")
    pop: float = Field(..., description="Probability of precipitation")


class OpenWeatherMapDaily(BaseModel):
    """OpenWeatherMap daily forecast model."""

    dt: int = Field(..., description="Timestamp")
    sunrise: int = Field(..., description="Sunrise timestamp")
    sunset: int = Field(..., description="Sunset timestamp")
    moonrise: int | None = Field(None, description="Moonrise timestamp")
    moonset: int | None = Field(None, description="Moonset timestamp")
    temp: dict[str, float] = Field(..., description="Temperature data")
    feels_like: dict[str, float] = Field(..., description="Feels like temperature")
    pressure: int = Field(..., description="Atmospheric pressure")
    humidity: int = Field(..., description="Humidity percentage")
    dew_point: float = Field(..., description="Dew point")
    wind_speed: float = Field(..., description="Wind speed")
    wind_deg: int | None = Field(None, description="Wind direction")
    weather: list[dict[str, Any]] = Field(..., description="Weather conditions")
    clouds: int = Field(..., description="Cloud coverage percentage")
    pop: float = Field(..., description="Probability of precipitation")
    rain: float | None = Field(None, description="Rain volume")
    snow: float | None = Field(None, description="Snow volume")
    uvi: float = Field(..., description="UV index")


class OpenWeatherMapAlert(BaseModel):
    """OpenWeatherMap weather alert model."""

    sender_name: str = Field(..., description="Alert sender")
    event: str = Field(..., description="Alert event type")
    start: int = Field(..., description="Alert start timestamp")
    end: int = Field(..., description="Alert end timestamp")
    description: str = Field(..., description="Alert description")
    tags: list[str] = Field(default_factory=list, description="Alert tags")


class OpenWeatherMapResponse(BaseModel):
    """OpenWeatherMap One Call API response model."""

    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    timezone: str = Field(..., description="Timezone")
    timezone_offset: int = Field(..., description="Timezone offset")
    current: OpenWeatherMapCurrent | None = Field(None, description="Current weather")
    hourly: list[OpenWeatherMapHourly] = Field(default_factory=list, description="Hourly forecast")
    daily: list[OpenWeatherMapDaily] = Field(default_factory=list, description="Daily forecast")
    alerts: list[OpenWeatherMapAlert] = Field(default_factory=list, description="Weather alerts")


class OpenWeatherMapAPIClient:
    """OpenWeatherMap API client for weather forecasts."""

    def __init__(self):
        """Initialize OpenWeatherMap API client."""
        self.settings = get_settings()
        self.logger = logging.getLogger("travel_companion.services.external_apis.openweather")

        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.api_key = self.settings.openweather_api_key

        # Request configuration
        self.timeout = 30.0
        self.max_retries = 3
        self.retry_delay = 1.0

        self.logger.info("OpenWeatherMap API client initialized")

    async def get_weather_forecast(self, request: WeatherSearchRequest) -> WeatherForecast:
        """Get weather forecast for a location and date range.
        
        Args:
            request: Weather search request with location and dates
            
        Returns:
            Weather forecast data
            
        Raises:
            httpx.HTTPError: If API request fails
            ValueError: If location cannot be geocoded
        """
        try:
            # Get coordinates if not provided
            if request.latitude is None or request.longitude is None:
                coordinates = await self._geocode_location(request.location)
                lat, lon = coordinates["lat"], coordinates["lon"]
            else:
                lat, lon = request.latitude, request.longitude

            # Get weather data from One Call API
            weather_data = await self._get_onecall_data(lat, lon, request.include_alerts)

            # Convert to our weather models
            forecast = self._convert_to_forecast(weather_data, request.location)

            self.logger.info(f"Retrieved weather forecast for {request.location}")
            return forecast

        except Exception as e:
            self.logger.error(f"Failed to get weather forecast for {request.location}: {e}")
            raise

    async def get_historical_weather(
        self,
        lat: float,
        lon: float,
        start_timestamp: int,
        end_timestamp: int
    ) -> list[WeatherData]:
        """Get historical weather data for a location and time range.
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate  
            start_timestamp: Start timestamp (Unix time)
            end_timestamp: End timestamp (Unix time)
            
        Returns:
            List of historical weather data points
            
        Note:
            Historical data is only available for dates up to 5 days ago
            and requires a paid OpenWeatherMap subscription.
        """
        try:
            historical_data = []
            current_time = start_timestamp

            # Historical API requires separate calls for each day
            while current_time <= end_timestamp:
                try:
                    daily_data = await self._get_historical_data(lat, lon, current_time)
                    if daily_data and daily_data.current:
                        weather_point = self._convert_current_weather(daily_data.current)
                        historical_data.append(weather_point)
                except Exception as e:
                    self.logger.warning(f"Failed to get historical data for timestamp {current_time}: {e}")

                # Move to next day (86400 seconds = 1 day)
                current_time += 86400

            self.logger.info(f"Retrieved {len(historical_data)} historical weather data points")
            return historical_data

        except Exception as e:
            self.logger.error(f"Failed to get historical weather data: {e}")
            raise

    async def _get_historical_data(self, lat: float, lon: float, timestamp: int) -> OpenWeatherMapResponse:
        """Get historical weather data for a specific timestamp.
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            timestamp: Unix timestamp
            
        Returns:
            OpenWeatherMap historical response
        """
        url = f"{self.base_url}/onecall/timemachine"
        params = {
            "lat": lat,
            "lon": lon,
            "dt": timestamp,
            "appid": self.api_key,
            "units": "metric"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.get(url, params=params)
                    response.raise_for_status()

                    data = response.json()
                    return OpenWeatherMapResponse(**data)

                except httpx.HTTPError as e:
                    if attempt == self.max_retries - 1:
                        raise
                    self.logger.warning(f"Historical API request failed, retrying in {self.retry_delay}s: {e}")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

    async def _geocode_location(self, location: str) -> dict[str, float]:
        """Geocode location name to coordinates.
        
        Args:
            location: Location name to geocode
            
        Returns:
            Dictionary with lat and lon coordinates
        """
        url = "http://api.openweathermap.org/geo/1.0/direct"
        params = {
            "q": location,
            "limit": 1,
            "appid": self.api_key
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            if not data:
                raise ValueError(f"Location not found: {location}")

            location_data = data[0]
            return {
                "lat": location_data["lat"],
                "lon": location_data["lon"],
                "name": location_data.get("name", location),
                "country": location_data.get("country")
            }

    async def _get_onecall_data(self, lat: float, lon: float, include_alerts: bool = True) -> OpenWeatherMapResponse:
        """Get One Call API data for coordinates.
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            include_alerts: Whether to include weather alerts
            
        Returns:
            OpenWeatherMap One Call API response
        """
        url = f"{self.base_url}/onecall"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",  # Use Celsius
            "exclude": "minutely"  # Exclude minutely data to reduce response size
        }

        if not include_alerts:
            params["exclude"] += ",alerts"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.get(url, params=params)
                    response.raise_for_status()

                    data = response.json()
                    return OpenWeatherMapResponse(**data)

                except httpx.HTTPError as e:
                    if attempt == self.max_retries - 1:
                        raise
                    self.logger.warning(f"API request failed, retrying in {self.retry_delay}s: {e}")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

    def _convert_to_forecast(self, data: OpenWeatherMapResponse, location_name: str) -> WeatherForecast:
        """Convert OpenWeatherMap response to our weather forecast model.
        
        Args:
            data: OpenWeatherMap API response
            location_name: Original location name from request
            
        Returns:
            Weather forecast in our format
        """
        # Create location info
        location = WeatherLocation(
            name=location_name,
            latitude=data.lat,
            longitude=data.lon,
            timezone=data.timezone
        )

        # Convert current weather
        current = None
        if data.current:
            current = self._convert_current_weather(data.current)

        # Convert hourly forecast
        hourly = [self._convert_hourly_weather(hour) for hour in data.hourly[:48]]  # Limit to 48 hours

        # Convert daily forecast
        daily = [self._convert_daily_weather(day) for day in data.daily[:7]]  # Limit to 7 days

        # Convert alerts
        alerts = [self._convert_alert(alert) for alert in data.alerts]

        return WeatherForecast(
            location=location,
            current=current,
            hourly=hourly,
            daily=daily,
            alerts=alerts
        )

    def _convert_current_weather(self, current: OpenWeatherMapCurrent) -> WeatherData:
        """Convert current weather data."""
        return WeatherData(
            timestamp=datetime.fromtimestamp(current.dt, tz=UTC),
            temperature=current.temp,
            feels_like=current.feels_like,
            humidity=current.humidity,
            pressure=current.pressure,
            visibility=current.visibility / 1000 if current.visibility else 10.0,  # Convert m to km
            wind_speed=current.wind_speed * 3.6,  # Convert m/s to km/h
            wind_direction=current.wind_deg or 0,
            precipitation=self._get_precipitation_amount(current.rain, current.snow),
            precipitation_probability=0.0,  # Not available in current weather
            condition=self._map_weather_condition(current.weather[0]["main"]),
            condition_description=current.weather[0]["description"],
            uv_index=current.uvi
        )

    def _convert_hourly_weather(self, hourly: OpenWeatherMapHourly) -> WeatherData:
        """Convert hourly weather data."""
        return WeatherData(
            timestamp=datetime.fromtimestamp(hourly.dt, tz=UTC),
            temperature=hourly.temp,
            feels_like=hourly.feels_like,
            humidity=hourly.humidity,
            pressure=hourly.pressure,
            visibility=hourly.visibility / 1000 if hourly.visibility else 10.0,  # Convert m to km
            wind_speed=hourly.wind_speed * 3.6,  # Convert m/s to km/h
            wind_direction=hourly.wind_deg or 0,
            precipitation=self._get_precipitation_amount(hourly.rain, hourly.snow),
            precipitation_probability=hourly.pop,
            condition=self._map_weather_condition(hourly.weather[0]["main"]),
            condition_description=hourly.weather[0]["description"],
            uv_index=hourly.uvi
        )

    def _convert_daily_weather(self, daily: OpenWeatherMapDaily) -> WeatherData:
        """Convert daily weather data."""
        return WeatherData(
            timestamp=datetime.fromtimestamp(daily.dt, tz=UTC),
            temperature=daily.temp["day"],
            feels_like=daily.feels_like["day"],
            humidity=daily.humidity,
            pressure=daily.pressure,
            visibility=10.0,  # Default visibility for daily data
            wind_speed=daily.wind_speed * 3.6,  # Convert m/s to km/h
            wind_direction=daily.wind_deg or 0,
            precipitation=daily.rain or daily.snow or 0,
            precipitation_probability=daily.pop,
            condition=self._map_weather_condition(daily.weather[0]["main"]),
            condition_description=daily.weather[0]["description"],
            uv_index=daily.uvi
        )

    def _convert_alert(self, alert: OpenWeatherMapAlert) -> WeatherAlert:
        """Convert weather alert data."""
        severity = self._map_alert_severity(alert.event.lower())

        return WeatherAlert(
            title=alert.event,
            description=alert.description,
            severity=severity,
            start_time=datetime.fromtimestamp(alert.start, tz=UTC),
            end_time=datetime.fromtimestamp(alert.end, tz=UTC),
            regions=alert.tags
        )

    def _map_weather_condition(self, condition: str) -> WeatherCondition:
        """Map OpenWeatherMap condition to our weather condition enum."""
        condition_mapping = {
            "Clear": WeatherCondition.CLEAR,
            "Clouds": WeatherCondition.CLOUDY,
            "Drizzle": WeatherCondition.LIGHT_RAIN,
            "Rain": WeatherCondition.RAIN,
            "Thunderstorm": WeatherCondition.THUNDERSTORM,
            "Snow": WeatherCondition.SNOW,
            "Mist": WeatherCondition.MIST,
            "Smoke": WeatherCondition.FOG,
            "Haze": WeatherCondition.MIST,
            "Dust": WeatherCondition.FOG,
            "Fog": WeatherCondition.FOG,
            "Sand": WeatherCondition.FOG,
            "Ash": WeatherCondition.FOG,
            "Squall": WeatherCondition.WIND,
            "Tornado": WeatherCondition.WIND,
        }

        return condition_mapping.get(condition, WeatherCondition.UNKNOWN)

    def _map_alert_severity(self, event: str) -> WeatherSeverity:
        """Map alert event type to severity level."""
        if any(keyword in event for keyword in ["extreme", "hurricane", "tornado"]):
            return WeatherSeverity.EXTREME
        elif any(keyword in event for keyword in ["severe", "warning", "watch"]):
            return WeatherSeverity.HIGH
        elif any(keyword in event for keyword in ["advisory", "caution"]):
            return WeatherSeverity.MODERATE
        else:
            return WeatherSeverity.LOW

    def _get_precipitation_amount(self, rain: dict[str, float] | None, snow: dict[str, float] | None) -> float:
        """Get total precipitation amount from rain and snow data."""
        total = 0.0
        if rain:
            total += rain.get("1h", 0)
        if snow:
            total += snow.get("1h", 0)
        return total

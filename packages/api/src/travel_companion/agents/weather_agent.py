"""Weather intelligence agent for travel planning."""

from datetime import datetime, timedelta
from typing import Any

from travel_companion.agents.base import BaseAgent
from travel_companion.models.external import (
    ActivityRecommendation,
    WeatherCondition,
    WeatherData,
    WeatherSearchRequest,
    WeatherSearchResponse,
)
from travel_companion.services.cache import CacheManager
from travel_companion.services.external_apis.openweather import OpenWeatherMapAPIClient


class WeatherAgent(BaseAgent[WeatherSearchResponse]):
    """Agent for weather forecasting and activity impact analysis."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize weather agent with API client."""
        super().__init__(**kwargs)

        self.openweather_client = OpenWeatherMapAPIClient()
        self.cache_manager = CacheManager(self.redis)

        self.logger.info(
            "Weather agent initialized with OpenWeatherMap API client and cache manager"
        )

    @property
    def agent_name(self) -> str:
        """Name of the agent for logging and identification."""
        return "weather_agent"

    @property
    def agent_version(self) -> str:
        """Version of the agent for compatibility and debugging."""
        return "1.0.0"

    async def process(self, request_data: dict[str, Any]) -> WeatherSearchResponse:
        """Process weather search request and return forecast data.

        Args:
            request_data: Weather search parameters

        Returns:
            WeatherSearchResponse with forecast data
        """
        start_time = datetime.now()

        try:
            # Validate request data
            search_request = WeatherSearchRequest(**request_data)

            self.logger.info(f"Processing weather search request for {search_request.location}")

            # Check cache first
            cache_key = self._generate_cache_key(search_request)
            cached_response = await self.cache_manager.get_weather_cache(cache_key)
            if cached_response:
                self.logger.info(f"Returning cached weather data for {search_request.location}")
                return cached_response

            # Get weather forecast from OpenWeatherMap
            forecast = await self.openweather_client.get_weather_forecast(search_request)

            # Get historical weather data if requested
            historical_data = []
            if search_request.include_historical:
                try:
                    # Calculate historical data timestamps (past 5 days from start_date)
                    historical_start = int(
                        (search_request.start_date - timedelta(days=5)).timestamp()
                    )
                    historical_end = int(search_request.start_date.timestamp())

                    # Get coordinates from forecast location
                    lat = forecast.location.latitude
                    lon = forecast.location.longitude

                    historical_data = await self.openweather_client.get_historical_weather(
                        lat, lon, historical_start, historical_end
                    )

                    self.logger.info(
                        f"Retrieved {len(historical_data)} historical weather data points"
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to get historical weather data: {e}")
                    # Continue without historical data

            # Create response
            search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            response = WeatherSearchResponse(
                forecast=forecast,
                historical_data=historical_data,
                search_time_ms=search_time_ms,
                search_metadata={
                    "location": search_request.location,
                    "start_date": search_request.start_date.isoformat(),
                    "end_date": search_request.end_date.isoformat(),
                    "include_alerts": search_request.include_alerts,
                    "include_historical": search_request.include_historical,
                },
                data_source="OpenWeatherMap",
            )

            self.logger.info(
                f"Weather search completed for {search_request.location}: "
                f"{len(forecast.daily)} daily forecasts, {len(forecast.alerts)} alerts, "
                f"{len(historical_data)} historical data points"
            )

            # Cache the response for 1-3 hours
            cache_ttl = 3600  # 1 hour default

            # Adjust cache TTL based on data type
            if search_request.include_historical:
                cache_ttl = 10800  # 3 hours for historical data (changes less frequently)
            elif len(forecast.alerts) > 0:
                cache_ttl = 1800  # 30 minutes if there are weather alerts (more volatile)

            await self.cache_manager.set_weather_cache(cache_key, response, cache_ttl)

            return response

        except Exception as e:
            self.logger.error(f"Weather search failed: {e}")
            raise

    async def get_activity_recommendations(
        self, weather_data: list[WeatherData], activity_types: list[str] | None = None
    ) -> list[ActivityRecommendation]:
        """Generate activity recommendations based on weather conditions.

        Args:
            weather_data: List of weather data points
            activity_types: Optional list of specific activity types to analyze

        Returns:
            List of weather-based activity recommendations
        """
        try:
            if activity_types is None:
                activity_types = [
                    "outdoor_sightseeing",
                    "museums_indoor",
                    "walking_tours",
                    "beach_activities",
                    "hiking",
                    "shopping",
                    "restaurants",
                    "water_sports",
                    "winter_sports",
                    "photography",
                ]

            recommendations = []

            for activity_type in activity_types:
                # Calculate average suitability across weather period
                suitability_scores = []
                weather_factors = []

                for weather in weather_data:
                    score, factors = self._calculate_activity_suitability(activity_type, weather)
                    suitability_scores.append(score)
                    weather_factors.extend(factors)

                avg_score = (
                    sum(suitability_scores) / len(suitability_scores) if suitability_scores else 0
                )
                unique_factors = list(set(weather_factors))

                recommendation = self._generate_recommendation_text(
                    activity_type, avg_score, unique_factors
                )

                recommendations.append(
                    ActivityRecommendation(
                        activity_type=activity_type,
                        suitability_score=avg_score,
                        recommendation=recommendation,
                        weather_factors=unique_factors,
                    )
                )

            # Sort by suitability score descending
            recommendations.sort(key=lambda x: x.suitability_score, reverse=True)

            self.logger.info(f"Generated {len(recommendations)} activity recommendations")
            return recommendations

        except Exception as e:
            self.logger.error(f"Failed to generate activity recommendations: {e}")
            raise

    def _generate_cache_key(self, request: WeatherSearchRequest) -> str:
        """Generate cache key for weather search request.

        Args:
            request: Weather search request

        Returns:
            Cache key string
        """
        import hashlib

        # Create cache key from request parameters
        key_parts = [
            "weather_agent",
            request.location.lower().replace(" ", "_").replace(",", ""),
            request.start_date.strftime("%Y%m%d"),
            request.end_date.strftime("%Y%m%d"),
            str(request.include_alerts).lower(),
            str(request.include_historical).lower(),
        ]

        # Add coordinates if provided
        if request.latitude is not None and request.longitude is not None:
            key_parts.extend([f"lat{request.latitude:.4f}", f"lon{request.longitude:.4f}"])

        cache_key = ":".join(key_parts)

        # Hash the key if it's too long to ensure compatibility
        if len(cache_key) > 200:
            cache_key_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_key = f"weather_agent:hashed:{cache_key_hash}"

        return cache_key

    async def assess_travel_impact(self, weather_data: list[WeatherData]) -> dict[str, Any]:
        """Assess weather impact on travel plans.

        Args:
            weather_data: List of weather data points

        Returns:
            Dictionary with travel impact assessment
        """
        try:
            impact_assessment = {
                "overall_impact": "low",
                "risk_factors": [],
                "recommendations": [],
                "critical_periods": [],
                "alternative_suggestions": [],
            }

            for weather in weather_data:
                # Check for high impact conditions
                if self._is_extreme_weather(weather):
                    impact_assessment["overall_impact"] = "high"
                    impact_assessment["risk_factors"].append(
                        f"Extreme weather: {weather.condition_description} on {weather.timestamp.date()}"
                    )
                    impact_assessment["critical_periods"].append(
                        {
                            "date": weather.timestamp.isoformat(),
                            "condition": weather.condition_description,
                            "temperature": weather.temperature,
                            "precipitation_probability": weather.precipitation_probability,
                        }
                    )

                # Check for moderate impact conditions
                elif self._is_challenging_weather(weather):
                    if impact_assessment["overall_impact"] == "low":
                        impact_assessment["overall_impact"] = "moderate"
                    impact_assessment["risk_factors"].append(
                        f"Challenging conditions: {weather.condition_description} on {weather.timestamp.date()}"
                    )

            # Generate recommendations based on impact
            if impact_assessment["overall_impact"] == "high":
                impact_assessment["recommendations"].extend(
                    [
                        "Consider indoor activities during extreme weather periods",
                        "Pack appropriate protective clothing",
                        "Monitor weather alerts closely",
                        "Have backup plans for outdoor activities",
                    ]
                )
                impact_assessment["alternative_suggestions"].extend(
                    [
                        "Museums and indoor attractions",
                        "Shopping centers and malls",
                        "Indoor dining experiences",
                        "Cultural venues and theaters",
                    ]
                )
            elif impact_assessment["overall_impact"] == "moderate":
                impact_assessment["recommendations"].extend(
                    [
                        "Pack weather-appropriate clothing",
                        "Plan flexible schedules for outdoor activities",
                        "Consider covered or indoor alternatives",
                    ]
                )

            self.logger.info(
                f"Travel impact assessment: {impact_assessment['overall_impact']} impact"
            )
            return impact_assessment

        except Exception as e:
            self.logger.error(f"Failed to assess travel impact: {e}")
            raise

    def _calculate_activity_suitability(
        self, activity_type: str, weather: WeatherData
    ) -> tuple[float, list[str]]:
        """Calculate weather suitability score for an activity type.

        Args:
            activity_type: Type of activity to assess
            weather: Weather data point

        Returns:
            Tuple of (suitability_score, weather_factors)
        """
        factors = []

        # Base suitability rules by activity type
        if activity_type in ["outdoor_sightseeing", "walking_tours", "photography"]:
            score = self._score_outdoor_activity(weather, factors)
        elif activity_type in ["museums_indoor", "shopping", "restaurants"]:
            score = self._score_indoor_activity(weather, factors)
        elif activity_type in ["beach_activities", "water_sports"]:
            score = self._score_beach_activity(weather, factors)
        elif activity_type == "hiking":
            score = self._score_hiking_activity(weather, factors)
        elif activity_type == "winter_sports":
            score = self._score_winter_sports(weather, factors)
        else:
            # Default outdoor activity scoring
            score = self._score_outdoor_activity(weather, factors)

        return max(0.0, min(1.0, score)), factors

    def _score_outdoor_activity(self, weather: WeatherData, factors: list[str]) -> float:
        """Score suitability for outdoor activities."""
        score = 0.7  # Base score

        # Temperature scoring
        if 15 <= weather.temperature <= 25:
            score += 0.2
            factors.append("ideal_temperature")
        elif 10 <= weather.temperature < 15 or 25 < weather.temperature <= 30:
            score += 0.1
            factors.append("acceptable_temperature")
        elif weather.temperature < 5 or weather.temperature > 35:
            score -= 0.3
            factors.append("extreme_temperature")

        # Precipitation scoring
        if weather.precipitation_probability < 0.2:
            score += 0.1
            factors.append("low_rain_chance")
        elif weather.precipitation_probability > 0.7:
            score -= 0.4
            factors.append("high_rain_chance")

        # Wind scoring
        if weather.wind_speed > 50:  # km/h
            score -= 0.2
            factors.append("strong_winds")

        return score

    def _score_indoor_activity(self, weather: WeatherData, factors: list[str]) -> float:
        """Score suitability for indoor activities."""
        score = 0.8  # Base score - always good for indoor

        # Indoor activities are better when outdoor conditions are poor
        if weather.precipitation_probability > 0.5:
            score += 0.1
            factors.append("rain_makes_indoor_attractive")

        if weather.temperature < 5 or weather.temperature > 35:
            score += 0.1
            factors.append("extreme_temperature_favors_indoor")

        return score

    def _score_beach_activity(self, weather: WeatherData, factors: list[str]) -> float:
        """Score suitability for beach activities."""
        score = 0.5  # Base score

        # Temperature is critical for beach activities
        if 22 <= weather.temperature <= 32:
            score += 0.3
            factors.append("ideal_beach_temperature")
        elif weather.temperature < 18:
            score -= 0.4
            factors.append("too_cold_for_beach")

        # Clear skies preferred
        if weather.condition in [WeatherCondition.CLEAR, WeatherCondition.PARTLY_CLOUDY]:
            score += 0.2
            factors.append("good_beach_weather")
        elif weather.condition in [WeatherCondition.RAIN, WeatherCondition.THUNDERSTORM]:
            score -= 0.5
            factors.append("rain_unsuitable_for_beach")

        # UV considerations
        if weather.uv_index and weather.uv_index > 8:
            score -= 0.1
            factors.append("high_uv_caution")

        return score

    def _score_hiking_activity(self, weather: WeatherData, factors: list[str]) -> float:
        """Score suitability for hiking activities."""
        score = 0.6  # Base score

        # Temperature range for hiking
        if 10 <= weather.temperature <= 20:
            score += 0.2
            factors.append("ideal_hiking_temperature")
        elif weather.temperature < 0 or weather.temperature > 30:
            score -= 0.3
            factors.append("challenging_hiking_temperature")

        # Precipitation and trail conditions
        if weather.precipitation_probability > 0.6:
            score -= 0.3
            factors.append("rain_makes_trails_dangerous")

        # Visibility important for safety
        if weather.visibility < 1.0:  # km
            score -= 0.4
            factors.append("poor_visibility_unsafe")

        return score

    def _score_winter_sports(self, weather: WeatherData, factors: list[str]) -> float:
        """Score suitability for winter sports."""
        score = 0.3  # Base score - depends on conditions

        # Temperature needs to be cold
        if weather.temperature < 0:
            score += 0.4
            factors.append("cold_temperature_for_snow_sports")
        elif weather.temperature > 5:
            score -= 0.2
            factors.append("too_warm_for_winter_sports")

        # Snow conditions
        if weather.condition in [WeatherCondition.SNOW, WeatherCondition.HEAVY_SNOW]:
            score += 0.3
            factors.append("active_snowfall")

        return score

    def _is_extreme_weather(self, weather: WeatherData) -> bool:
        """Check if weather conditions are extreme."""
        return (
            weather.condition
            in [
                WeatherCondition.THUNDERSTORM,
                WeatherCondition.HEAVY_RAIN,
                WeatherCondition.HEAVY_SNOW,
            ]
            or weather.temperature < -10
            or weather.temperature > 40
            or weather.wind_speed > 70  # km/h
            or weather.precipitation_probability > 0.9
        )

    def _is_challenging_weather(self, weather: WeatherData) -> bool:
        """Check if weather conditions are challenging but not extreme."""
        return (
            weather.condition
            in [WeatherCondition.RAIN, WeatherCondition.SNOW, WeatherCondition.FOG]
            or weather.temperature < 0
            or weather.temperature > 35
            or weather.wind_speed > 40  # km/h
            or weather.precipitation_probability > 0.7
        )

    def _generate_recommendation_text(
        self, activity_type: str, score: float, factors: list[str]
    ) -> str:
        """Generate human-readable recommendation text."""
        if score >= 0.8:
            sentiment = "Excellent conditions"
        elif score >= 0.6:
            sentiment = "Good conditions"
        elif score >= 0.4:
            sentiment = "Fair conditions"
        else:
            sentiment = "Challenging conditions"

        activity_name = activity_type.replace("_", " ").title()

        recommendation = f"{sentiment} for {activity_name}."

        if factors:
            key_factors = factors[:3]  # Limit to top 3 factors
            factors_text = ", ".join(key_factors).replace("_", " ")
            recommendation += f" Key factors: {factors_text}."

        return recommendation

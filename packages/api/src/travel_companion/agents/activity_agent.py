"""Activity and attraction agent for travel planning."""

import asyncio
from datetime import datetime
from typing import Any, cast

from travel_companion.agents.base import BaseAgent
from travel_companion.models.external import (
    ActivityCategory,
    ActivityComparisonResult,
    ActivityOption,
    ActivitySearchRequest,
    ActivitySearchResponse,
)
from travel_companion.services.activity_cache import ActivityCacheManager
from travel_companion.services.activity_repository import ActivityRepository
from travel_companion.services.external_apis.google_places_client import GooglePlacesClient
from travel_companion.services.external_apis.geoapify import GeoapifyClient
from travel_companion.services.external_apis.getyourguide import GetYourGuideAPIClient
from travel_companion.services.external_apis.tripadvisor import TripAdvisorAPIClient
from travel_companion.services.external_apis.viator import ViatorAPIClient


class ActivityAgent(BaseAgent[ActivitySearchResponse]):
    """Agent for searching and ranking activities and attractions."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize activity agent with API clients, database, and cache."""
        super().__init__(**kwargs)

        # Initialize Google Places as primary provider
        self.google_places_client = GooglePlacesClient()

        # Keep other providers available but not used by default
        self.geoapify_client = GeoapifyClient()
        self.tripadvisor_client = TripAdvisorAPIClient()
        self.viator_client = ViatorAPIClient()
        self.getyourguide_client = GetYourGuideAPIClient()

        # Initialize database repository and cache manager
        self.repository = ActivityRepository(self.database)
        self.cache_manager = ActivityCacheManager(self.redis)

        self.logger.info("Activity agent initialized with API clients, database, and cache")

    @property
    def agent_name(self) -> str:
        """Name of the agent for logging and identification."""
        return "activity_agent"

    @property
    def agent_version(self) -> str:
        """Version of the agent for compatibility and debugging."""
        return "1.0.0"

    async def process(self, request_data: dict[str, Any]) -> ActivitySearchResponse:
        """Process activity search request and return ranked activities.

        Args:
            request_data: Activity search parameters

        Returns:
            ActivitySearchResponse with ranked activities
        """
        start_time = datetime.now()

        try:
            # Validate request data
            search_request = ActivitySearchRequest(**request_data)

            # Check advanced cache first
            cached_result = await self.cache_manager.get_search_results(search_request)
            if cached_result:
                return cached_result

            self.logger.info(f"Processing activity search request for {search_request.location}")

            # Search activities from all providers with fallback chain
            activities = await self._search_all_providers(search_request)

            # Rank and filter activities
            ranked_activities = await self._rank_activities(activities, search_request)

            # Create response
            search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            response = ActivitySearchResponse(
                activities=ranked_activities,
                total_results=len(ranked_activities),
                search_time_ms=search_time_ms,
                search_metadata={
                    "location": search_request.location,
                    "category": search_request.category,
                    "guest_count": search_request.guest_count,
                },
                cached=False,
                cache_expires_at=None,
            )

            # Cache the result with advanced caching
            await self.cache_manager.cache_search_results(search_request, response)

            # Persist activities to database if trip_id is provided
            if "trip_id" in request_data and ranked_activities:
                try:
                    trip_id = request_data["trip_id"]
                    await self.repository.insert_activity_options(ranked_activities, trip_id)
                    self.logger.debug(f"Persisted {len(ranked_activities)} activities to database")
                except Exception as e:
                    self.logger.warning(f"Failed to persist activities to database: {e}")
                    # Don't fail the request if database persistence fails

            self.logger.info(
                f"Activity search completed: {len(ranked_activities)} activities found"
            )

            return response

        except Exception as e:
            self.logger.error(f"Activity search failed: {e}")
            raise

    async def _search_all_providers(self, request: ActivitySearchRequest) -> list[ActivityOption]:
        """Search activities from all providers with fallback chain.

        Args:
            request: Activity search request

        Returns:
            List of activity options from all providers
        """
        activities: list[ActivityOption] = []

        # Use Google Places API as the primary provider
        search_tasks = [
            self._search_google_places(request),
        ]

        results = await asyncio.gather(*search_tasks, return_exceptions=True)

        for i, result in enumerate(results):
            provider_name = ["Google Places"][i]

            if isinstance(result, Exception):
                self.logger.warning(f"{provider_name} search failed: {result}")
            else:
                activities.extend(cast(list[ActivityOption], result))
                self.logger.info(
                    f"{provider_name} returned {len(cast(list[ActivityOption], result))} activities"
                )

        # Remove duplicates based on name and location similarity
        unique_activities = await self._deduplicate_activities(activities)

        self.logger.info(f"Total activities after deduplication: {len(unique_activities)}")

        return unique_activities

    async def _search_google_places(self, request: ActivitySearchRequest) -> list[ActivityOption]:
        """Search activities from Google Places API.

        Args:
            request: Activity search request

        Returns:
            List of Google Places activities
        """
        try:
            return await self.google_places_client.search_activities(request)
        except Exception as e:
            self.logger.warning(f"Google Places search failed: {e}")
            return []

    async def _search_geoapify(self, request: ActivitySearchRequest) -> list[ActivityOption]:
        """Search activities from Geoapify API.

        Args:
            request: Activity search request

        Returns:
            List of Geoapify activities
        """
        try:
            return await self.geoapify_client.search_activities(request)
        except Exception as e:
            self.logger.warning(f"Geoapify search failed: {e}")
            return []

    async def _search_tripadvisor(self, request: ActivitySearchRequest) -> list[ActivityOption]:
        """Search activities from TripAdvisor API.

        Args:
            request: Activity search request

        Returns:
            List of TripAdvisor activities
        """
        try:
            return await self.tripadvisor_client.search_activities(request)
        except Exception as e:
            self.logger.warning(f"TripAdvisor search failed: {e}")
            return []

    async def _search_viator(self, request: ActivitySearchRequest) -> list[ActivityOption]:
        """Search activities from Viator API.

        Args:
            request: Activity search request

        Returns:
            List of Viator activities
        """
        try:
            return await self.viator_client.search_activities(request)
        except Exception as e:
            self.logger.warning(f"Viator search failed: {e}")
            return []

    async def _search_getyourguide(self, request: ActivitySearchRequest) -> list[ActivityOption]:
        """Search activities from GetYourGuide API.

        Args:
            request: Activity search request

        Returns:
            List of GetYourGuide activities
        """
        try:
            return await self.getyourguide_client.search_activities(request)
        except Exception as e:
            self.logger.warning(f"GetYourGuide search failed: {e}")
            return []

    async def _deduplicate_activities(
        self, activities: list[ActivityOption]
    ) -> list[ActivityOption]:
        """Remove duplicate activities based on name and location similarity.

        Args:
            activities: List of all activities

        Returns:
            Deduplicated list of activities
        """
        if not activities:
            return []

        unique_activities: list[ActivityOption] = []
        seen_activities: set[str] = set()

        for activity in activities:
            # Create similarity key based on normalized name and location
            name_normalized = activity.name.lower().strip()
            location_key = f"{activity.location.latitude:.3f},{activity.location.longitude:.3f}"
            similarity_key = f"{name_normalized}:{location_key}"

            if similarity_key not in seen_activities:
                seen_activities.add(similarity_key)
                unique_activities.append(activity)
            else:
                self.logger.debug(f"Duplicate activity filtered: {activity.name}")

        return unique_activities

    async def _rank_activities(
        self, activities: list[ActivityOption], request: ActivitySearchRequest
    ) -> list[ActivityOption]:
        """Rank activities based on user preferences and criteria.

        Args:
            activities: List of activities to rank
            request: Original search request with preferences

        Returns:
            Ranked list of activities limited to max_results
        """
        if not activities:
            return []

        comparison_results: list[ActivityComparisonResult] = []

        for activity in activities:
            score = await self._calculate_activity_score(activity, request)

            comparison_result = ActivityComparisonResult(
                activity=activity,
                score=score.get("total_score", 50.0),
                price_rank=1,  # Will be calculated after sorting
                rating_rank=1,  # Will be calculated after sorting
                duration_preference_score=score.get("duration_score", 0.5),
                category_match_score=score.get("category_score", 0.5),
                reasons=score.get("reasons", []),
            )
            comparison_results.append(comparison_result)

        # Sort by total score (descending)
        comparison_results.sort(key=lambda x: x.score, reverse=True)

        # Calculate ranks after sorting
        await self._calculate_ranks(comparison_results)

        # Apply budget filtering
        if request.budget_per_person:
            comparison_results = [
                result
                for result in comparison_results
                if result.activity.price <= request.budget_per_person
            ]

        # Return top results
        top_results = comparison_results[: request.max_results]
        return [result.activity for result in top_results]

    async def _calculate_activity_score(
        self, activity: ActivityOption, request: ActivitySearchRequest
    ) -> dict[str, Any]:
        """Calculate comprehensive score for an activity.

        Args:
            activity: Activity to score
            request: Search request with preferences

        Returns:
            Dictionary with scoring details
        """
        score_components = {}
        reasons = []

        # Base score from rating (0-50 points)
        if activity.rating:
            rating_score = (activity.rating / 5.0) * 50
            score_components["rating_score"] = rating_score
            reasons.append(f"Rating: {activity.rating}/5.0")
        else:
            score_components["rating_score"] = 25  # Neutral score for unrated

        # Category match score (0-25 points)
        if request.category and activity.category == request.category:
            score_components["category_score"] = 25
            reasons.append(f"Perfect category match: {request.category}")
        else:
            score_components["category_score"] = 0

        # Duration preference score (0-15 points)
        duration_score = 0.0
        if request.duration_hours and activity.duration_minutes:
            requested_minutes = request.duration_hours * 60
            duration_diff = abs(activity.duration_minutes - requested_minutes)
            # Score based on how close to requested duration
            duration_score = max(0, 15 - (duration_diff / 60))  # Penalty per hour difference
            reasons.append(f"Duration: {activity.duration_minutes} min")

        score_components["duration_score"] = duration_score

        # Price value score (0-10 points, lower price = higher score within reason)
        if activity.price > 0:
            # Normalize price (assuming reasonable activity range $10-500)
            normalized_price = min(float(activity.price) / 500, 1.0)
            price_score = (1 - normalized_price) * 10
            score_components["price_score"] = price_score
            reasons.append(f"Price: ${activity.price}")
        else:
            score_components["price_score"] = 10  # Free activities get max price score

        # Calculate total score
        total_score = sum(score_components.values())

        return {
            "total_score": total_score,
            "components": score_components,
            "reasons": reasons,
            "duration_score": duration_score / 15 if duration_score > 0 else 0.5,
            "category_score": score_components["category_score"] / 25,
        }

    async def _calculate_ranks(self, comparison_results: list[ActivityComparisonResult]) -> None:
        """Calculate price and rating ranks for comparison results.

        Args:
            comparison_results: List of comparison results to rank (modified in place)
        """
        # Sort by price for price ranking
        price_sorted = sorted(comparison_results, key=lambda x: x.activity.price)
        for i, result in enumerate(price_sorted):
            result.price_rank = i + 1

        # Sort by rating for rating ranking
        rating_sorted = sorted(
            comparison_results, key=lambda x: x.activity.rating or 0, reverse=True
        )
        for i, result in enumerate(rating_sorted):
            result.rating_rank = i + 1

    async def search_activities_with_geoapify(
        self,
        location: str,
        category: ActivityCategory | None = None,
        guest_count: int = 1,
        max_results: int = 20,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_meters: int = 5000,
    ) -> ActivitySearchResponse:
        """
        Enhanced activity search using only Geoapify Places API.

        Args:
            location: Search location (city, address, etc.)
            category: Activity category filter
            guest_count: Number of guests
            max_results: Maximum number of results
            latitude: Latitude for geo-based search
            longitude: Longitude for geo-based search
            radius_meters: Search radius in meters

        Returns:
            ActivitySearchResponse with activities from Geoapify
        """
        start_time = datetime.now()

        try:
            # Create search request
            search_request = ActivitySearchRequest(
                location=location,
                check_in_date=None,
                check_out_date=None,
                category=category,
                budget_per_person=None,
                duration_hours=None,
                guest_count=guest_count,
                max_results=max_results,
            )

            self.logger.info(f"Searching activities in {location} via Geoapify only")

            # Search activities from Geoapify
            activities = await self.geoapify_client.search_activities(
                search_request, latitude=latitude, longitude=longitude, radius_meters=radius_meters
            )

            # Rank activities (simplified ranking for Geoapify-only)
            ranked_activities = await self._rank_activities(activities, search_request)

            # Create response
            search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            response = ActivitySearchResponse(
                activities=ranked_activities,
                total_results=len(ranked_activities),
                search_time_ms=search_time_ms,
                search_metadata={
                    "provider": "geoapify_only",
                    "location": location,
                    "category": category.value if category else None,
                    "guest_count": guest_count,
                    "radius_meters": radius_meters,
                },
                cached=False,
                cache_expires_at=None,
            )

            self.logger.info(
                f"Geoapify activity search completed: {len(ranked_activities)} activities found"
            )
            return response

        except Exception as e:
            self.logger.error(f"Geoapify activity search failed: {e}")
            # Return empty response on error for graceful fallback
            search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return ActivitySearchResponse(
                activities=[],
                total_results=0,
                search_time_ms=search_time_ms,
                search_metadata={
                    "provider": "geoapify_only",
                    "location": location,
                    "category": category.value if category else None,
                    "guest_count": guest_count,
                    "radius_meters": radius_meters,
                    "error": str(e),
                },
                cached=False,
                cache_expires_at=None,
            )

"""Base agent class for travel planning agents."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from travel_companion.core.config import Settings, get_settings
from travel_companion.core.database import DatabaseManager, get_database_manager
from travel_companion.core.redis import RedisManager, get_redis_manager

# Type variable for agent response data
T = TypeVar("T")


class BaseAgent(ABC, Generic[T]):
    """Base class for all travel planning agents."""

    def __init__(
        self,
        settings: Settings | None = None,
        database: DatabaseManager | None = None,
        redis: RedisManager | None = None,
    ) -> None:
        """Initialize base agent with configuration and dependencies.

        Args:
            settings: Application settings instance
            database: Database manager instance
            redis: Redis manager instance
        """
        self.settings = settings or get_settings()
        self.database = database or get_database_manager()
        self.redis = redis or get_redis_manager()
        self.logger = logging.getLogger(
            f"travel_companion.agents.{self.__class__.__name__.lower()}"
        )

        self.logger.info(f"Initialized {self.__class__.__name__} agent")

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Name of the agent for logging and identification."""
        pass

    @property
    @abstractmethod
    def agent_version(self) -> str:
        """Version of the agent for compatibility and debugging."""
        pass

    @abstractmethod
    async def process(self, request_data: dict[str, Any]) -> T:
        """Process a request and return the result.

        Args:
            request_data: Input data for processing

        Returns:
            Processed result of type T
        """
        pass

    async def health_check(self) -> dict[str, Any]:
        """Check agent health and dependencies.

        Returns:
            Health status dictionary
        """
        status: dict[str, Any] = {
            "agent": self.agent_name,
            "version": self.agent_version,
            "status": "healthy",
            "dependencies": {},
        }

        try:
            # Check database connection
            db_healthy = await self.database.health_check()
            status["dependencies"]["database"] = "healthy" if db_healthy else "unhealthy"

            # Check Redis connection
            redis_healthy = await self.redis.ping()
            status["dependencies"]["redis"] = "healthy" if redis_healthy else "unhealthy"

            # Overall status based on dependencies
            if not db_healthy or not redis_healthy:
                status["status"] = "degraded"

        except Exception as e:
            self.logger.error(f"Health check failed for {self.agent_name}: {e}")
            status["status"] = "unhealthy"
            status["error"] = str(e)

        return status

    async def _cache_key(self, request_data: dict[str, Any]) -> str:
        """Generate cache key for request data with enhanced strategy.

        Args:
            request_data: Request data to generate key from

        Returns:
            Cache key string
        """
        import hashlib
        import json
        from datetime import date, datetime
        from decimal import Decimal

        def json_serializer(obj: Any) -> str:
            """Custom JSON serializer for datetime, date and Decimal objects."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, date):
                return obj.isoformat()
            elif isinstance(obj, Decimal):
                return str(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        # Create normalized copy of request data for consistent caching
        normalized_data = {}

        # Normalize location (lowercase, strip spaces)
        if "location" in request_data:
            normalized_data["location"] = request_data["location"].lower().strip()

        # Keep dates as strings for consistency
        for date_field in ["check_in_date", "check_out_date"]:
            if date_field in request_data:
                if isinstance(request_data[date_field], datetime):
                    normalized_data[date_field] = request_data[date_field].date().isoformat()
                else:
                    # Try to parse and normalize date format
                    try:
                        parsed_date = datetime.fromisoformat(str(request_data[date_field]))
                        normalized_data[date_field] = parsed_date.date().isoformat()
                    except (ValueError, TypeError):
                        normalized_data[date_field] = str(request_data[date_field])

        # Keep numeric values as consistent types
        for numeric_field in ["guest_count", "room_count", "max_results"]:
            if numeric_field in request_data:
                normalized_data[numeric_field] = int(request_data[numeric_field])

        # Handle budget with consistent decimal precision
        if "budget" in request_data and request_data["budget"] is not None:
            normalized_data["budget"] = f"{float(request_data['budget']):.2f}"

        # Keep currency uppercase for consistency
        if "currency" in request_data:
            normalized_data["currency"] = request_data["currency"].upper()

        # Add any remaining fields
        for key, value in request_data.items():
            if key not in normalized_data:
                normalized_data[key] = value

        # Create deterministic hash from normalized data
        sorted_data = json.dumps(normalized_data, sort_keys=True, default=json_serializer)
        hash_obj = hashlib.md5(sorted_data.encode())

        # Create hierarchical cache key structure for better organization
        location_part = normalized_data.get("location", "unknown").replace(" ", "_")[:20]

        # Use check_in_date, start_date, or date field if available
        date_part = None
        for date_field in ["check_in_date", "start_date", "date"]:
            if date_field in normalized_data:
                date_part = normalized_data[date_field].replace("-", "")
                break

        # Only include date part if it exists
        if date_part:
            return f"{self.agent_name}:{location_part}:{date_part}:{hash_obj.hexdigest()}"
        else:
            return f"{self.agent_name}:{location_part}:{hash_obj.hexdigest()}"

    async def _get_cached_result(self, cache_key: str) -> T | None:
        """Get cached result from Redis.

        Args:
            cache_key: Cache key to lookup

        Returns:
            Cached result or None if not found
        """
        try:
            cached_data = await self.redis.get(cache_key, json_decode=True)
            if cached_data:
                self.logger.debug(f"Cache hit for {self.agent_name}: {cache_key}")
                result_data: T = cached_data
                return result_data
        except Exception as e:
            self.logger.warning(f"Failed to get cached result: {e}")

        return None

    async def _set_cached_result(
        self, cache_key: str, result: Any, expire_seconds: int = 300
    ) -> None:
        """Cache result in Redis.

        Args:
            cache_key: Cache key to store under
            result: Result data to cache
            expire_seconds: Expiration time in seconds
        """
        try:
            await self.redis.set(cache_key, result, expire=expire_seconds)
            self.logger.debug(f"Cached result for {self.agent_name}: {cache_key}")
        except Exception as e:
            self.logger.warning(f"Failed to cache result: {e}")

"""Travel planning agents used as tools for Claude SDK."""

from travel_companion.agents.base import BaseAgent
from travel_companion.agents.flight_agent import FlightAgent
from travel_companion.core.config import Settings
from travel_companion.core.database import DatabaseManager
from travel_companion.core.redis import RedisManager

__all__ = [
    "BaseAgent",
    "FlightAgent",
    "create_flight_agent",
]


def create_flight_agent(
    settings: Settings | None = None,
    database: DatabaseManager | None = None,
    redis: RedisManager | None = None,
) -> FlightAgent:
    """Create a FlightAgent instance with dependency injection.

    Args:
        settings: Application settings instance
        database: Database manager instance
        redis: Redis manager instance

    Returns:
        Configured FlightAgent instance
    """
    return FlightAgent(settings=settings, database=database, redis=redis)

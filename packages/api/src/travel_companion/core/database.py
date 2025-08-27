"""Database connection and configuration for Supabase."""

from collections.abc import AsyncGenerator
from functools import lru_cache

import httpx
from supabase import Client, create_client

from travel_companion.core.config import get_settings


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self):
        self._client: Client | None = None
        self._settings = get_settings()

    @property
    def client(self) -> Client:
        """Get or create Supabase client instance."""
        if self._client is None:
            if not self._settings.supabase_url or not self._settings.supabase_key:
                raise ValueError(
                    "Supabase configuration missing. Please set SUPABASE_URL and SUPABASE_KEY"
                )

            self._client = create_client(self._settings.supabase_url, self._settings.supabase_key)

        return self._client

    async def health_check(self) -> bool:
        """Check database connection health."""
        try:
            if not self._settings.supabase_url:
                return False

            # Simple health check by attempting to connect
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._settings.supabase_url}/rest/v1/",
                    headers={"apikey": self._settings.supabase_key},
                    timeout=5.0,
                )
                return response.status_code in [200, 404]  # 404 is OK for root endpoint
        except Exception:
            return False

    async def close(self) -> None:
        """Close database connection."""
        if self._client:
            # Supabase client doesn't need explicit closing
            self._client = None


@lru_cache
def get_database_manager() -> DatabaseManager:
    """Get cached database manager instance."""
    return DatabaseManager()


async def get_database() -> AsyncGenerator[DatabaseManager, None]:
    """Dependency for getting database manager in FastAPI."""
    db = get_database_manager()
    try:
        yield db
    finally:
        await db.close()

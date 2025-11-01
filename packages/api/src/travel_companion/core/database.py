"""Database connection and configuration for Supabase."""

from collections.abc import AsyncGenerator
from functools import lru_cache

import httpx
from supabase import Client, ClientOptions, create_client

from travel_companion.core.config import get_settings


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self) -> None:
        self._client: Client | None = None
        self._settings = get_settings()
        self._async_http_client: httpx.AsyncClient | None = None

    @property
    def client(self) -> Client:
        """Get or create Supabase client instance."""
        if self._client is None:
            # Use service key if available, otherwise fall back to anon key
            key = self._settings.supabase_key

            if not self._settings.supabase_url or not key:
                raise ValueError(
                    "Supabase configuration missing. Please set SUPABASE_URL and SUPABASE_KEY"
                )

            # Configure httpx client with timeout and verify settings
            # This prevents deprecation warnings from Supabase
            http_client = httpx.Client(timeout=30.0, verify=True)

            # Create client with proper options to avoid deprecation warnings
            options = ClientOptions(
                httpx_client=http_client,
                postgrest_client_timeout=30.0,
                storage_client_timeout=30.0,
            )

            self._client = create_client(
                self._settings.supabase_url,
                key,
                options=options
            )

        return self._client

    @property
    def async_http_client(self) -> httpx.AsyncClient:
        """Get or create shared async HTTP client for health checks."""
        if self._async_http_client is None:
            self._async_http_client = httpx.AsyncClient(timeout=5.0, verify=True)
        return self._async_http_client

    async def health_check(self) -> bool:
        """Check database connection health."""
        try:
            if not self._settings.supabase_url:
                return False

            # Simple health check by attempting to connect using shared client
            key = self._settings.supabase_key
            response = await self.async_http_client.get(
                f"{self._settings.supabase_url}/rest/v1/",
                headers={"apikey": key},
                timeout=5.0,
            )
            return response.status_code in [200, 404]  # 404 is OK for root endpoint
        except Exception:
            return False

    async def close(self) -> None:
        """Close database connection and async HTTP client."""
        if self._client:
            # Supabase client doesn't need explicit closing
            self._client = None

        if self._async_http_client:
            try:
                await self._async_http_client.aclose()
            except RuntimeError:
                # Event loop might already be closed, which is fine
                pass
            self._async_http_client = None


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

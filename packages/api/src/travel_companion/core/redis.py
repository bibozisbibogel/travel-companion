"""Redis connection and configuration for caching and rate limiting."""

import json
from functools import lru_cache
from typing import Any, cast

import redis.asyncio as redis

from travel_companion.core.config import get_settings


class RedisManager:
    """Manages Redis connections and operations."""

    def __init__(self) -> None:
        self._client: redis.Redis | None = None
        self._settings = get_settings()

    @property
    def client(self) -> redis.Redis:
        """Get or create Redis client instance."""
        if self._client is None:
            if not self._settings.redis_url:
                raise ValueError(
                    "Redis URL not configured. Please set REDIS_URL environment variable"
                )

            self._client = redis.from_url(
                self._settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )

        return self._client

    async def ping(self) -> bool:
        """Check Redis connection health."""
        try:
            result = await self.client.ping()
            return result is True
        except Exception:
            return False

    async def set(
        self, key: str, value: str | dict[str, Any] | list[Any], expire: int | None = None
    ) -> bool:
        """Set a value in Redis with optional expiration."""
        try:
            # Serialize complex data types
            if isinstance(value, dict | list):
                value = json.dumps(value)

            if expire:
                return bool(await self.client.setex(key, expire, value))
            else:
                return bool(await self.client.set(key, value))
        except Exception:
            return False

    async def get(self, key: str, json_decode: bool = False) -> Any | None:
        """Get a value from Redis with optional JSON decoding."""
        try:
            value = await self.client.get(key)
            if value is None:
                return None

            if json_decode:
                return json.loads(value)

            return value
        except Exception:
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        try:
            result = await self.client.delete(key)
            return bool(result > 0)
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        try:
            result = await self.client.exists(key)
            return bool(result > 0)
        except Exception:
            return False

    async def incr(self, key: str, amount: int = 1) -> int | None:
        """Increment a counter in Redis."""
        try:
            return int(await self.client.incr(key, amount))
        except Exception:
            return None

    async def expire(self, key: str, time: int) -> bool:
        """Set expiration time for a key."""
        try:
            return bool(await self.client.expire(key, time))
        except Exception:
            return False

    async def ttl(self, key: str) -> int:
        """Get time to live for a key."""
        try:
            return int(await self.client.ttl(key))
        except Exception:
            return -1

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    def get_client(self) -> redis.Redis:
        """Get Redis client - alias for client property for compatibility."""
        return self.client

    async def scan_keys(self, pattern: str = "*", count: int = 100) -> list[str]:
        """Scan for keys matching a pattern."""
        try:
            keys = []
            cursor = 0
            while True:
                cursor, batch = await self.client.scan(cursor, match=pattern, count=count)
                keys.extend(batch)
                if cursor == 0:
                    break
            return keys
        except Exception:
            return []

    async def delete_keys(self, keys: list[str]) -> int:
        """Delete multiple keys at once."""
        try:
            if not keys:
                return 0
            return cast(int, await self.client.delete(*keys))
        except Exception:
            return 0


@lru_cache
def get_redis_manager() -> RedisManager:
    """Get cached Redis manager instance."""
    return RedisManager()


async def get_redis() -> RedisManager:
    """Dependency for getting Redis manager in FastAPI."""
    return get_redis_manager()

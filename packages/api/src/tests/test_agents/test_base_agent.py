"""Tests for base agent functionality."""

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from travel_companion.agents.base import BaseAgent
from travel_companion.core.config import Settings
from travel_companion.core.database import DatabaseManager
from travel_companion.core.redis import RedisManager


class _TestableAgent(BaseAgent[dict]):
    """Testable implementation of BaseAgent for testing."""

    @property
    def agent_name(self) -> str:
        """Name of the test agent."""
        return "TestAgent"

    @property
    def agent_version(self) -> str:
        """Version of the test agent."""
        return "1.0.0"

    async def process(self, request_data: dict[str, Any]) -> dict:
        """Process test request."""
        return {"result": "processed", "data": request_data}


class TestBaseAgent:
    """Test cases for BaseAgent."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        return Settings(
            app_name="Test Travel Companion API",
            debug=True,
            database_url="test://localhost",
            redis_url="redis://localhost:6379/1",
            secret_key="test-secret",
        )

    @pytest.fixture
    def mock_database(self):
        """Create mock database manager for testing."""
        mock_db = Mock(spec=DatabaseManager)
        mock_db.health_check = AsyncMock(return_value=True)
        return mock_db

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis manager for testing."""
        mock_redis = Mock(spec=RedisManager)
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)
        return mock_redis

    @pytest.fixture
    def test_agent(self, mock_settings, mock_database, mock_redis):
        """Create a test agent instance."""
        return _TestableAgent(
            settings=mock_settings,
            database=mock_database,
            redis=mock_redis,
        )

    def test_agent_initialization(self, test_agent, mock_settings, mock_database, mock_redis):
        """Test agent initialization with dependencies."""
        assert test_agent.settings == mock_settings
        assert test_agent.database == mock_database
        assert test_agent.redis == mock_redis
        assert test_agent.agent_name == "TestAgent"
        assert test_agent.agent_version == "1.0.0"

    def test_agent_initialization_with_defaults(self):
        """Test agent initialization with default dependencies."""
        with (
            patch("travel_companion.agents.base.get_settings") as mock_get_settings,
            patch("travel_companion.agents.base.get_database_manager") as mock_get_db,
            patch("travel_companion.agents.base.get_redis_manager") as mock_get_redis,
            patch("logging.getLogger") as mock_get_logger,
        ):
            mock_settings = Mock()
            mock_database = Mock()
            mock_redis = Mock()
            mock_logger = Mock()

            mock_get_settings.return_value = mock_settings
            mock_get_db.return_value = mock_database
            mock_get_redis.return_value = mock_redis
            mock_get_logger.return_value = mock_logger

            agent = _TestableAgent()

            assert agent.settings == mock_settings
            assert agent.database == mock_database
            assert agent.redis == mock_redis
            assert agent.logger == mock_logger
            mock_get_logger.assert_called_once_with("travel_companion.agents._testableagent")

    @pytest.mark.asyncio
    async def test_health_check_success(self, test_agent, mock_database, mock_redis):
        """Test successful health check."""
        mock_database.health_check.return_value = True
        mock_redis.ping.return_value = True

        result = await test_agent.health_check()

        assert result["agent"] == "TestAgent"
        assert result["version"] == "1.0.0"
        assert result["status"] == "healthy"
        assert result["dependencies"]["database"] == "healthy"
        assert result["dependencies"]["redis"] == "healthy"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_health_check_database_failure(self, test_agent, mock_database, mock_redis):
        """Test health check with database failure."""
        mock_database.health_check.return_value = False
        mock_redis.ping.return_value = True

        result = await test_agent.health_check()

        assert result["agent"] == "TestAgent"
        assert result["status"] == "degraded"
        assert result["dependencies"]["database"] == "unhealthy"
        assert result["dependencies"]["redis"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_redis_failure(self, test_agent, mock_database, mock_redis):
        """Test health check with Redis failure."""
        mock_database.health_check.return_value = True
        mock_redis.ping.return_value = False

        result = await test_agent.health_check()

        assert result["agent"] == "TestAgent"
        assert result["status"] == "degraded"
        assert result["dependencies"]["database"] == "healthy"
        assert result["dependencies"]["redis"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_exception(self, test_agent, mock_database, mock_redis):
        """Test health check with exception."""
        mock_database.health_check.side_effect = Exception("Database connection failed")

        result = await test_agent.health_check()

        assert result["agent"] == "TestAgent"
        assert result["status"] == "unhealthy"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, test_agent):
        """Test cache key generation."""
        request_data = {"origin": "NYC", "destination": "LAX", "date": "2024-01-01"}

        cache_key = await test_agent._cache_key(request_data)

        assert cache_key.startswith("TestAgent:")
        assert len(cache_key) == len("TestAgent:") + 32  # MD5 hash length

        # Same data should generate same key
        cache_key2 = await test_agent._cache_key(request_data)
        assert cache_key == cache_key2

        # Different data should generate different key
        different_data = {"origin": "LAX", "destination": "NYC", "date": "2024-01-01"}
        cache_key3 = await test_agent._cache_key(different_data)
        assert cache_key != cache_key3

    @pytest.mark.asyncio
    async def test_get_cached_result_miss(self, test_agent, mock_redis):
        """Test cache miss scenario."""
        mock_redis.get.return_value = None

        result = await test_agent._get_cached_result("test_key")

        assert result is None
        mock_redis.get.assert_called_once_with("test_key", json_decode=True)

    @pytest.mark.asyncio
    async def test_get_cached_result_hit(self, test_agent, mock_redis):
        """Test cache hit scenario."""
        cached_data = {"cached": True, "result": "test"}
        mock_redis.get.return_value = cached_data

        result = await test_agent._get_cached_result("test_key")

        assert result == cached_data
        mock_redis.get.assert_called_once_with("test_key", json_decode=True)

    @pytest.mark.asyncio
    async def test_get_cached_result_exception(self, test_agent, mock_redis):
        """Test cache get with exception."""
        mock_redis.get.side_effect = Exception("Redis error")

        result = await test_agent._get_cached_result("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_cached_result_success(self, test_agent, mock_redis):
        """Test successful cache set."""
        test_data = {"test": "data"}

        await test_agent._set_cached_result("test_key", test_data, expire_seconds=300)

        mock_redis.set.assert_called_once_with("test_key", test_data, expire=300)

    @pytest.mark.asyncio
    async def test_set_cached_result_exception(self, test_agent, mock_redis):
        """Test cache set with exception."""
        mock_redis.set.side_effect = Exception("Redis error")
        test_data = {"test": "data"}

        # Should not raise exception, just log warning
        await test_agent._set_cached_result("test_key", test_data)

        mock_redis.set.assert_called_once_with("test_key", test_data, expire=300)

    @pytest.mark.asyncio
    async def test_process_method(self, test_agent):
        """Test the abstract process method implementation."""
        test_data = {"input": "test"}

        result = await test_agent.process(test_data)

        assert result["result"] == "processed"
        assert result["data"] == test_data

    def test_agent_properties(self, test_agent):
        """Test agent property values."""
        assert test_agent.agent_name == "TestAgent"
        assert test_agent.agent_version == "1.0.0"

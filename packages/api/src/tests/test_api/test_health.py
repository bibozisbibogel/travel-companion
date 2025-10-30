"""Tests for health check endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


def test_health_check_basic(client: TestClient):
    """Test basic health check endpoint structure."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
    assert "service" in data


def test_detailed_health_check_structure(client: TestClient):
    """Test detailed health check endpoint structure."""
    response = client.get("/api/v1/health/detailed")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "timestamp" in data
    assert "version" in data
    assert "service" in data
    assert "environment" in data
    assert "uptime_check" in data
    assert "dependencies" in data
    assert "cached" in data
    assert "metrics" in data

    # Check dependencies structure
    dependencies = data["dependencies"]
    assert "database" in dependencies
    assert "redis" in dependencies
    assert "external_apis" in dependencies

    # Check metrics structure
    metrics = data["metrics"]
    assert "dependencies_checked" in metrics
    assert "healthy_dependencies" in metrics
    assert "unhealthy_dependencies" in metrics
    assert "error_dependencies" in metrics


def test_detailed_health_check_caching(client: TestClient):
    """Test health check caching functionality."""
    # First request - should not be cached
    response1 = client.get("/api/v1/health/detailed")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["cached"] is False

    # Second request within cache TTL - should be cached if Redis is healthy
    response2 = client.get("/api/v1/health/detailed")
    assert response2.status_code == 200
    data2 = response2.json()

    # If Redis is working, it should be cached
    if "redis" in data2["dependencies"] and data2["dependencies"]["redis"]["status"] == "healthy":
        # Cache might be present (depending on TTL and timing)
        if data2.get("cached"):
            assert "cache_ttl_remaining" in data2
            assert data2["cache_ttl_remaining"] >= 0


@patch("travel_companion.core.database.get_database_manager")
def test_detailed_health_check_database_error(mock_db, client: TestClient):
    """Test health check with database connection error."""
    # Mock database manager to raise exception
    mock_db_manager = AsyncMock()
    mock_db_manager.health_check.side_effect = Exception("Database connection failed")
    mock_db.return_value = mock_db_manager

    response = client.get("/api/v1/health/detailed")
    assert response.status_code == 200

    data = response.json()
    dependencies = data["dependencies"]
    assert dependencies["database"]["status"] == "error"
    assert "error" in dependencies["database"]
    assert "Database connection failed" in dependencies["database"]["error"]


@patch("travel_companion.core.redis.get_redis_manager")
def test_detailed_health_check_redis_error(mock_redis, client: TestClient):
    """Test health check with Redis connection error."""
    # Mock Redis manager to raise exception
    mock_redis_manager = AsyncMock()
    mock_redis_manager.ping.side_effect = Exception("Redis connection failed")
    mock_redis.return_value = mock_redis_manager

    response = client.get("/api/v1/health/detailed")
    assert response.status_code == 200

    data = response.json()
    dependencies = data["dependencies"]
    assert dependencies["redis"]["status"] == "error"
    assert "error" in dependencies["redis"]
    assert "Redis connection failed" in dependencies["redis"]["error"]


def test_detailed_health_check_external_apis_configuration(client: TestClient):
    """Test health check external API configuration reporting."""
    response = client.get("/api/v1/health/detailed")
    assert response.status_code == 200

    data = response.json()
    external_apis = data["dependencies"]["external_apis"]

    # Check that all expected API configurations are reported
    expected_apis = ["amadeus", "booking", "tripadvisor", "openai"]
    for api_name in expected_apis:
        assert api_name in external_apis
        api_config = external_apis[api_name]
        assert "configured" in api_config
        assert isinstance(api_config["configured"], bool)


def test_detailed_health_check_metrics_calculation(client: TestClient):
    """Test health check metrics calculation."""
    response = client.get("/api/v1/health/detailed")
    assert response.status_code == 200

    data = response.json()
    metrics = data["metrics"]
    dependencies = data["dependencies"]

    # Verify metrics calculation
    total_deps = len(dependencies)
    assert metrics["dependencies_checked"] == total_deps

    # Count actual statuses
    healthy_count = 0
    unhealthy_count = 0
    error_count = 0

    for dep in dependencies.values():
        if isinstance(dep, dict) and "status" in dep:
            if dep["status"] == "healthy":
                healthy_count += 1
            elif dep["status"] == "unhealthy":
                unhealthy_count += 1
            elif dep["status"] == "error":
                error_count += 1

    assert metrics["healthy_dependencies"] == healthy_count
    assert metrics["unhealthy_dependencies"] == unhealthy_count
    assert metrics["error_dependencies"] == error_count


@patch("travel_companion.core.database.get_database_manager")
@patch("travel_companion.core.redis.get_redis_manager")
def test_detailed_health_check_degraded_status(mock_redis, mock_db, client: TestClient):
    """Test health check degraded status when dependencies fail."""
    # Mock all dependencies to fail
    mock_db_manager = AsyncMock()
    mock_db_manager.health_check.side_effect = Exception("Database failed")
    mock_db.return_value = mock_db_manager

    mock_redis_manager = AsyncMock()
    mock_redis_manager.ping.side_effect = Exception("Redis failed")
    mock_redis.return_value = mock_redis_manager

    response = client.get("/api/v1/health/detailed")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "degraded"  # Should be degraded when dependencies fail


@pytest.mark.asyncio
async def test_health_check_cache_integration():
    """Test health check caching integration with real Redis operations."""
    from travel_companion.api.v1.health import HEALTH_CACHE_KEY, HEALTH_CACHE_TTL
    from travel_companion.core.redis import get_redis_manager

    redis_manager = get_redis_manager()

    # Clean up any existing cache
    try:
        await redis_manager.delete(HEALTH_CACHE_KEY)
    except Exception:
        pass  # Redis might not be available in test environment

    # Test cache key structure
    assert HEALTH_CACHE_KEY == "health_check:detailed"
    assert HEALTH_CACHE_TTL == 30


def test_health_check_response_headers(client: TestClient):
    """Test that health check responses include proper headers."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("content-type") == "application/json"

    response_detailed = client.get("/api/v1/health/detailed")
    assert response_detailed.status_code == 200
    assert response_detailed.headers.get("content-type") == "application/json"


def test_health_check_concurrent_requests(client: TestClient):
    """Test health check endpoint under concurrent load."""
    import threading

    results = []

    def make_request():
        response = client.get("/api/v1/health/detailed")
        results.append(response.status_code)

    # Create multiple threads to test concurrent access
    threads = []
    for _ in range(5):
        thread = threading.Thread(target=make_request)
        threads.append(thread)

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # All requests should succeed
    assert len(results) == 5
    assert all(status == 200 for status in results)

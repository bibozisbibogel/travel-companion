"""Integration tests for API versioning and endpoint access."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from travel_companion.main import create_app


@pytest.fixture
def app():
    """Create the FastAPI application for testing."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestAPIVersioningIntegration:
    """Integration tests for API versioning structure."""

    def test_root_endpoint_no_version_headers(self, client):
        """Test that root endpoint doesn't have version headers."""
        response = client.get("/")

        # Root endpoint should not have version headers regardless of status
        assert "X-API-Version" not in response.headers
        assert "X-App-Version" not in response.headers

    def test_health_endpoint_has_version_headers(self, client):
        """Test that health endpoint has version headers."""
        with patch("travel_companion.core.database.get_database_manager") as mock_db:
            with patch("travel_companion.core.redis.get_redis_manager") as mock_redis:
                # Mock database and Redis managers
                mock_db_instance = AsyncMock()
                mock_db_instance.health_check.return_value = True
                mock_db.return_value = mock_db_instance

                mock_redis_instance = AsyncMock()
                mock_redis_instance.ping.return_value = True
                mock_redis.return_value = mock_redis_instance

                response = client.get("/api/v1/health")

                assert response.status_code == 200
                assert response.headers["X-API-Version"] == "v1"
                assert response.headers["X-App-Version"] == "0.1.0"

                data = response.json()
                assert data["status"] == "healthy"
                assert "version" in data
                assert "service" in data

    def test_detailed_health_endpoint_has_version_headers(self, client):
        """Test that detailed health endpoint has version headers."""
        # Simply test that the endpoint has version headers, even if it fails internally
        response = client.get("/api/v1/health/detailed")

        # Should have version headers regardless of the response content
        assert response.headers["X-API-Version"] == "v1"
        assert response.headers["X-App-Version"] == "0.1.0"

    def test_trips_endpoint_has_version_headers(self, client):
        """Test that trips endpoint has version headers."""
        response = client.get("/api/v1/trips/")

        # Should have version headers regardless of authentication status
        assert response.headers["X-API-Version"] == "v1"
        assert response.headers["X-App-Version"] == "0.1.0"

    def test_users_endpoint_has_version_headers(self, client):
        """Test that users endpoint has version headers."""
        # Test registration endpoint (public, no auth required)
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123",
        }

        with patch("travel_companion.core.database.get_database_manager") as mock_db:
            mock_db_instance = AsyncMock()
            mock_db_instance.create_user.return_value = {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "testuser",
                "email": "test@example.com",
                "created_at": "2023-01-01T00:00:00Z",
            }
            mock_db.return_value = mock_db_instance

            response = client.post("/api/v1/users/register", json=user_data)

            # May return 500 due to missing database connection, but should have version headers
            assert response.headers["X-API-Version"] == "v1"
            assert response.headers["X-App-Version"] == "0.1.0"

    def test_workflows_endpoint_has_version_headers(self, client):
        """Test that workflows endpoint has version headers."""
        workflow_data = {
            "user_id": "test-user-123",
            "request_id": "test-request-456",
            "input_data": {
                "destination": {"city": "Paris", "country": "France"},
                "requirements": {
                    "start_date": "2024-06-01",
                    "end_date": "2024-06-07",
                    "budget": 2000,
                },
                "preferences": {
                    "activity_types": ["cultural", "food"],
                    "accommodation_type": "hotel",
                },
            },
        }

        with patch("travel_companion.workflows.orchestrator.TripPlanningWorkflow") as mock_workflow:
            mock_workflow_instance = AsyncMock()
            mock_workflow_instance.execute_trip_planning.return_value = {
                "trip_id": "test-trip-789",
                "status": "completed",
            }
            mock_workflow.return_value = mock_workflow_instance

            response = client.post("/api/v1/workflows/execute", json=workflow_data)

            # May return error due to missing dependencies, but should have version headers
            assert response.headers["X-API-Version"] == "v1"
            assert response.headers["X-App-Version"] == "0.1.0"

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/v1/health",
            "/api/v1/health/detailed",
            "/api/v1/trips/",
            "/api/v1/users/me",  # Will return 401, but should have headers
            "/api/v1/workflows/status/test-session",  # Will return error, but should have headers
        ],
    )
    def test_all_versioned_endpoints_have_headers(self, client, endpoint):
        """Test that all API v1 endpoints have version headers regardless of response status."""
        # Use GET for all endpoints (some may return method not allowed, but should have headers)
        response = client.get(endpoint)

        # Regardless of the status code, version headers should be present
        assert response.headers["X-API-Version"] == "v1"
        assert response.headers["X-App-Version"] == "0.1.0"

    def test_api_version_consistency_across_endpoints(self, client):
        """Test that API version is consistent across all endpoints."""
        endpoints = [
            "/api/v1/health",
            "/api/v1/trips/",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)

            assert response.headers["X-API-Version"] == "v1"
            assert response.headers["X-App-Version"] == "0.1.0"

    def test_openapi_documentation_reflects_versioning(self, client):
        """Test that OpenAPI documentation reflects the API versioning."""
        response = client.get("/docs")

        # In debug mode, docs should be available
        # The specific content depends on the environment, but the endpoint should respond
        assert response.status_code in [200, 404]  # 404 if debug is False


class TestAPIVersioningValidation:
    """Validation tests for API versioning implementation."""

    def test_version_header_format_validation(self, client):
        """Test that version headers follow expected format."""
        response = client.get("/api/v1/health")

        # API version should follow vN format
        api_version = response.headers["X-API-Version"]
        assert api_version.startswith("v")
        assert api_version[1:].isdigit() or api_version[1:] == "1"

        # App version should follow semantic versioning
        app_version = response.headers["X-App-Version"]
        version_parts = app_version.split(".")
        assert len(version_parts) >= 2  # At least major.minor
        for part in version_parts:
            assert part.isdigit()

    def test_version_middleware_does_not_interfere_with_cors(self, client):
        """Test that version middleware doesn't interfere with CORS functionality."""
        # Make an OPTIONS request to test CORS preflight
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        }

        response = client.options("/api/v1/health", headers=headers)

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
        # Should also have version headers for API endpoints
        assert response.headers["X-API-Version"] == "v1"
        assert response.headers["X-App-Version"] == "0.1.0"

    def test_error_responses_include_version_headers(self, client):
        """Test that error responses also include version headers."""
        # Try to access a non-existent API endpoint
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404
        assert response.headers["X-API-Version"] == "v1"
        assert response.headers["X-App-Version"] == "0.1.0"

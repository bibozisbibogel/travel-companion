"""Tests for API versioning middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from travel_companion.middleware.versioning import APIVersionMiddleware


@pytest.fixture
def app_with_versioning():
    """Create FastAPI app with versioning middleware for testing."""
    app = FastAPI()

    app.add_middleware(APIVersionMiddleware, api_version="v1", app_version="0.1.0")

    @app.get("/api/v1/test")
    async def test_v1_endpoint():
        return {"message": "v1 endpoint"}

    @app.get("/api/v2/test")
    async def test_v2_endpoint():
        return {"message": "v2 endpoint"}

    @app.get("/health")
    async def non_api_endpoint():
        return {"status": "ok"}

    @app.get("/")
    async def root():
        return {"message": "root"}

    return app


class TestAPIVersionMiddleware:
    """Test cases for API version middleware."""

    def test_adds_version_headers_to_api_endpoints(self, app_with_versioning):
        """Test that version headers are added to API endpoints."""
        with TestClient(app_with_versioning) as client:
            response = client.get("/api/v1/test")

            assert response.status_code == 200
            assert response.headers["X-API-Version"] == "v1"
            assert response.headers["X-App-Version"] == "0.1.0"
            assert response.json() == {"message": "v1 endpoint"}

    def test_adds_version_headers_to_different_api_versions(self, app_with_versioning):
        """Test that version headers are added to different API versions."""
        with TestClient(app_with_versioning) as client:
            response = client.get("/api/v2/test")

            assert response.status_code == 200
            assert response.headers["X-API-Version"] == "v1"  # Middleware version
            assert response.headers["X-App-Version"] == "0.1.0"
            assert response.json() == {"message": "v2 endpoint"}

    def test_no_version_headers_for_non_api_endpoints(self, app_with_versioning):
        """Test that version headers are not added to non-API endpoints."""
        with TestClient(app_with_versioning) as client:
            response = client.get("/health")

            assert response.status_code == 200
            assert "X-API-Version" not in response.headers
            assert "X-App-Version" not in response.headers
            assert response.json() == {"status": "ok"}

    def test_no_version_headers_for_root_endpoint(self, app_with_versioning):
        """Test that version headers are not added to root endpoints."""
        with TestClient(app_with_versioning) as client:
            response = client.get("/")

            assert response.status_code == 200
            assert "X-API-Version" not in response.headers
            assert "X-App-Version" not in response.headers
            assert response.json() == {"message": "root"}

    def test_custom_version_values(self):
        """Test middleware with custom version values."""
        app = FastAPI()
        app.add_middleware(APIVersionMiddleware, api_version="v2", app_version="1.2.3")

        @app.get("/api/v2/custom")
        async def custom_endpoint():
            return {"message": "custom"}

        with TestClient(app) as client:
            response = client.get("/api/v2/custom")

            assert response.status_code == 200
            assert response.headers["X-API-Version"] == "v2"
            assert response.headers["X-App-Version"] == "1.2.3"

    def test_handles_missing_request_attributes_gracefully(self, app_with_versioning):
        """Test that middleware handles edge cases gracefully."""
        with TestClient(app_with_versioning) as client:
            # Test with various endpoint paths
            test_cases = [
                "/api/",
                "/api/v1/",
                "/api/v1/test/",
                "/api/v1/test/nested/path",
            ]

            for path in test_cases:
                # Create a dynamic endpoint for testing with unique function name
                def create_endpoint(endpoint_path: str):
                    @app_with_versioning.get(endpoint_path)
                    async def dynamic_endpoint():
                        return {"path": endpoint_path}

                    return dynamic_endpoint

                create_endpoint(path)
                response = client.get(path)

                # Should have version headers for all API paths
                assert "X-API-Version" in response.headers
                assert "X-App-Version" in response.headers


class TestAPIVersionMiddlewareIntegration:
    """Integration tests for API version middleware with actual app structure."""

    def test_middleware_order_with_other_middleware(self):
        """Test that versioning middleware works correctly with other middleware."""
        from fastapi.middleware.cors import CORSMiddleware

        app = FastAPI()

        # Add CORS middleware first, then versioning
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
        app.add_middleware(APIVersionMiddleware, api_version="v1", app_version="0.1.0")

        @app.get("/api/v1/middleware-test")
        async def middleware_test():
            return {"middleware": "working"}

        with TestClient(app) as client:
            response = client.get("/api/v1/middleware-test")

            assert response.status_code == 200
            assert response.headers["X-API-Version"] == "v1"
            assert response.headers["X-App-Version"] == "0.1.0"
            # CORS headers are only present for preflight requests (OPTIONS)
            # Test an OPTIONS request to verify CORS is working
            options_response = client.options(
                "/api/v1/middleware-test",
                headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
            )
            assert "access-control-allow-origin" in options_response.headers

    def test_preserves_original_response_body_and_status(self, app_with_versioning):
        """Test that middleware preserves original response characteristics."""
        app = FastAPI()
        app.add_middleware(APIVersionMiddleware, api_version="v1", app_version="0.1.0")

        @app.get("/api/v1/status-test")
        async def status_test():
            from fastapi import status
            from fastapi.responses import JSONResponse

            return JSONResponse(content={"custom": "response"}, status_code=status.HTTP_201_CREATED)

        with TestClient(app) as client:
            response = client.get("/api/v1/status-test")

            assert response.status_code == 201  # Original status preserved
            assert response.json() == {"custom": "response"}  # Original body preserved
            assert response.headers["X-API-Version"] == "v1"  # Headers added
            assert response.headers["X-App-Version"] == "0.1.0"

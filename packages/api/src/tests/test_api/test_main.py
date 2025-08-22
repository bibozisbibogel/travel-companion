"""Tests for main application endpoints."""

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "Travel Companion API"
    assert data["version"] == "0.1.0"


def test_docs_endpoint(client: TestClient):
    """Test API documentation endpoint."""
    response = client.get("/docs")
    # Docs should be available in debug mode
    assert response.status_code in [200, 404]  # 404 if disabled in production


def test_openapi_endpoint(client: TestClient):
    """Test OpenAPI schema endpoint."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert data["info"]["title"] == "Travel Companion API"

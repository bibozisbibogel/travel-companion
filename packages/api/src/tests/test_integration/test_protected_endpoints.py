"""Integration tests for protected endpoints and authentication middleware."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from jose import jwt

from travel_companion.core.config import get_settings
from travel_companion.core.security import create_access_token


class TestProtectedEndpoints:
    """Test protected endpoint authentication middleware."""

    def test_get_current_user_success(self, client: TestClient, sample_user):
        """Test successful access to protected endpoint with valid token."""
        # Arrange
        user_id = str(sample_user.user_id)
        access_token = create_access_token(data={"sub": user_id, "email": sample_user.email})

        # Mock the user service using dependency override
        mock_user_service = Mock()
        mock_user_service.get_user_by_id = AsyncMock(return_value=sample_user)

        from travel_companion.api.deps import get_user_service
        from travel_companion.main import app

        # Override the dependency
        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        try:
            # Act
            response = client.get(
                "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["user_id"] == str(sample_user.user_id)
            assert data["email"] == sample_user.email
            assert data["first_name"] == sample_user.first_name
            assert data["last_name"] == sample_user.last_name
            assert "password_hash" not in data  # Ensure sensitive data is not included
        finally:
            # Clean up override
            app.dependency_overrides.clear()

    def test_protected_endpoint_missing_token(self, client: TestClient):
        """Test protected endpoint access without token returns 403."""
        # Act
        response = client.get("/api/v1/users/me")

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_protected_endpoint_invalid_token_format(self, client: TestClient):
        """Test protected endpoint with malformed token."""
        # Mock user service (won't be called but prevents DB initialization)
        mock_user_service = Mock()

        from travel_companion.api.deps import get_user_service
        from travel_companion.main import app

        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        try:
            # Act
            response = client.get(
                "/api/v1/users/me", headers={"Authorization": "Bearer invalid-token-format"}
            )

            # Assert
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            data = response.json()
            assert data["detail"] == "Could not validate credentials"
        finally:
            app.dependency_overrides.clear()

    def test_protected_endpoint_expired_token(self, client: TestClient, sample_user):
        """Test protected endpoint with expired token."""
        # Arrange
        settings = get_settings()
        expired_time = datetime.now(UTC) - timedelta(minutes=30)

        # Create expired token
        to_encode = {
            "sub": str(sample_user.user_id),
            "email": sample_user.email,
            "exp": expired_time,
        }
        expired_token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

        # Mock user service (won't be called but prevents DB initialization)
        mock_user_service = Mock()

        from travel_companion.api.deps import get_user_service
        from travel_companion.main import app

        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        try:
            # Act
            response = client.get(
                "/api/v1/users/me", headers={"Authorization": f"Bearer {expired_token}"}
            )

            # Assert
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            app.dependency_overrides.clear()

    def test_protected_endpoint_invalid_user_id_in_token(self, client: TestClient):
        """Test protected endpoint with invalid user ID format in token."""
        # Arrange - Create token with invalid UUID
        access_token = create_access_token(
            data={"sub": "invalid-uuid", "email": "test@example.com"}
        )

        # Mock user service (won't be called but prevents DB initialization)
        mock_user_service = Mock()

        from travel_companion.api.deps import get_user_service
        from travel_companion.main import app

        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        try:
            # Act
            response = client.get(
                "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
            )

            # Assert
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            app.dependency_overrides.clear()

    def test_protected_endpoint_user_not_found(self, client: TestClient):
        """Test protected endpoint when user in token doesn't exist in database."""
        # Arrange
        non_existent_user_id = str(uuid4())
        access_token = create_access_token(
            data={"sub": non_existent_user_id, "email": "nonexistent@example.com"}
        )

        # Mock user service to return None (user not found)
        mock_user_service = Mock()
        mock_user_service.get_user_by_id = AsyncMock(return_value=None)

        from travel_companion.api.deps import get_user_service
        from travel_companion.main import app

        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        try:
            # Act
            response = client.get(
                "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
            )

            # Assert
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            app.dependency_overrides.clear()

    def test_protected_endpoint_wrong_authorization_scheme(self, client: TestClient):
        """Test protected endpoint with wrong authorization scheme."""
        # Arrange
        access_token = create_access_token(data={"sub": str(uuid4()), "email": "test@example.com"})

        # Act - Use "Basic" instead of "Bearer"
        response = client.get(
            "/api/v1/users/me", headers={"Authorization": f"Basic {access_token}"}
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_protected_endpoint_database_error(self, client: TestClient, sample_user):
        """Test protected endpoint when database error occurs during user lookup."""
        # Arrange
        access_token = create_access_token(
            data={"sub": str(sample_user.user_id), "email": sample_user.email}
        )

        # Mock user service to raise database error
        mock_user_service = Mock()
        mock_user_service.get_user_by_id = AsyncMock(
            side_effect=Exception("Database connection error")
        )

        from travel_companion.api.deps import get_user_service
        from travel_companion.main import app

        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        try:
            # Act
            response = client.get(
                "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
            )

            # Assert
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            app.dependency_overrides.clear()

    def test_token_with_missing_sub_claim(self, client: TestClient):
        """Test token without required 'sub' claim."""
        # Arrange - Create token without 'sub' claim
        settings = get_settings()
        to_encode = {"email": "test@example.com", "exp": datetime.now(UTC) + timedelta(minutes=30)}
        token_without_sub = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

        # Mock user service (won't be called but prevents DB initialization)
        mock_user_service = Mock()

        from travel_companion.api.deps import get_user_service
        from travel_companion.main import app

        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        try:
            # Act
            response = client.get(
                "/api/v1/users/me", headers={"Authorization": f"Bearer {token_without_sub}"}
            )

            # Assert
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            app.dependency_overrides.clear()

    def test_token_with_empty_credentials(self, client: TestClient):
        """Test with empty bearer token."""
        # Act
        response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer "})

        # Assert - HTTPBearer returns 403 for empty credentials
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_multiple_protected_endpoint_calls_same_token(self, client: TestClient, sample_user):
        """Test multiple calls to protected endpoint with same valid token."""
        # Arrange
        access_token = create_access_token(
            data={"sub": str(sample_user.user_id), "email": sample_user.email}
        )

        mock_user_service = Mock()
        mock_user_service.get_user_by_id = AsyncMock(return_value=sample_user)

        from travel_companion.api.deps import get_user_service
        from travel_companion.main import app

        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        try:
            # Act - Make multiple calls
            response1 = client.get(
                "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
            )
            response2 = client.get(
                "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
            )

            # Assert
            assert response1.status_code == status.HTTP_200_OK
            assert response2.status_code == status.HTTP_200_OK
            assert response1.json()["user_id"] == response2.json()["user_id"]

            # Verify user service was called twice
            assert mock_user_service.get_user_by_id.call_count == 2
        finally:
            app.dependency_overrides.clear()

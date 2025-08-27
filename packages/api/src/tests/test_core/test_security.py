"""Tests for security utilities."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from jose import jwt

from travel_companion.core.security import (
    create_access_token,
    get_user_id_from_token,
    hash_password,
    verify_password,
    verify_token,
)


class TestPasswordHashing:
    """Test cases for password hashing functions."""

    def test_hash_password_creates_hash(self):
        """Test that hash_password creates a hash."""
        password = "SecurePassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash format

    def test_hash_password_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "SecurePassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2

    def test_verify_password_correct_password(self):
        """Test password verification with correct password."""
        password = "SecurePassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect_password(self):
        """Test password verification with incorrect password."""
        password = "SecurePassword123"
        wrong_password = "WrongPassword456"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_strings(self):
        """Test password verification with empty strings."""
        # Empty hash should return False
        assert verify_password("password", "") is False

        # Test with actual hash for empty password verification
        password = "test"
        hashed = hash_password(password)
        assert verify_password("", hashed) is False


class TestJWTTokens:
    """Test cases for JWT token functions."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for JWT."""
        with patch("travel_companion.core.security.settings") as mock:
            mock.secret_key = "test-secret-key"
            mock.algorithm = "HS256"
            mock.access_token_expire_minutes = 30
            yield mock

    def test_create_access_token_with_data(self, mock_settings):
        """Test creating access token with user data."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        assert token is not None
        assert len(token) > 0

        # Verify token can be decoded
        payload = jwt.decode(token, mock_settings.secret_key, algorithms=[mock_settings.algorithm])
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload

    def test_create_access_token_with_custom_expiration(self, mock_settings):
        """Test creating access token with custom expiration."""
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=60)

        token = create_access_token(data, expires_delta)

        payload = jwt.decode(token, mock_settings.secret_key, algorithms=[mock_settings.algorithm])

        # Check that expiration is roughly 60 minutes from now
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        now = datetime.now(UTC)
        time_diff = exp_time - now

        # Should be around 60 minutes (with some tolerance for test execution time)
        assert 59 < time_diff.total_seconds() / 60 < 61

    def test_create_access_token_default_expiration(self, mock_settings):
        """Test creating access token with default expiration."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        payload = jwt.decode(token, mock_settings.secret_key, algorithms=[mock_settings.algorithm])

        # Check that expiration uses default settings
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        now = datetime.now(UTC)
        time_diff = exp_time - now

        # Should be around 30 minutes (default)
        assert 29 < time_diff.total_seconds() / 60 < 31

    def test_verify_token_valid_token(self, mock_settings):
        """Test verifying a valid token."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        payload = verify_token(token)

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"

    def test_verify_token_invalid_token(self, mock_settings):
        """Test verifying an invalid token."""
        invalid_token = "invalid.token.here"

        payload = verify_token(invalid_token)

        assert payload is None

    def test_verify_token_expired_token(self, mock_settings):
        """Test verifying an expired token."""
        data = {"sub": "user123"}
        # Create token that expires immediately
        expired_delta = timedelta(seconds=-1)
        token = create_access_token(data, expired_delta)

        payload = verify_token(token)

        assert payload is None

    def test_verify_token_wrong_secret(self, mock_settings):
        """Test verifying token with wrong secret."""
        data = {"sub": "user123"}

        # Create token with one secret
        token = jwt.encode(data, "wrong-secret", algorithm="HS256")

        # Try to verify with different secret (from mock_settings)
        payload = verify_token(token)

        assert payload is None

    def test_get_user_id_from_token_valid(self, mock_settings):
        """Test extracting user ID from valid token."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        user_id = get_user_id_from_token(token)

        assert user_id == "user123"

    def test_get_user_id_from_token_invalid(self, mock_settings):
        """Test extracting user ID from invalid token."""
        invalid_token = "invalid.token.here"

        user_id = get_user_id_from_token(invalid_token)

        assert user_id is None

    def test_get_user_id_from_token_no_sub(self, mock_settings):
        """Test extracting user ID from token without sub claim."""
        data = {"email": "test@example.com"}  # No 'sub' field
        token = create_access_token(data)

        user_id = get_user_id_from_token(token)

        assert user_id is None


class TestEdgeCases:
    """Test edge cases and security scenarios."""

    def test_hash_password_unicode_characters(self):
        """Test password hashing with unicode characters."""
        password = "Пароль123!@#"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("WrongПароль", hashed) is False

    def test_hash_password_very_long_password(self):
        """Test password hashing with very long password."""
        password = "a" * 1000
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_create_token_empty_data(self, mock_settings):
        """Test creating token with empty data."""
        with patch("travel_companion.core.security.settings") as mock:
            mock.secret_key = "test-secret-key"
            mock.algorithm = "HS256"
            mock.access_token_expire_minutes = 30

            token = create_access_token({})

            assert token is not None
            payload = verify_token(token)
            assert payload is not None
            assert "exp" in payload

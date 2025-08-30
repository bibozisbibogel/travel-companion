"""Tests for CORS configuration functionality."""

from travel_companion.core.config import Settings


class TestCORSConfiguration:
    """Test CORS configuration and environment handling."""

    def test_default_cors_settings(self):
        """Test default CORS configuration values."""
        settings = Settings()

        # Test default origins
        expected_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ]
        assert settings.allowed_origins == expected_origins

        # Test default methods
        expected_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
        assert settings.allowed_methods == expected_methods

        # Test default headers
        expected_headers = [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Client-Version",
            "X-API-Key",
            "Cache-Control",
        ]
        assert settings.allowed_headers == expected_headers

        # Test other defaults
        assert settings.allow_credentials is True
        assert settings.max_age == 86400

    def test_development_environment_cors(self):
        """Test CORS configuration for development environment."""
        settings = Settings(environment="development")

        origins = settings.get_cors_origins_for_environment()
        methods = settings.get_cors_methods_for_environment()

        # Development should allow localhost
        assert any("localhost" in origin for origin in origins)
        assert any("127.0.0.1" in origin for origin in origins)

        # Development should allow all methods
        assert "HEAD" in methods
        assert "OPTIONS" in methods
        assert len(methods) >= 6  # Should have all development methods

    def test_staging_environment_cors(self):
        """Test CORS configuration for staging environment."""
        settings = Settings(environment="staging")

        settings.get_cors_origins_for_environment()
        settings.get_cors_methods_for_environment()

        # Staging should allow localhost for testing + staging domains
        staging_origins = settings.get_cors_origins_for_environment()
        assert any("localhost" in origin for origin in staging_origins)

        # Should include staging domains if not custom configured
        if len(settings.allowed_origins) == 4:  # Default config
            assert any("staging" in origin.lower() for origin in staging_origins)

    def test_production_environment_cors(self):
        """Test CORS configuration for production environment."""
        settings = Settings(environment="production")

        origins = settings.get_cors_origins_for_environment()
        methods = settings.get_cors_methods_for_environment()

        # Production should not have localhost by default
        assert not any("localhost" in origin for origin in origins)

        # Production should have production domains
        assert any("travel-companion.com" in origin for origin in origins)

        # Production should be more restrictive with methods (no HEAD/OPTIONS explicitly)
        assert len(methods) < len(settings.allowed_methods)

    def test_cors_debug_enabled(self):
        """Test CORS debug configuration."""
        # Debug should be enabled in development with debug=True
        settings = Settings(environment="development", debug=True)
        assert settings.is_cors_debug_enabled() is True

        # Debug should be disabled in development with debug=False
        settings = Settings(environment="development", debug=False)
        assert settings.is_cors_debug_enabled() is False

        # Debug should be disabled in production regardless of debug flag
        settings = Settings(environment="production", debug=True)
        assert settings.is_cors_debug_enabled() is False

    def test_cors_origins_from_env_json(self):
        """Test parsing CORS origins from JSON environment variable."""
        json_origins = '["https://example.com", "https://api.example.com"]'
        settings = Settings(allowed_origins=json_origins)

        assert settings.allowed_origins == ["https://example.com", "https://api.example.com"]

    def test_cors_origins_from_env_csv(self):
        """Test parsing CORS origins from CSV environment variable."""
        csv_origins = "https://example.com,https://api.example.com,http://localhost:3000"
        settings = Settings(allowed_origins=csv_origins)

        expected = ["https://example.com", "https://api.example.com", "http://localhost:3000"]
        assert settings.allowed_origins == expected

    def test_cors_methods_from_env_json(self):
        """Test parsing CORS methods from JSON environment variable."""
        json_methods = '["GET", "POST", "PUT"]'
        settings = Settings(allowed_methods=json_methods)

        assert settings.allowed_methods == ["GET", "POST", "PUT"]

    def test_cors_methods_from_env_csv(self):
        """Test parsing CORS methods from CSV environment variable."""
        csv_methods = "get,post,put,delete"  # Test case insensitive
        settings = Settings(allowed_methods=csv_methods)

        assert settings.allowed_methods == ["GET", "POST", "PUT", "DELETE"]

    def test_cors_headers_from_env_json(self):
        """Test parsing CORS headers from JSON environment variable."""
        json_headers = '["Content-Type", "Authorization", "X-Custom-Header"]'
        settings = Settings(allowed_headers=json_headers)

        assert settings.allowed_headers == ["Content-Type", "Authorization", "X-Custom-Header"]

    def test_cors_headers_from_env_csv(self):
        """Test parsing CORS headers from CSV environment variable."""
        csv_headers = "Content-Type,Authorization,X-Custom-Header"
        settings = Settings(allowed_headers=csv_headers)

        expected = ["Content-Type", "Authorization", "X-Custom-Header"]
        assert settings.allowed_headers == expected

    def test_cors_empty_env_fallback(self):
        """Test that empty environment variables fall back to defaults."""
        # Empty string should use defaults
        settings = Settings(allowed_origins="", allowed_methods="", allowed_headers="")

        # Should fall back to default values
        assert len(settings.allowed_origins) == 4  # Default localhost origins
        assert len(settings.allowed_methods) >= 6  # Default methods
        assert len(settings.allowed_headers) >= 8  # Default headers

    def test_cors_invalid_json_fallback(self):
        """Test that invalid JSON falls back to CSV parsing."""
        # Invalid JSON should be parsed as CSV
        invalid_json = "https://example.com,https://api.example.com"
        settings = Settings(allowed_origins=invalid_json)

        assert "https://example.com" in settings.allowed_origins
        assert "https://api.example.com" in settings.allowed_origins

    def test_custom_origins_override_environment_defaults(self):
        """Test that custom origins override environment defaults."""
        custom_origins = ["https://custom.com", "https://app.custom.com"]

        # Production with custom origins should use custom, not production defaults
        settings = Settings(environment="production", allowed_origins=custom_origins)
        prod_origins = settings.get_cors_origins_for_environment()

        # Should use custom origins instead of production defaults
        assert prod_origins == custom_origins

    def test_cors_settings_immutability(self):
        """Test that CORS settings maintain expected types."""
        settings = Settings()

        # Test that all CORS settings are proper types
        assert isinstance(settings.allowed_origins, list)
        assert isinstance(settings.allowed_methods, list)
        assert isinstance(settings.allowed_headers, list)
        assert isinstance(settings.allow_credentials, bool)
        assert isinstance(settings.max_age, int)

        # Test that list items are strings
        assert all(isinstance(origin, str) for origin in settings.allowed_origins)
        assert all(isinstance(method, str) for method in settings.allowed_methods)
        assert all(isinstance(header, str) for header in settings.allowed_headers)


class TestCORSValidationEdgeCases:
    """Test CORS configuration edge cases and validation."""

    def test_cors_origins_whitespace_handling(self):
        """Test that whitespace in origins is handled correctly."""
        origins_with_spaces = " https://example.com , https://api.example.com , "
        settings = Settings(allowed_origins=origins_with_spaces)

        # Should strip whitespace and filter empty strings
        assert settings.allowed_origins == ["https://example.com", "https://api.example.com"]

    def test_cors_methods_uppercase_normalization(self):
        """Test that HTTP methods are normalized to uppercase."""
        lowercase_methods = "get,post,put"
        settings = Settings(allowed_methods=lowercase_methods)

        assert settings.allowed_methods == ["GET", "POST", "PUT"]

    def test_cors_empty_list_handling(self):
        """Test handling of empty lists in configuration."""
        settings = Settings(allowed_origins=[], allowed_methods=[], allowed_headers=[])

        # Empty lists should be preserved (may be intentional)
        assert settings.allowed_origins == []
        assert settings.allowed_methods == []
        assert settings.allowed_headers == []

    def test_cors_single_value_handling(self):
        """Test handling of single values (non-list) in configuration."""
        # Single string should be converted to list
        settings = Settings(allowed_origins="https://single.com")
        assert settings.allowed_origins == ["https://single.com"]

    def test_cors_environment_case_sensitivity(self):
        """Test that environment names are handled correctly."""
        # Test various case combinations
        prod_settings = Settings(environment="PRODUCTION")
        assert prod_settings.environment == "PRODUCTION"

        # Environment-specific logic should still work
        origins = prod_settings.get_cors_origins_for_environment()
        assert not any("localhost" in origin for origin in origins)

    def test_cors_max_age_validation(self):
        """Test CORS max-age configuration."""
        settings = Settings(max_age=3600)  # 1 hour
        assert settings.max_age == 3600

        # Test default
        default_settings = Settings()
        assert default_settings.max_age == 86400  # 24 hours

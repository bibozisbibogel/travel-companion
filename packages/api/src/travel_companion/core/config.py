"""Application configuration settings."""

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Travel Companion API"
    debug: bool = False
    version: str = "0.1.0"
    environment: str = "development"  # development, staging, production

    # CORS Configuration
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",  # Additional dev port
        "http://127.0.0.1:3001",
    ]
    allowed_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
    allowed_headers: list[str] = [
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
    allow_credentials: bool = True
    max_age: int = 86400  # 24 hours for preflight cache

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from environment variable or default."""
        if isinstance(v, str):
            # Return default for empty strings
            if not v.strip():
                return [
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                    "http://localhost:3001",
                    "http://127.0.0.1:3001",
                ]
            # Handle JSON string from environment variable
            import json

            try:
                parsed = json.loads(v)
                return list(parsed) if isinstance(parsed, list) else [str(parsed)]
            except json.JSONDecodeError:
                # Handle comma-separated string
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        else:
            return [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3001",
            ]

    @field_validator("allowed_methods", mode="before")
    @classmethod
    def parse_cors_methods(cls, v: Any) -> list[str]:
        """Parse CORS methods from environment variable or default."""
        if isinstance(v, str):
            if not v.strip():
                return ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
            import json

            try:
                parsed = json.loads(v)
                return list(parsed) if isinstance(parsed, list) else [str(parsed)]
            except json.JSONDecodeError:
                return [method.strip().upper() for method in v.split(",") if method.strip()]
        elif isinstance(v, list):
            return [method.upper() for method in v]
        else:
            return ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]

    @field_validator("allowed_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v: Any) -> list[str]:
        """Parse CORS headers from environment variable or default."""
        if isinstance(v, str):
            if not v.strip():
                return [
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
            import json

            try:
                parsed = json.loads(v)
                return list(parsed) if isinstance(parsed, list) else [str(parsed)]
            except json.JSONDecodeError:
                return [header.strip() for header in v.split(",") if header.strip()]
        elif isinstance(v, list):
            return v
        else:
            return [
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

    # Database
    database_url: str = ""
    supabase_url: str = ""
    supabase_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379"

    # External APIs
    amadeus_api_key: str = ""
    amadeus_api_secret: str = ""
    booking_api_key: str = ""
    tripadvisor_api_key: str = ""
    openai_api_key: str = ""

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # LangGraph Workflow Configuration
    workflow_timeout_seconds: int = 300
    workflow_max_retries: int = 3
    workflow_state_ttl: int = 3600
    workflow_enable_debug_logging: bool = False

    def get_cors_origins_for_environment(self) -> list[str]:
        """Get CORS origins based on environment."""
        # Check if origins were explicitly set (not default)
        default_dev_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ]

        # If custom origins are set (different from default), always use them
        if self.allowed_origins != default_dev_origins:
            return self.allowed_origins

        if self.environment.lower() == "production":
            # Production should have explicit origins set via environment variables
            # Never use wildcard in production
            return [
                "https://travel-companion.com",
                "https://www.travel-companion.com",
                "https://app.travel-companion.com",
            ]

        elif self.environment.lower() == "staging":
            # Staging environment origins
            return [
                "https://staging.travel-companion.com",
                "https://test.travel-companion.com",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]

        else:
            # Development environment - use configured origins or defaults
            return self.allowed_origins

    def get_cors_methods_for_environment(self) -> list[str]:
        """Get CORS methods based on environment."""
        if self.environment.lower() == "production":
            # Production - be more restrictive, no HEAD/OPTIONS needed explicitly
            return ["GET", "POST", "PUT", "DELETE", "PATCH"]
        else:
            # Development/Staging - allow all methods for easier debugging
            return self.allowed_methods

    def is_cors_debug_enabled(self) -> bool:
        """Check if CORS debug logging should be enabled."""
        return self.environment.lower() == "development" and self.debug


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

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

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from environment variable or default."""
        if isinstance(v, str):
            # Handle JSON string from environment variable
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Handle comma-separated string
                return [origin.strip() for origin in v.split(",")]
        elif isinstance(v, list):
            return v
        else:
            return ["http://localhost:3000", "http://127.0.0.1:3000"]

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


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

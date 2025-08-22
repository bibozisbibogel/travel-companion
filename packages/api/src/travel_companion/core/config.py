"""Application configuration settings."""

from functools import lru_cache

from pydantic import Field
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
    debug: bool = Field(default=False, env="DEBUG")
    version: str = "0.1.0"

    # CORS
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        env="ALLOWED_ORIGINS"
    )

    # Database
    database_url: str = Field(env="DATABASE_URL", default="")
    supabase_url: str = Field(env="SUPABASE_URL", default="")
    supabase_key: str = Field(env="SUPABASE_ANON_KEY", default="")

    # Redis
    redis_url: str = Field(env="REDIS_URL", default="redis://localhost:6379")

    # External APIs
    amadeus_api_key: str = Field(env="AMADEUS_API_KEY", default="")
    amadeus_api_secret: str = Field(env="AMADEUS_API_SECRET", default="")

    booking_api_key: str = Field(env="BOOKING_API_KEY", default="")

    tripadvisor_api_key: str = Field(env="TRIPADVISOR_API_KEY", default="")

    openai_api_key: str = Field(env="OPENAI_API_KEY", default="")

    # Security
    secret_key: str = Field(env="SECRET_KEY", default="your-secret-key-change-in-production")
    access_token_expire_minutes: int = Field(env="ACCESS_TOKEN_EXPIRE_MINUTES", default=30)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

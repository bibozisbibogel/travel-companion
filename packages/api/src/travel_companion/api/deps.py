"""FastAPI dependencies."""

from collections.abc import Generator

from travel_companion.core.config import get_settings


def get_current_settings() -> Generator:
    """Get current application settings."""
    settings = get_settings()
    try:
        yield settings
    finally:
        pass

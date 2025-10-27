"""Coordinate models for geocoding support."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """
    Geographic coordinates with geocoding metadata.

    Added in Story 3.6: Geocoding Integration.
    """

    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate (-90 to 90)")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate (-180 to 180)")
    geocoding_status: Literal["success", "failed", "pending"] = Field(
        ..., description="Status of geocoding operation"
    )
    geocoded_at: datetime | None = Field(None, description="Timestamp when geocoding was performed")
    geocoding_error_message: str | None = Field(
        None, description="Error message if geocoding failed"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "latitude": 41.9009,
                "longitude": 12.4833,
                "geocoding_status": "success",
                "geocoded_at": "2025-10-26T14:30:00Z",
                "geocoding_error_message": None,
            }
        }
    }

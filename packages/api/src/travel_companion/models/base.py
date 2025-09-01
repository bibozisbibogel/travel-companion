"""Base response models for standardized API responses."""

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer

# Type variable for generic response data
T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Standardized API response wrapper."""

    success: bool = Field(..., description="Whether the request was successful")
    data: T | None = Field(None, description="Response data")
    message: str = Field(default="", description="Response message")
    error_code: str | None = Field(None, description="Error code for failed requests")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        """Serialize timestamp to ISO format string."""
        return value.isoformat()


class SuccessResponse(BaseResponse[T]):
    """Standardized success response."""

    success: bool = Field(default=True, description="Success flag")
    error_code: str | None = Field(default=None, description="Error code for failed requests")


class ErrorResponse(BaseResponse[dict[str, Any]]):
    """Standardized error response."""

    success: bool = Field(default=False, description="Success flag")
    data: dict[str, Any] | None = Field(default=None, description="Error details")
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, le=100, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class PaginatedResponse(BaseResponse[T]):
    """Standardized paginated response."""

    success: bool = Field(default=True, description="Success flag")
    data: T = Field(..., description="Response data")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    error_code: str | None = Field(default=None, description="Error code for failed requests")


class IDResponse(BaseModel):
    """Response containing an ID."""

    id: UUID = Field(..., description="Entity ID")


class StatusResponse(BaseModel):
    """Simple status response."""

    status: str = Field(..., description="Status message")
    details: dict[str, Any] | None = Field(None, description="Additional status details")

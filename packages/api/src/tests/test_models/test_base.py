"""Tests for base response models."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from travel_companion.models.base import (
    BaseResponse,
    ErrorResponse,
    IDResponse,
    PaginatedResponse,
    PaginationMeta,
    StatusResponse,
    SuccessResponse,
)


class TestBaseResponse:
    """Test BaseResponse model."""

    def test_base_response_creation(self):
        """Test creating a base response with data."""
        response = BaseResponse[dict](
            success=True,
            data={"key": "value"},
            message="Test message"
        )

        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.message == "Test message"
        assert response.error_code is None
        assert isinstance(response.timestamp, datetime)

    def test_base_response_without_data(self):
        """Test creating a base response without data."""
        response = BaseResponse[None](
            success=False,
            message="Error occurred",
            error_code="TEST_ERROR"
        )

        assert response.success is False
        assert response.data is None
        assert response.message == "Error occurred"
        assert response.error_code == "TEST_ERROR"

    def test_base_response_serialization(self):
        """Test base response serialization to dict."""
        response = BaseResponse[dict](
            success=True,
            data={"test": "data"},
            message="Success"
        )

        data = response.model_dump()
        assert "success" in data
        assert "data" in data
        assert "message" in data
        assert "timestamp" in data
        assert data["success"] is True
        assert data["data"] == {"test": "data"}


class TestSuccessResponse:
    """Test SuccessResponse model."""

    def test_success_response_defaults(self):
        """Test success response default values."""
        response = SuccessResponse[dict](data={"result": "ok"})

        assert response.success is True
        assert response.data == {"result": "ok"}
        assert response.message == ""  # Default empty message
        assert response.error_code is None

    def test_success_response_with_message(self):
        """Test success response with custom message."""
        response = SuccessResponse[dict](
            data={"result": "ok"},
            message="Operation completed successfully"
        )

        assert response.success is True
        assert response.message == "Operation completed successfully"

    def test_success_response_type_safety(self):
        """Test success response maintains type safety."""
        response = SuccessResponse[list[str]](
            data=["item1", "item2"],
            message="Items retrieved"
        )

        assert isinstance(response.data, list)
        assert all(isinstance(item, str) for item in response.data)


class TestErrorResponse:
    """Test ErrorResponse model."""

    def test_error_response_creation(self):
        """Test creating an error response."""
        response = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Validation failed"
        )

        assert response.success is False
        assert response.data is None
        assert response.error_code == "VALIDATION_ERROR"
        assert response.message == "Validation failed"

    def test_error_response_required_fields(self):
        """Test that error response requires error_code and message."""
        with pytest.raises(ValidationError):
            ErrorResponse()  # Missing required fields

        with pytest.raises(ValidationError):
            ErrorResponse(message="Test")  # Missing error_code

        with pytest.raises(ValidationError):
            ErrorResponse(error_code="TEST")  # Missing message

    def test_error_response_immutable_success_field(self):
        """Test that success field is always False for error responses."""
        response = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test message"
        )

        assert response.success is False  # Should always be False

    def test_error_response_with_data(self):
        """Test error response with additional error details."""
        error_details = {
            "errors": [
                {"field": "email", "message": "Invalid format"},
                {"field": "password", "message": "Too short"}
            ]
        }

        response = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Validation failed for 2 field(s)",
            data=error_details
        )

        assert response.success is False
        assert response.data == error_details
        assert response.error_code == "VALIDATION_ERROR"
        assert "2 field(s)" in response.message

    def test_error_response_edge_cases(self):
        """Test error response edge cases."""
        # None values for required fields should raise validation error
        with pytest.raises(ValidationError):
            ErrorResponse(error_code=None, message="Test")

        with pytest.raises(ValidationError):
            ErrorResponse(error_code="TEST", message=None)

        # Empty strings are valid for error_code and message
        response = ErrorResponse(error_code="", message="")
        assert response.error_code == ""
        assert response.message == ""
        assert response.success is False


class TestPaginationMeta:
    """Test PaginationMeta model."""

    def test_pagination_meta_creation(self):
        """Test creating pagination metadata."""
        meta = PaginationMeta(
            page=2,
            per_page=10,
            total_items=45,
            total_pages=5,
            has_next=True,
            has_prev=True
        )

        assert meta.page == 2
        assert meta.per_page == 10
        assert meta.total_items == 45
        assert meta.total_pages == 5
        assert meta.has_next is True
        assert meta.has_prev is True

    def test_pagination_meta_validation(self):
        """Test pagination metadata validation."""
        # Page must be >= 1
        with pytest.raises(ValidationError):
            PaginationMeta(
                page=0,
                per_page=10,
                total_items=0,
                total_pages=0,
                has_next=False,
                has_prev=False
            )

        # Per page must be >= 1 and <= 100
        with pytest.raises(ValidationError):
            PaginationMeta(
                page=1,
                per_page=0,
                total_items=0,
                total_pages=0,
                has_next=False,
                has_prev=False
            )

        with pytest.raises(ValidationError):
            PaginationMeta(
                page=1,
                per_page=101,
                total_items=0,
                total_pages=0,
                has_next=False,
                has_prev=False
            )

        # Total items must be >= 0
        with pytest.raises(ValidationError):
            PaginationMeta(
                page=1,
                per_page=10,
                total_items=-1,
                total_pages=0,
                has_next=False,
                has_prev=False
            )


class TestPaginatedResponse:
    """Test PaginatedResponse model."""

    def test_paginated_response_creation(self):
        """Test creating a paginated response."""
        data = [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
        pagination = PaginationMeta(
            page=1,
            per_page=2,
            total_items=10,
            total_pages=5,
            has_next=True,
            has_prev=False
        )

        response = PaginatedResponse[list[dict]](
            data=data,
            pagination=pagination,
            message="Items retrieved successfully"
        )

        assert response.success is True
        assert response.data == data
        assert response.pagination.page == 1
        assert response.pagination.total_items == 10
        assert response.message == "Items retrieved successfully"

    def test_paginated_response_empty_data(self):
        """Test paginated response with empty data."""
        pagination = PaginationMeta(
            page=1,
            per_page=10,
            total_items=0,
            total_pages=0,
            has_next=False,
            has_prev=False
        )

        response = PaginatedResponse[list](
            data=[],
            pagination=pagination
        )

        assert response.success is True
        assert response.data == []
        assert response.pagination.total_items == 0


class TestIDResponse:
    """Test IDResponse model."""

    def test_id_response_creation(self):
        """Test creating an ID response."""
        test_id = uuid4()
        response = IDResponse(id=test_id)

        assert response.id == test_id

    def test_id_response_validation(self):
        """Test ID response validation."""
        # Valid UUID string should be accepted
        response = IDResponse(id="550e8400-e29b-41d4-a716-446655440000")
        assert isinstance(response.id, type(uuid4()))

        # Invalid UUID should raise validation error
        with pytest.raises(ValidationError):
            IDResponse(id="not-a-uuid")


class TestStatusResponse:
    """Test StatusResponse model."""

    def test_status_response_simple(self):
        """Test creating a simple status response."""
        response = StatusResponse(status="healthy")

        assert response.status == "healthy"
        assert response.details is None

    def test_status_response_with_details(self):
        """Test creating a status response with details."""
        details = {
            "database": "connected",
            "redis": "connected",
            "uptime": "2h 30m"
        }

        response = StatusResponse(
            status="healthy",
            details=details
        )

        assert response.status == "healthy"
        assert response.details == details

    def test_status_response_required_field(self):
        """Test that status field is required."""
        with pytest.raises(ValidationError):
            StatusResponse()  # Missing required status field

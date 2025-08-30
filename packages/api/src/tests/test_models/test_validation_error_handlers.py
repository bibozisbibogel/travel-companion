"""Tests for validation error handler functions."""

from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.responses import JSONResponse

from travel_companion.main import (
    pydantic_validation_exception_handler,
    validation_exception_handler,
)


class MockRequest:
    """Mock FastAPI Request for testing."""
    pass


class TestValidationExceptionHandler:
    """Test validation exception handler function."""

    def test_validation_exception_handler(self):
        """Test validation exception handler with mock request validation error."""
        # Create a mock RequestValidationError
        errors = [
            {
                "loc": ("name",),
                "msg": "field required",
                "type": "missing",
                "input": {}
            },
            {
                "loc": ("destination", "city"),
                "msg": "ensure this value has at least 1 characters",
                "type": "value_error.any_str.min_length",
                "input": ""
            }
        ]

        exc = RequestValidationError(errors)
        request = MockRequest()

        # Test the handler
        response = validation_exception_handler(request, exc)

        # Since it's async, we need to await it
        import asyncio
        response = asyncio.run(validation_exception_handler(request, exc))

        assert isinstance(response, JSONResponse)
        assert response.status_code == 422

        # Check response content
        content = response.body.decode()
        import json
        data = json.loads(content)

        assert data["success"] is False
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "Validation failed for 2 field(s)" in data["message"]
        assert "errors" in data["data"]
        assert len(data["data"]["errors"]) == 2

        # Check error details
        error_details = data["data"]["errors"]
        assert error_details[0]["field"] == "name"
        assert error_details[0]["message"] == "field required"
        assert error_details[1]["field"] == "destination -> city"
        assert "min_length" in error_details[1]["type"]

    def test_pydantic_validation_exception_handler(self):
        """Test direct Pydantic validation exception handler."""
        from pydantic import BaseModel, Field

        class TestModel(BaseModel):
            name: str = Field(..., min_length=1)
            age: int = Field(..., gt=0)

        # Create validation error by trying to validate invalid data
        try:
            TestModel(name="", age=-5)
        except ValidationError as exc:
            request = MockRequest()

            # Test the handler
            import asyncio
            response = asyncio.run(pydantic_validation_exception_handler(request, exc))

            assert isinstance(response, JSONResponse)
            assert response.status_code == 422

            # Check response content
            content = response.body.decode()
            import json
            data = json.loads(content)

            assert data["success"] is False
            assert data["error_code"] == "VALIDATION_ERROR"
            assert "Model validation failed" in data["message"]
            assert "errors" in data["data"]
            assert len(data["data"]["errors"]) >= 1

            # Check that errors contain field information
            field_paths = [error["field"] for error in data["data"]["errors"]]
            assert any("name" in path for path in field_paths)
            assert any("age" in path for path in field_paths)

    def test_validation_exception_handler_error_formatting(self):
        """Test that validation errors are properly formatted."""
        # Create a nested validation error
        errors = [
            {
                "loc": ("requirements", "budget"),
                "msg": "ensure this value is greater than 0",
                "type": "value_error.number.not_gt",
                "input": -100
            },
            {
                "loc": ("requirements", "travelers"),
                "msg": "ensure this value is greater than or equal to 1",
                "type": "value_error.number.not_ge",
                "input": 0
            }
        ]

        exc = RequestValidationError(errors)
        request = MockRequest()

        import asyncio
        response = asyncio.run(validation_exception_handler(request, exc))

        content = response.body.decode()
        import json
        data = json.loads(content)

        error_details = data["data"]["errors"]

        # Check field path formatting
        assert error_details[0]["field"] == "requirements -> budget"
        assert error_details[0]["input"] == -100
        assert "greater than 0" in error_details[0]["message"]

        assert error_details[1]["field"] == "requirements -> travelers"
        assert error_details[1]["input"] == 0
        assert "greater than or equal to 1" in error_details[1]["message"]

    def test_validation_exception_handler_single_field(self):
        """Test validation exception handler with single field error."""
        errors = [
            {
                "loc": ("email",),
                "msg": "field required",
                "type": "missing"
            }
        ]

        exc = RequestValidationError(errors)
        request = MockRequest()

        import asyncio
        response = asyncio.run(validation_exception_handler(request, exc))

        content = response.body.decode()
        import json
        data = json.loads(content)

        assert "Validation failed for 1 field(s)" in data["message"]
        assert len(data["data"]["errors"]) == 1
        assert data["data"]["errors"][0]["field"] == "email"

    def test_validation_exception_handler_complex_nested_path(self):
        """Test validation exception handler with complex nested field paths."""
        errors = [
            {
                "loc": ("trip_data", "destination", "coordinates", "latitude"),
                "msg": "ensure this value is less than or equal to 90",
                "type": "value_error.number.not_le",
                "input": 95.5
            }
        ]

        exc = RequestValidationError(errors)
        request = MockRequest()

        import asyncio
        response = asyncio.run(validation_exception_handler(request, exc))

        content = response.body.decode()
        import json
        data = json.loads(content)

        error_details = data["data"]["errors"]
        expected_path = "trip_data -> destination -> coordinates -> latitude"
        assert error_details[0]["field"] == expected_path
        assert error_details[0]["input"] == 95.5

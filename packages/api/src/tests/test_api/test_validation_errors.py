"""Tests for Pydantic validation error handling."""


class TestValidationErrorHandling:
    """Test validation error handling middleware."""

    def test_request_validation_error_handling(self, authenticated_client) -> None:
        """Test handling of FastAPI RequestValidationError."""

        # Send invalid data to a validated endpoint - missing required fields
        response = authenticated_client.post(
            "/api/v1/trips/",
            json={},  # Missing required fields
        )

        assert response.status_code == 422
        data = response.json()

        # Check standardized error response format
        assert data["success"] is False
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "Validation failed" in data["message"]
        assert "field(s)" in data["message"]
        assert "data" in data
        assert "errors" in data["data"]
        assert isinstance(data["data"]["errors"], list)
        assert len(data["data"]["errors"]) > 0

        # Check error detail structure
        error_detail = data["data"]["errors"][0]
        assert "field" in error_detail
        assert "message" in error_detail
        assert "type" in error_detail

    def test_request_validation_error_with_field_details(self, authenticated_client) -> None:
        """Test validation error with specific field validation failures."""

        # Send data with invalid field types/values
        response = authenticated_client.post(
            "/api/v1/trips/",
            json={
                "name": "",  # Empty name should fail validation
                "destination": {
                    "city": "",  # Empty city should fail
                    "country": "France",
                    "country_code": "FR",
                },
                "requirements": {
                    "budget": -100,  # Negative budget should fail
                    "start_date": "2024-06-01",
                    "end_date": "2024-05-01",  # End before start should fail
                    "travelers": 0,  # Zero travelers should fail
                },
            },
        )

        assert response.status_code == 422
        data = response.json()

        assert data["success"] is False
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "errors" in data["data"]

        # Should have multiple validation errors
        errors = data["data"]["errors"]
        assert len(errors) > 1

        # Check that field paths are properly formatted
        field_paths = [error["field"] for error in errors]
        assert any("name" in path for path in field_paths)

    def test_request_validation_error_with_nested_fields(self, authenticated_client) -> None:
        """Test validation errors in nested model structures."""

        response = authenticated_client.post(
            "/api/v1/trips/",
            json={
                "name": "Test Trip",
                "destination": {
                    "city": "Paris",
                    "country": "France",
                    "country_code": "FR",
                    "latitude": 91,  # Invalid latitude > 90
                },
                "requirements": {
                    "budget": 1000,
                    "currency": "eur",  # Should be uppercase
                    "start_date": "2024-06-01",
                    "end_date": "2024-06-07",
                    "travelers": 2,
                },
            },
        )

        assert response.status_code == 422
        data = response.json()

        # Check nested field error paths
        errors = data["data"]["errors"]
        field_paths = [error["field"] for error in errors]

        # Should have nested path for latitude error
        assert any("destination" in path and "latitude" in path for path in field_paths)
        # Should have nested path for currency error
        assert any("requirements" in path and "currency" in path for path in field_paths)

    def test_validation_error_response_format(self, authenticated_client) -> None:
        """Test that validation error response follows standardized format."""

        response = authenticated_client.post("/api/v1/trips/", json={"invalid": "data"})

        assert response.status_code == 422
        data = response.json()

        # Verify complete response structure
        required_fields = ["success", "data", "message", "error_code", "timestamp"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        assert data["success"] is False
        assert isinstance(data["timestamp"], str)
        assert data["error_code"] == "VALIDATION_ERROR"
        assert isinstance(data["message"], str)
        assert isinstance(data["data"], dict)
        assert "errors" in data["data"]

    def test_validation_error_message_count(self, authenticated_client) -> None:
        """Test that error message includes correct error count."""

        # Create request with multiple validation errors
        response = authenticated_client.post(
            "/api/v1/trips/",
            json={
                "name": "",  # Error 1: empty name
                "destination": {
                    "city": "",  # Error 2: empty city
                    "country": "",  # Error 3: empty country
                    "country_code": "",  # Error 4: empty country code
                },
                "requirements": {
                    "budget": 0,  # Error 5: zero budget
                    "start_date": "invalid-date",  # Error 6: invalid date
                    "end_date": "2024-06-07",
                    "travelers": -1,  # Error 7: negative travelers
                },
            },
        )

        assert response.status_code == 422
        data = response.json()

        error_count = len(data["data"]["errors"])
        assert f"{error_count} field(s)" in data["message"]

    def test_valid_request_no_validation_error(self, authenticated_client) -> None:
        """Test that valid requests don't trigger validation errors."""

        # This might fail due to other business logic, but shouldn't have validation errors
        response = authenticated_client.post(
            "/api/v1/trips/",
            json={
                "name": "Valid Trip",
                "destination": {"city": "Paris", "country": "France", "country_code": "FR"},
                "requirements": {
                    "budget": 1500,
                    "currency": "EUR",
                    "start_date": "2024-08-01",
                    "end_date": "2024-08-07",
                    "travelers": 2,
                },
            },
            headers={"Authorization": "Bearer valid-token-would-go-here"},
        )

        # Should not be a validation error (422), might be auth error (401) or other
        assert response.status_code != 422

    def test_validation_error_field_paths(self, authenticated_client) -> None:
        """Test that field paths in validation errors are properly formatted."""

        response = authenticated_client.post(
            "/api/v1/trips/",
            json={
                "requirements": {
                    "budget": "not-a-number"  # Type validation error
                }
            },
        )

        assert response.status_code == 422
        data = response.json()

        errors = data["data"]["errors"]

        # Should have properly formatted nested field path
        budget_errors = [error for error in errors if "budget" in error["field"]]
        assert len(budget_errors) > 0

        # Field path should be formatted with arrows
        budget_error = budget_errors[0]
        assert " -> " in budget_error["field"] or budget_error["field"] == "requirements -> budget"

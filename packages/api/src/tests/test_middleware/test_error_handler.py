"""Unit tests for error handling middleware."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from travel_companion.middleware.error_handler import (
    AuthErrorHandlerMiddleware,
    add_error_handlers,
    auth_exception_handler,
)
from travel_companion.utils.errors import (
    AuthenticationError,
    AuthErrorCode,
    AuthorizationError,
    DatabaseError,
    DatabaseErrorCode,
    ExternalAPIError,
    InvalidTokenError,
    TokenExpiredError,
    TokenMissingError,
    TravelCompanionError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
    ValidationErrorCode,
)


@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request."""
    request = Mock(spec=Request)
    request.method = "POST"
    request.url = Mock()
    request.url.__str__ = Mock(return_value="https://api.example.com/users/login")
    request.headers = {
        "user-agent": "Mozilla/5.0 (Test Browser)",
        "content-type": "application/json",
    }
    request.client = Mock()
    request.client.host = "192.168.1.1"
    return request


@pytest.fixture
def error_middleware():
    """Create error handling middleware instance."""
    app = Mock()
    return AuthErrorHandlerMiddleware(app)


class TestAuthErrorHandlerMiddleware:
    """Test AuthErrorHandlerMiddleware class."""

    @pytest.mark.asyncio
    async def test_handle_token_missing_error(self, error_middleware, mock_request):
        """Test handling TokenMissingError."""
        exception = TokenMissingError("Token required")

        response = await error_middleware._handle_exception(mock_request, exception)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 403

        content = response.body.decode()
        import json

        parsed = json.loads(content)
        assert parsed["error"] is True
        assert parsed["message"] == "Authentication token required"
        assert parsed["error_code"] == AuthErrorCode.TOKEN_MISSING

    @pytest.mark.asyncio
    async def test_handle_token_expired_error(self, error_middleware, mock_request):
        """Test handling TokenExpiredError."""
        exception = TokenExpiredError("Token expired")

        response = await error_middleware._handle_exception(mock_request, exception)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 401

        content = response.body.decode()
        import json

        parsed = json.loads(content)
        assert parsed["message"] == "Token has expired"
        assert parsed["error_code"] == AuthErrorCode.TOKEN_EXPIRED

    @pytest.mark.asyncio
    async def test_handle_invalid_token_error(self, error_middleware, mock_request):
        """Test handling InvalidTokenError."""
        exception = InvalidTokenError("Invalid token format")

        response = await error_middleware._handle_exception(mock_request, exception)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 401

        content = response.body.decode()
        import json

        parsed = json.loads(content)
        assert parsed["message"] == "Invalid authentication token"
        assert parsed["error_code"] == AuthErrorCode.TOKEN_INVALID

    @pytest.mark.asyncio
    async def test_handle_user_not_found_error(self, error_middleware, mock_request):
        """Test handling UserNotFoundError with security message."""
        exception = UserNotFoundError("User not found")

        response = await error_middleware._handle_exception(mock_request, exception)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 401

        content = response.body.decode()
        import json

        parsed = json.loads(content)
        # Should return generic message for security
        assert parsed["message"] == "Invalid credentials"
        assert parsed["error_code"] == AuthErrorCode.INVALID_CREDENTIALS

    @pytest.mark.asyncio
    async def test_handle_user_already_exists_error(self, error_middleware, mock_request):
        """Test handling UserAlreadyExistsError."""
        exception = UserAlreadyExistsError("Email already registered")

        response = await error_middleware._handle_exception(mock_request, exception)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 409

        content = response.body.decode()
        import json

        parsed = json.loads(content)
        assert parsed["message"] == "User already exists"
        assert parsed["error_code"] == AuthErrorCode.USER_ALREADY_EXISTS

    @pytest.mark.asyncio
    async def test_handle_authentication_error(self, error_middleware, mock_request):
        """Test handling generic AuthenticationError."""
        exception = AuthenticationError(
            "Custom auth error", AuthErrorCode.LOGIN_FAILED, {"reason": "too_many_attempts"}
        )

        response = await error_middleware._handle_exception(mock_request, exception)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 401

        content = response.body.decode()
        import json

        parsed = json.loads(content)
        assert parsed["message"] == "Custom auth error"
        assert parsed["error_code"] == AuthErrorCode.LOGIN_FAILED
        assert parsed["details"] == {"reason": "too_many_attempts"}

    @pytest.mark.asyncio
    async def test_handle_authorization_error(self, error_middleware, mock_request):
        """Test handling AuthorizationError."""
        exception = AuthorizationError(
            "Admin required", AuthErrorCode.INSUFFICIENT_PERMISSIONS, {"required_role": "admin"}
        )

        response = await error_middleware._handle_exception(mock_request, exception)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 403

        content = response.body.decode()
        import json

        parsed = json.loads(content)
        assert parsed["message"] == "Admin required"
        assert parsed["error_code"] == AuthErrorCode.INSUFFICIENT_PERMISSIONS
        assert parsed["details"] == {"required_role": "admin"}

    @pytest.mark.asyncio
    async def test_handle_validation_error(self, error_middleware, mock_request):
        """Test handling ValidationError."""
        exception = ValidationError(
            "Invalid email format", ValidationErrorCode.INVALID_EMAIL_FORMAT, field="email"
        )

        response = await error_middleware._handle_exception(mock_request, exception)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 422

        content = response.body.decode()
        import json

        parsed = json.loads(content)
        assert parsed["message"] == "Invalid email format"
        assert parsed["error_code"] == ValidationErrorCode.INVALID_EMAIL_FORMAT
        assert parsed["details"]["field"] == "email"

    @pytest.mark.asyncio
    async def test_handle_pydantic_validation_error(self, error_middleware, mock_request):
        """Test handling Pydantic ValidationError."""
        # Create a mock Pydantic ValidationError
        mock_error = Mock(spec=PydanticValidationError)
        mock_error.errors.return_value = [
            {
                "loc": ("email",),
                "msg": "field required",
                "type": "value_error.missing",
            },
            {
                "loc": ("password",),
                "msg": "ensure this value has at least 8 characters",
                "type": "value_error.any_str.min_length",
            },
        ]

        response = await error_middleware._handle_exception(mock_request, mock_error)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 422

        content = response.body.decode()
        import json

        parsed = json.loads(content)
        assert parsed["message"] == "Validation failed"
        assert parsed["error_code"] == "VAL003"
        assert len(parsed["details"]["field_errors"]) == 2
        assert parsed["details"]["field_errors"][0]["field"] == "email"
        assert parsed["details"]["field_errors"][1]["field"] == "password"

    @pytest.mark.asyncio
    async def test_handle_database_error(self, error_middleware, mock_request):
        """Test handling DatabaseError."""
        exception = DatabaseError(
            "Query failed", DatabaseErrorCode.QUERY_FAILED, operation="SELECT users"
        )

        response = await error_middleware._handle_exception(mock_request, exception)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

        content = response.body.decode()
        import json

        parsed = json.loads(content)
        assert parsed["message"] == "Database operation failed"
        assert parsed["error_code"] == DatabaseErrorCode.QUERY_FAILED

    @pytest.mark.asyncio
    async def test_handle_external_api_error(self, error_middleware, mock_request):
        """Test handling ExternalAPIError."""
        exception = ExternalAPIError(
            "Service unavailable", service="payment_gateway", status_code=503
        )

        response = await error_middleware._handle_exception(mock_request, exception)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 502

        content = response.body.decode()
        import json

        parsed = json.loads(content)
        assert parsed["message"] == "External service unavailable"
        assert parsed["error_code"] == "EXT001"
        assert parsed["details"]["service"] == "payment_gateway"

    @pytest.mark.asyncio
    async def test_handle_http_exception(self, error_middleware, mock_request):
        """Test handling FastAPI HTTPException."""
        exception = HTTPException(status_code=400, detail="Bad request data")

        response = await error_middleware._handle_exception(mock_request, exception)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 400

        content = response.body.decode()
        import json

        parsed = json.loads(content)
        assert parsed["message"] == "Bad request data"

    @pytest.mark.asyncio
    async def test_handle_travel_companion_error(self, error_middleware, mock_request):
        """Test handling generic TravelCompanionError."""
        exception = TravelCompanionError(
            "Custom application error", error_code="APP001", details={"context": "test"}
        )

        response = await error_middleware._handle_exception(mock_request, exception)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

        content = response.body.decode()
        import json

        parsed = json.loads(content)
        assert parsed["message"] == "Custom application error"
        assert parsed["error_code"] == "APP001"
        assert parsed["details"] == {"context": "test"}

    @pytest.mark.asyncio
    async def test_handle_unexpected_error(self, error_middleware, mock_request):
        """Test handling unexpected system errors."""
        exception = RuntimeError("Unexpected system error")

        with patch.object(error_middleware, "_log_error") as mock_log:
            response = await error_middleware._handle_exception(mock_request, exception)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

        content = response.body.decode()
        import json

        parsed = json.loads(content)
        assert parsed["message"] == "Internal server error"
        assert parsed["error_code"] == "SYS001"

        # Should log the unexpected error
        mock_log.assert_called_once()

    @patch("travel_companion.middleware.error_handler.logger")
    def test_log_error_redacts_sensitive_headers(self, mock_logger, error_middleware, mock_request):
        """Test that sensitive headers are redacted in logs."""
        mock_request.headers = {
            "authorization": "Bearer secret-token",
            "cookie": "session=secret-cookie",
            "x-api-key": "secret-api-key",
            "user-agent": "Mozilla/5.0",
            "content-type": "application/json",
        }

        exception = AuthenticationError("Test error")
        error_middleware._log_error(mock_request, exception)

        # Check that the logger was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[1]["extra"]

        headers = call_args["headers"]
        assert headers["authorization"] == "[REDACTED]"
        assert headers["cookie"] == "[REDACTED]"
        assert headers["x-api-key"] == "[REDACTED]"
        assert headers["user-agent"] == "Mozilla/5.0"
        assert headers["content-type"] == "application/json"

    @patch("travel_companion.middleware.error_handler.logger")
    def test_log_error_different_severity_levels(self, mock_logger, error_middleware, mock_request):
        """Test that different error types are logged at appropriate levels."""
        # Test INFO level for user errors
        auth_error = AuthenticationError("Invalid credentials")
        error_middleware._log_error(mock_request, auth_error)
        mock_logger.info.assert_called()

        mock_logger.reset_mock()

        # Test ERROR level for system errors
        db_error = DatabaseError("Connection failed")
        error_middleware._log_error(mock_request, db_error)
        mock_logger.error.assert_called()

        mock_logger.reset_mock()

        # Test ERROR level with stack trace for unexpected errors
        system_error = RuntimeError("Unexpected error")
        error_middleware._log_error(mock_request, system_error)
        mock_logger.error.assert_called()


class TestAuthExceptionHandler:
    """Test standalone auth exception handler function."""

    @pytest.mark.asyncio
    async def test_auth_exception_handler_delegates_to_middleware(self, mock_request):
        """Test that auth_exception_handler delegates to middleware."""
        exception = AuthenticationError("Test error")

        with patch.object(AuthErrorHandlerMiddleware, "_handle_exception") as mock_handle:
            mock_handle.return_value = JSONResponse(
                status_code=401, content={"error": True, "message": "Test error"}
            )

            result = await auth_exception_handler(mock_request, exception)

            mock_handle.assert_called_once_with(mock_request, exception)
            assert isinstance(result, JSONResponse)


class TestAddErrorHandlers:
    """Test add_error_handlers function."""

    def test_add_error_handlers_registers_all_handlers(self):
        """Test that add_error_handlers registers all expected exception handlers."""
        mock_app = Mock()

        add_error_handlers(mock_app)

        # Should register handlers for all custom exception types
        expected_exception_types = [
            AuthenticationError,
            AuthorizationError,
            ValidationError,
            UserNotFoundError,
            UserAlreadyExistsError,
            TokenExpiredError,
            InvalidTokenError,
            TokenMissingError,
            DatabaseError,
            TravelCompanionError,
        ]

        assert mock_app.exception_handler.call_count == len(expected_exception_types)

        # Verify each exception type was registered
        registered_types = [call[0][0] for call in mock_app.exception_handler.call_args_list]

        for exception_type in expected_exception_types:
            assert exception_type in registered_types


class TestMiddlewareIntegration:
    """Test middleware integration with FastAPI application."""

    @pytest.mark.asyncio
    async def test_middleware_call_passes_through_non_http(self):
        """Test middleware passes through non-HTTP requests."""
        app = AsyncMock()
        middleware = AuthErrorHandlerMiddleware(app)

        scope = {"type": "websocket"}
        receive = Mock()
        send = Mock()

        await middleware(scope, receive, send)

        app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_middleware_call_handles_http_exceptions(self):
        """Test middleware catches and handles HTTP exceptions."""

        # Create a mock app that raises an exception
        async def failing_app(scope, receive, send):
            raise AuthenticationError("Test auth error")

        middleware = AuthErrorHandlerMiddleware(failing_app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/test",
            "headers": [],
            "client": ("192.168.1.1", 0),
        }
        receive = Mock()
        send = AsyncMock()

        with patch.object(middleware, "_handle_exception") as mock_handle:
            mock_response = Mock(spec=JSONResponse)
            mock_response.status_code = 401
            mock_response.body = b'{"error": true}'
            mock_handle.return_value = mock_response

            await middleware(scope, receive, send)

            # Should handle the exception
            mock_handle.assert_called_once()

            # Should send error response
            assert send.call_count >= 2  # response.start + response.body

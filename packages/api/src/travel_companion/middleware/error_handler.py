"""Error handling middleware for the Travel Companion API."""

import logging
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from ..utils.errors import (
    AuthenticationError,
    AuthErrorCode,
    AuthorizationError,
    DatabaseError,
    ExternalAPIError,
    InvalidTokenError,
    TokenExpiredError,
    TokenMissingError,
    TravelCompanionError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
    create_auth_error_response,
    create_error_response,
    create_validation_error_response,
)

logger = logging.getLogger(__name__)


class AuthErrorHandlerMiddleware:
    """Middleware for handling authentication and authorization errors."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Any],
        send: Callable[[dict[str, Any]], Any],
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                # Process the response before sending
                await send(message)
            else:
                await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            # Handle any unhandled exceptions
            response = await self._handle_exception(request, exc)
            await self._send_error_response(response, send)

    async def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle different types of exceptions and return appropriate responses."""

        # Log the exception (without sensitive data)
        self._log_error(request, exc)

        # Handle specific authentication/authorization errors
        if isinstance(exc, TokenMissingError):
            return JSONResponse(
                status_code=403,
                content=create_auth_error_response(
                    message="Authentication token required",
                    error_code=AuthErrorCode.TOKEN_MISSING,
                ),
            )

        elif isinstance(exc, TokenExpiredError):
            return JSONResponse(
                status_code=401,
                content=create_auth_error_response(
                    message="Token has expired",
                    error_code=AuthErrorCode.TOKEN_EXPIRED,
                ),
            )

        elif isinstance(exc, InvalidTokenError):
            return JSONResponse(
                status_code=401,
                content=create_auth_error_response(
                    message="Invalid authentication token",
                    error_code=AuthErrorCode.TOKEN_INVALID,
                ),
            )

        elif isinstance(exc, UserNotFoundError):
            return JSONResponse(
                status_code=401,
                content=create_auth_error_response(
                    message="Invalid credentials",  # Generic message for security
                    error_code=AuthErrorCode.INVALID_CREDENTIALS,
                ),
            )

        elif isinstance(exc, UserAlreadyExistsError):
            return JSONResponse(
                status_code=409,
                content=create_error_response(
                    message="User already exists",
                    error_code=AuthErrorCode.USER_ALREADY_EXISTS,
                    status_code=409,
                ),
            )

        elif isinstance(exc, AuthenticationError):
            return JSONResponse(
                status_code=401,
                content=create_auth_error_response(
                    message=str(exc) if str(exc) else "Authentication failed",
                    error_code=getattr(exc, "error_code", AuthErrorCode.INVALID_CREDENTIALS),
                    details=getattr(exc, "details", None),
                ),
            )

        elif isinstance(exc, AuthorizationError):
            return JSONResponse(
                status_code=403,
                content=create_error_response(
                    message=str(exc) if str(exc) else "Insufficient permissions",
                    error_code=getattr(exc, "error_code", AuthErrorCode.INSUFFICIENT_PERMISSIONS),
                    details=getattr(exc, "details", None),
                    status_code=403,
                ),
            )

        elif isinstance(exc, ValidationError):
            return JSONResponse(
                status_code=422,
                content=create_validation_error_response(
                    message=str(exc),
                    field=getattr(exc, "details", {}).get("field"),
                    error_code=getattr(exc, "error_code", "VAL003"),
                ),
            )

        elif isinstance(exc, PydanticValidationError):
            # Handle Pydantic validation errors
            errors = exc.errors()
            field_errors = []
            for error in errors:
                field_name = ".".join(str(loc) for loc in error["loc"])
                field_errors.append(
                    {
                        "field": field_name,
                        "message": error["msg"],
                        "type": error["type"],
                    }
                )

            return JSONResponse(
                status_code=422,
                content=create_error_response(
                    message="Validation failed",
                    error_code="VAL003",
                    details={"field_errors": field_errors},
                    status_code=422,
                ),
            )

        elif isinstance(exc, DatabaseError):
            return JSONResponse(
                status_code=500,
                content=create_error_response(
                    message="Database operation failed",
                    error_code=getattr(exc, "error_code", "DB002"),
                    status_code=500,
                ),
            )

        elif isinstance(exc, ExternalAPIError):
            return JSONResponse(
                status_code=502,
                content=create_error_response(
                    message="External service unavailable",
                    error_code="EXT001",
                    details={"service": getattr(exc, "details", {}).get("service")},
                    status_code=502,
                ),
            )

        elif isinstance(exc, HTTPException):
            # Handle FastAPI HTTP exceptions
            return JSONResponse(
                status_code=exc.status_code,
                content=create_error_response(
                    message=exc.detail,
                    status_code=exc.status_code,
                ),
            )

        elif isinstance(exc, TravelCompanionError):
            # Handle any other custom application errors
            return JSONResponse(status_code=500, content=exc.to_dict())

        else:
            # Handle unexpected errors
            logger.exception("Unhandled exception occurred")
            return JSONResponse(
                status_code=500,
                content=create_error_response(
                    message="Internal server error",
                    error_code="SYS001",
                    status_code=500,
                ),
            )

    def _log_error(self, request: Request, exc: Exception) -> None:
        """Log error information without sensitive data."""

        # Create safe request info (exclude sensitive headers)
        safe_headers = {}
        for name, value in request.headers.items():
            if name.lower() not in ["authorization", "cookie", "x-api-key"]:
                safe_headers[name] = value
            else:
                safe_headers[name] = "[REDACTED]"

        error_context = {
            "method": request.method,
            "url": str(request.url),
            "headers": safe_headers,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": safe_headers.get("user-agent", "unknown"),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }

        # Add error code if available
        if hasattr(exc, "error_code"):
            error_context["error_code"] = exc.error_code

        # Log based on error severity
        if isinstance(exc, AuthenticationError | AuthorizationError | ValidationError):
            # These are expected user errors, log at INFO level
            logger.info("Authentication/Authorization error occurred", extra=error_context)
        elif isinstance(exc, DatabaseError | ExternalAPIError):
            # These are system errors, log at ERROR level
            logger.error("System error occurred", extra=error_context)
        else:
            # Unexpected errors, log at ERROR level with stack trace
            logger.error("Unexpected error occurred", extra=error_context, exc_info=True)

    async def _send_error_response(
        self, response: JSONResponse, send: Callable[[dict[str, Any]], Any]
    ) -> None:
        """Send error response through ASGI."""
        await send(
            {
                "type": "http.response.start",
                "status": response.status_code,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(response.body)).encode()],
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": response.body,
            }
        )


async def auth_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    FastAPI exception handler for authentication errors.

    This can be used as an alternative to middleware for more granular control.
    """
    middleware = AuthErrorHandlerMiddleware(None)
    return await middleware._handle_exception(request, exc)


def add_error_handlers(app: Any) -> None:
    """Add error handlers to FastAPI app."""

    @app.exception_handler(AuthenticationError)
    async def authentication_exception_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        return await auth_exception_handler(request, exc)

    @app.exception_handler(AuthorizationError)
    async def authorization_exception_handler(
        request: Request, exc: AuthorizationError
    ) -> JSONResponse:
        return await auth_exception_handler(request, exc)

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
        return await auth_exception_handler(request, exc)

    @app.exception_handler(UserNotFoundError)
    async def user_not_found_exception_handler(
        request: Request, exc: UserNotFoundError
    ) -> JSONResponse:
        return await auth_exception_handler(request, exc)

    @app.exception_handler(UserAlreadyExistsError)
    async def user_exists_exception_handler(
        request: Request, exc: UserAlreadyExistsError
    ) -> JSONResponse:
        return await auth_exception_handler(request, exc)

    @app.exception_handler(TokenExpiredError)
    async def token_expired_exception_handler(
        request: Request, exc: TokenExpiredError
    ) -> JSONResponse:
        return await auth_exception_handler(request, exc)

    @app.exception_handler(InvalidTokenError)
    async def invalid_token_exception_handler(
        request: Request, exc: InvalidTokenError
    ) -> JSONResponse:
        return await auth_exception_handler(request, exc)

    @app.exception_handler(TokenMissingError)
    async def token_missing_exception_handler(
        request: Request, exc: TokenMissingError
    ) -> JSONResponse:
        return await auth_exception_handler(request, exc)

    @app.exception_handler(DatabaseError)
    async def database_exception_handler(request: Request, exc: DatabaseError) -> JSONResponse:
        return await auth_exception_handler(request, exc)

    @app.exception_handler(TravelCompanionError)
    async def travel_companion_exception_handler(
        request: Request, exc: TravelCompanionError
    ) -> JSONResponse:
        return await auth_exception_handler(request, exc)

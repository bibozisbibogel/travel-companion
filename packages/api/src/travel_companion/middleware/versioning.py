"""API versioning middleware for adding version headers to responses."""

import logging
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class APIVersionMiddleware(BaseHTTPMiddleware):
    """Middleware to add API version information to response headers."""

    def __init__(self, app: ASGIApp, api_version: str = "v1", app_version: str = "0.1.0") -> None:
        """
        Initialize API version middleware.

        Args:
            app: FastAPI application instance
            api_version: API version string (e.g., "v1", "v2")
            app_version: Application version string (e.g., "0.1.0")
        """
        super().__init__(app)
        self.api_version = api_version
        self.app_version = app_version

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process request and add version headers to response.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in the chain

        Returns:
            HTTP response with added version headers
        """
        response = await call_next(request)

        # Only add version headers to API endpoints
        if request.url.path.startswith("/api/"):
            response.headers["X-API-Version"] = self.api_version
            response.headers["X-App-Version"] = self.app_version

            # Add API version information for debugging
            if request.url.path.startswith("/api/v1/"):
                logger.debug(f"API v1 request processed: {request.method} {request.url.path}")

        return response

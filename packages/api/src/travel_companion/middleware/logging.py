"""Request/response logging middleware for the Travel Companion API."""

import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from travel_companion.utils.logging import (
    auth_logger,
    get_client_ip,
    get_user_agent,
    setup_auth_logger,
)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses."""

    def __init__(self, app: Any, log_level: str = "INFO") -> None:
        super().__init__(app)
        self.logger = setup_auth_logger("travel_companion.api")
        self.log_level = log_level.upper()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Log request and response information."""
        start_time = time.time()
        client_ip = get_client_ip(request)
        user_agent = get_user_agent(request)

        # Extract request details (without sensitive data)
        request_details = {
            "method": request.method,
            "path": str(request.url.path),
            "query_params": dict(request.query_params),
            "client_ip": client_ip,
            "user_agent": user_agent,
            "content_type": request.headers.get("content-type"),
        }

        # Log request (excluding sensitive headers)
        safe_headers = self._sanitize_headers(dict(request.headers))
        request_details["headers"] = safe_headers

        # Log the incoming request
        self.logger.info(
            f"{request.method} {request.url.path} - Request started",
            extra={
                "event_type": "HTTP_REQUEST_START",
                "request_id": self._generate_request_id(request),
                **request_details,
            },
        )

        # Process the request
        try:
            response = await call_next(request)

            # Calculate processing time
            processing_time = time.time() - start_time

            # Log the response
            response_details = {
                "status_code": response.status_code,
                "processing_time_ms": round(processing_time * 1000, 2),
                "content_type": response.headers.get("content-type"),
                "content_length": response.headers.get("content-length"),
            }

            # Determine log level based on status code
            if response.status_code >= 500:
                log_level = "error"
                log_message = (
                    f"{request.method} {request.url.path} - Server Error ({response.status_code})"
                )
            elif response.status_code >= 400:
                log_level = "warning"
                log_message = (
                    f"{request.method} {request.url.path} - Client Error ({response.status_code})"
                )
            else:
                log_level = "info"
                log_message = (
                    f"{request.method} {request.url.path} - Success ({response.status_code})"
                )

            # Log the response
            log_method = getattr(self.logger, log_level)
            log_method(
                log_message,
                extra={
                    "event_type": "HTTP_REQUEST_COMPLETE",
                    "request_id": self._generate_request_id(request),
                    **request_details,
                    **response_details,
                },
            )

            return response

        except Exception as exc:
            # Log the exception
            processing_time = time.time() - start_time

            self.logger.error(
                f"{request.method} {request.url.path} - Request failed: {str(exc)}",
                extra={
                    "event_type": "HTTP_REQUEST_ERROR",
                    "request_id": self._generate_request_id(request),
                    "processing_time_ms": round(processing_time * 1000, 2),
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    **request_details,
                },
                exc_info=True,
            )
            raise

    def _sanitize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Remove or mask sensitive headers for logging."""
        sensitive_headers = {
            "authorization",
            "cookie",
            "x-api-key",
            "x-auth-token",
            "x-access-token",
            "bearer",
        }

        sanitized = {}
        for key, value in headers.items():
            if key.lower() in sensitive_headers:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value

        return sanitized

    def _generate_request_id(self, request: Request) -> str:
        """Generate a unique request ID for tracking."""
        # Use request headers or generate from request details
        request_id_header = request.headers.get("x-request-id")
        if request_id_header:
            return request_id_header

        # Generate from timestamp and client info
        import hashlib

        timestamp = str(time.time())
        client_info = f"{get_client_ip(request)}:{request.method}:{request.url.path}"
        request_id = hashlib.md5(f"{timestamp}:{client_info}".encode()).hexdigest()[:12]
        return f"req_{request_id}"


class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """Enhanced security-focused logging middleware."""

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.logger = setup_auth_logger("travel_companion.security")

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Log security-relevant events and suspicious activity."""
        client_ip = get_client_ip(request)
        user_agent = get_user_agent(request)
        path = str(request.url.path)
        method = request.method

        # Check for suspicious patterns
        suspicious_patterns = [
            # Common attack patterns
            "../",  # Directory traversal
            "<script",  # XSS attempts
            "union select",  # SQL injection
            "drop table",  # SQL injection
            "exec(",  # Code injection
            "eval(",  # Code injection
            "system(",  # Command injection
        ]

        # Check query parameters and path for suspicious content
        query_string = str(request.url.query).lower()
        path_lower = path.lower()

        for pattern in suspicious_patterns:
            if pattern in query_string or pattern in path_lower:
                auth_logger.log_security_event(
                    event_type="SUSPICIOUS_REQUEST",
                    level="warning",
                    message=f"Suspicious pattern detected: {pattern}",
                    ip_address=client_ip,
                    error_code="SEC001",
                    details={
                        "pattern": pattern,
                        "method": method,
                        "path": path,
                        "query_string": str(request.url.query),
                        "user_agent": user_agent,
                    },
                )

        # Log access to sensitive endpoints
        sensitive_endpoints = [
            "/api/v1/auth/",
            "/api/v1/users/",
            "/admin/",
            "/docs",
            "/redoc",
        ]

        for endpoint in sensitive_endpoints:
            if path.startswith(endpoint):
                self.logger.info(
                    f"Access to sensitive endpoint: {path}",
                    extra={
                        "event_type": "SENSITIVE_ENDPOINT_ACCESS",
                        "client_ip": client_ip,
                        "user_agent": user_agent,
                        "method": method,
                        "path": path,
                        "endpoint_type": endpoint,
                    },
                )

        # Process the request
        response = await call_next(request)

        # Log failed authentication attempts (401/403 responses)
        if response.status_code in [401, 403]:
            auth_logger.log_security_event(
                event_type="ACCESS_DENIED",
                level="warning",
                message=f"Access denied for {method} {path}",
                ip_address=client_ip,
                error_code=f"HTTP_{response.status_code}",
                details={
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "user_agent": user_agent,
                },
            )

        # Log potential brute force attempts (multiple 401s from same IP)
        if response.status_code == 401:
            # This would typically integrate with rate limiting or Redis
            # to track failed attempts per IP
            self._log_potential_brute_force(client_ip, path, user_agent)

        return response

    def _log_potential_brute_force(self, client_ip: str, path: str, user_agent: str) -> None:
        """Log potential brute force attempts (simplified implementation)."""
        # In a full implementation, this would check Redis for
        # recent failed attempts from the same IP
        auth_logger.log_security_event(
            event_type="POTENTIAL_BRUTE_FORCE",
            level="warning",
            message=f"Potential brute force attempt from {client_ip}",
            ip_address=client_ip,
            error_code="SEC002",
            details={
                "path": path,
                "user_agent": user_agent,
                "note": "Consider implementing rate limiting",
            },
        )


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """Performance monitoring middleware for slow requests."""

    def __init__(self, app: Any, slow_request_threshold_ms: int = 1000) -> None:
        super().__init__(app)
        self.logger = setup_auth_logger("travel_companion.performance")
        self.slow_threshold_ms = slow_request_threshold_ms

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Monitor request performance and log slow requests."""
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        # Log slow requests
        if processing_time_ms > self.slow_threshold_ms:
            self.logger.warning(
                f"Slow request detected: {request.method} {request.url.path}",
                extra={
                    "event_type": "SLOW_REQUEST",
                    "method": request.method,
                    "path": str(request.url.path),
                    "processing_time_ms": round(processing_time_ms, 2),
                    "threshold_ms": self.slow_threshold_ms,
                    "status_code": response.status_code,
                    "client_ip": get_client_ip(request),
                },
            )

        return response

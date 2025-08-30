"""Unit tests for logging middleware."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import Request, Response

from travel_companion.middleware.logging import (
    LoggingMiddleware,
    PerformanceLoggingMiddleware,
    SecurityLoggingMiddleware,
)


@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request."""
    request = Mock(spec=Request)
    request.method = "GET"
    request.url = Mock()
    request.url.path = "/api/v1/users/profile"
    request.url.query = "filter=active"
    request.query_params = {"filter": "active"}
    request.headers = {
        "user-agent": "Mozilla/5.0 (Test Browser)",
        "content-type": "application/json",
        "authorization": "Bearer secret-token",
        "x-request-id": "test-request-123",
    }
    request.client = Mock()
    request.client.host = "192.168.1.1"
    return request


@pytest.fixture
def mock_response():
    """Create a mock FastAPI Response."""
    response = Mock(spec=Response)
    response.status_code = 200
    response.headers = {
        "content-type": "application/json",
        "content-length": "1234",
    }
    return response


class TestLoggingMiddleware:
    """Test LoggingMiddleware class."""

    @pytest.fixture
    def logging_middleware(self):
        """Create LoggingMiddleware instance."""
        app = Mock()
        return LoggingMiddleware(app)

    @pytest.mark.asyncio
    async def test_successful_request_logging(
        self, logging_middleware, mock_request, mock_response
    ):
        """Test logging of successful requests."""
        call_next = AsyncMock(return_value=mock_response)

        with patch.object(logging_middleware, "logger") as mock_logger:
            response = await logging_middleware.dispatch(mock_request, call_next)

        assert response == mock_response

        # Should log request start and completion
        assert mock_logger.info.call_count == 2

        # Check request start log
        start_call = mock_logger.info.call_args_list[0]
        assert "Request started" in start_call[0][0]
        start_extra = start_call[1]["extra"]
        assert start_extra["event_type"] == "HTTP_REQUEST_START"
        assert start_extra["method"] == "GET"
        assert start_extra["path"] == "/api/v1/users/profile"
        assert start_extra["client_ip"] == "192.168.1.1"

        # Check request completion log
        complete_call = mock_logger.info.call_args_list[1]
        assert "Success (200)" in complete_call[0][0]
        complete_extra = complete_call[1]["extra"]
        assert complete_extra["event_type"] == "HTTP_REQUEST_COMPLETE"
        assert complete_extra["status_code"] == 200
        assert "processing_time_ms" in complete_extra

    @pytest.mark.asyncio
    async def test_client_error_logging(self, logging_middleware, mock_request):
        """Test logging of client errors (4xx)."""
        error_response = Mock(spec=Response)
        error_response.status_code = 400
        error_response.headers = {"content-type": "application/json"}

        call_next = AsyncMock(return_value=error_response)

        with patch.object(logging_middleware, "logger") as mock_logger:
            response = await logging_middleware.dispatch(mock_request, call_next)

        assert response == error_response

        # Should use warning level for client errors
        assert mock_logger.warning.called
        warning_call = mock_logger.warning.call_args
        assert "Client Error (400)" in warning_call[0][0]

    @pytest.mark.asyncio
    async def test_server_error_logging(self, logging_middleware, mock_request):
        """Test logging of server errors (5xx)."""
        error_response = Mock(spec=Response)
        error_response.status_code = 500
        error_response.headers = {"content-type": "application/json"}

        call_next = AsyncMock(return_value=error_response)

        with patch.object(logging_middleware, "logger") as mock_logger:
            response = await logging_middleware.dispatch(mock_request, call_next)

        assert response == error_response

        # Should use error level for server errors
        assert mock_logger.error.called
        error_call = mock_logger.error.call_args
        assert "Server Error (500)" in error_call[0][0]

    @pytest.mark.asyncio
    async def test_exception_logging(self, logging_middleware, mock_request):
        """Test logging when exceptions occur during request processing."""
        call_next = AsyncMock(side_effect=RuntimeError("Something went wrong"))

        with patch.object(logging_middleware, "logger") as mock_logger:
            with pytest.raises(RuntimeError):
                await logging_middleware.dispatch(mock_request, call_next)

        # Should log the exception
        assert mock_logger.error.called
        error_call = mock_logger.error.call_args
        assert "Request failed" in error_call[0][0]
        assert "Something went wrong" in error_call[0][0]

        extra_data = error_call[1]["extra"]
        assert extra_data["event_type"] == "HTTP_REQUEST_ERROR"
        assert extra_data["exception_type"] == "RuntimeError"
        assert extra_data["exception_message"] == "Something went wrong"

    def test_sanitize_headers(self, logging_middleware):
        """Test that sensitive headers are properly sanitized."""
        headers = {
            "authorization": "Bearer secret-token",
            "cookie": "session=secret-session",
            "x-api-key": "secret-api-key",
            "x-auth-token": "secret-auth-token",
            "user-agent": "Mozilla/5.0",
            "content-type": "application/json",
        }

        sanitized = logging_middleware._sanitize_headers(headers)

        # Sensitive headers should be redacted
        assert sanitized["authorization"] == "[REDACTED]"
        assert sanitized["cookie"] == "[REDACTED]"
        assert sanitized["x-api-key"] == "[REDACTED]"
        assert sanitized["x-auth-token"] == "[REDACTED]"

        # Non-sensitive headers should remain
        assert sanitized["user-agent"] == "Mozilla/5.0"
        assert sanitized["content-type"] == "application/json"

    def test_generate_request_id_from_header(self, logging_middleware, mock_request):
        """Test request ID generation when provided in headers."""
        mock_request.headers = {"x-request-id": "custom-request-id"}

        request_id = logging_middleware._generate_request_id(mock_request)

        assert request_id == "custom-request-id"

    def test_generate_request_id_fallback(self, logging_middleware, mock_request):
        """Test request ID generation fallback when not in headers."""
        mock_request.headers = {}  # No x-request-id header

        request_id = logging_middleware._generate_request_id(mock_request)

        assert request_id.startswith("req_")
        assert len(request_id) == 16  # "req_" + 12 character hash


class TestSecurityLoggingMiddleware:
    """Test SecurityLoggingMiddleware class."""

    @pytest.fixture
    def security_middleware(self):
        """Create SecurityLoggingMiddleware instance."""
        app = Mock()
        return SecurityLoggingMiddleware(app)

    @pytest.mark.asyncio
    async def test_suspicious_pattern_detection(
        self, security_middleware, mock_request, mock_response
    ):
        """Test detection of suspicious patterns in requests."""
        # Set up suspicious request
        mock_request.url.path = "/api/v1/users/../admin"
        mock_request.url.query = "q=<script>alert('xss')</script>"

        call_next = AsyncMock(return_value=mock_response)

        with patch("travel_companion.middleware.logging.auth_logger") as mock_auth_logger:
            response = await security_middleware.dispatch(mock_request, call_next)

        assert response == mock_response

        # Should log suspicious activity
        assert mock_auth_logger.log_security_event.called
        security_calls = mock_auth_logger.log_security_event.call_args_list

        # Check for directory traversal detection
        traversal_logged = any("../" in str(call) for call in security_calls)
        assert traversal_logged

    @pytest.mark.asyncio
    async def test_sensitive_endpoint_access_logging(
        self, security_middleware, mock_request, mock_response
    ):
        """Test logging of access to sensitive endpoints."""
        mock_request.url.path = "/api/v1/auth/login"

        call_next = AsyncMock(return_value=mock_response)

        with patch.object(security_middleware, "logger") as mock_logger:
            response = await security_middleware.dispatch(mock_request, call_next)

        assert response == mock_response

        # Should log sensitive endpoint access
        assert mock_logger.info.called
        info_call = mock_logger.info.call_args
        assert "Access to sensitive endpoint" in info_call[0][0]

        extra_data = info_call[1]["extra"]
        assert extra_data["event_type"] == "SENSITIVE_ENDPOINT_ACCESS"
        assert extra_data["path"] == "/api/v1/auth/login"

    @pytest.mark.asyncio
    async def test_access_denied_logging(self, security_middleware, mock_request):
        """Test logging of access denied responses."""
        denied_response = Mock(spec=Response)
        denied_response.status_code = 403

        call_next = AsyncMock(return_value=denied_response)

        with patch("travel_companion.middleware.logging.auth_logger") as mock_auth_logger:
            response = await security_middleware.dispatch(mock_request, call_next)

        assert response == denied_response

        # Should log access denied event
        mock_auth_logger.log_security_event.assert_called_with(
            event_type="ACCESS_DENIED",
            level="warning",
            message=f"Access denied for {mock_request.method} {mock_request.url.path}",
            ip_address="192.168.1.1",
            error_code="HTTP_403",
            details={
                "method": mock_request.method,
                "path": mock_request.url.path,
                "status_code": 403,
                "user_agent": "unknown",  # get_user_agent returns "unknown" for missing header
            },
        )

    @pytest.mark.asyncio
    async def test_potential_brute_force_logging(self, security_middleware, mock_request):
        """Test logging of potential brute force attempts."""
        unauthorized_response = Mock(spec=Response)
        unauthorized_response.status_code = 401

        call_next = AsyncMock(return_value=unauthorized_response)

        with patch("travel_companion.middleware.logging.auth_logger") as mock_auth_logger:
            response = await security_middleware.dispatch(mock_request, call_next)

        assert response == unauthorized_response

        # Should log potential brute force
        security_calls = mock_auth_logger.log_security_event.call_args_list
        brute_force_logged = any("POTENTIAL_BRUTE_FORCE" in str(call) for call in security_calls)
        assert brute_force_logged


class TestPerformanceLoggingMiddleware:
    """Test PerformanceLoggingMiddleware class."""

    @pytest.fixture
    def performance_middleware(self):
        """Create PerformanceLoggingMiddleware instance."""
        app = Mock()
        return PerformanceLoggingMiddleware(app, slow_request_threshold_ms=500)

    @pytest.mark.asyncio
    async def test_fast_request_no_logging(
        self, performance_middleware, mock_request, mock_response
    ):
        """Test that fast requests are not logged as slow."""

        # Mock a fast request (< 500ms)
        async def fast_call_next(request):
            await asyncio.sleep(0.1)  # 100ms
            return mock_response

        with patch.object(performance_middleware, "logger") as mock_logger:
            response = await performance_middleware.dispatch(mock_request, fast_call_next)

        assert response == mock_response

        # Should not log as slow request
        assert not mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_slow_request_logging(self, performance_middleware, mock_request, mock_response):
        """Test that slow requests are logged."""

        # Mock a slow request (> 500ms)
        async def slow_call_next(request):
            # Mock slow processing time
            with patch("time.time") as mock_time:
                mock_time.side_effect = [0, 0.6]  # 600ms processing time
                return mock_response

        call_next = AsyncMock(return_value=mock_response)

        with patch("time.time") as mock_time:
            mock_time.side_effect = [0, 0.6]  # 600ms processing time

            with patch.object(performance_middleware, "logger") as mock_logger:
                response = await performance_middleware.dispatch(mock_request, call_next)

        assert response == mock_response

        # Should log as slow request
        assert mock_logger.warning.called
        warning_call = mock_logger.warning.call_args
        assert "Slow request detected" in warning_call[0][0]

        extra_data = warning_call[1]["extra"]
        assert extra_data["event_type"] == "SLOW_REQUEST"
        assert extra_data["processing_time_ms"] == 600.0
        assert extra_data["threshold_ms"] == 500

    def test_custom_threshold(self):
        """Test custom slow request threshold."""
        app = Mock()
        middleware = PerformanceLoggingMiddleware(app, slow_request_threshold_ms=2000)

        assert middleware.slow_threshold_ms == 2000


class TestMiddlewareUtilityFunctions:
    """Test utility functions used by middleware."""

    def test_get_client_ip_from_x_forwarded_for(self):
        """Test IP extraction from X-Forwarded-For header."""
        from travel_companion.utils.logging import get_client_ip

        mock_request = Mock()
        mock_request.headers = {"X-Forwarded-For": "203.0.113.1, 192.168.1.1"}
        mock_request.client = Mock()
        mock_request.client.host = "10.0.0.1"

        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.1"  # First IP in X-Forwarded-For

    def test_get_client_ip_from_x_real_ip(self):
        """Test IP extraction from X-Real-IP header."""
        from travel_companion.utils.logging import get_client_ip

        mock_request = Mock()
        mock_request.headers = {"X-Real-IP": "203.0.113.2"}
        mock_request.client = Mock()
        mock_request.client.host = "10.0.0.1"

        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.2"

    def test_get_client_ip_fallback(self):
        """Test IP extraction fallback to direct connection."""
        from travel_companion.utils.logging import get_client_ip

        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "10.0.0.1"

        ip = get_client_ip(mock_request)
        assert ip == "10.0.0.1"

    def test_get_client_ip_no_client(self):
        """Test IP extraction when client is None."""
        from travel_companion.utils.logging import get_client_ip

        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = None

        ip = get_client_ip(mock_request)
        assert ip == "unknown"

    def test_get_user_agent(self):
        """Test User-Agent extraction."""
        from travel_companion.utils.logging import get_user_agent

        mock_request = Mock()
        mock_request.headers = {"User-Agent": "Mozilla/5.0 (Test Browser)"}

        user_agent = get_user_agent(mock_request)
        assert user_agent == "Mozilla/5.0 (Test Browser)"

    def test_get_user_agent_missing(self):
        """Test User-Agent extraction when header is missing."""
        from travel_companion.utils.logging import get_user_agent

        mock_request = Mock()
        mock_request.headers = {}

        user_agent = get_user_agent(mock_request)
        assert user_agent == "unknown"

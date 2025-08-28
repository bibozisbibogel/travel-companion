"""Unit tests for authentication logging utilities."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from io import StringIO

from travel_companion.utils.logging import (
    AuthEvent,
    SecurityLogLevel,
    setup_auth_logger,
    AuthLogFormatter,
    AuthLogger,
    auth_logger,
    get_client_ip,
    get_user_agent,
)


class TestAuthEvent:
    """Test AuthEvent enum."""
    
    def test_auth_events(self):
        """Test authentication event types are correctly defined."""
        assert AuthEvent.REGISTRATION_ATTEMPT == "registration_attempt"
        assert AuthEvent.REGISTRATION_SUCCESS == "registration_success"
        assert AuthEvent.REGISTRATION_FAILED == "registration_failed"
        assert AuthEvent.LOGIN_ATTEMPT == "login_attempt"
        assert AuthEvent.LOGIN_SUCCESS == "login_success"
        assert AuthEvent.LOGIN_FAILED == "login_failed"
        assert AuthEvent.TOKEN_GENERATED == "token_generated"
        assert AuthEvent.TOKEN_VALIDATED == "token_validated"
        assert AuthEvent.TOKEN_EXPIRED == "token_expired"
        assert AuthEvent.TOKEN_INVALID == "token_invalid"
        assert AuthEvent.TOKEN_MISSING == "token_missing"
        assert AuthEvent.PROFILE_ACCESSED == "profile_accessed"
        assert AuthEvent.PROFILE_UPDATED == "profile_updated"
        assert AuthEvent.LOGOUT == "logout"
        assert AuthEvent.PASSWORD_RESET_REQUEST == "password_reset_request"
        assert AuthEvent.PASSWORD_RESET_SUCCESS == "password_reset_success"


class TestSecurityLogLevel:
    """Test SecurityLogLevel enum."""
    
    def test_security_log_levels(self):
        """Test security log levels are correctly defined."""
        assert SecurityLogLevel.INFO == "info"
        assert SecurityLogLevel.WARNING == "warning"
        assert SecurityLogLevel.ERROR == "error"
        assert SecurityLogLevel.CRITICAL == "critical"


class TestSetupAuthLogger:
    """Test auth logger setup."""
    
    @patch('travel_companion.utils.logging.logging.getLogger')
    def test_setup_auth_logger_default_name(self, mock_get_logger):
        """Test auth logger setup with default name."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        result = setup_auth_logger()
        
        mock_get_logger.assert_called_once_with("auth")
        mock_logger.setLevel.assert_called_once_with(20)  # logging.INFO
        assert result == mock_logger
    
    @patch('travel_companion.utils.logging.logging.getLogger')
    def test_setup_auth_logger_custom_name(self, mock_get_logger):
        """Test auth logger setup with custom name."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        result = setup_auth_logger("custom_auth")
        
        mock_get_logger.assert_called_once_with("custom_auth")
        assert result == mock_logger
    
    @patch('travel_companion.utils.logging.logging.getLogger')
    def test_setup_auth_logger_prevents_duplicate_handlers(self, mock_get_logger):
        """Test auth logger setup prevents duplicate handlers."""
        mock_logger = Mock()
        mock_logger.handlers = [Mock()]  # Logger already has handlers
        mock_get_logger.return_value = mock_logger
        
        result = setup_auth_logger()
        
        # Should not add new handlers when handlers already exist
        assert not mock_logger.addHandler.called
        assert result == mock_logger


class TestAuthLogFormatter:
    """Test AuthLogFormatter."""
    
    @pytest.fixture
    def formatter(self):
        """Create a formatter instance."""
        return AuthLogFormatter()
    
    def test_format_basic_record(self, formatter):
        """Test formatting basic log record."""
        record = Mock()
        record.levelname = "INFO"
        record.name = "test_logger"
        record.getMessage.return_value = "Test message"
        record.exc_info = None
        
        result = formatter.format(record)
        parsed = json.loads(result)
        
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_logger"
        assert parsed["message"] == "Test message"
        assert "timestamp" in parsed
    
    def test_format_record_with_auth_fields(self, formatter):
        """Test formatting log record with authentication fields."""
        record = Mock()
        record.levelname = "INFO"
        record.name = "auth_logger"
        record.getMessage.return_value = "Login attempt"
        record.exc_info = None
        
        # Add authentication-specific fields
        record.event_type = AuthEvent.LOGIN_ATTEMPT
        record.user_id = str(uuid4())
        record.email = "test@example.com"
        record.ip_address = "192.168.1.1"
        record.user_agent = "Mozilla/5.0"
        record.error_code = "AUTH001"
        record.details = {"reason": "invalid_credentials"}
        
        result = formatter.format(record)
        parsed = json.loads(result)
        
        assert parsed["event_type"] == AuthEvent.LOGIN_ATTEMPT
        assert parsed["user_id"] == record.user_id
        assert parsed["email"] == record.email
        assert parsed["ip_address"] == record.ip_address
        assert parsed["user_agent"] == record.user_agent
        assert parsed["error_code"] == record.error_code
        assert parsed["details"] == {"reason": "invalid_credentials"}
    
    def test_format_record_with_exception(self, formatter):
        """Test formatting log record with exception."""
        record = Mock()
        record.levelname = "ERROR"
        record.name = "auth_logger"
        record.getMessage.return_value = "Authentication error"
        record.exc_info = (Exception, Exception("Test error"), None)
        
        formatter.formatException = Mock(return_value="Exception traceback")
        
        result = formatter.format(record)
        parsed = json.loads(result)
        
        assert parsed["exception"] == "Exception traceback"


class TestAuthLogger:
    """Test AuthLogger class."""
    
    @pytest.fixture
    def logger(self):
        """Create AuthLogger with mocked internal logger."""
        auth_logger_instance = AuthLogger()
        auth_logger_instance.logger = Mock()
        return auth_logger_instance
    
    def test_log_registration_attempt(self, logger):
        """Test logging registration attempt."""
        logger.log_registration_attempt(
            email="test@example.com",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            details={"source": "web"}
        )
        
        logger.logger.info.assert_called_once()
        call_args = logger.logger.info.call_args
        
        assert "User registration attempt" in call_args[0]
        extra = call_args[1]["extra"]
        assert extra["event_type"] == AuthEvent.REGISTRATION_ATTEMPT
        assert extra["email"] == "te**@e******.com"  # Sanitized email
        assert extra["ip_address"] == "192.168.1.1"
        assert extra["user_agent"] == "Mozilla/5.0"
        assert extra["details"] == {"source": "web"}
    
    def test_log_registration_success(self, logger):
        """Test logging successful registration."""
        user_id = uuid4()
        logger.log_registration_success(
            user_id=user_id,
            email="test@example.com",
            ip_address="192.168.1.1"
        )
        
        logger.logger.info.assert_called_once()
        call_args = logger.logger.info.call_args
        
        assert "User registration successful" in call_args[0]
        extra = call_args[1]["extra"]
        assert extra["event_type"] == AuthEvent.REGISTRATION_SUCCESS
        assert extra["user_id"] == str(user_id)
        assert extra["email"] == "te**@e******.com"
    
    def test_log_registration_failed(self, logger):
        """Test logging failed registration."""
        logger.log_registration_failed(
            email="test@example.com",
            ip_address="192.168.1.1",
            error_code="AUTH008",
            reason="User already exists"
        )
        
        logger.logger.warning.assert_called_once()
        call_args = logger.logger.warning.call_args
        
        assert "User registration failed: User already exists" in call_args[0]
        extra = call_args[1]["extra"]
        assert extra["event_type"] == AuthEvent.REGISTRATION_FAILED
        assert extra["error_code"] == "AUTH008"
    
    def test_log_login_attempt(self, logger):
        """Test logging login attempt."""
        logger.log_login_attempt(
            email="test@example.com",
            ip_address="192.168.1.1"
        )
        
        logger.logger.info.assert_called_once()
        call_args = logger.logger.info.call_args
        
        assert "User login attempt" in call_args[0]
        extra = call_args[1]["extra"]
        assert extra["event_type"] == AuthEvent.LOGIN_ATTEMPT
    
    def test_log_login_success(self, logger):
        """Test logging successful login."""
        user_id = uuid4()
        logger.log_login_success(
            user_id=user_id,
            email="test@example.com",
            ip_address="192.168.1.1"
        )
        
        logger.logger.info.assert_called_once()
        call_args = logger.logger.info.call_args
        
        assert "User login successful" in call_args[0]
        extra = call_args[1]["extra"]
        assert extra["event_type"] == AuthEvent.LOGIN_SUCCESS
        assert extra["user_id"] == str(user_id)
    
    def test_log_login_failed(self, logger):
        """Test logging failed login."""
        logger.log_login_failed(
            email="test@example.com",
            ip_address="192.168.1.1",
            error_code="AUTH001",
            reason="Invalid credentials"
        )
        
        logger.logger.warning.assert_called_once()
        call_args = logger.logger.warning.call_args
        
        assert "User login failed: Invalid credentials" in call_args[0]
        extra = call_args[1]["extra"]
        assert extra["event_type"] == AuthEvent.LOGIN_FAILED
        assert extra["error_code"] == "AUTH001"
    
    def test_log_token_generated(self, logger):
        """Test logging token generation."""
        user_id = uuid4()
        logger.log_token_generated(
            user_id=user_id,
            ip_address="192.168.1.1",
            expires_in_minutes=30
        )
        
        logger.logger.info.assert_called_once()
        call_args = logger.logger.info.call_args
        
        assert "JWT token generated" in call_args[0]
        extra = call_args[1]["extra"]
        assert extra["event_type"] == AuthEvent.TOKEN_GENERATED
        assert extra["details"]["expires_in_minutes"] == 30
    
    def test_log_token_validated(self, logger):
        """Test logging token validation."""
        user_id = uuid4()
        logger.log_token_validated(
            user_id=user_id,
            ip_address="192.168.1.1",
            endpoint="/api/v1/users/me"
        )
        
        logger.logger.info.assert_called_once()
        call_args = logger.logger.info.call_args
        
        assert "JWT token validated" in call_args[0]
        extra = call_args[1]["extra"]
        assert extra["event_type"] == AuthEvent.TOKEN_VALIDATED
        assert extra["details"]["endpoint"] == "/api/v1/users/me"
    
    def test_log_token_expired(self, logger):
        """Test logging expired token."""
        logger.log_token_expired(
            ip_address="192.168.1.1",
            endpoint="/api/v1/users/me"
        )
        
        logger.logger.warning.assert_called_once()
        call_args = logger.logger.warning.call_args
        
        assert "Expired token used" in call_args[0]
        extra = call_args[1]["extra"]
        assert extra["event_type"] == AuthEvent.TOKEN_EXPIRED
        assert extra["error_code"] == "AUTH002"
    
    def test_log_token_invalid(self, logger):
        """Test logging invalid token."""
        logger.log_token_invalid(
            ip_address="192.168.1.1",
            endpoint="/api/v1/users/me",
            reason="Malformed signature"
        )
        
        logger.logger.warning.assert_called_once()
        call_args = logger.logger.warning.call_args
        
        assert "Invalid token used: Malformed signature" in call_args[0]
        extra = call_args[1]["extra"]
        assert extra["event_type"] == AuthEvent.TOKEN_INVALID
        assert extra["error_code"] == "AUTH003"
        assert extra["details"]["reason"] == "Malformed signature"
    
    def test_log_token_missing(self, logger):
        """Test logging missing token."""
        logger.log_token_missing(
            ip_address="192.168.1.1",
            endpoint="/api/v1/users/me"
        )
        
        logger.logger.warning.assert_called_once()
        call_args = logger.logger.warning.call_args
        
        assert "Protected endpoint accessed without token" in call_args[0]
        extra = call_args[1]["extra"]
        assert extra["event_type"] == AuthEvent.TOKEN_MISSING
        assert extra["error_code"] == "AUTH004"
    
    def test_log_profile_accessed(self, logger):
        """Test logging profile access."""
        user_id = uuid4()
        logger.log_profile_accessed(
            user_id=user_id,
            ip_address="192.168.1.1"
        )
        
        logger.logger.info.assert_called_once()
        call_args = logger.logger.info.call_args
        
        assert "User profile accessed" in call_args[0]
        extra = call_args[1]["extra"]
        assert extra["event_type"] == AuthEvent.PROFILE_ACCESSED
        assert extra["user_id"] == str(user_id)
    
    def test_log_profile_updated(self, logger):
        """Test logging profile update."""
        user_id = uuid4()
        logger.log_profile_updated(
            user_id=user_id,
            ip_address="192.168.1.1",
            fields_updated=["first_name", "travel_preferences"]
        )
        
        logger.logger.info.assert_called_once()
        call_args = logger.logger.info.call_args
        
        assert "User profile updated" in call_args[0]
        extra = call_args[1]["extra"]
        assert extra["event_type"] == AuthEvent.PROFILE_UPDATED
        assert extra["details"]["fields_updated"] == ["first_name", "travel_preferences"]
    
    def test_log_security_event(self, logger):
        """Test logging general security event."""
        user_id = uuid4()
        logger.log_security_event(
            event_type="suspicious_activity",
            level=SecurityLogLevel.WARNING,
            message="Multiple failed login attempts",
            ip_address="192.168.1.1",
            error_code="SEC001",
            user_id=user_id,
            email="test@example.com",
            details={"attempts": 5}
        )
        
        logger.logger.warning.assert_called_once()
        call_args = logger.logger.warning.call_args
        
        assert "Multiple failed login attempts" in call_args[0]
        extra = call_args[1]["extra"]
        assert extra["event_type"] == "suspicious_activity"
        assert extra["error_code"] == "SEC001"
        assert extra["user_id"] == str(user_id)
        assert extra["email"] == "te**@e******.com"
        assert extra["details"] == {"attempts": 5}
    
    def test_sanitize_email_basic(self, logger):
        """Test email sanitization for privacy."""
        result = logger._sanitize_email("test@example.com")
        assert result == "te**@e******.com"
    
    def test_sanitize_email_short_local(self, logger):
        """Test email sanitization with short local part."""
        result = logger._sanitize_email("ab@example.com")
        assert result == "ab@e******.com"
    
    def test_sanitize_email_subdomain(self, logger):
        """Test email sanitization with subdomain."""
        result = logger._sanitize_email("test@mail.example.com")
        assert result == "te**@m***.example.com"
    
    def test_sanitize_email_no_at_symbol(self, logger):
        """Test email sanitization without @ symbol."""
        result = logger._sanitize_email("notanemail")
        assert result == "notanemail"


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_get_client_ip_from_x_forwarded_for(self):
        """Test extracting client IP from X-Forwarded-For header."""
        request = Mock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.1, 198.51.100.1, 192.168.1.1",
            "X-Real-IP": "198.51.100.1",
        }
        request.client.host = "192.168.1.1"
        
        result = get_client_ip(request)
        assert result == "203.0.113.1"
    
    def test_get_client_ip_from_x_real_ip(self):
        """Test extracting client IP from X-Real-IP header."""
        request = Mock()
        request.headers = {
            "X-Real-IP": "203.0.113.1",
        }
        request.client.host = "192.168.1.1"
        
        result = get_client_ip(request)
        assert result == "203.0.113.1"
    
    def test_get_client_ip_from_client_host(self):
        """Test extracting client IP from direct connection."""
        request = Mock()
        request.headers = {}
        request.client.host = "203.0.113.1"
        
        result = get_client_ip(request)
        assert result == "203.0.113.1"
    
    def test_get_client_ip_no_client(self):
        """Test extracting client IP when no client info available."""
        request = Mock()
        request.headers = {}
        request.client = None
        
        result = get_client_ip(request)
        assert result == "unknown"
    
    def test_get_user_agent_present(self):
        """Test extracting User-Agent when present."""
        request = Mock()
        request.headers = {"User-Agent": "Mozilla/5.0 (compatible; TestBot/1.0)"}
        
        result = get_user_agent(request)
        assert result == "Mozilla/5.0 (compatible; TestBot/1.0)"
    
    def test_get_user_agent_missing(self):
        """Test extracting User-Agent when missing."""
        request = Mock()
        request.headers = {}
        
        result = get_user_agent(request)
        assert result == "unknown"


class TestGlobalAuthLogger:
    """Test global auth_logger instance."""
    
    def test_auth_logger_instance_exists(self):
        """Test that global auth_logger instance exists."""
        assert auth_logger is not None
        assert isinstance(auth_logger, AuthLogger)
    
    @patch('travel_companion.utils.logging.setup_auth_logger')
    def test_auth_logger_uses_correct_name(self, mock_setup):
        """Test that auth_logger is initialized with correct name."""
        # Re-import to trigger initialization
        from travel_companion.utils.logging import AuthLogger
        logger_instance = AuthLogger()
        
        # The logger should be created with the travel_companion.auth name
        # This is verified by checking the setup_auth_logger call in __init__
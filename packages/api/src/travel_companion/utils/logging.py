"""Structured logging utilities for the Travel Companion API."""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from uuid import UUID


class AuthEvent(str, Enum):
    """Authentication event types for logging."""
    
    REGISTRATION_ATTEMPT = "registration_attempt"
    REGISTRATION_SUCCESS = "registration_success"
    REGISTRATION_FAILED = "registration_failed"
    
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    
    TOKEN_GENERATED = "token_generated"
    TOKEN_VALIDATED = "token_validated"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"
    TOKEN_MISSING = "token_missing"
    
    PROFILE_ACCESSED = "profile_accessed"
    PROFILE_UPDATED = "profile_updated"
    
    LOGOUT = "logout"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_SUCCESS = "password_reset_success"


class SecurityLogLevel(str, Enum):
    """Security-specific log levels."""
    
    INFO = "info"           # Normal operations
    WARNING = "warning"     # Potential security issues
    ERROR = "error"         # Security violations
    CRITICAL = "critical"   # Serious security breaches


def setup_auth_logger(name: str = "auth") -> logging.Logger:
    """Set up structured logging for authentication events."""
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate handlers
    if not logger.handlers:
        # Create console handler with JSON formatter
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        
        # Create JSON formatter for structured logs
        formatter = AuthLogFormatter()
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        logger.propagate = False  # Prevent duplicate logs
    
    return logger


class AuthLogFormatter(logging.Formatter):
    """JSON formatter for authentication logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        
        # Base log structure
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'event_type'):
            log_entry["event_type"] = record.event_type
        
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
            
        if hasattr(record, 'email'):
            log_entry["email"] = record.email
            
        if hasattr(record, 'ip_address'):
            log_entry["ip_address"] = record.ip_address
            
        if hasattr(record, 'user_agent'):
            log_entry["user_agent"] = record.user_agent
            
        if hasattr(record, 'error_code'):
            log_entry["error_code"] = record.error_code
            
        if hasattr(record, 'details'):
            log_entry["details"] = record.details
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


class AuthLogger:
    """Centralized authentication event logger with security focus."""
    
    def __init__(self):
        self.logger = setup_auth_logger("travel_companion.auth")
    
    def log_registration_attempt(
        self,
        email: str,
        ip_address: str,
        user_agent: str = "unknown",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log user registration attempt."""
        self.logger.info(
            "User registration attempt",
            extra={
                "event_type": AuthEvent.REGISTRATION_ATTEMPT,
                "email": self._sanitize_email(email),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "details": details or {},
            }
        )
    
    def log_registration_success(
        self,
        user_id: UUID,
        email: str,
        ip_address: str,
        user_agent: str = "unknown",
    ) -> None:
        """Log successful user registration."""
        self.logger.info(
            "User registration successful",
            extra={
                "event_type": AuthEvent.REGISTRATION_SUCCESS,
                "user_id": str(user_id),
                "email": self._sanitize_email(email),
                "ip_address": ip_address,
                "user_agent": user_agent,
            }
        )
    
    def log_registration_failed(
        self,
        email: str,
        ip_address: str,
        error_code: str,
        reason: str,
        user_agent: str = "unknown",
    ) -> None:
        """Log failed user registration."""
        self.logger.warning(
            f"User registration failed: {reason}",
            extra={
                "event_type": AuthEvent.REGISTRATION_FAILED,
                "email": self._sanitize_email(email),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "error_code": error_code,
                "details": {"reason": reason},
            }
        )
    
    def log_login_attempt(
        self,
        email: str,
        ip_address: str,
        user_agent: str = "unknown",
    ) -> None:
        """Log user login attempt."""
        self.logger.info(
            "User login attempt",
            extra={
                "event_type": AuthEvent.LOGIN_ATTEMPT,
                "email": self._sanitize_email(email),
                "ip_address": ip_address,
                "user_agent": user_agent,
            }
        )
    
    def log_login_success(
        self,
        user_id: UUID,
        email: str,
        ip_address: str,
        user_agent: str = "unknown",
    ) -> None:
        """Log successful user login."""
        self.logger.info(
            "User login successful",
            extra={
                "event_type": AuthEvent.LOGIN_SUCCESS,
                "user_id": str(user_id),
                "email": self._sanitize_email(email),
                "ip_address": ip_address,
                "user_agent": user_agent,
            }
        )
    
    def log_login_failed(
        self,
        email: str,
        ip_address: str,
        error_code: str,
        reason: str,
        user_agent: str = "unknown",
    ) -> None:
        """Log failed user login."""
        self.logger.warning(
            f"User login failed: {reason}",
            extra={
                "event_type": AuthEvent.LOGIN_FAILED,
                "email": self._sanitize_email(email),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "error_code": error_code,
                "details": {"reason": reason},
            }
        )
    
    def log_token_generated(
        self,
        user_id: UUID,
        ip_address: str,
        expires_in_minutes: int = 30,
    ) -> None:
        """Log JWT token generation."""
        self.logger.info(
            "JWT token generated",
            extra={
                "event_type": AuthEvent.TOKEN_GENERATED,
                "user_id": str(user_id),
                "ip_address": ip_address,
                "details": {"expires_in_minutes": expires_in_minutes},
            }
        )
    
    def log_token_validated(
        self,
        user_id: UUID,
        ip_address: str,
        endpoint: str,
    ) -> None:
        """Log successful token validation."""
        self.logger.info(
            "JWT token validated",
            extra={
                "event_type": AuthEvent.TOKEN_VALIDATED,
                "user_id": str(user_id),
                "ip_address": ip_address,
                "details": {"endpoint": endpoint},
            }
        )
    
    def log_token_expired(
        self,
        ip_address: str,
        endpoint: str,
        user_agent: str = "unknown",
    ) -> None:
        """Log expired token access attempt."""
        self.logger.warning(
            "Expired token used",
            extra={
                "event_type": AuthEvent.TOKEN_EXPIRED,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "error_code": "AUTH002",
                "details": {"endpoint": endpoint},
            }
        )
    
    def log_token_invalid(
        self,
        ip_address: str,
        endpoint: str,
        reason: str,
        user_agent: str = "unknown",
    ) -> None:
        """Log invalid token access attempt."""
        self.logger.warning(
            f"Invalid token used: {reason}",
            extra={
                "event_type": AuthEvent.TOKEN_INVALID,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "error_code": "AUTH003",
                "details": {
                    "endpoint": endpoint,
                    "reason": reason,
                },
            }
        )
    
    def log_token_missing(
        self,
        ip_address: str,
        endpoint: str,
        user_agent: str = "unknown",
    ) -> None:
        """Log missing token access attempt."""
        self.logger.warning(
            "Protected endpoint accessed without token",
            extra={
                "event_type": AuthEvent.TOKEN_MISSING,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "error_code": "AUTH004",
                "details": {"endpoint": endpoint},
            }
        )
    
    def log_profile_accessed(
        self,
        user_id: UUID,
        ip_address: str,
        user_agent: str = "unknown",
    ) -> None:
        """Log user profile access."""
        self.logger.info(
            "User profile accessed",
            extra={
                "event_type": AuthEvent.PROFILE_ACCESSED,
                "user_id": str(user_id),
                "ip_address": ip_address,
                "user_agent": user_agent,
            }
        )
    
    def log_profile_updated(
        self,
        user_id: UUID,
        ip_address: str,
        fields_updated: list,
        user_agent: str = "unknown",
    ) -> None:
        """Log user profile update."""
        self.logger.info(
            "User profile updated",
            extra={
                "event_type": AuthEvent.PROFILE_UPDATED,
                "user_id": str(user_id),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "details": {"fields_updated": fields_updated},
            }
        )
    
    def log_security_event(
        self,
        event_type: str,
        level: SecurityLogLevel,
        message: str,
        ip_address: str,
        error_code: Optional[str] = None,
        user_id: Optional[UUID] = None,
        email: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log general security events."""
        
        extra_data = {
            "event_type": event_type,
            "ip_address": ip_address,
        }
        
        if error_code:
            extra_data["error_code"] = error_code
            
        if user_id:
            extra_data["user_id"] = str(user_id)
            
        if email:
            extra_data["email"] = self._sanitize_email(email)
            
        if details:
            extra_data["details"] = details
        
        log_method = getattr(self.logger, level.value)
        log_method(message, extra=extra_data)
    
    def _sanitize_email(self, email: str) -> str:
        """Sanitize email for logging (mask domain for privacy)."""
        if "@" in email:
            local, domain = email.split("@", 1)
            # Mask part of local and domain for privacy
            masked_local = local[:2] + "*" * (len(local) - 2) if len(local) > 2 else local
            domain_parts = domain.split(".")
            if len(domain_parts) > 1:
                masked_domain = domain_parts[0][:1] + "*" * (len(domain_parts[0]) - 1)
                masked_domain += "." + ".".join(domain_parts[1:])
            else:
                masked_domain = domain[:1] + "*" * (len(domain) - 1)
            return f"{masked_local}@{masked_domain}"
        return email


# Global auth logger instance
auth_logger = AuthLogger()


def get_client_ip(request) -> str:
    """Extract client IP from request, considering proxies."""
    # Check for forwarded headers first (from load balancers/proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct connection IP
    return request.client.host if request.client else "unknown"


def get_user_agent(request) -> str:
    """Extract User-Agent from request."""
    return request.headers.get("User-Agent", "unknown")
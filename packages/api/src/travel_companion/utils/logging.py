"""Structured logging utilities for the Travel Companion API."""

import json
import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any
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


class WorkflowEvent(str, Enum):
    """Workflow event types for logging."""

    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_TIMEOUT = "workflow_timeout"

    NODE_ENTERED = "node_entered"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"

    STATE_UPDATED = "state_updated"
    STATE_PERSISTED = "state_persisted"
    STATE_RESTORED = "state_restored"


class SecurityLogLevel(str, Enum):
    """Security-specific log levels."""

    INFO = "info"  # Normal operations
    WARNING = "warning"  # Potential security issues
    ERROR = "error"  # Security violations
    CRITICAL = "critical"  # Serious security breaches


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
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "event_type"):
            log_entry["event_type"] = record.event_type

        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id

        if hasattr(record, "email"):
            log_entry["email"] = record.email

        if hasattr(record, "ip_address"):
            log_entry["ip_address"] = record.ip_address

        if hasattr(record, "user_agent"):
            log_entry["user_agent"] = record.user_agent

        if hasattr(record, "error_code"):
            log_entry["error_code"] = record.error_code

        if hasattr(record, "details"):
            log_entry["details"] = record.details

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


class AuthLogger:
    """Centralized authentication event logger with security focus."""

    def __init__(self) -> None:
        self.logger = setup_auth_logger("travel_companion.auth")

    def log_registration_attempt(
        self,
        email: str,
        ip_address: str,
        user_agent: str = "unknown",
        details: dict[str, Any] | None = None,
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
            },
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
            },
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
            },
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
            },
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
            },
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
            },
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
            },
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
            },
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
            },
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
            },
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
            },
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
            },
        )

    def log_profile_updated(
        self,
        user_id: UUID,
        ip_address: str,
        fields_updated: list[str],
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
            },
        )

    def log_security_event(
        self,
        event_type: str,
        level: SecurityLogLevel,
        message: str,
        ip_address: str,
        error_code: str | None = None,
        user_id: UUID | None = None,
        email: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log general security events."""

        extra_data: dict[str, Any] = {
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


class WorkflowLogger:
    """Centralized workflow event logger for LangGraph workflows."""

    def __init__(self) -> None:
        self.logger = setup_auth_logger("travel_companion.workflow")

    def log_workflow_started(
        self,
        workflow_id: str,
        workflow_type: str,
        request_id: str,
        input_data: dict[str, Any] | None = None,
    ) -> None:
        """Log workflow execution start."""
        self.logger.info(
            f"Workflow {workflow_type} started",
            extra={
                "event_type": WorkflowEvent.WORKFLOW_STARTED,
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "request_id": request_id,
                "details": {"input_keys": list(input_data.keys()) if input_data else []},
            },
        )

    def log_workflow_completed(
        self,
        workflow_id: str,
        workflow_type: str,
        request_id: str,
        execution_time_ms: float,
        output_data: dict[str, Any] | None = None,
    ) -> None:
        """Log successful workflow completion."""
        self.logger.info(
            f"Workflow {workflow_type} completed successfully",
            extra={
                "event_type": WorkflowEvent.WORKFLOW_COMPLETED,
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "request_id": request_id,
                "details": {
                    "execution_time_ms": execution_time_ms,
                    "output_keys": list(output_data.keys()) if output_data else [],
                },
            },
        )

    def log_workflow_failed(
        self,
        workflow_id: str,
        workflow_type: str,
        request_id: str,
        error: str,
        execution_time_ms: float,
        node_name: str | None = None,
    ) -> None:
        """Log workflow execution failure."""
        self.logger.error(
            f"Workflow {workflow_type} failed: {error}",
            extra={
                "event_type": WorkflowEvent.WORKFLOW_FAILED,
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "request_id": request_id,
                "error_code": "WORKFLOW_FAILED",
                "details": {
                    "execution_time_ms": execution_time_ms,
                    "failed_node": node_name,
                    "error_message": error,
                },
            },
        )

    def log_node_entered(
        self,
        workflow_id: str,
        node_name: str,
        request_id: str,
        state_keys: list[str] | None = None,
    ) -> None:
        """Log node execution start."""
        self.logger.debug(
            f"Entering node: {node_name}",
            extra={
                "event_type": WorkflowEvent.NODE_ENTERED,
                "workflow_id": workflow_id,
                "node_name": node_name,
                "request_id": request_id,
                "details": {"state_keys": state_keys or []},
            },
        )

    def log_node_completed(
        self,
        workflow_id: str,
        node_name: str,
        request_id: str,
        execution_time_ms: float,
        output_keys: list[str] | None = None,
    ) -> None:
        """Log successful node completion."""
        self.logger.debug(
            f"Node {node_name} completed",
            extra={
                "event_type": WorkflowEvent.NODE_COMPLETED,
                "workflow_id": workflow_id,
                "node_name": node_name,
                "request_id": request_id,
                "details": {
                    "execution_time_ms": execution_time_ms,
                    "output_keys": output_keys or [],
                },
            },
        )

    def log_node_failed(
        self,
        workflow_id: str,
        node_name: str,
        request_id: str,
        error: str,
        execution_time_ms: float,
    ) -> None:
        """Log node execution failure."""
        self.logger.error(
            f"Node {node_name} failed: {error}",
            extra={
                "event_type": WorkflowEvent.NODE_FAILED,
                "workflow_id": workflow_id,
                "node_name": node_name,
                "request_id": request_id,
                "error_code": "NODE_FAILED",
                "details": {
                    "execution_time_ms": execution_time_ms,
                    "error_message": error,
                },
            },
        )

    def log_state_updated(
        self,
        workflow_id: str,
        request_id: str,
        updated_keys: list[str],
        node_name: str | None = None,
    ) -> None:
        """Log workflow state update."""
        self.logger.debug(
            "Workflow state updated",
            extra={
                "event_type": WorkflowEvent.STATE_UPDATED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "node_name": node_name,
                "details": {"updated_keys": updated_keys},
            },
        )

    def log_state_persisted(
        self,
        workflow_id: str,
        request_id: str,
        persistence_time_ms: float,
    ) -> None:
        """Log workflow state persistence."""
        self.logger.debug(
            "Workflow state persisted",
            extra={
                "event_type": WorkflowEvent.STATE_PERSISTED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": {"persistence_time_ms": persistence_time_ms},
            },
        )

    def log_state_restored(
        self,
        workflow_id: str,
        request_id: str,
        restoration_time_ms: float,
        restored_keys: list[str],
    ) -> None:
        """Log workflow state restoration."""
        self.logger.info(
            "Workflow state restored",
            extra={
                "event_type": WorkflowEvent.STATE_RESTORED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": {
                    "restoration_time_ms": restoration_time_ms,
                    "restored_keys": restored_keys,
                },
            },
        )


# Global logger instances
auth_logger = AuthLogger()
workflow_logger = WorkflowLogger()


def get_client_ip(request: Any) -> str:
    """Extract client IP from request, considering proxies."""
    # Check for forwarded headers first (from load balancers/proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return str(forwarded_for.split(",")[0].strip())

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return str(real_ip.strip())

    # Fall back to direct connection IP
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Any) -> str:
    """Extract User-Agent from request."""
    return str(request.headers.get("User-Agent", "unknown"))

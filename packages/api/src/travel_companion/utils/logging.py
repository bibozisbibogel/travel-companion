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
    
    # Parallel execution events
    PARALLEL_EXECUTION_STARTED = "parallel_execution_started"
    PARALLEL_EXECUTION_COMPLETED = "parallel_execution_completed"
    PARALLEL_EXECUTION_FAILED = "parallel_execution_failed"
    
    # Agent coordination events
    AGENT_EXECUTION_STARTED = "agent_execution_started"
    AGENT_EXECUTION_COMPLETED = "agent_execution_completed"
    AGENT_EXECUTION_FAILED = "agent_execution_failed"
    AGENT_FAILURE_HANDLED = "agent_failure_handled"
    
    # Coordination events  
    COORDINATION_STARTED = "coordination_started"
    COORDINATION_COMPLETED = "coordination_completed"
    COORDINATION_FAILED = "coordination_failed"
    COORDINATION_METRICS = "coordination_metrics"


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
        level: SecurityLogLevel | str,
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

        # Handle both enum and string levels
        if isinstance(level, SecurityLogLevel):
            log_level = level.value
        else:
            log_level = level

        log_method = getattr(self.logger, log_level)
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

    # Parallel execution logging methods
    def log_parallel_execution_started(
        self,
        workflow_id: str,
        request_id: str,
        total_agents: int,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Log parallel execution start."""
        self.logger.info(
            "Parallel agent execution started",
            extra={
                "event_type": WorkflowEvent.PARALLEL_EXECUTION_STARTED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": {
                    "total_agents": total_agents,
                    "config": config or {},
                },
            },
        )

    def log_parallel_execution_completed(
        self,
        workflow_id: str,
        request_id: str,
        execution_metrics: dict[str, Any],
    ) -> None:
        """Log successful parallel execution completion."""
        self.logger.info(
            "Parallel agent execution completed",
            extra={
                "event_type": WorkflowEvent.PARALLEL_EXECUTION_COMPLETED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": execution_metrics,
            },
        )

    def log_parallel_execution_failed(
        self,
        workflow_id: str,
        request_id: str,
        error: str,
        partial_metrics: dict[str, Any],
    ) -> None:
        """Log parallel execution failure."""
        self.logger.error(
            f"Parallel agent execution failed: {error}",
            extra={
                "event_type": WorkflowEvent.PARALLEL_EXECUTION_FAILED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "error_code": "PARALLEL_EXECUTION_FAILED",
                "details": {
                    "error_message": error,
                    "partial_metrics": partial_metrics,
                },
            },
        )

    def log_parallel_execution_starting(
        self,
        workflow_id: str,
        request_id: str,
        agent_count: int,
    ) -> None:
        """Log parallel execution starting (convenience method)."""
        self.logger.info(
            f"Starting parallel execution of {agent_count} agents",
            extra={
                "event_type": WorkflowEvent.PARALLEL_EXECUTION_STARTED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": {"agent_count": agent_count},
            },
        )

    # Agent coordination logging methods
    def log_agent_execution_started(
        self,
        workflow_id: str,
        request_id: str,
        agent_name: str,
        phase: str,
    ) -> None:
        """Log individual agent execution start."""
        self.logger.debug(
            f"Agent {agent_name} execution started in phase {phase}",
            extra={
                "event_type": WorkflowEvent.AGENT_EXECUTION_STARTED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "agent_name": agent_name,
                "details": {"execution_phase": phase},
            },
        )

    def log_agent_execution_completed(
        self,
        workflow_id: str,
        request_id: str,
        agent_name: str,
        execution_time_ms: float,
    ) -> None:
        """Log individual agent execution completion."""
        self.logger.debug(
            f"Agent {agent_name} execution completed",
            extra={
                "event_type": WorkflowEvent.AGENT_EXECUTION_COMPLETED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "agent_name": agent_name,
                "details": {"execution_time_ms": execution_time_ms},
            },
        )

    def log_agent_execution_failed(
        self,
        workflow_id: str,
        request_id: str,
        agent_name: str,
        error: str,
        execution_time_ms: float,
    ) -> None:
        """Log individual agent execution failure."""
        self.logger.warning(
            f"Agent {agent_name} execution failed: {error}",
            extra={
                "event_type": WorkflowEvent.AGENT_EXECUTION_FAILED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "agent_name": agent_name,
                "error_code": "AGENT_EXECUTION_FAILED",
                "details": {
                    "execution_time_ms": execution_time_ms,
                    "error_message": error,
                },
            },
        )

    def log_agent_failure_handled(
        self,
        workflow_id: str,
        request_id: str,
        agent_name: str,
        error: str,
        workflow_continuing: bool,
    ) -> None:
        """Log agent failure being handled gracefully."""
        self.logger.info(
            f"Agent {agent_name} failure handled, workflow continuing: {workflow_continuing}",
            extra={
                "event_type": WorkflowEvent.AGENT_FAILURE_HANDLED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "agent_name": agent_name,
                "details": {
                    "error_message": error,
                    "workflow_continuing": workflow_continuing,
                },
            },
        )

    # Coordination logging methods
    def log_coordination_started(
        self,
        workflow_id: str,
        request_id: str,
        total_agents: int,
    ) -> None:
        """Log workflow coordination start."""
        self.logger.info(
            "Workflow coordination started",
            extra={
                "event_type": WorkflowEvent.COORDINATION_STARTED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": {"total_agents": total_agents},
            },
        )

    def log_coordination_completed(
        self,
        workflow_id: str,
        request_id: str,
        execution_summary: dict[str, Any],
    ) -> None:
        """Log workflow coordination completion."""
        self.logger.info(
            "Workflow coordination completed",
            extra={
                "event_type": WorkflowEvent.COORDINATION_COMPLETED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": execution_summary,
            },
        )

    def log_coordination_failed(
        self,
        workflow_id: str,
        request_id: str,
        error: str,
        execution_summary: dict[str, Any],
    ) -> None:
        """Log workflow coordination failure."""
        self.logger.error(
            f"Workflow coordination failed: {error}",
            extra={
                "event_type": WorkflowEvent.COORDINATION_FAILED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "error_code": "COORDINATION_FAILED",
                "details": {
                    "error_message": error,
                    "execution_summary": execution_summary,
                },
            },
        )

    def log_coordination_metrics(
        self,
        workflow_id: str,
        request_id: str,
        metrics: dict[str, Any],
    ) -> None:
        """Log coordination performance metrics."""
        self.logger.info(
            "Coordination metrics recorded",
            extra={
                "event_type": WorkflowEvent.COORDINATION_METRICS,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": metrics,
            },
        )

    # Enhanced state persistence logging methods for Task 6
    def log_enhanced_state_persisted(
        self,
        workflow_id: str,
        request_id: str,
        persistence_time_ms: float,
        checkpoint_type: str,
        state_size_bytes: int,
        progress_description: str | None = None,
    ) -> None:
        """Log enhanced workflow state persistence."""
        self.logger.debug(
            "Enhanced workflow state persisted",
            extra={
                "event_type": WorkflowEvent.STATE_PERSISTED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": {
                    "persistence_time_ms": persistence_time_ms,
                    "checkpoint_type": checkpoint_type,
                    "state_size_bytes": state_size_bytes,
                    "progress_description": progress_description,
                },
            },
        )

    def log_enhanced_state_restored(
        self,
        workflow_id: str,
        request_id: str,
        restoration_time_ms: float,
        snapshot_id: str | None,
        include_progress: bool,
    ) -> None:
        """Log enhanced workflow state restoration."""
        self.logger.info(
            "Enhanced workflow state restored",
            extra={
                "event_type": WorkflowEvent.STATE_RESTORED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": {
                    "restoration_time_ms": restoration_time_ms,
                    "snapshot_id": snapshot_id,
                    "include_progress": include_progress,
                },
            },
        )

    def log_workflow_initialized(
        self,
        workflow_id: str,
        request_id: str,
        ttl_seconds: int,
        estimated_duration_minutes: int | None,
    ) -> None:
        """Log workflow initialization with enhanced tracking."""
        self.logger.info(
            "Workflow initialized with enhanced tracking",
            extra={
                "event_type": WorkflowEvent.WORKFLOW_STARTED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": {
                    "ttl_seconds": ttl_seconds,
                    "estimated_duration_minutes": estimated_duration_minutes,
                    "enhanced_tracking": True,
                },
            },
        )

    def log_workflow_initialization_error(
        self,
        workflow_id: str,
        error: str,
    ) -> None:
        """Log workflow initialization error."""
        self.logger.error(
            f"Workflow initialization failed: {error}",
            extra={
                "event_type": WorkflowEvent.WORKFLOW_FAILED,
                "workflow_id": workflow_id,
                "error_code": "WORKFLOW_INIT_FAILED",
                "details": {
                    "error_message": error,
                    "initialization_phase": True,
                },
            },
        )

    def log_workflow_suspended(
        self,
        workflow_id: str,
        request_id: str,
        reason: str,
        suspended_ttl: int,
    ) -> None:
        """Log workflow suspension."""
        self.logger.info(
            f"Workflow suspended: {reason}",
            extra={
                "event_type": "workflow_suspended",
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": {
                    "reason": reason,
                    "suspended_ttl": suspended_ttl,
                },
            },
        )

    def log_workflow_suspension_error(
        self,
        workflow_id: str,
        error: str,
        reason: str,
    ) -> None:
        """Log workflow suspension error."""
        self.logger.error(
            f"Workflow suspension failed: {error}",
            extra={
                "event_type": "workflow_suspension_failed",
                "workflow_id": workflow_id,
                "error_code": "WORKFLOW_SUSPEND_FAILED",
                "details": {
                    "error_message": error,
                    "attempted_reason": reason,
                },
            },
        )

    def log_workflow_resumed(
        self,
        workflow_id: str,
        request_id: str,
        snapshot_id: str | None,
        active_ttl: int,
    ) -> None:
        """Log workflow resumption."""
        self.logger.info(
            "Workflow resumed from suspension",
            extra={
                "event_type": "workflow_resumed",
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": {
                    "snapshot_id": snapshot_id,
                    "active_ttl": active_ttl,
                },
            },
        )

    def log_workflow_resume_error(
        self,
        workflow_id: str,
        error: str,
        snapshot_id: str | None,
    ) -> None:
        """Log workflow resumption error."""
        self.logger.error(
            f"Workflow resumption failed: {error}",
            extra={
                "event_type": "workflow_resume_failed",
                "workflow_id": workflow_id,
                "error_code": "WORKFLOW_RESUME_FAILED",
                "details": {
                    "error_message": error,
                    "snapshot_id": snapshot_id,
                },
            },
        )

    def log_workflow_completed(
        self,
        workflow_id: str,
        request_id: str,
        completion_summary: str | None,
        completed_ttl: int,
    ) -> None:
        """Log workflow completion with enhanced tracking."""
        self.logger.info(
            "Workflow completed successfully",
            extra={
                "event_type": WorkflowEvent.WORKFLOW_COMPLETED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": {
                    "completion_summary": completion_summary,
                    "completed_ttl": completed_ttl,
                    "enhanced_tracking": True,
                },
            },
        )

    def log_workflow_completion_error(
        self,
        workflow_id: str,
        error: str,
        completion_summary: str | None,
    ) -> None:
        """Log workflow completion error."""
        self.logger.error(
            f"Workflow completion failed: {error}",
            extra={
                "event_type": WorkflowEvent.WORKFLOW_FAILED,
                "workflow_id": workflow_id,
                "error_code": "WORKFLOW_COMPLETE_FAILED",
                "details": {
                    "error_message": error,
                    "attempted_completion_summary": completion_summary,
                },
            },
        )

    def log_enhanced_checkpoint_created(
        self,
        workflow_id: str,
        request_id: str,
        snapshot_id: str,
        checkpoint_type: str,
        description: str,
    ) -> None:
        """Log enhanced checkpoint creation."""
        self.logger.debug(
            f"Enhanced checkpoint created: {checkpoint_type}",
            extra={
                "event_type": "checkpoint_created",
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": {
                    "snapshot_id": snapshot_id,
                    "checkpoint_type": checkpoint_type,
                    "description": description,
                },
            },
        )

    def log_manual_checkpoint_created(
        self,
        workflow_id: str,
        request_id: str,
        snapshot_id: str,
        description: str,
    ) -> None:
        """Log manual checkpoint creation."""
        self.logger.info(
            "Manual checkpoint created",
            extra={
                "event_type": "manual_checkpoint_created",
                "workflow_id": workflow_id,
                "request_id": request_id,
                "details": {
                    "snapshot_id": snapshot_id,
                    "description": description,
                },
            },
        )

    def log_snapshot_storage_error(
        self,
        workflow_id: str,
        snapshot_id: str,
        error: str,
    ) -> None:
        """Log snapshot storage error."""
        self.logger.error(
            f"Snapshot storage failed: {error}",
            extra={
                "event_type": "snapshot_storage_failed",
                "workflow_id": workflow_id,
                "error_code": "SNAPSHOT_STORE_FAILED",
                "details": {
                    "snapshot_id": snapshot_id,
                    "error_message": error,
                },
            },
        )

    def log_snapshot_listing_error(
        self,
        workflow_id: str,
        error: str,
    ) -> None:
        """Log snapshot listing error."""
        self.logger.error(
            f"Snapshot listing failed: {error}",
            extra={
                "event_type": "snapshot_listing_failed",
                "workflow_id": workflow_id,
                "error_code": "SNAPSHOT_LIST_FAILED",
                "details": {"error_message": error},
            },
        )

    def log_snapshot_restoration_error(
        self,
        workflow_id: str,
        snapshot_id: str,
        error: str,
    ) -> None:
        """Log snapshot restoration error."""
        self.logger.error(
            f"Snapshot restoration failed: {error}",
            extra={
                "event_type": "snapshot_restoration_failed",
                "workflow_id": workflow_id,
                "error_code": "SNAPSHOT_RESTORE_FAILED",
                "details": {
                    "snapshot_id": snapshot_id,
                    "error_message": error,
                },
            },
        )

    def log_snapshots_cleaned(
        self,
        workflow_id: str,
        cleaned_count: int,
        remaining_count: int,
    ) -> None:
        """Log snapshot cleanup operation."""
        self.logger.info(
            f"Cleaned {cleaned_count} old snapshots, {remaining_count} remaining",
            extra={
                "event_type": "snapshots_cleaned",
                "workflow_id": workflow_id,
                "details": {
                    "cleaned_count": cleaned_count,
                    "remaining_count": remaining_count,
                },
            },
        )

    def log_snapshot_cleanup_error(
        self,
        workflow_id: str,
        error: str,
    ) -> None:
        """Log snapshot cleanup error."""
        self.logger.error(
            f"Snapshot cleanup failed: {error}",
            extra={
                "event_type": "snapshot_cleanup_failed",
                "workflow_id": workflow_id,
                "error_code": "SNAPSHOT_CLEANUP_FAILED",
                "details": {"error_message": error},
            },
        )

    def log_workflow_cleanup_completed(
        self,
        processed_count: int,
        expired_cleaned: int,
        completed_cleaned: int,
        failed_cleanups: int,
        cleanup_time: float,
    ) -> None:
        """Log comprehensive workflow cleanup completion."""
        self.logger.info(
            f"Workflow cleanup completed: {processed_count} processed, {expired_cleaned + completed_cleaned} cleaned",
            extra={
                "event_type": "workflow_cleanup_completed",
                "details": {
                    "processed_count": processed_count,
                    "expired_cleaned": expired_cleaned,
                    "completed_cleaned": completed_cleaned,
                    "failed_cleanups": failed_cleanups,
                    "cleanup_time_seconds": cleanup_time,
                },
            },
        )

    def log_workflow_cleanup_error(
        self,
        error: str,
    ) -> None:
        """Log workflow cleanup error."""
        self.logger.error(
            f"Workflow cleanup failed: {error}",
            extra={
                "event_type": "workflow_cleanup_failed",
                "error_code": "WORKFLOW_CLEANUP_FAILED",
                "details": {"error_message": error},
            },
        )

    def log_single_workflow_cleanup_error(
        self,
        workflow_id: str,
        error: str,
    ) -> None:
        """Log single workflow cleanup error."""
        self.logger.error(
            f"Single workflow cleanup failed: {error}",
            extra={
                "event_type": "single_workflow_cleanup_failed",
                "workflow_id": workflow_id,
                "error_code": "SINGLE_WORKFLOW_CLEANUP_FAILED",
                "details": {"error_message": error},
            },
        )

    def log_cleanup_scheduled(
        self,
        workflow_id: str,
        cleanup_delay: int,
        cleanup_type: str,
    ) -> None:
        """Log cleanup scheduling."""
        self.logger.debug(
            f"Cleanup scheduled for workflow: {cleanup_type}",
            extra={
                "event_type": "cleanup_scheduled",
                "workflow_id": workflow_id,
                "details": {
                    "cleanup_delay_seconds": cleanup_delay,
                    "cleanup_type": cleanup_type,
                },
            },
        )

    def log_cleanup_scheduling_error(
        self,
        workflow_id: str,
        error: str,
    ) -> None:
        """Log cleanup scheduling error."""
        self.logger.error(
            f"Cleanup scheduling failed: {error}",
            extra={
                "event_type": "cleanup_scheduling_failed",
                "workflow_id": workflow_id,
                "error_code": "CLEANUP_SCHEDULE_FAILED",
                "details": {"error_message": error},
            },
        )

    def log_workflow_index_error(
        self,
        workflow_id: str,
        error: str,
    ) -> None:
        """Log workflow index operation error."""
        self.logger.error(
            f"Workflow index operation failed: {error}",
            extra={
                "event_type": "workflow_index_failed",
                "workflow_id": workflow_id,
                "error_code": "WORKFLOW_INDEX_FAILED",
                "details": {"error_message": error},
            },
        )

    def log_progress_update_error(
        self,
        workflow_id: str,
        error: str,
    ) -> None:
        """Log progress update error."""
        self.logger.error(
            f"Progress update failed: {error}",
            extra={
                "event_type": "progress_update_failed",
                "workflow_id": workflow_id,
                "error_code": "PROGRESS_UPDATE_FAILED",
                "details": {"error_message": error},
            },
        )

    def log_progress_retrieval_error(
        self,
        workflow_id: str,
        error: str,
    ) -> None:
        """Log progress retrieval error."""
        self.logger.error(
            f"Progress retrieval failed: {error}",
            extra={
                "event_type": "progress_retrieval_failed",
                "workflow_id": workflow_id,
                "error_code": "PROGRESS_RETRIEVAL_FAILED",
                "details": {"error_message": error},
            },
        )

    def log_metadata_retrieval_error(
        self,
        workflow_id: str,
        error: str,
    ) -> None:
        """Log metadata retrieval error."""
        self.logger.error(
            f"Metadata retrieval failed: {error}",
            extra={
                "event_type": "metadata_retrieval_failed",
                "workflow_id": workflow_id,
                "error_code": "METADATA_RETRIEVAL_FAILED",
                "details": {"error_message": error},
            },
        )

    def log_heartbeat_update_error(
        self,
        workflow_id: str,
        error: str,
    ) -> None:
        """Log heartbeat update error."""
        self.logger.error(
            f"Heartbeat update failed: {error}",
            extra={
                "event_type": "heartbeat_update_failed",
                "workflow_id": workflow_id,
                "error_code": "HEARTBEAT_UPDATE_FAILED",
                "details": {"error_message": error},
            },
        )

    def log_heartbeat_stop_error(
        self,
        workflow_id: str,
        error: str,
    ) -> None:
        """Log heartbeat stop error."""
        self.logger.error(
            f"Heartbeat stop failed: {error}",
            extra={
                "event_type": "heartbeat_stop_failed",
                "workflow_id": workflow_id,
                "error_code": "HEARTBEAT_STOP_FAILED",
                "details": {"error_message": error},
            },
        )

    def log_state_persistence_error(
        self,
        workflow_id: str,
        request_id: str,
        error: str,
        checkpoint_type: str,
    ) -> None:
        """Log state persistence error."""
        self.logger.error(
            f"State persistence failed: {error}",
            extra={
                "event_type": WorkflowEvent.STATE_PERSISTED,
                "workflow_id": workflow_id,
                "request_id": request_id,
                "error_code": "STATE_PERSIST_FAILED",
                "details": {
                    "error_message": error,
                    "checkpoint_type": checkpoint_type,
                },
            },
        )

    # Convenience logging methods
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message."""
        self.logger.warning(message, extra=kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message."""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message."""
        self.logger.info(message, extra=kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message."""
        self.logger.error(message, extra=kwargs)

    def log_workflow_cleanup(
        self, 
        workflow_id: str,
        cleanup_scope: str = "full",
    ) -> None:
        """Log workflow data cleanup."""
        self.logger.info(
            "workflow.cleanup",
            workflow_id=workflow_id,
            cleanup_scope=cleanup_scope,
        )

    def log_workflow_cancelled(
        self,
        workflow_id: str,
        request_id: str,
        cancellation_reason: str = "user_request",
    ) -> None:
        """Log workflow cancellation."""
        self.logger.warning(
            "workflow.cancelled",
            workflow_id=workflow_id,
            request_id=request_id,
            cancellation_reason=cancellation_reason,
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
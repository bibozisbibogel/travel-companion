"""Custom exception classes and error handling for the Travel Companion API."""

from enum import Enum
from typing import Any


class AuthErrorCode(str, Enum):
    """Authentication error codes for standardized responses."""

    INVALID_CREDENTIALS = "AUTH001"
    TOKEN_EXPIRED = "AUTH002"
    TOKEN_INVALID = "AUTH003"
    TOKEN_MISSING = "AUTH004"
    USER_NOT_FOUND = "AUTH005"
    EMAIL_VALIDATION = "AUTH006"
    PASSWORD_VALIDATION = "AUTH007"
    USER_ALREADY_EXISTS = "AUTH008"
    REGISTRATION_FAILED = "AUTH009"
    LOGIN_FAILED = "AUTH010"
    TOKEN_GENERATION_FAILED = "AUTH011"
    AUTHENTICATION_REQUIRED = "AUTH012"
    INSUFFICIENT_PERMISSIONS = "AUTH013"


class DatabaseErrorCode(str, Enum):
    """Database error codes for standardized responses."""

    CONNECTION_FAILED = "DB001"
    QUERY_FAILED = "DB002"
    CONSTRAINT_VIOLATION = "DB003"
    TRANSACTION_FAILED = "DB004"
    USER_LOOKUP_FAILED = "DB005"


class WorkflowErrorCode(str, Enum):
    """Workflow and agent orchestration error codes."""

    AGENT_EXECUTION_FAILED = "WF001"
    CIRCUIT_BREAKER_OPEN = "WF002"
    RETRY_EXHAUSTED = "WF003"
    CRITICAL_SERVICE_UNAVAILABLE = "WF004"
    CRITICAL_SERVICE_FAILED = "WF005"
    WORKFLOW_TIMEOUT = "WF006"
    AGENT_COORDINATION_FAILED = "WF007"
    FALLBACK_ACTIVATION = "WF008"
    PARTIAL_WORKFLOW_SUCCESS = "WF009"


class ValidationErrorCode(str, Enum):
    """Validation error codes for standardized responses."""

    INVALID_EMAIL_FORMAT = "VAL001"
    INVALID_PASSWORD_FORMAT = "VAL002"
    MISSING_REQUIRED_FIELD = "VAL003"
    INVALID_UUID_FORMAT = "VAL004"
    INVALID_JSON_FORMAT = "VAL005"


class TravelCompanionError(Exception):
    """Base exception for Travel Companion application."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to standardized error response format."""
        error_response = {
            "error": True,
            "message": self.message,
            "data": None,
        }

        if self.error_code:
            error_response["error_code"] = self.error_code

        if self.details:
            error_response["details"] = self.details

        return error_response


class ValidationError(TravelCompanionError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        error_code: str = ValidationErrorCode.MISSING_REQUIRED_FIELD,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        enhanced_details = details or {}
        if field:
            enhanced_details["field"] = field
        super().__init__(message, error_code, enhanced_details)


class AuthenticationError(TravelCompanionError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = AuthErrorCode.INVALID_CREDENTIALS,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)


class AuthorizationError(TravelCompanionError):
    """Raised when authorization fails."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        error_code: str = AuthErrorCode.INSUFFICIENT_PERMISSIONS,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)


class UserNotFoundError(TravelCompanionError):
    """Raised when a user is not found."""

    def __init__(
        self,
        message: str = "User not found",
        error_code: str = AuthErrorCode.USER_NOT_FOUND,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        enhanced_details = details or {}
        if user_id:
            enhanced_details["user_id"] = user_id
        super().__init__(message, error_code, enhanced_details)


class UserAlreadyExistsError(TravelCompanionError):
    """Raised when trying to create a user that already exists."""

    def __init__(
        self,
        message: str = "User already exists",
        error_code: str = AuthErrorCode.USER_ALREADY_EXISTS,
        email: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        enhanced_details = details or {}
        if email:
            enhanced_details["email"] = email
        super().__init__(message, error_code, enhanced_details)


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT token has expired."""

    def __init__(
        self,
        message: str = "Token has expired",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, AuthErrorCode.TOKEN_EXPIRED, details)


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT token is invalid."""

    def __init__(
        self,
        message: str = "Invalid token",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, AuthErrorCode.TOKEN_INVALID, details)


class TokenMissingError(AuthenticationError):
    """Raised when a JWT token is missing."""

    def __init__(
        self,
        message: str = "Authentication token required",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, AuthErrorCode.TOKEN_MISSING, details)


class ExternalAPIError(TravelCompanionError):
    """Raised when external API calls fail."""

    def __init__(
        self,
        message: str,
        service: str | None = None,
        status_code: int | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        enhanced_details = details or {}
        enhanced_details.update(
            {
                "service": service,
                "status_code": status_code,
            }
        )
        super().__init__(message, error_code, enhanced_details)


class RateLimitError(ExternalAPIError):
    """Raised when API rate limits are exceeded."""

    def __init__(
        self,
        message: str,
        service: str | None = None,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        enhanced_details = details or {}
        if retry_after:
            enhanced_details["retry_after"] = retry_after
        super().__init__(message, service, 429, "RATE_LIMIT_EXCEEDED", enhanced_details)


class DatabaseError(TravelCompanionError):
    """Raised when database operations fail."""

    def __init__(
        self,
        message: str,
        error_code: str = DatabaseErrorCode.QUERY_FAILED,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        enhanced_details = details or {}
        if operation:
            enhanced_details["operation"] = operation
        super().__init__(message, error_code, enhanced_details)


class WorkflowError(TravelCompanionError):
    """Raised when workflow orchestration fails."""

    def __init__(
        self,
        message: str,
        error_code: str = WorkflowErrorCode.AGENT_EXECUTION_FAILED,
        agent_name: str | None = None,
        workflow_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        enhanced_details = details or {}
        if agent_name:
            enhanced_details["agent_name"] = agent_name
        if workflow_id:
            enhanced_details["workflow_id"] = workflow_id
        super().__init__(message, error_code, enhanced_details)


class AgentExecutionError(WorkflowError):
    """Raised when agent execution fails."""

    def __init__(
        self,
        message: str,
        agent_name: str,
        error_code: str = WorkflowErrorCode.AGENT_EXECUTION_FAILED,
        attempt: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        enhanced_details = details or {}
        if attempt:
            enhanced_details["attempt"] = attempt
        super().__init__(message, error_code, agent_name, None, enhanced_details)


class CircuitBreakerOpenError(WorkflowError):
    """Raised when circuit breaker prevents agent execution."""

    def __init__(
        self,
        message: str,
        agent_name: str,
        next_attempt_time: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        enhanced_details = details or {}
        if next_attempt_time:
            enhanced_details["next_attempt_time"] = next_attempt_time
        super().__init__(
            message,
            WorkflowErrorCode.CIRCUIT_BREAKER_OPEN,
            agent_name,
            None,
            enhanced_details
        )


class CriticalAgentFailureError(WorkflowError):
    """Raised when critical agents fail and workflow cannot continue."""

    def __init__(
        self,
        message: str,
        agent_name: str,
        recovery_strategy: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        enhanced_details = details or {}
        if recovery_strategy:
            enhanced_details["recovery_strategy"] = recovery_strategy
        super().__init__(
            message,
            WorkflowErrorCode.CRITICAL_SERVICE_FAILED,
            agent_name,
            None,
            enhanced_details
        )


# Standardized error response helper functions
def create_error_response(
    message: str,
    error_code: str | None = None,
    details: dict[str, Any] | None = None,
    status_code: int = 400,
) -> dict[str, Any]:
    """Create a standardized error response."""
    response = {
        "error": True,
        "message": message,
        "data": None,
        "status_code": status_code,
    }

    if error_code:
        response["error_code"] = error_code

    if details:
        response["details"] = details

    return response


def create_auth_error_response(
    message: str = "Authentication failed",
    error_code: str = AuthErrorCode.INVALID_CREDENTIALS,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a standardized authentication error response."""
    return create_error_response(
        message=message,
        error_code=error_code,
        details=details,
        status_code=401,
    )


def create_validation_error_response(
    message: str,
    field: str | None = None,
    error_code: str = ValidationErrorCode.MISSING_REQUIRED_FIELD,
) -> dict[str, Any]:
    """Create a standardized validation error response."""
    details = {"field": field} if field else None
    return create_error_response(
        message=message,
        error_code=error_code,
        details=details,
        status_code=422,
    )

"""Custom exception classes and error handling for the Travel Companion API."""

from typing import Dict, Any, Optional
from enum import Enum


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
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
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
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
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
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class AuthorizationError(TravelCompanionError):
    """Raised when authorization fails."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        error_code: str = AuthErrorCode.INSUFFICIENT_PERMISSIONS,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class UserNotFoundError(TravelCompanionError):
    """Raised when a user is not found."""

    def __init__(
        self,
        message: str = "User not found",
        error_code: str = AuthErrorCode.USER_NOT_FOUND,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
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
        email: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
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
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, AuthErrorCode.TOKEN_EXPIRED, details)


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT token is invalid."""

    def __init__(
        self,
        message: str = "Invalid token",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, AuthErrorCode.TOKEN_INVALID, details)


class TokenMissingError(AuthenticationError):
    """Raised when a JWT token is missing."""

    def __init__(
        self,
        message: str = "Authentication token required",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, AuthErrorCode.TOKEN_MISSING, details)


class ExternalAPIError(TravelCompanionError):
    """Raised when external API calls fail."""

    def __init__(
        self, 
        message: str, 
        service: str, 
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        enhanced_details = details or {}
        enhanced_details.update({
            "service": service,
            "status_code": status_code,
        })
        super().__init__(message, error_code, enhanced_details)


class DatabaseError(TravelCompanionError):
    """Raised when database operations fail."""

    def __init__(
        self,
        message: str,
        error_code: str = DatabaseErrorCode.QUERY_FAILED,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        enhanced_details = details or {}
        if operation:
            enhanced_details["operation"] = operation
        super().__init__(message, error_code, enhanced_details)


# Standardized error response helper functions
def create_error_response(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 400,
) -> Dict[str, Any]:
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
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a standardized authentication error response."""
    return create_error_response(
        message=message,
        error_code=error_code,
        details=details,
        status_code=401,
    )


def create_validation_error_response(
    message: str,
    field: Optional[str] = None,
    error_code: str = ValidationErrorCode.MISSING_REQUIRED_FIELD,
) -> Dict[str, Any]:
    """Create a standardized validation error response."""
    details = {"field": field} if field else None
    return create_error_response(
        message=message,
        error_code=error_code,
        details=details,
        status_code=422,
    )
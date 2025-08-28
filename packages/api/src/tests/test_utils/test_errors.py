"""Unit tests for error handling utilities."""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from travel_companion.utils.errors import (
    TravelCompanionError,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    UserNotFoundError,
    UserAlreadyExistsError,
    TokenExpiredError,
    InvalidTokenError,
    TokenMissingError,
    DatabaseError,
    ExternalAPIError,
    AuthErrorCode,
    DatabaseErrorCode,
    ValidationErrorCode,
    create_error_response,
    create_auth_error_response,
    create_validation_error_response,
)


class TestErrorCodes:
    """Test error code enums."""
    
    def test_auth_error_codes(self):
        """Test authentication error codes are correctly defined."""
        assert AuthErrorCode.INVALID_CREDENTIALS == "AUTH001"
        assert AuthErrorCode.TOKEN_EXPIRED == "AUTH002"
        assert AuthErrorCode.TOKEN_INVALID == "AUTH003"
        assert AuthErrorCode.TOKEN_MISSING == "AUTH004"
        assert AuthErrorCode.USER_NOT_FOUND == "AUTH005"
        assert AuthErrorCode.EMAIL_VALIDATION == "AUTH006"
        assert AuthErrorCode.PASSWORD_VALIDATION == "AUTH007"
        assert AuthErrorCode.USER_ALREADY_EXISTS == "AUTH008"
        assert AuthErrorCode.REGISTRATION_FAILED == "AUTH009"
        assert AuthErrorCode.LOGIN_FAILED == "AUTH010"
        assert AuthErrorCode.TOKEN_GENERATION_FAILED == "AUTH011"
        assert AuthErrorCode.AUTHENTICATION_REQUIRED == "AUTH012"
        assert AuthErrorCode.INSUFFICIENT_PERMISSIONS == "AUTH013"
    
    def test_database_error_codes(self):
        """Test database error codes are correctly defined."""
        assert DatabaseErrorCode.CONNECTION_FAILED == "DB001"
        assert DatabaseErrorCode.QUERY_FAILED == "DB002"
        assert DatabaseErrorCode.CONSTRAINT_VIOLATION == "DB003"
        assert DatabaseErrorCode.TRANSACTION_FAILED == "DB004"
        assert DatabaseErrorCode.USER_LOOKUP_FAILED == "DB005"
    
    def test_validation_error_codes(self):
        """Test validation error codes are correctly defined."""
        assert ValidationErrorCode.INVALID_EMAIL_FORMAT == "VAL001"
        assert ValidationErrorCode.INVALID_PASSWORD_FORMAT == "VAL002"
        assert ValidationErrorCode.MISSING_REQUIRED_FIELD == "VAL003"
        assert ValidationErrorCode.INVALID_UUID_FORMAT == "VAL004"
        assert ValidationErrorCode.INVALID_JSON_FORMAT == "VAL005"


class TestTravelCompanionError:
    """Test base TravelCompanionError class."""
    
    def test_basic_error_creation(self):
        """Test basic error creation with message only."""
        error = TravelCompanionError("Test error")
        
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.error_code is None
        assert error.details == {}
    
    def test_error_with_code_and_details(self):
        """Test error creation with error code and details."""
        details = {"field": "email", "value": "invalid"}
        error = TravelCompanionError(
            "Test error",
            error_code="TEST001",
            details=details
        )
        
        assert error.message == "Test error"
        assert error.error_code == "TEST001"
        assert error.details == details
    
    def test_to_dict_basic(self):
        """Test to_dict() method with basic error."""
        error = TravelCompanionError("Test error")
        result = error.to_dict()
        
        expected = {
            "error": True,
            "message": "Test error",
            "data": None,
        }
        assert result == expected
    
    def test_to_dict_with_code_and_details(self):
        """Test to_dict() method with error code and details."""
        details = {"field": "email"}
        error = TravelCompanionError(
            "Test error",
            error_code="TEST001",
            details=details
        )
        result = error.to_dict()
        
        expected = {
            "error": True,
            "message": "Test error",
            "data": None,
            "error_code": "TEST001",
            "details": details,
        }
        assert result == expected


class TestAuthenticationError:
    """Test AuthenticationError class."""
    
    def test_default_authentication_error(self):
        """Test default authentication error creation."""
        error = AuthenticationError()
        
        assert error.message == "Authentication failed"
        assert error.error_code == AuthErrorCode.INVALID_CREDENTIALS
        assert error.details == {}
    
    def test_custom_authentication_error(self):
        """Test custom authentication error creation."""
        details = {"reason": "token_expired"}
        error = AuthenticationError(
            message="Custom auth error",
            error_code=AuthErrorCode.TOKEN_EXPIRED,
            details=details
        )
        
        assert error.message == "Custom auth error"
        assert error.error_code == AuthErrorCode.TOKEN_EXPIRED
        assert error.details == details


class TestAuthorizationError:
    """Test AuthorizationError class."""
    
    def test_default_authorization_error(self):
        """Test default authorization error creation."""
        error = AuthorizationError()
        
        assert error.message == "Insufficient permissions"
        assert error.error_code == AuthErrorCode.INSUFFICIENT_PERMISSIONS
        assert error.details == {}
    
    def test_custom_authorization_error(self):
        """Test custom authorization error creation."""
        details = {"required_role": "admin"}
        error = AuthorizationError(
            message="Admin access required",
            error_code=AuthErrorCode.INSUFFICIENT_PERMISSIONS,
            details=details
        )
        
        assert error.message == "Admin access required"
        assert error.error_code == AuthErrorCode.INSUFFICIENT_PERMISSIONS
        assert error.details == details


class TestValidationError:
    """Test ValidationError class."""
    
    def test_default_validation_error(self):
        """Test default validation error creation."""
        error = ValidationError("Field is required")
        
        assert error.message == "Field is required"
        assert error.error_code == ValidationErrorCode.MISSING_REQUIRED_FIELD
        assert error.details == {}
    
    def test_validation_error_with_field(self):
        """Test validation error with field specification."""
        error = ValidationError(
            message="Invalid email format",
            error_code=ValidationErrorCode.INVALID_EMAIL_FORMAT,
            field="email"
        )
        
        assert error.message == "Invalid email format"
        assert error.error_code == ValidationErrorCode.INVALID_EMAIL_FORMAT
        assert error.details == {"field": "email"}
    
    def test_validation_error_with_field_and_details(self):
        """Test validation error with field and additional details."""
        additional_details = {"pattern": r"^[^@]+@[^@]+\.[^@]+$"}
        error = ValidationError(
            message="Invalid email format",
            error_code=ValidationErrorCode.INVALID_EMAIL_FORMAT,
            field="email",
            details=additional_details
        )
        
        assert error.message == "Invalid email format"
        assert error.error_code == ValidationErrorCode.INVALID_EMAIL_FORMAT
        assert error.details == {"field": "email", "pattern": r"^[^@]+@[^@]+\.[^@]+$"}


class TestUserNotFoundError:
    """Test UserNotFoundError class."""
    
    def test_default_user_not_found_error(self):
        """Test default user not found error creation."""
        error = UserNotFoundError()
        
        assert error.message == "User not found"
        assert error.error_code == AuthErrorCode.USER_NOT_FOUND
        assert error.details == {}
    
    def test_user_not_found_error_with_user_id(self):
        """Test user not found error with user ID."""
        user_id = str(uuid4())
        error = UserNotFoundError(
            message="User does not exist",
            user_id=user_id
        )
        
        assert error.message == "User does not exist"
        assert error.error_code == AuthErrorCode.USER_NOT_FOUND
        assert error.details == {"user_id": user_id}


class TestUserAlreadyExistsError:
    """Test UserAlreadyExistsError class."""
    
    def test_default_user_already_exists_error(self):
        """Test default user already exists error creation."""
        error = UserAlreadyExistsError()
        
        assert error.message == "User already exists"
        assert error.error_code == AuthErrorCode.USER_ALREADY_EXISTS
        assert error.details == {}
    
    def test_user_already_exists_error_with_email(self):
        """Test user already exists error with email."""
        email = "test@example.com"
        error = UserAlreadyExistsError(
            message="Email already registered",
            email=email
        )
        
        assert error.message == "Email already registered"
        assert error.error_code == AuthErrorCode.USER_ALREADY_EXISTS
        assert error.details == {"email": email}


class TestTokenErrors:
    """Test token-related error classes."""
    
    def test_token_expired_error(self):
        """Test TokenExpiredError creation."""
        error = TokenExpiredError()
        
        assert error.message == "Token has expired"
        assert error.error_code == AuthErrorCode.TOKEN_EXPIRED
        assert error.details == {}
    
    def test_token_expired_error_with_details(self):
        """Test TokenExpiredError with custom details."""
        details = {"expired_at": "2023-01-01T00:00:00Z"}
        error = TokenExpiredError(
            message="JWT token expired",
            details=details
        )
        
        assert error.message == "JWT token expired"
        assert error.error_code == AuthErrorCode.TOKEN_EXPIRED
        assert error.details == details
    
    def test_invalid_token_error(self):
        """Test InvalidTokenError creation."""
        error = InvalidTokenError()
        
        assert error.message == "Invalid token"
        assert error.error_code == AuthErrorCode.TOKEN_INVALID
        assert error.details == {}
    
    def test_invalid_token_error_with_details(self):
        """Test InvalidTokenError with custom details."""
        details = {"reason": "malformed_signature"}
        error = InvalidTokenError(
            message="JWT signature invalid",
            details=details
        )
        
        assert error.message == "JWT signature invalid"
        assert error.error_code == AuthErrorCode.TOKEN_INVALID
        assert error.details == details
    
    def test_token_missing_error(self):
        """Test TokenMissingError creation."""
        error = TokenMissingError()
        
        assert error.message == "Authentication token required"
        assert error.error_code == AuthErrorCode.TOKEN_MISSING
        assert error.details == {}


class TestDatabaseError:
    """Test DatabaseError class."""
    
    def test_default_database_error(self):
        """Test default database error creation."""
        error = DatabaseError("Connection failed")
        
        assert error.message == "Connection failed"
        assert error.error_code == DatabaseErrorCode.QUERY_FAILED
        assert error.details == {}
    
    def test_database_error_with_operation(self):
        """Test database error with operation specification."""
        error = DatabaseError(
            message="Query execution failed",
            error_code=DatabaseErrorCode.QUERY_FAILED,
            operation="SELECT users WHERE id = $1"
        )
        
        assert error.message == "Query execution failed"
        assert error.error_code == DatabaseErrorCode.QUERY_FAILED
        assert error.details == {"operation": "SELECT users WHERE id = $1"}
    
    def test_database_error_with_operation_and_details(self):
        """Test database error with operation and additional details."""
        additional_details = {"table": "users", "constraint": "unique_email"}
        error = DatabaseError(
            message="Constraint violation",
            error_code=DatabaseErrorCode.CONSTRAINT_VIOLATION,
            operation="INSERT INTO users",
            details=additional_details
        )
        
        assert error.message == "Constraint violation"
        assert error.error_code == DatabaseErrorCode.CONSTRAINT_VIOLATION
        assert error.details == {
            "operation": "INSERT INTO users",
            "table": "users",
            "constraint": "unique_email"
        }


class TestExternalAPIError:
    """Test ExternalAPIError class."""
    
    def test_basic_external_api_error(self):
        """Test basic external API error creation."""
        error = ExternalAPIError(
            message="Service unavailable",
            service="payment_gateway"
        )
        
        assert error.message == "Service unavailable"
        assert error.error_code is None
        assert error.details == {
            "service": "payment_gateway",
            "status_code": None
        }
    
    def test_external_api_error_with_status_code(self):
        """Test external API error with HTTP status code."""
        error = ExternalAPIError(
            message="Bad request",
            service="booking_api",
            status_code=400,
            error_code="EXT001"
        )
        
        assert error.message == "Bad request"
        assert error.error_code == "EXT001"
        assert error.details == {
            "service": "booking_api",
            "status_code": 400
        }
    
    def test_external_api_error_with_additional_details(self):
        """Test external API error with additional details."""
        additional_details = {"endpoint": "/api/v1/bookings", "retry_count": 3}
        error = ExternalAPIError(
            message="Rate limit exceeded",
            service="hotel_api",
            status_code=429,
            error_code="EXT002",
            details=additional_details
        )
        
        assert error.message == "Rate limit exceeded"
        assert error.error_code == "EXT002"
        assert error.details == {
            "service": "hotel_api",
            "status_code": 429,
            "endpoint": "/api/v1/bookings",
            "retry_count": 3
        }


class TestErrorResponseHelpers:
    """Test error response helper functions."""
    
    def test_create_error_response_basic(self):
        """Test basic error response creation."""
        response = create_error_response("Test error")
        
        expected = {
            "error": True,
            "message": "Test error",
            "data": None,
            "status_code": 400
        }
        assert response == expected
    
    def test_create_error_response_with_code_and_details(self):
        """Test error response creation with code and details."""
        details = {"field": "email"}
        response = create_error_response(
            message="Validation failed",
            error_code="VAL001",
            details=details,
            status_code=422
        )
        
        expected = {
            "error": True,
            "message": "Validation failed",
            "data": None,
            "status_code": 422,
            "error_code": "VAL001",
            "details": details
        }
        assert response == expected
    
    def test_create_auth_error_response_default(self):
        """Test default auth error response creation."""
        response = create_auth_error_response()
        
        expected = {
            "error": True,
            "message": "Authentication failed",
            "data": None,
            "status_code": 401,
            "error_code": AuthErrorCode.INVALID_CREDENTIALS
        }
        assert response == expected
    
    def test_create_auth_error_response_custom(self):
        """Test custom auth error response creation."""
        details = {"reason": "token_expired"}
        response = create_auth_error_response(
            message="Token has expired",
            error_code=AuthErrorCode.TOKEN_EXPIRED,
            details=details
        )
        
        expected = {
            "error": True,
            "message": "Token has expired",
            "data": None,
            "status_code": 401,
            "error_code": AuthErrorCode.TOKEN_EXPIRED,
            "details": details
        }
        assert response == expected
    
    def test_create_validation_error_response_basic(self):
        """Test basic validation error response creation."""
        response = create_validation_error_response("Field is required")
        
        expected = {
            "error": True,
            "message": "Field is required",
            "data": None,
            "status_code": 422,
            "error_code": ValidationErrorCode.MISSING_REQUIRED_FIELD
        }
        assert response == expected
    
    def test_create_validation_error_response_with_field(self):
        """Test validation error response creation with field."""
        response = create_validation_error_response(
            message="Invalid email format",
            field="email",
            error_code=ValidationErrorCode.INVALID_EMAIL_FORMAT
        )
        
        expected = {
            "error": True,
            "message": "Invalid email format",
            "data": None,
            "status_code": 422,
            "error_code": ValidationErrorCode.INVALID_EMAIL_FORMAT,
            "details": {"field": "email"}
        }
        assert response == expected
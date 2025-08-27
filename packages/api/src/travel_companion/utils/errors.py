"""Custom exception classes for the Travel Companion API."""


class TravelCompanionError(Exception):
    """Base exception for Travel Companion application."""

    pass


class ValidationError(TravelCompanionError):
    """Raised when input validation fails."""

    pass


class AuthenticationError(TravelCompanionError):
    """Raised when authentication fails."""

    pass


class AuthorizationError(TravelCompanionError):
    """Raised when authorization fails."""

    pass


class UserNotFoundError(TravelCompanionError):
    """Raised when a user is not found."""

    pass


class UserAlreadyExistsError(TravelCompanionError):
    """Raised when trying to create a user that already exists."""

    pass


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT token has expired."""

    pass


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT token is invalid."""

    pass


class ExternalAPIError(TravelCompanionError):
    """Raised when external API calls fail."""

    def __init__(self, message: str, service: str, status_code: int = None):
        super().__init__(message)
        self.service = service
        self.status_code = status_code


class DatabaseError(TravelCompanionError):
    """Raised when database operations fail."""

    pass

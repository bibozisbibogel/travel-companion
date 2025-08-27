"""FastAPI dependencies."""

from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from travel_companion.core.config import get_settings
from travel_companion.core.database import get_database_manager
from travel_companion.core.security import get_user_id_from_token
from travel_companion.models.user import User
from travel_companion.services.user_service import UserService

# OAuth2 scheme for token extraction
security = HTTPBearer()


def get_current_settings() -> Generator:
    """Get current application settings."""
    settings = get_settings()
    try:
        yield settings
    finally:
        pass


def get_user_service() -> UserService:
    """Get user service instance."""
    db_manager = get_database_manager()
    return UserService(db_manager.client)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials or not credentials.credentials:
        raise credentials_exception

    # Extract user ID from token
    user_id_str = get_user_id_from_token(credentials.credentials)
    if not user_id_str:
        raise credentials_exception

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise credentials_exception from None

    # Retrieve user from database
    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise credentials_exception
        return user
    except Exception:
        # Any database or service error should result in authentication failure
        raise credentials_exception from None

"""FastAPI dependencies."""

from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from travel_companion.core.config import get_settings
from travel_companion.core.database import get_database_manager
from travel_companion.core.security import get_user_id_from_token
from travel_companion.models.user import User
from travel_companion.services.user_service import UserService
from travel_companion.utils.logging import auth_logger, get_client_ip, get_user_agent

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
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Get current authenticated user from JWT token."""
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)
    endpoint = str(request.url.path)
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials or not credentials.credentials:
        # Log missing token
        auth_logger.log_token_missing(
            ip_address=client_ip,
            endpoint=endpoint,
            user_agent=user_agent
        )
        raise credentials_exception

    # Extract user ID from token
    user_id_str = get_user_id_from_token(credentials.credentials)
    if not user_id_str:
        # Log invalid token
        auth_logger.log_token_invalid(
            ip_address=client_ip,
            endpoint=endpoint,
            reason="Failed to extract user ID from token",
            user_agent=user_agent
        )
        raise credentials_exception

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        # Log invalid token format
        auth_logger.log_token_invalid(
            ip_address=client_ip,
            endpoint=endpoint,
            reason="Invalid user ID format in token",
            user_agent=user_agent
        )
        raise credentials_exception from None

    # Retrieve user from database
    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            # Log user not found (could be token with non-existent user)
            auth_logger.log_token_invalid(
                ip_address=client_ip,
                endpoint=endpoint,
                reason="User not found for token",
                user_agent=user_agent
            )
            raise credentials_exception
        
        # Log successful token validation
        auth_logger.log_token_validated(
            user_id=user.user_id,
            ip_address=client_ip,
            endpoint=endpoint
        )
        
        return user
        
    except HTTPException:
        # Re-raise HTTP exceptions (already logged above)
        raise
    except Exception:
        # Log database/service errors
        auth_logger.log_token_invalid(
            ip_address=client_ip,
            endpoint=endpoint,
            reason="Database error during user lookup",
            user_agent=user_agent
        )
        # Any database or service error should result in authentication failure
        raise credentials_exception from None
"""User management API endpoints."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from travel_companion.api.deps import get_current_user
from travel_companion.core.config import get_settings
from travel_companion.core.database import DatabaseManager, get_database
from travel_companion.core.security import create_access_token
from travel_companion.models.user import AuthToken, User, UserCreate, UserLogin, UserResponse, UserUpdate
from travel_companion.services.user_service import UserService
from travel_companion.utils.errors import UserAlreadyExistsError, ValidationError

router = APIRouter()
settings = get_settings()


def get_user_service(db: DatabaseManager = Depends(get_database)) -> UserService:
    """Dependency to get user service."""
    return UserService(db.client)


@router.post(
    "/register",
    response_model=AuthToken,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password validation",
)
async def register_user(
    user_data: UserCreate, user_service: UserService = Depends(get_user_service)
) -> AuthToken:
    """
    Register a new user with the following features:

    - Email validation and uniqueness check
    - Password strength validation
    - Secure password hashing
    - Default travel preferences initialization
    - JWT token generation for immediate authentication
    """
    try:
        # Create the user
        user = await user_service.create_user(user_data)

        # Create access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": str(user.user_id), "email": user.email}, expires_delta=access_token_expires
        )

        # Return user data without password hash
        user_response = UserResponse(
            user_id=user.user_id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            travel_preferences=user.travel_preferences,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

        return AuthToken(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=user_response,
        )

    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(e), "error_code": "USER_ALREADY_EXISTS"},
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(e), "error_code": "VALIDATION_ERROR"},
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Internal server error", "error_code": "INTERNAL_ERROR"},
        ) from e


@router.post(
    "/login",
    response_model=AuthToken,
    summary="Authenticate user",
    description="Login with email and password to receive authentication token",
)
async def login_user(
    login_data: UserLogin, user_service: UserService = Depends(get_user_service)
) -> AuthToken:
    """
    Authenticate user and return access token:

    - Validate email and password
    - Generate JWT token with user information
    - Return user profile data
    """
    try:
        # Authenticate user
        user = await user_service.authenticate_user(login_data.email, login_data.password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Invalid email or password",
                    "error_code": "INVALID_CREDENTIALS",
                },
            )

        # Create access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": str(user.user_id), "email": user.email}, expires_delta=access_token_expires
        )

        # Return user data without password hash
        user_response = UserResponse(
            user_id=user.user_id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            travel_preferences=user.travel_preferences,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

        return AuthToken(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=user_response,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Internal server error", "error_code": "INTERNAL_ERROR"},
        ) from e


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Retrieve authenticated user's profile information",
)
async def get_current_user_profile(current_user: User = Depends(get_current_user)) -> UserResponse:
    """
    Get the current authenticated user's profile.

    This is a protected endpoint that requires valid JWT token.
    Returns user profile information without sensitive data.
    """
    return UserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        travel_preferences=current_user.travel_preferences,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    description="Update authenticated user's profile information and travel preferences",
)
async def update_current_user_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
) -> UserResponse:
    """
    Update the current authenticated user's profile.
    
    Allows updating:
    - first_name: User's first name
    - last_name: User's last name  
    - travel_preferences: Complete travel preferences object
    
    This is a protected endpoint that requires valid JWT token.
    """
    try:
        # Update user profile
        updated_user = await user_service.update_user(current_user.user_id, update_data)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User not found",
                    "error_code": "USER_NOT_FOUND",
                },
            )

        # Return updated user profile
        return UserResponse(
            user_id=updated_user.user_id,
            email=updated_user.email,
            first_name=updated_user.first_name,
            last_name=updated_user.last_name,
            travel_preferences=updated_user.travel_preferences,
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at,
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(e), "error_code": "VALIDATION_ERROR"},
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Internal server error", "error_code": "INTERNAL_ERROR"},
        ) from e

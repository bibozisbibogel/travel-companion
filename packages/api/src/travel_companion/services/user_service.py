"""User service for handling user operations."""

from datetime import UTC, datetime
from uuid import UUID

from supabase import Client

from travel_companion.core.security import hash_password, verify_password
from travel_companion.models.user import User, UserCreate, UserUpdate, TravelPreferences
from travel_companion.utils.errors import DatabaseError, UserAlreadyExistsError


class UserService:
    """Service for user operations."""

    def __init__(self, client: Client):
        self.client = client

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user with hashed password and default preferences."""
        # Check if user already exists
        existing_user = (
            self.client.table("users").select("email").eq("email", user_data.email).execute()
        )

        if existing_user.data:
            raise UserAlreadyExistsError(f"User with email {user_data.email} already exists")

        # Create user with hashed password
        hashed_password = hash_password(user_data.password)
        now = datetime.now(UTC)

        # Default travel preferences
        default_preferences = TravelPreferences(
            budget_min=0,
            budget_max=5000,
            preferred_currency="USD",
            accommodation_types=["hotel", "apartment"],
            activity_interests=[],
            dietary_restrictions=[],
            accessibility_needs=[],
            travel_style="moderate"
        )

        user_dict = {
            "email": user_data.email,
            "password_hash": hashed_password,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "travel_preferences": default_preferences.model_dump(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        try:
            result = self.client.table("users").insert(user_dict).execute()

            if not result.data:
                raise DatabaseError("Failed to create user - no data returned from database")

            return User(**result.data[0])
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                raise UserAlreadyExistsError(
                    f"User with email {user_data.email} already exists"
                ) from e
            raise DatabaseError(f"Database error during user creation: {str(e)}") from e

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        try:
            result = self.client.table("users").select("*").eq("email", email).execute()

            if not result.data:
                return None

            return User(**result.data[0])
        except Exception as e:
            raise DatabaseError(f"Database error retrieving user by email: {str(e)}") from e

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        try:
            result = self.client.table("users").select("*").eq("user_id", str(user_id)).execute()

            if not result.data:
                return None

            return User(**result.data[0])
        except Exception as e:
            raise DatabaseError(f"Database error retrieving user by ID: {str(e)}") from e

    async def authenticate_user(self, email: str, password: str) -> User | None:
        """Authenticate user with email and password."""
        user = await self.get_user_by_email(email)

        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user

    async def update_user(self, user_id: UUID, update_data: UserUpdate) -> User | None:
        """Update user profile information."""
        try:
            # Build update dictionary with only provided fields
            update_dict = {"updated_at": datetime.now(UTC).isoformat()}
            
            if update_data.first_name is not None:
                update_dict["first_name"] = update_data.first_name
                
            if update_data.last_name is not None:
                update_dict["last_name"] = update_data.last_name
                
            if update_data.travel_preferences is not None:
                update_dict["travel_preferences"] = update_data.travel_preferences.model_dump()

            # Update user in database
            result = self.client.table("users").update(update_dict).eq("user_id", str(user_id)).execute()

            if not result.data:
                return None

            return User(**result.data[0])
        except Exception as e:
            raise DatabaseError(f"Database error updating user profile: {str(e)}") from e

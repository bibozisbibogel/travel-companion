"""User data models and validation schemas."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class TravelPreferences(BaseModel):
    """Travel preferences schema with validation."""
    
    budget_min: int | None = Field(None, ge=0, description="Minimum budget per trip")
    budget_max: int | None = Field(None, ge=0, description="Maximum budget per trip")
    preferred_currency: str = Field(default="USD", min_length=3, max_length=3, description="Currency code")
    accommodation_types: list[str] = Field(default_factory=list, description="Preferred accommodation types")
    activity_interests: list[str] = Field(default_factory=list, description="Activity interests")
    dietary_restrictions: list[str] = Field(default_factory=list, description="Dietary restrictions")
    accessibility_needs: list[str] = Field(default_factory=list, description="Accessibility requirements")
    travel_style: str | None = Field(None, description="Travel style preference")
    
    @field_validator("budget_max")
    @classmethod
    def validate_budget_range(cls, v: int | None, info) -> int | None:
        """Ensure budget_max is greater than budget_min if both are set."""
        if v is not None and "budget_min" in info.data:
            budget_min = info.data["budget_min"]
            if budget_min is not None and v <= budget_min:
                raise ValueError("Maximum budget must be greater than minimum budget")
        return v
    
    @field_validator("preferred_currency")
    @classmethod
    def validate_currency_code(cls, v: str) -> str:
        """Validate currency code format."""
        if not v.isupper():
            raise ValueError("Currency code must be uppercase")
        return v


class UserBase(BaseModel):
    """Base user model with common fields."""

    email: EmailStr = Field(..., description="User email address")
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    travel_preferences: TravelPreferences = Field(default_factory=TravelPreferences)


class UserCreate(BaseModel):
    """Model for user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """Model for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserUpdate(BaseModel):
    """Model for user profile updates."""
    
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    travel_preferences: TravelPreferences | None = None


class UserResponse(UserBase):
    """User model for API responses (without password)."""

    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class User(UserBase):
    """Complete user model with database fields."""

    user_id: UUID = Field(default_factory=uuid4)
    password_hash: str = Field(..., description="Hashed password")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(from_attributes=True)


class AuthToken(BaseModel):
    """Authentication token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: UserResponse = Field(..., description="Authenticated user data")

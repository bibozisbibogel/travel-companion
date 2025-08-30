"""Trip data models and validation schemas."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TripStatus(str, Enum):
    """Trip status enumeration."""

    DRAFT = "draft"
    PLANNING = "planning"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TravelClass(str, Enum):
    """Travel class enumeration."""

    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class AccommodationType(str, Enum):
    """Accommodation type enumeration."""

    HOTEL = "hotel"
    APARTMENT = "apartment"
    HOSTEL = "hostel"
    RESORT = "resort"
    BED_AND_BREAKFAST = "bed_and_breakfast"
    VACATION_RENTAL = "vacation_rental"


class TripDestination(BaseModel):
    """Trip destination model."""

    city: str = Field(..., min_length=1, max_length=100, description="Destination city")
    country: str = Field(..., min_length=1, max_length=100, description="Destination country")
    country_code: str = Field(..., min_length=2, max_length=3, description="ISO country code")
    airport_code: str | None = Field(None, min_length=3, max_length=4, description="Airport code")
    latitude: float | None = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: float | None = Field(None, ge=-180, le=180, description="Longitude coordinate")


class TripRequirements(BaseModel):
    """Trip planning requirements."""

    budget: Decimal = Field(..., gt=0, description="Total trip budget")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Budget currency")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    travelers: int = Field(..., ge=1, le=10, description="Number of travelers")
    travel_class: TravelClass = Field(
        default=TravelClass.ECONOMY, description="Preferred travel class"
    )
    accommodation_type: AccommodationType | None = Field(
        None, description="Preferred accommodation"
    )

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: date, info: Any) -> date:
        """Ensure end date is after start date."""
        if "start_date" in info.data:
            start_date = info.data["start_date"]
            if v <= start_date:
                raise ValueError("End date must be after start date")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency_code(cls, v: str) -> str:
        """Validate currency code format."""
        if not v.isupper():
            raise ValueError("Currency code must be uppercase")
        return v


class TripPlanRequest(BaseModel):
    """Request model for trip planning."""

    destination: TripDestination = Field(..., description="Trip destination")
    requirements: TripRequirements = Field(..., description="Trip requirements")
    preferences: dict[str, str | int | bool | list[str]] | None = Field(
        None, description="Additional preferences from user profile"
    )


class FlightOption(BaseModel):
    """Flight option model."""

    airline: str = Field(..., description="Airline name")
    flight_number: str = Field(..., description="Flight number")
    departure_airport: str = Field(..., description="Departure airport code")
    arrival_airport: str = Field(..., description="Arrival airport code")
    departure_time: datetime = Field(..., description="Departure datetime")
    arrival_time: datetime = Field(..., description="Arrival datetime")
    duration_minutes: int = Field(..., gt=0, description="Flight duration in minutes")
    price: Decimal = Field(..., gt=0, description="Flight price")
    currency: str = Field(..., description="Price currency")
    travel_class: TravelClass = Field(..., description="Travel class")
    stops: int = Field(..., ge=0, description="Number of stops")


class HotelOption(BaseModel):
    """Hotel option model."""

    name: str = Field(..., description="Hotel name")
    address: str = Field(..., description="Hotel address")
    star_rating: int | None = Field(None, ge=1, le=5, description="Star rating")
    guest_rating: float | None = Field(None, ge=0, le=10, description="Guest rating")
    price_per_night: Decimal = Field(..., gt=0, description="Price per night")
    currency: str = Field(..., description="Price currency")
    accommodation_type: AccommodationType = Field(..., description="Accommodation type")
    amenities: list[str] = Field(default_factory=list, description="Hotel amenities")
    distance_to_center: float | None = Field(
        None, ge=0, description="Distance to city center in km"
    )


class ActivityOption(BaseModel):
    """Activity option model."""

    name: str = Field(..., description="Activity name")
    description: str = Field(..., description="Activity description")
    category: str = Field(..., description="Activity category")
    duration_hours: float | None = Field(None, gt=0, description="Activity duration in hours")
    price: Decimal | None = Field(None, gt=0, description="Activity price")
    currency: str | None = Field(None, description="Price currency")
    location: str = Field(..., description="Activity location")
    rating: float | None = Field(None, ge=0, le=10, description="Activity rating")
    min_age: int | None = Field(None, ge=0, description="Minimum age requirement")


class TripPlan(BaseModel):
    """Complete trip plan model."""

    flights: list[FlightOption] = Field(default_factory=list, description="Flight options")
    hotels: list[HotelOption] = Field(default_factory=list, description="Hotel options")
    activities: list[ActivityOption] = Field(default_factory=list, description="Activity options")
    total_estimated_cost: Decimal = Field(..., gt=0, description="Total estimated cost")
    currency: str = Field(..., description="Cost currency")
    generated_at: datetime = Field(default_factory=datetime.now, description="Plan generation time")


class TripBase(BaseModel):
    """Base trip model with common fields."""

    name: str = Field(..., min_length=1, max_length=200, description="Trip name")
    description: str | None = Field(None, max_length=1000, description="Trip description")
    destination: TripDestination = Field(..., description="Trip destination")
    requirements: TripRequirements = Field(..., description="Trip requirements")
    status: TripStatus = Field(default=TripStatus.DRAFT, description="Trip status")


class TripCreate(TripPlanRequest):
    """Model for creating a new trip."""

    name: str = Field(..., min_length=1, max_length=200, description="Trip name")
    description: str | None = Field(None, max_length=1000, description="Trip description")


class TripUpdate(BaseModel):
    """Model for updating a trip."""

    name: str | None = Field(None, min_length=1, max_length=200, description="Trip name")
    description: str | None = Field(None, max_length=1000, description="Trip description")
    status: TripStatus | None = Field(None, description="Trip status")
    requirements: TripRequirements | None = Field(None, description="Updated requirements")


class TripResponse(TripBase):
    """Trip model for API responses."""

    trip_id: UUID = Field(..., description="Trip ID")
    user_id: UUID = Field(..., description="Owner user ID")
    plan: TripPlan | None = Field(None, description="Generated trip plan")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class Trip(TripBase):
    """Complete trip model with database fields."""

    trip_id: UUID = Field(default_factory=uuid4, description="Trip ID")
    user_id: UUID = Field(..., description="Owner user ID")
    plan: TripPlan | None = Field(None, description="Generated trip plan")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)

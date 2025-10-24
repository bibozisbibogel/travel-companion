"""Trip data models and validation schemas."""

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from travel_companion.models.itinerary_output import ItineraryOutput


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
    start_date: date_type = Field(..., description="Trip start date")
    end_date: date_type = Field(..., description="Trip end date")
    travelers: int = Field(..., ge=1, le=10, description="Number of travelers")
    travel_class: TravelClass = Field(
        default=TravelClass.ECONOMY, description="Preferred travel class"
    )
    accommodation_type: AccommodationType | None = Field(
        None, description="Preferred accommodation"
    )

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: date_type, info: Any) -> date_type:
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
    """Request model for trip planning.

    Supports two execution modes:
    1. Standalone mode: Only destination, requirements, and preferences are provided.
       The itinerary agent will call all other agents (flight, hotel, activity, etc.)
    2. Workflow mode: Pre-fetched agent results are provided in optional fields.
       The itinerary agent uses these results directly without calling other agents.
    """

    destination: TripDestination = Field(..., description="Trip destination")
    requirements: TripRequirements = Field(..., description="Trip requirements")
    preferences: dict[str, str | int | bool | list[str]] | None = Field(
        None, description="Additional preferences from user profile"
    )

    # Workflow mode: optional pre-fetched agent results
    flight_options: list[Any] | None = Field(
        None,
        description="Pre-fetched flight options (workflow mode). If None, flight agent will be called.",
    )
    weather_forecast: dict[str, Any] | None = Field(
        None,
        description="Pre-fetched weather data (workflow mode). If None, weather agent will be called.",
    )
    hotel_options: list[Any] | None = Field(
        None,
        description="Pre-fetched hotel options (workflow mode). If None, hotel agent will be called.",
    )
    activity_options: list[Any] | None = Field(
        None,
        description="Pre-fetched activity options (workflow mode). If None, activity agent will be called.",
    )
    restaurant_options: list[Any] | None = Field(
        None,
        description="Pre-fetched restaurant options (workflow mode). If None, food agent will be called.",
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
    plan: ItineraryOutput | None = Field(None, description="Generated trip plan")
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


class ItineraryItem(BaseModel):
    """Individual itinerary item with activity, time slot, location, and booking details."""

    item_id: str = Field(..., description="Unique identifier for the itinerary item")
    item_type: str = Field(..., description="Type of item (flight, hotel, activity, restaurant)")
    name: str = Field(..., description="Name/title of the item")
    description: str | None = Field(None, description="Description of the item")

    # Time and duration
    start_time: datetime = Field(..., description="Start time of the item")
    end_time: datetime = Field(..., description="End time of the item")
    duration_minutes: int = Field(..., gt=0, description="Duration in minutes")

    # Location information
    location: dict[str, Any] = Field(default_factory=dict, description="Location details")
    latitude: float | None = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: float | None = Field(None, ge=-180, le=180, description="Longitude coordinate")
    address: str | None = Field(None, description="Physical address")

    # Booking and cost information
    booking_reference: str | None = Field(None, description="Booking confirmation number")
    booking_url: str | None = Field(None, description="Direct booking URL")
    contact_info: dict[str, str] = Field(default_factory=dict, description="Contact information")

    # Cost details
    cost: Decimal = Field(..., ge=0, description="Cost of the item")
    currency: str = Field(default="USD", description="Currency code")

    # Additional metadata
    priority: int = Field(default=1, ge=1, le=5, description="Priority level (1=low, 5=high)")
    is_confirmed: bool = Field(default=False, description="Whether booking is confirmed")
    cancellation_policy: str | None = Field(None, description="Cancellation policy details")
    special_instructions: str | None = Field(None, description="Special instructions or notes")


class DailyItinerary(BaseModel):
    """Daily itinerary structure with date, activities, and schedule."""

    date: date_type = Field(..., description="Date for this daily itinerary")
    day_number: int = Field(..., ge=1, description="Day number in the trip")

    # Daily items organized by type
    items: list["ItineraryItem"] = Field(default_factory=list, description="All items for this day")

    # Daily summary information
    daily_cost: Decimal = Field(default=Decimal("0.00"), ge=0, description="Total cost for the day")
    currency: str = Field(default="USD", description="Currency code")
    weather_summary: str | None = Field(None, description="Weather forecast summary")

    # Geographic optimization data
    total_travel_distance_km: float = Field(default=0.0, ge=0, description="Total travel distance")
    estimated_travel_time_minutes: int = Field(default=0, ge=0, description="Estimated travel time")

    # Daily notes and recommendations
    notes: str | None = Field(None, description="Daily notes or recommendations")
    meal_plan: dict[str, str] = Field(default_factory=dict, description="Meal planning")

    def get_items_by_type(self, item_type: str) -> list["ItineraryItem"]:
        """Get all items of a specific type for this day."""
        return [item for item in self.items if item.item_type == item_type]

    def get_total_duration_minutes(self) -> int:
        """Calculate total duration of all activities for the day."""
        return sum(item.duration_minutes for item in self.items)

    def get_free_time_minutes(self) -> int:
        """Calculate free time available in the day (assuming 16 active hours)."""
        active_minutes = 16 * 60  # 16 hours * 60 minutes
        return max(0, active_minutes - self.get_total_duration_minutes())


class TripItinerary(BaseModel):
    """Complete trip itinerary containing all daily schedules."""

    trip_id: str = Field(..., description="Associated trip ID")
    days: list["DailyItinerary"] = Field(default_factory=list, description="Daily itineraries")

    # Trip-level summary
    total_days: int = Field(..., ge=1, description="Total number of days")
    total_cost: Decimal = Field(..., ge=0, description="Total trip cost")
    currency: str = Field(default="USD", description="Currency code")

    # Optimization metrics
    optimization_score: float = Field(..., ge=0, le=1, description="Overall optimization score")
    total_travel_distance_km: float = Field(default=0.0, ge=0, description="Total travel distance")
    average_daily_cost: Decimal = Field(
        default=Decimal("0.00"), ge=0, description="Average daily cost"
    )

    # Budget and conflict tracking
    budget_status: str = Field(..., description="Budget status (within_budget, over_budget, etc.)")
    conflicts: list[dict[str, Any]] = Field(default_factory=list, description="Detected conflicts")

    # Export and sharing
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Last update timestamp"
    )
    export_formats: list[str] = Field(default_factory=list, description="Available export formats")

    def get_day_by_date(self, target_date: date_type) -> Union["DailyItinerary", None]:
        """Get daily itinerary for a specific date."""
        for day in self.days:
            if day.date == target_date:
                return day
        return None

    def get_total_duration_hours(self) -> float:
        """Calculate total activity duration for the entire trip."""
        total_minutes = sum(day.get_total_duration_minutes() for day in self.days)
        return total_minutes / 60.0

    def calculate_budget_utilization(self, original_budget: Decimal) -> float:
        """Calculate percentage of budget utilized."""
        if original_budget <= 0:
            return 0.0
        return float(self.total_cost / original_budget * 100)


class TripSummary(BaseModel):
    """Trip summary model for export functionality with complete trip breakdown."""

    # Trip identification
    trip_id: str = Field(..., description="Trip ID")
    trip_name: str = Field(..., description="Trip name")
    destination: str = Field(..., description="Primary destination")

    # Trip dates and duration
    start_date: date_type = Field(..., description="Trip start date")
    end_date: date_type = Field(..., description="Trip end date")
    total_days: int = Field(..., ge=1, description="Total trip duration in days")

    # Travelers information
    travelers: int = Field(..., ge=1, description="Number of travelers")
    traveler_names: list[str] = Field(default_factory=list, description="Names of travelers")

    # Complete itinerary
    itinerary: "TripItinerary" = Field(..., description="Complete trip itinerary")

    # Financial summary
    cost_breakdown: dict[str, Decimal] = Field(default_factory=dict, description="Cost by category")
    total_cost: Decimal = Field(..., ge=0, description="Total trip cost")
    currency: str = Field(default="USD", description="Currency code")
    budget_original: Decimal | None = Field(None, description="Original budget")
    budget_remaining: Decimal | None = Field(None, description="Remaining budget")

    # Bookings and confirmations
    flight_confirmations: list[str] = Field(
        default_factory=list, description="Flight confirmation numbers"
    )
    hotel_confirmations: list[str] = Field(
        default_factory=list, description="Hotel confirmation numbers"
    )
    activity_bookings: list[str] = Field(
        default_factory=list, description="Activity booking references"
    )

    # Emergency and contact information
    emergency_contacts: list[dict[str, str]] = Field(
        default_factory=list, description="Emergency contacts"
    )
    important_phone_numbers: dict[str, str] = Field(
        default_factory=dict, description="Important numbers"
    )

    # Export metadata
    generated_at: datetime = Field(
        default_factory=datetime.now, description="Export generation time"
    )
    export_format: str = Field(default="json", description="Current export format")
    qr_code_data: str | None = Field(None, description="QR code for quick access")

    def get_cost_by_category(self) -> dict[str, Decimal]:
        """Get cost breakdown by category (flights, hotels, activities, restaurants)."""
        breakdown = {
            "flights": Decimal("0.00"),
            "hotels": Decimal("0.00"),
            "activities": Decimal("0.00"),
            "restaurants": Decimal("0.00"),
            "other": Decimal("0.00"),
        }

        for day in self.itinerary.days:
            for item in day.items:
                category = item.item_type.lower()
                if category in breakdown:
                    breakdown[category] += item.cost
                else:
                    breakdown["other"] += item.cost

        return breakdown

    def get_daily_costs(self) -> list[tuple[date_type, Decimal]]:
        """Get list of daily costs for the trip."""
        return [(day.date, day.daily_cost) for day in self.itinerary.days]

"""Itinerary output models for structured JSON generation.

This module provides Pydantic models to convert text-based travel itineraries
into structured JSON format suitable for export, display, and programmatic processing.
"""

from datetime import date as date_type
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ActivityCategory(str, Enum):
    """Activity category enumeration."""

    TRANSPORTATION = "transportation"
    ACCOMMODATION = "accommodation"
    ATTRACTION = "attraction"
    DINING = "dining"
    EXPLORATION = "exploration"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    OTHER = "other"


class MealType(str, Enum):
    """Meal type enumeration."""

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    APERITIVO = "aperitivo"


class Destination(BaseModel):
    """Destination information."""

    city: str = Field(..., min_length=1, max_length=100, description="Destination city")
    country: str = Field(..., min_length=1, max_length=100, description="Country name")


class DateRange(BaseModel):
    """Date range for trip."""

    start: date_type = Field(..., description="Trip start date (ISO 8601)")
    end: date_type = Field(..., description="Trip end date (ISO 8601)")
    duration_days: int = Field(..., ge=1, description="Total trip duration in days")

    @field_validator("duration_days")
    @classmethod
    def validate_duration(cls, v: int, info: Any) -> int:
        """Validate duration matches date range (inclusive of both start and end dates)."""
        if "start" in info.data and "end" in info.data:
            start = info.data["start"]
            end = info.data["end"]
            calculated_days = (end - start).days + 1
            if v != calculated_days:
                raise ValueError(f"Duration {v} doesn't match date range ({calculated_days} days)")
        return v


class TravelerInfo(BaseModel):
    """Traveler information."""

    count: int = Field(..., ge=1, le=20, description="Number of travelers")
    type: str = Field(default="adults", description="Type of travelers (adults, family, etc.)")


class BudgetInfo(BaseModel):
    """Budget information and tracking."""

    total: Decimal = Field(..., gt=0, description="Total budget amount")
    currency: str = Field(..., min_length=3, max_length=3, description="Currency code (ISO 4217)")
    spent: Decimal = Field(default=Decimal("0"), ge=0, description="Amount spent")
    remaining: Decimal = Field(default=Decimal("0"), ge=0, description="Remaining budget")

    @field_validator("currency")
    @classmethod
    def validate_currency_uppercase(cls, v: str) -> str:
        """Ensure currency code is uppercase."""
        return v.upper()


class TripInfo(BaseModel):
    """Trip overview information."""

    destination: Destination = Field(..., description="Trip destination")
    dates: DateRange = Field(..., description="Trip date range")
    travelers: TravelerInfo = Field(..., description="Traveler information")
    budget: BudgetInfo = Field(..., description="Budget details")


class RouteInfo(BaseModel):
    """Flight route information."""

    from_airport: str = Field(
        ..., alias="from", min_length=3, max_length=4, description="Origin airport code"
    )
    to_airport: str = Field(
        ..., alias="to", min_length=3, max_length=4, description="Destination airport code"
    )

    model_config = ConfigDict(populate_by_name=True)


class TimeInfo(BaseModel):
    """Time and timezone information."""

    time: str = Field(..., description="Time in HH:MM format")
    timezone: str = Field(..., description="IANA timezone (e.g., America/New_York)")


class FlightDetails(BaseModel):
    """Individual flight details."""

    airline: str = Field(..., min_length=1, description="Airline name")
    flight_number: str = Field(..., description="Flight number")
    route: RouteInfo = Field(..., description="Flight route")
    departure: TimeInfo = Field(..., description="Departure time and timezone")
    arrival: TimeInfo | None = Field(None, description="Arrival time and timezone")
    duration_minutes: int | None = Field(None, gt=0, description="Flight duration in minutes")
    stops: int = Field(default=0, ge=0, description="Number of stops")
    price_per_person: Decimal = Field(..., gt=0, description="Price per person")
    total_price: Decimal = Field(..., gt=0, description="Total price for all travelers")


class FlightInfo(BaseModel):
    """Flight information for outbound and return."""

    outbound: FlightDetails = Field(..., description="Outbound flight details")
    return_flight: FlightDetails | None = Field(
        None, alias="return", description="Return flight details"
    )
    total_cost: Decimal = Field(..., gt=0, description="Total cost for all flights")

    model_config = ConfigDict(populate_by_name=True)


class Address(BaseModel):
    """Physical address information."""

    street: str | None = Field(None, description="Street address")
    postal_code: str | None = Field(None, description="Postal/ZIP code")
    city: str = Field(..., description="City name")
    region: str | None = Field(None, description="State/region/province")
    country: str = Field(..., description="Country name")


class AccommodationInfo(BaseModel):
    """Accommodation details."""

    name: str = Field(..., min_length=1, description="Hotel/accommodation name")
    rating: float | None = Field(None, ge=0, le=5, description="Rating (0-5)")
    stars: int | None = Field(None, ge=1, le=5, description="Star rating")
    address: Address = Field(..., description="Physical address")
    amenities: list[str] = Field(default_factory=list, description="Available amenities")
    price_per_night: Decimal = Field(..., gt=0, description="Price per night")
    nights: int = Field(..., ge=1, description="Number of nights")
    total_cost: Decimal = Field(..., gt=0, description="Total accommodation cost")
    location_notes: str | None = Field(None, description="Location description/notes")


class VenueInfo(BaseModel):
    """Restaurant or dining venue information."""

    name: str = Field(..., min_length=1, description="Venue name")
    cuisine: str | None = Field(None, description="Cuisine type")
    location: str | None = Field(None, description="Location description")
    style: str | None = Field(None, description="Dining style (e.g., fine dining, casual)")


class OptionalActivity(BaseModel):
    """Optional activity or upgrade."""

    title: str = Field(..., description="Activity title")
    cost_per_person: Decimal | None = Field(None, ge=0, description="Cost per person")
    total_cost: Decimal | None = Field(None, ge=0, description="Total cost")


class ItineraryActivity(BaseModel):
    """Individual activity in the itinerary."""

    time_start: str | None = Field(None, description="Start time (HH:MM)")
    time_end: str | None = Field(None, description="End time (HH:MM)")
    category: ActivityCategory = Field(..., description="Activity category")
    title: str = Field(..., min_length=1, description="Activity title")
    description: str | None = Field(None, description="Activity description")
    location: str | None = Field(None, description="Activity location")
    visit_type: str | None = Field(None, description="Visit type (self-guided, guided, etc.)")
    duration_minutes: int | None = Field(None, gt=0, description="Duration in minutes")
    cost_per_person: Decimal | None = Field(None, ge=0, description="Cost per person")
    total_cost: Decimal | None = Field(None, ge=0, description="Total cost")
    booking_required: bool = Field(default=False, description="Booking required flag")
    booking_notes: str | None = Field(None, description="Booking instructions")
    highlights: list[str] = Field(default_factory=list, description="Activity highlights")
    optional_activities: list[OptionalActivity] = Field(
        default_factory=list, description="Optional add-ons"
    )

    # Dining-specific fields
    meal_type: MealType | None = Field(None, description="Type of meal")
    venue: VenueInfo | None = Field(None, description="Dining venue information")
    recommended_dishes: list[str] = Field(default_factory=list, description="Recommended dishes")

    # Cost estimates (for activities with flexible pricing)
    cost_estimate_min: Decimal | None = Field(None, ge=0, description="Minimum cost estimate")
    cost_estimate_max: Decimal | None = Field(None, ge=0, description="Maximum cost estimate")
    cost: Decimal | None = Field(None, ge=0, description="Fixed cost")


class DailyCost(BaseModel):
    """Daily cost summary."""

    min: Decimal = Field(..., ge=0, description="Minimum estimated cost")
    max: Decimal = Field(..., ge=0, description="Maximum estimated cost")
    currency: str = Field(default="USD", description="Currency code")
    breakdown: str | None = Field(None, description="Cost breakdown description")


class DayItinerary(BaseModel):
    """Single day itinerary."""

    day: int = Field(..., ge=1, description="Day number")
    date: date_type = Field(..., description="Date (ISO 8601)")
    day_of_week: str = Field(..., description="Day of week (e.g., Monday)")
    title: str = Field(..., min_length=1, description="Day title/theme")
    activities: list[ItineraryActivity] = Field(
        default_factory=list, description="Daily activities"
    )
    daily_cost: DailyCost = Field(..., description="Daily cost summary")


class BudgetCategoryRange(BaseModel):
    """Budget range for a category."""

    min: Decimal = Field(..., ge=0, description="Minimum amount")
    max: Decimal = Field(..., ge=0, description="Maximum amount")


class BudgetBreakdown(BaseModel):
    """Complete budget breakdown."""

    flights: Decimal = Field(..., ge=0, description="Total flight costs")
    accommodation: Decimal = Field(..., ge=0, description="Total accommodation costs")
    activities: BudgetCategoryRange | None = Field(None, description="Activities cost range")
    meals: BudgetCategoryRange | None = Field(None, description="Meals cost range")
    transportation: BudgetCategoryRange | None = Field(
        None, description="Local transportation cost range"
    )
    extras: dict[str, Any] | None = Field(None, description="Extra costs (description, min, max)")
    total: BudgetCategoryRange = Field(..., description="Total cost range")
    buffer: dict[str, Any] | None = Field(None, description="Remaining buffer")


class TransportationTips(BaseModel):
    """Transportation tips and information."""

    from_airport: dict[str, Any] | None = Field(None, description="Airport transfer information")
    metro_pass: dict[str, Any] | None = Field(None, description="Metro/transit pass info")
    notes: list[str] = Field(default_factory=list, description="General transportation notes")


class BookingEssentials(BaseModel):
    """Booking requirements and tips."""

    advance_booking_required: list[str] = Field(
        default_factory=list, description="Items requiring advance booking"
    )
    booking_window: str | None = Field(None, description="Recommended booking timeframe")


class MoneyTips(BaseModel):
    """Money and payment information."""

    payment: str | None = Field(None, description="Payment acceptance info")
    cash_recommended: dict[str, Any] | None = Field(None, description="Cash recommendations")
    tipping: str | None = Field(None, description="Tipping guidelines")


class BestPractice(BaseModel):
    """Best practice or tip."""

    category: str = Field(..., description="Practice category")
    rule: str | None = Field(None, description="Rule or guideline")
    note: str | None = Field(None, description="Additional notes")
    tip: str | None = Field(None, description="Helpful tip")


class FoodTips(BaseModel):
    """Food and dining tips."""

    breakfast: str | None = Field(None, description="Breakfast information")
    aperitivo: str | None = Field(None, description="Aperitivo/happy hour info")
    local_specialties: list[str] = Field(default_factory=list, description="Local specialty dishes")


class Phrase(BaseModel):
    """Useful phrase translation."""

    italian: str | None = Field(None, description="Phrase in Italian (or local language)")
    english: str = Field(..., description="English translation")


class TravelTips(BaseModel):
    """Comprehensive travel tips."""

    transportation: TransportationTips | None = Field(
        None, description="Transportation information"
    )
    booking_essentials: BookingEssentials | None = Field(None, description="Booking requirements")
    money: MoneyTips | None = Field(None, description="Money and payment tips")
    best_practices: list[BestPractice | str] = Field(
        default_factory=list, description="Best practices and tips"
    )
    safety: list[str] = Field(default_factory=list, description="Safety tips")
    food_tips: FoodTips | None = Field(None, description="Food and dining information")
    useful_phrases: list[Phrase] = Field(default_factory=list, description="Useful local phrases")


class ItineraryOutput(BaseModel):
    """Complete structured itinerary output.

    This model represents the full itinerary in JSON format, suitable for
    export, API responses, and programmatic processing.
    """

    trip: TripInfo = Field(..., description="Trip overview information")
    flights: FlightInfo = Field(..., description="Flight details")
    accommodation: AccommodationInfo = Field(..., description="Accommodation details")
    itinerary: list[DayItinerary] = Field(..., description="Day-by-day itinerary")
    budget_breakdown: BudgetBreakdown = Field(..., description="Complete budget breakdown")
    travel_tips: TravelTips | None = Field(None, description="Travel tips and information")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trip": {
                    "destination": {"city": "Rome", "country": "Italy"},
                    "dates": {
                        "start": "2024-06-15",
                        "end": "2024-06-20",
                        "duration_days": 6,
                    },
                    "travelers": {"count": 2, "type": "adults"},
                    "budget": {
                        "total": 3000,
                        "currency": "USD",
                        "spent": 2894,
                        "remaining": 106,
                    },
                },
                "flights": {
                    "outbound": {
                        "airline": "United Airlines",
                        "flight_number": "UN3333",
                        "route": {"from": "JFK", "to": "FCO"},
                        "departure": {"time": "09:45", "timezone": "America/New_York"},
                        "arrival": {"time": "12:25", "timezone": "Europe/Rome"},
                        "duration_minutes": 520,
                        "stops": 0,
                        "price_per_person": 272.20,
                        "total_price": 544.40,
                    },
                    "total_cost": 1089,
                },
            }
        }
    )

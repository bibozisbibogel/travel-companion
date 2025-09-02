"""External API data models and validation schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from travel_companion.models.trip import TravelClass


class FlightSearchRequest(BaseModel):
    """Request model for flight search operations."""

    origin: str = Field(..., min_length=3, max_length=4, description="Origin airport code")
    destination: str = Field(
        ..., min_length=3, max_length=4, description="Destination airport code"
    )
    departure_date: datetime = Field(..., description="Departure date")
    return_date: datetime | None = Field(None, description="Return date for round trip")
    passengers: int = Field(default=1, ge=1, le=9, description="Number of passengers")
    travel_class: TravelClass = Field(
        default=TravelClass.ECONOMY, description="Travel class preference"
    )
    currency: str = Field(
        default="USD", min_length=3, max_length=3, description="Preferred currency"
    )
    max_results: int = Field(default=50, ge=1, le=250, description="Maximum results to return")

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate airport code format."""
        return v.upper().strip()

    @field_validator("currency")
    @classmethod
    def validate_currency_code(cls, v: str) -> str:
        """Validate currency code format."""
        if not v.isupper():
            raise ValueError("Currency code must be uppercase")
        return v

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )


class AmadeusFlightSegment(BaseModel):
    """Amadeus API flight segment model."""

    carrier_code: str = Field(..., description="Airline carrier code")
    number: str = Field(..., description="Flight number")
    aircraft_code: str | None = Field(None, description="Aircraft type code")
    departure: dict[str, Any] = Field(..., description="Departure information")
    arrival: dict[str, Any] = Field(..., description="Arrival information")
    operating: dict[str, Any] | None = Field(None, description="Operating carrier info")
    duration: str = Field(..., description="Flight duration in ISO format")
    stops: int = Field(default=0, description="Number of stops")

    model_config = ConfigDict(populate_by_name=True)


class AmadeusPrice(BaseModel):
    """Amadeus API price information model."""

    currency: str = Field(..., description="Price currency")
    total: str = Field(..., description="Total price as string")
    base: str = Field(..., description="Base price as string")
    fees: list[dict[str, Any]] = Field(default_factory=list, description="Fee breakdown")
    taxes: list[dict[str, Any]] = Field(default_factory=list, description="Tax breakdown")

    @property
    def total_decimal(self) -> Decimal:
        """Get total price as Decimal."""
        return Decimal(self.total)

    @property
    def base_decimal(self) -> Decimal:
        """Get base price as Decimal."""
        return Decimal(self.base)

    model_config = ConfigDict(populate_by_name=True)


class AmadeusFlightOffer(BaseModel):
    """Amadeus API flight offer model."""

    id: str = Field(..., description="Offer ID from Amadeus")
    type: str = Field(..., description="Offer type")
    source: str = Field(..., description="Offer source")
    instant_ticketing_required: bool = Field(
        default=False, description="Instant ticketing requirement"
    )
    non_homogeneous: bool = Field(default=False, description="Non-homogeneous booking")
    paymentCardRequired: bool = Field(default=False, description="Payment card requirement")
    last_ticketing_date: str | None = Field(None, description="Last ticketing date")
    itineraries: list[dict[str, Any]] = Field(..., description="Flight itineraries")
    price: AmadeusPrice = Field(..., description="Price information")
    pricing_options: dict[str, Any] = Field(default_factory=dict, description="Pricing options")
    validating_airline_codes: list[str] = Field(
        default_factory=list, description="Validating airlines"
    )
    traveler_pricings: list[dict[str, Any]] = Field(
        default_factory=list, description="Traveler pricing"
    )

    model_config = ConfigDict(populate_by_name=True)


class AmadeusFlightResponse(BaseModel):
    """Amadeus API flight search response model."""

    meta: dict[str, Any] = Field(default_factory=dict, description="Response metadata")
    data: list[AmadeusFlightOffer] = Field(default_factory=list, description="Flight offers")
    dictionaries: dict[str, Any] = Field(default_factory=dict, description="Reference dictionaries")
    warnings: list[dict[str, Any]] = Field(default_factory=list, description="API warnings")
    errors: list[dict[str, Any]] = Field(default_factory=list, description="API errors")

    model_config = ConfigDict(populate_by_name=True)


class FlightOption(BaseModel):
    """Standardized flight option model for internal use."""

    flight_id: UUID = Field(default_factory=uuid4, description="Internal flight ID")
    trip_id: UUID | None = Field(None, description="Associated trip ID")
    external_id: str = Field(..., description="External provider ID")
    airline: str = Field(..., description="Airline name")
    flight_number: str = Field(..., description="Flight number")
    origin: str = Field(..., description="Origin airport code")
    destination: str = Field(..., description="Destination airport code")
    departure_time: datetime = Field(..., description="Departure timestamp")
    arrival_time: datetime = Field(..., description="Arrival timestamp")
    duration_minutes: int = Field(..., gt=0, description="Flight duration in minutes")
    stops: int = Field(default=0, ge=0, description="Number of stops")
    price: Decimal = Field(..., gt=0, description="Flight price")
    currency: str = Field(default="USD", description="Price currency")
    travel_class: TravelClass = Field(default=TravelClass.ECONOMY, description="Travel class")
    booking_url: str | None = Field(None, description="Booking URL")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        """Validate price is positive with max 2 decimal places."""
        if v <= 0:
            raise ValueError("Price must be positive")
        # Round to 2 decimal places
        return v.quantize(Decimal("0.01"))

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        from_attributes=True,
    )


class FlightSearchResponse(BaseModel):
    """Flight search response model."""

    flights: list[FlightOption] = Field(default_factory=list, description="Flight options")
    search_metadata: dict[str, Any] = Field(default_factory=dict, description="Search metadata")
    total_results: int = Field(default=0, ge=0, description="Total number of results")
    search_time_ms: int = Field(default=0, ge=0, description="Search time in milliseconds")
    cached: bool = Field(default=False, description="Whether result was cached")
    cache_expires_at: datetime | None = Field(None, description="Cache expiration timestamp")

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )


class FlightComparisonResult(BaseModel):
    """Flight comparison and ranking result model."""

    flight: FlightOption = Field(..., description="Flight option")
    score: float = Field(..., ge=0, le=100, description="Ranking score (0-100)")
    price_rank: int = Field(..., ge=1, description="Price ranking (1=cheapest)")
    duration_rank: int = Field(..., ge=1, description="Duration ranking (1=shortest)")
    departure_preference_score: float = Field(
        ..., ge=0, le=1, description="Departure time preference score"
    )
    reasons: list[str] = Field(default_factory=list, description="Ranking reasons")

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )

"""External API data models and validation schemas."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationInfo

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


# Hotel-related models


class HotelSearchRequest(BaseModel):
    """Request model for hotel search operations."""

    location: str = Field(..., min_length=1, description="Hotel search location")
    check_in_date: datetime = Field(..., description="Check-in date")
    check_out_date: datetime = Field(..., description="Check-out date")
    guest_count: int = Field(..., ge=1, le=20, description="Number of guests")
    room_count: int = Field(default=1, ge=1, le=10, description="Number of rooms")
    budget_per_night: Decimal | None = Field(None, gt=0, description="Budget per night")
    currency: str = Field(
        default="USD", min_length=3, max_length=3, description="Preferred currency"
    )
    max_results: int = Field(default=50, ge=1, le=250, description="Maximum results to return")

    @field_validator("check_out_date")
    @classmethod
    def validate_checkout_after_checkin(cls, v: datetime, info: Any) -> datetime:
        """Validate check-out date is after check-in date."""
        if hasattr(info, "data") and "check_in_date" in info.data:
            if v <= info.data["check_in_date"]:
                raise ValueError("Check-out date must be after check-in date")
        return v

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


class HotelLocation(BaseModel):
    """Hotel location information."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    address: str | None = Field(None, description="Hotel address")
    city: str | None = Field(None, description="City name")
    country: str | None = Field(None, description="Country name")
    postal_code: str | None = Field(None, description="Postal code")

    model_config = ConfigDict(populate_by_name=True)


class HotelOption(BaseModel):
    """Standardized hotel option model for internal use."""

    hotel_id: UUID = Field(default_factory=uuid4, description="Internal hotel ID")
    trip_id: UUID | None = Field(None, description="Associated trip ID")
    external_id: str = Field(..., description="External provider ID")
    name: str = Field(..., min_length=1, description="Hotel name")
    location: HotelLocation = Field(..., description="Hotel location")
    price_per_night: Decimal = Field(..., gt=0, description="Price per night")
    currency: str = Field(default="USD", description="Price currency")
    rating: float | None = Field(None, ge=1, le=5, description="Hotel rating (1-5)")
    amenities: list[str] = Field(default_factory=list, description="Available amenities")
    photos: list[str] = Field(default_factory=list, description="Photo URLs")
    booking_url: str | None = Field(None, description="Booking URL")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

    @field_validator("price_per_night")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        """Validate price is positive with max 2 decimal places."""
        if v <= 0:
            raise ValueError("Price must be positive")
        return v.quantize(Decimal("0.01"))

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        from_attributes=True,
    )


class HotelSearchResponse(BaseModel):
    """Hotel search response model."""

    hotels: list[HotelOption] = Field(default_factory=list, description="Hotel options")
    search_metadata: dict[str, Any] = Field(default_factory=dict, description="Search metadata")
    total_results: int = Field(default=0, ge=0, description="Total number of results")
    search_time_ms: int = Field(default=0, ge=0, description="Search time in milliseconds")
    cached: bool = Field(default=False, description="Whether result was cached")
    cache_expires_at: datetime | None = Field(None, description="Cache expiration timestamp")

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )


class HotelComparisonResult(BaseModel):
    """Hotel comparison and ranking result model."""

    hotel: HotelOption = Field(..., description="Hotel option")
    score: float = Field(..., ge=0, le=100, description="Ranking score (0-100)")
    price_rank: int = Field(..., ge=1, description="Price ranking (1=cheapest)")
    location_rank: int = Field(..., ge=1, description="Location ranking (1=closest)")
    rating_rank: int = Field(..., ge=1, description="Rating ranking (1=highest)")
    value_score: float = Field(..., ge=0, le=1, description="Price-to-rating value score")
    reasons: list[str] = Field(default_factory=list, description="Ranking reasons")

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )


# Activity-related models


class ActivityCategory(str, Enum):
    """Activity category enumeration matching database schema."""

    CULTURAL = "cultural"
    ADVENTURE = "adventure"
    FOOD = "food"
    ENTERTAINMENT = "entertainment"
    NATURE = "nature"
    SHOPPING = "shopping"
    RELAXATION = "relaxation"
    NIGHTLIFE = "nightlife"


class ActivitySearchRequest(BaseModel):
    """Request model for activity search operations."""

    location: str = Field(..., min_length=1, description="Activity search location")
    check_in_date: datetime | None = Field(None, description="Start date for activities")
    check_out_date: datetime | None = Field(None, description="End date for activities")
    category: ActivityCategory | None = Field(None, description="Activity category filter")
    budget_per_person: Decimal | None = Field(None, gt=0, description="Budget per person")
    currency: str = Field(
        default="USD", min_length=3, max_length=3, description="Preferred currency"
    )
    duration_hours: int | None = Field(None, gt=0, le=24, description="Preferred duration in hours")
    guest_count: int = Field(default=1, ge=1, le=20, description="Number of guests")
    max_results: int = Field(default=50, ge=1, le=250, description="Maximum results to return")

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


class ActivityLocation(BaseModel):
    """Activity location information."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    address: str | None = Field(None, description="Activity address")
    city: str | None = Field(None, description="City name")
    country: str | None = Field(None, description="Country name")
    postal_code: str | None = Field(None, description="Postal code")

    model_config = ConfigDict(populate_by_name=True)


class ActivityOption(BaseModel):
    """Standardized activity option model for internal use."""

    activity_id: UUID = Field(default_factory=uuid4, description="Internal activity ID")
    trip_id: UUID | None = Field(None, description="Associated trip ID")
    external_id: str = Field(..., description="External provider ID")
    name: str = Field(..., min_length=1, description="Activity name")
    description: str | None = Field(None, description="Activity description")
    category: ActivityCategory = Field(..., description="Activity category")
    location: ActivityLocation = Field(..., description="Activity location")
    duration_minutes: int | None = Field(None, gt=0, description="Activity duration in minutes")
    price: Decimal = Field(..., ge=0, description="Activity price")
    currency: str = Field(default="USD", description="Price currency")
    rating: float | None = Field(None, ge=1, le=5, description="Activity rating (1-5)")
    review_count: int | None = Field(None, ge=0, description="Number of reviews")
    images: list[str] = Field(default_factory=list, description="Activity image URLs")
    booking_url: str | None = Field(None, description="Booking URL")
    provider: str = Field(..., description="API provider (tripadvisor, viator, getyourguide)")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        """Validate price with max 2 decimal places."""
        if v < 0:
            raise ValueError("Price cannot be negative")
        return v.quantize(Decimal("0.01"))

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        from_attributes=True,
    )


class ActivitySearchResponse(BaseModel):
    """Activity search response model."""

    activities: list[ActivityOption] = Field(default_factory=list, description="Activity options")
    search_metadata: dict[str, Any] = Field(default_factory=dict, description="Search metadata")
    total_results: int = Field(default=0, ge=0, description="Total number of results")
    search_time_ms: int = Field(default=0, ge=0, description="Search time in milliseconds")
    cached: bool = Field(default=False, description="Whether result was cached")
    cache_expires_at: datetime | None = Field(None, description="Cache expiration timestamp")

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )


class ActivityComparisonResult(BaseModel):
    """Activity comparison and ranking result model."""

    activity: ActivityOption = Field(..., description="Activity option")
    score: float = Field(..., ge=0, le=100, description="Ranking score (0-100)")
    price_rank: int = Field(..., ge=1, description="Price ranking (1=cheapest)")
    rating_rank: int = Field(..., ge=1, description="Rating ranking (1=highest)")
    duration_preference_score: float = Field(
        ..., ge=0, le=1, description="Duration preference score"
    )
    category_match_score: float = Field(
        ..., ge=0, le=1, description="Category preference match score"
    )
    reasons: list[str] = Field(default_factory=list, description="Ranking reasons")

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )


# Weather-related models


class WeatherCondition(str, Enum):
    """Weather condition categories."""

    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    LIGHT_RAIN = "light_rain"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    SNOW = "snow"
    HEAVY_SNOW = "heavy_snow"
    FOG = "fog"
    MIST = "mist"
    WIND = "wind"
    UNKNOWN = "unknown"


class WeatherSeverity(str, Enum):
    """Weather severity levels for alerts."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class WeatherAlert(BaseModel):
    """Weather alert and warning model."""

    title: str = Field(..., description="Alert title")
    description: str = Field(..., description="Alert description")
    severity: WeatherSeverity = Field(..., description="Alert severity level")
    start_time: datetime = Field(..., description="Alert start time")
    end_time: datetime = Field(..., description="Alert end time")
    regions: list[str] = Field(default_factory=list, description="Affected regions")

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )


class WeatherData(BaseModel):
    """Individual weather data point model."""

    timestamp: datetime = Field(..., description="Weather data timestamp")
    temperature: float = Field(..., description="Temperature in Celsius")
    feels_like: float = Field(..., description="Feels like temperature in Celsius")
    humidity: float = Field(..., ge=0, le=100, description="Humidity percentage")
    pressure: float = Field(..., description="Atmospheric pressure in hPa")
    visibility: float = Field(..., ge=0, description="Visibility in kilometers")
    wind_speed: float = Field(..., ge=0, description="Wind speed in km/h")
    wind_direction: float = Field(..., ge=0, le=360, description="Wind direction in degrees")
    precipitation: float = Field(default=0, ge=0, description="Precipitation in mm")
    precipitation_probability: float = Field(
        default=0, ge=0, le=1, description="Precipitation probability"
    )
    condition: WeatherCondition = Field(..., description="Weather condition")
    condition_description: str = Field(..., description="Human-readable condition description")
    uv_index: float | None = Field(None, ge=0, le=11, description="UV index")

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )


class WeatherLocation(BaseModel):
    """Weather location information model."""

    name: str = Field(..., description="Location name")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    country: str | None = Field(None, description="Country name")
    timezone: str | None = Field(None, description="Timezone identifier")

    model_config = ConfigDict(populate_by_name=True)


class WeatherSearchRequest(BaseModel):
    """Weather search request model."""

    location: str = Field(..., min_length=1, description="Location name or coordinates")
    latitude: float | None = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: float | None = Field(None, ge=-180, le=180, description="Longitude coordinate")
    start_date: datetime = Field(..., description="Start date for weather data")
    end_date: datetime = Field(..., description="End date for weather data")
    include_alerts: bool = Field(default=True, description="Include weather alerts")
    include_historical: bool = Field(default=False, description="Include historical data context")

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: datetime, info: ValidationInfo) -> datetime:
        """Validate that end date is after start date."""
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("End date must be after start date")
        return v

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )


class WeatherForecast(BaseModel):
    """Weather forecast model."""

    location: WeatherLocation = Field(..., description="Forecast location")
    current: WeatherData | None = Field(None, description="Current weather conditions")
    hourly: list[WeatherData] = Field(default_factory=list, description="Hourly forecast data")
    daily: list[WeatherData] = Field(default_factory=list, description="Daily forecast data")
    alerts: list[WeatherAlert] = Field(default_factory=list, description="Weather alerts")

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )


class WeatherSearchResponse(BaseModel):
    """Weather search response model."""

    forecast: WeatherForecast = Field(..., description="Weather forecast data")
    historical_data: list[WeatherData] = Field(
        default_factory=list, description="Historical weather data"
    )
    search_metadata: dict[str, Any] = Field(default_factory=dict, description="Search metadata")
    search_time_ms: int = Field(default=0, ge=0, description="Search time in milliseconds")
    cached: bool = Field(default=False, description="Whether result was cached")
    cache_expires_at: datetime | None = Field(None, description="Cache expiration timestamp")
    data_source: str = Field(..., description="Weather data provider")

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )


class ActivityRecommendation(BaseModel):
    """Weather-based activity recommendation model."""

    activity_type: str = Field(..., description="Type of activity")
    suitability_score: float = Field(..., ge=0, le=1, description="Weather suitability score")
    recommendation: str = Field(..., description="Recommendation text")
    weather_factors: list[str] = Field(
        default_factory=list, description="Weather factors considered"
    )

    model_config = ConfigDict(populate_by_name=True)


# Restaurant and Food-related models


class CuisineType(str, Enum):
    """Restaurant cuisine type enumeration."""

    AMERICAN = "american"
    ITALIAN = "italian"
    CHINESE = "chinese"
    JAPANESE = "japanese"
    INDIAN = "indian"
    MEXICAN = "mexican"
    FRENCH = "french"
    THAI = "thai"
    MEDITERRANEAN = "mediterranean"
    SEAFOOD = "seafood"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    BBQ = "bbq"
    PIZZA = "pizza"
    SUSHI = "sushi"
    STEAKHOUSE = "steakhouse"
    FAST_FOOD = "fast_food"
    FINE_DINING = "fine_dining"
    CASUAL_DINING = "casual_dining"
    LOCAL_SPECIALTY = "local_specialty"
    FUSION = "fusion"
    OTHER = "other"


class DietaryRestriction(str, Enum):
    """Dietary restriction enumeration."""

    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    NUT_FREE = "nut_free"
    HALAL = "halal"
    KOSHER = "kosher"
    KETO = "keto"
    PALEO = "paleo"
    LOW_CARB = "low_carb"
    DIABETIC_FRIENDLY = "diabetic_friendly"


class PriceRange(str, Enum):
    """Restaurant price range enumeration."""

    BUDGET = "$"  # Under $15 per person
    MODERATE = "$$"  # $15-30 per person
    EXPENSIVE = "$$$"  # $30-60 per person
    VERY_EXPENSIVE = "$$$$"  # Over $60 per person


class RestaurantSearchRequest(BaseModel):
    """Request model for restaurant search operations."""

    location: str = Field(..., min_length=1, description="Restaurant search location")
    latitude: float | None = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: float | None = Field(None, ge=-180, le=180, description="Longitude coordinate")
    cuisine_type: CuisineType | None = Field(None, description="Preferred cuisine type")
    price_range: PriceRange | None = Field(None, description="Price range filter")
    dietary_restrictions: list[DietaryRestriction] = Field(
        default_factory=list, description="Dietary restrictions to accommodate"
    )
    budget_per_person: Decimal | None = Field(None, gt=0, description="Budget per person")
    currency: str = Field(
        default="USD", min_length=3, max_length=3, description="Preferred currency"
    )
    radius_km: float = Field(default=5.0, gt=0, le=50, description="Search radius in kilometers")
    party_size: int = Field(default=2, ge=1, le=20, description="Number of people in party")
    meal_type: str | None = Field(None, description="Meal type (breakfast, lunch, dinner, etc.)")
    open_now: bool = Field(default=False, description="Only show restaurants open now")
    max_results: int = Field(default=50, ge=1, le=250, description="Maximum results to return")

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


class RestaurantLocation(BaseModel):
    """Restaurant location information."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    address: str | None = Field(None, description="Restaurant address")
    city: str | None = Field(None, description="City name")
    state: str | None = Field(None, description="State/province name")
    country: str | None = Field(None, description="Country name")
    postal_code: str | None = Field(None, description="Postal code")
    neighborhood: str | None = Field(None, description="Neighborhood name")

    model_config = ConfigDict(populate_by_name=True)


class RestaurantHours(BaseModel):
    """Restaurant operating hours model."""

    monday: str | None = Field(None, description="Monday hours (e.g., '9:00 AM - 10:00 PM')")
    tuesday: str | None = Field(None, description="Tuesday hours")
    wednesday: str | None = Field(None, description="Wednesday hours")
    thursday: str | None = Field(None, description="Thursday hours")
    friday: str | None = Field(None, description="Friday hours")
    saturday: str | None = Field(None, description="Saturday hours")
    sunday: str | None = Field(None, description="Sunday hours")
    is_open_now: bool = Field(default=False, description="Currently open status")

    model_config = ConfigDict(populate_by_name=True)


class RestaurantContact(BaseModel):
    """Restaurant contact information model."""

    phone: str | None = Field(None, description="Phone number")
    email: str | None = Field(None, description="Email address")
    website: str | None = Field(None, description="Website URL")
    reservation_url: str | None = Field(None, description="Online reservation URL")

    model_config = ConfigDict(populate_by_name=True)


class PopularDish(BaseModel):
    """Popular dish recommendation model."""

    name: str = Field(..., description="Dish name")
    description: str | None = Field(None, description="Dish description")
    price: Decimal | None = Field(None, gt=0, description="Dish price")
    currency: str = Field(default="USD", description="Price currency")
    is_specialty: bool = Field(default=False, description="Local specialty indicator")
    dietary_info: list[str] = Field(default_factory=list, description="Dietary information")

    model_config = ConfigDict(populate_by_name=True)


class RestaurantOption(BaseModel):
    """Standardized restaurant option model for internal use."""

    restaurant_id: UUID = Field(default_factory=uuid4, description="Internal restaurant ID")
    trip_id: UUID | None = Field(None, description="Associated trip ID")
    external_id: str = Field(..., description="External provider ID")
    name: str = Field(..., min_length=1, description="Restaurant name")
    cuisine_type: CuisineType = Field(..., description="Primary cuisine type")
    location: RestaurantLocation = Field(..., description="Restaurant location")
    rating: float | None = Field(None, ge=1, le=5, description="Restaurant rating (1-5)")
    review_count: int | None = Field(None, ge=0, description="Number of reviews")
    price_range: PriceRange = Field(..., description="Price range category")
    average_cost_per_person: Decimal | None = Field(
        None, gt=0, description="Average cost per person"
    )
    currency: str = Field(default="USD", description="Price currency")
    hours: RestaurantHours | None = Field(None, description="Operating hours")
    contact: RestaurantContact | None = Field(None, description="Contact information")
    amenities: list[str] = Field(default_factory=list, description="Available amenities")
    dietary_accommodations: list[DietaryRestriction] = Field(
        default_factory=list, description="Dietary restrictions accommodated"
    )
    popular_dishes: list[PopularDish] = Field(
        default_factory=list, description="Popular and specialty dishes"
    )
    photos: list[str] = Field(default_factory=list, description="Photo URLs")
    booking_url: str | None = Field(None, description="Booking/reservation URL")
    provider: str = Field(..., description="API provider (yelp, google_places, zomato)")
    distance_km: float | None = Field(None, ge=0, description="Distance from search location in km")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

    @field_validator("average_cost_per_person")
    @classmethod
    def validate_price(cls, v: Decimal | None) -> Decimal | None:
        """Validate price is positive with max 2 decimal places."""
        if v is not None:
            if v <= 0:
                raise ValueError("Price must be positive")
            return v.quantize(Decimal("0.01"))
        return v

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        from_attributes=True,
    )


class RestaurantSearchResponse(BaseModel):
    """Restaurant search response model."""

    restaurants: list[RestaurantOption] = Field(
        default_factory=list, description="Restaurant options"
    )
    search_metadata: dict[str, Any] = Field(default_factory=dict, description="Search metadata")
    total_results: int = Field(default=0, ge=0, description="Total number of results")
    search_time_ms: int = Field(default=0, ge=0, description="Search time in milliseconds")
    cached: bool = Field(default=False, description="Whether result was cached")
    cache_expires_at: datetime | None = Field(None, description="Cache expiration timestamp")

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )


class RestaurantComparisonResult(BaseModel):
    """Restaurant comparison and ranking result model."""

    restaurant: RestaurantOption = Field(..., description="Restaurant option")
    score: float = Field(..., ge=0, le=100, description="Ranking score (0-100)")
    rating_rank: int = Field(..., ge=1, description="Rating ranking (1=highest)")
    price_rank: int = Field(..., ge=1, description="Price ranking (1=best value)")
    distance_rank: int = Field(..., ge=1, description="Distance ranking (1=closest)")
    cuisine_match_score: float = Field(
        ..., ge=0, le=1, description="Cuisine preference match score"
    )
    dietary_match_score: float = Field(
        ..., ge=0, le=1, description="Dietary restriction match score"
    )
    local_specialty_bonus: float = Field(
        ..., ge=0, le=1, description="Local specialty bonus points"
    )
    reasons: list[str] = Field(default_factory=list, description="Ranking reasons")

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )

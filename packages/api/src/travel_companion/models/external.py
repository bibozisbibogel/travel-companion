"""External API data models and validation schemas."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

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


class AviationStackFlightInfo(BaseModel):
    """AviationStack API flight information model."""

    number: str = Field(..., description="Flight number")
    iata: str | None = Field(None, description="Flight IATA code")
    icao: str | None = Field(None, description="Flight ICAO code")
    codeshared: dict[str, Any] | None = Field(None, description="Codeshared flight info")

    model_config = ConfigDict(populate_by_name=True)


class AviationStackAirline(BaseModel):
    """AviationStack API airline information model."""

    name: str = Field(..., description="Airline name")
    iata: str | None = Field(None, description="Airline IATA code")
    icao: str | None = Field(None, description="Airline ICAO code")

    model_config = ConfigDict(populate_by_name=True)


class AviationStackFlightData(BaseModel):
    """AviationStack API flight data model."""

    flight_date: str = Field(..., description="Flight date")
    flight_status: str = Field(..., description="Flight status")
    departure: dict[str, Any] = Field(..., description="Departure information")
    arrival: dict[str, Any] = Field(..., description="Arrival information")
    airline: AviationStackAirline = Field(..., description="Airline information")
    flight: AviationStackFlightInfo = Field(..., description="Flight information")
    aircraft: dict[str, Any] | None = Field(None, description="Aircraft information")
    live: dict[str, Any] | None = Field(None, description="Live tracking data")

    model_config = ConfigDict(populate_by_name=True)


class AviationStackFlightResponse(BaseModel):
    """AviationStack API flight search response model."""

    pagination: dict[str, Any] = Field(default_factory=dict, description="Pagination info")
    data: list[AviationStackFlightData] = Field(default_factory=list, description="Flight data")

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
    flight_status: str | None = Field(None, description="Flight status")
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


class GeoapifyCateringCategory(str, Enum):
    """Geoapify catering category enumeration - comprehensive list."""

    # Main categories
    CATERING = "catering"
    BAR = "catering.bar"
    BIERGARTEN = "catering.biergarten"
    CAFE = "catering.cafe"
    FAST_FOOD = "catering.fast_food"
    FOOD_COURT = "catering.food_court"
    ICE_CREAM = "catering.ice_cream"
    PUB = "catering.pub"
    RESTAURANT = "catering.restaurant"
    TAPROOM = "catering.taproom"

    # Cafe subcategories
    CAFE_BUBBLE_TEA = "catering.cafe.bubble_tea"
    CAFE_CAKE = "catering.cafe.cake"
    CAFE_COFFEE = "catering.cafe.coffee"
    CAFE_COFFEE_SHOP = "catering.cafe.coffee_shop"
    CAFE_CREPE = "catering.cafe.crepe"
    CAFE_DESSERT = "catering.cafe.dessert"
    CAFE_DONUT = "catering.cafe.donut"
    CAFE_FROZEN_YOGURT = "catering.cafe.frozen_yogurt"
    CAFE_ICE_CREAM = "catering.cafe.ice_cream"
    CAFE_TEA = "catering.cafe.tea"
    CAFE_WAFFLE = "catering.cafe.waffle"

    # Fast food subcategories
    FAST_FOOD_BURGER = "catering.fast_food.burger"
    FAST_FOOD_FISH_CHIPS = "catering.fast_food.fish_and_chips"
    FAST_FOOD_HOT_DOG = "catering.fast_food.hot_dog"
    FAST_FOOD_KEBAB = "catering.fast_food.kebab"
    FAST_FOOD_NOODLE = "catering.fast_food.noodle"
    FAST_FOOD_PITA = "catering.fast_food.pita"
    FAST_FOOD_PIZZA = "catering.fast_food.pizza"
    FAST_FOOD_RAMEN = "catering.fast_food.ramen"
    FAST_FOOD_SALAD = "catering.fast_food.salad"
    FAST_FOOD_SANDWICH = "catering.fast_food.sandwich"
    FAST_FOOD_SOUP = "catering.fast_food.soup"
    FAST_FOOD_TACOS = "catering.fast_food.tacos"
    FAST_FOOD_TAPAS = "catering.fast_food.tapas"
    FAST_FOOD_WINGS = "catering.fast_food.wings"

    # Restaurant cuisine subcategories
    RESTAURANT_AFGHAN = "catering.restaurant.afghan"
    RESTAURANT_AFRICAN = "catering.restaurant.african"
    RESTAURANT_AMERICAN = "catering.restaurant.american"
    RESTAURANT_ARAB = "catering.restaurant.arab"
    RESTAURANT_ARGENTINIAN = "catering.restaurant.argentinian"
    RESTAURANT_ASIAN = "catering.restaurant.asian"
    RESTAURANT_AUSTRIAN = "catering.restaurant.austrian"
    RESTAURANT_BALKAN = "catering.restaurant.balkan"
    RESTAURANT_BARBECUE = "catering.restaurant.barbecue"
    RESTAURANT_BAVARIAN = "catering.restaurant.bavarian"
    RESTAURANT_BEEF_BOWL = "catering.restaurant.beef_bowl"
    RESTAURANT_BELGIAN = "catering.restaurant.belgian"
    RESTAURANT_BOLIVIAN = "catering.restaurant.bolivian"
    RESTAURANT_BRAZILIAN = "catering.restaurant.brazilian"
    RESTAURANT_BURGER = "catering.restaurant.burger"
    RESTAURANT_CARIBBEAN = "catering.restaurant.caribbean"
    RESTAURANT_CHICKEN = "catering.restaurant.chicken"
    RESTAURANT_CHILI = "catering.restaurant.chili"
    RESTAURANT_CHINESE = "catering.restaurant.chinese"
    RESTAURANT_CROATIAN = "catering.restaurant.croatian"
    RESTAURANT_CUBAN = "catering.restaurant.cuban"
    RESTAURANT_CURRY = "catering.restaurant.curry"
    RESTAURANT_CZECH = "catering.restaurant.czech"
    RESTAURANT_DANISH = "catering.restaurant.danish"
    RESTAURANT_DUMPLING = "catering.restaurant.dumpling"
    RESTAURANT_ETHIOPIAN = "catering.restaurant.ethiopian"
    RESTAURANT_EUROPEAN = "catering.restaurant.european"
    RESTAURANT_FILIPINO = "catering.restaurant.filipino"
    RESTAURANT_FISH = "catering.restaurant.fish"
    RESTAURANT_FISH_CHIPS = "catering.restaurant.fish_and_chips"
    RESTAURANT_FRENCH = "catering.restaurant.french"
    RESTAURANT_FRITURE = "catering.restaurant.friture"
    RESTAURANT_GEORGIAN = "catering.restaurant.georgian"
    RESTAURANT_GERMAN = "catering.restaurant.german"
    RESTAURANT_GREEK = "catering.restaurant.greek"
    RESTAURANT_HAWAIIAN = "catering.restaurant.hawaiian"
    RESTAURANT_HUNGARIAN = "catering.restaurant.hungarian"
    RESTAURANT_INDIAN = "catering.restaurant.indian"
    RESTAURANT_INDONESIAN = "catering.restaurant.indonesian"
    RESTAURANT_INTERNATIONAL = "catering.restaurant.international"
    RESTAURANT_IRISH = "catering.restaurant.irish"
    RESTAURANT_ITALIAN = "catering.restaurant.italian"
    RESTAURANT_JAMAICAN = "catering.restaurant.jamaican"
    RESTAURANT_JAPANESE = "catering.restaurant.japanese"
    RESTAURANT_KEBAB = "catering.restaurant.kebab"
    RESTAURANT_KOREAN = "catering.restaurant.korean"
    RESTAURANT_LATIN_AMERICAN = "catering.restaurant.latin_american"
    RESTAURANT_LEBANESE = "catering.restaurant.lebanese"
    RESTAURANT_MALAY = "catering.restaurant.malay"
    RESTAURANT_MALAYSIAN = "catering.restaurant.malaysian"
    RESTAURANT_MEDITERRANEAN = "catering.restaurant.mediterranean"
    RESTAURANT_MEXICAN = "catering.restaurant.mexican"
    RESTAURANT_MOROCCAN = "catering.restaurant.moroccan"
    RESTAURANT_NEPALESE = "catering.restaurant.nepalese"
    RESTAURANT_NOODLE = "catering.restaurant.noodle"
    RESTAURANT_ORIENTAL = "catering.restaurant.oriental"
    RESTAURANT_PAKISTANI = "catering.restaurant.pakistani"
    RESTAURANT_PERSIAN = "catering.restaurant.persian"
    RESTAURANT_PERUVIAN = "catering.restaurant.peruvian"
    RESTAURANT_PITA = "catering.restaurant.pita"
    RESTAURANT_PIZZA = "catering.restaurant.pizza"
    RESTAURANT_PORTUGUESE = "catering.restaurant.portuguese"
    RESTAURANT_RAMEN = "catering.restaurant.ramen"
    RESTAURANT_REGIONAL = "catering.restaurant.regional"
    RESTAURANT_RUSSIAN = "catering.restaurant.russian"
    RESTAURANT_SANDWICH = "catering.restaurant.sandwich"
    RESTAURANT_SEAFOOD = "catering.restaurant.seafood"
    RESTAURANT_SOUP = "catering.restaurant.soup"
    RESTAURANT_SPANISH = "catering.restaurant.spanish"
    RESTAURANT_STEAK_HOUSE = "catering.restaurant.steak_house"
    RESTAURANT_SUSHI = "catering.restaurant.sushi"
    RESTAURANT_SWEDISH = "catering.restaurant.swedish"
    RESTAURANT_SYRIAN = "catering.restaurant.syrian"
    RESTAURANT_TACOS = "catering.restaurant.tacos"
    RESTAURANT_TAIWANESE = "catering.restaurant.taiwanese"
    RESTAURANT_TAPAS = "catering.restaurant.tapas"
    RESTAURANT_TEX_MEX = "catering.restaurant.tex-mex"
    RESTAURANT_THAI = "catering.restaurant.thai"
    RESTAURANT_TURKISH = "catering.restaurant.turkish"
    RESTAURANT_UKRAINIAN = "catering.restaurant.ukrainian"
    RESTAURANT_UZBEK = "catering.restaurant.uzbek"
    RESTAURANT_VIETNAMESE = "catering.restaurant.vietnamese"
    RESTAURANT_WESTERN = "catering.restaurant.western"
    RESTAURANT_WINGS = "catering.restaurant.wings"


class RestaurantSearchRequest(BaseModel):
    """Request model for restaurant search operations - simplified for Geoapify."""

    location: str | None = Field(None, min_length=1, description="Restaurant search location name")
    latitude: float | None = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: float | None = Field(None, ge=-180, le=180, description="Longitude coordinate")
    categories: list[str] = Field(
        default_factory=lambda: ["catering.restaurant"],
        description="Geoapify categories (e.g., catering.restaurant, catering.fast_food)",
    )
    radius_meters: int = Field(default=5000, gt=0, le=50000, description="Search radius in meters")
    max_results: int = Field(default=50, ge=1, le=250, description="Maximum results to return")

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: list[str]) -> list[str]:
        """Validate at least one category is provided."""
        if not v:
            return ["catering.restaurant"]
        return v

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )


class RestaurantLocation(BaseModel):
    """Restaurant location information."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    address: str | None = Field(None, description="Restaurant address (address_line1)")
    address_line2: str | None = Field(
        None, description="Secondary address line (street, postal, city)"
    )
    city: str | None = Field(None, description="City name")
    state: str | None = Field(None, description="State/province name")
    country: str | None = Field(None, description="Country name")
    postal_code: str | None = Field(None, description="Postal code")
    neighborhood: str | None = Field(None, description="Neighborhood name")

    model_config = ConfigDict(populate_by_name=True)


# Restaurant hours, contact, and dish models removed - not available in Geoapify API


class RestaurantOption(BaseModel):
    """Standardized restaurant option model for internal use - simplified for Geoapify."""

    restaurant_id: UUID = Field(default_factory=uuid4, description="Internal restaurant ID")
    trip_id: UUID | None = Field(None, description="Associated trip ID")
    external_id: str = Field(..., description="Geoapify place_id")
    name: str = Field(..., min_length=1, description="Restaurant name")
    categories: list[str] = Field(
        default_factory=list, description="Geoapify categories (e.g., catering.restaurant)"
    )
    location: RestaurantLocation = Field(..., description="Restaurant location")
    formatted_address: str | None = Field(None, description="Full formatted address from Geoapify")
    distance_meters: int | None = Field(
        None, ge=0, description="Distance from search location in meters"
    )
    provider: str = Field(default="geoapify", description="API provider")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

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
    """Restaurant comparison and ranking result model - simplified for Geoapify."""

    restaurant: RestaurantOption = Field(..., description="Restaurant option")
    score: float = Field(..., ge=0, le=100, description="Ranking score (0-100)")
    distance_rank: int = Field(..., ge=1, description="Distance ranking (1=closest)")
    category_match_score: float = Field(
        ..., ge=0, le=1, description="Category preference match score"
    )
    reasons: list[str] = Field(default_factory=list, description="Ranking reasons")

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
    )

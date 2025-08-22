# Data Models

## User
**Purpose:** Represents authenticated users with travel preferences and history

**Key Attributes:**
- user_id: UUID - Primary identifier
- email: string - Authentication credential  
- travel_preferences: JSON - Stored preferences (budget ranges, accommodation types, activity interests)
- trip_history: Relationship - Past trips for personalization

**Relationships:**
- One-to-many with Trip entities
- One-to-many with SavedPreferences

## Trip
**Purpose:** Represents a complete travel planning session with all components

**Key Attributes:**
- trip_id: UUID - Primary identifier
- user_id: UUID - Foreign key to User
- destination: string - Primary travel destination
- start_date: date - Trip start date
- end_date: date - Trip end date
- budget: decimal - Total trip budget
- status: enum - (planning, booked, completed, cancelled)
- itinerary_data: JSON - Complete itinerary with all bookings

**Relationships:**
- Belongs to User
- Has many FlightOptions, HotelOptions, ActivityOptions

## FlightOption
**Purpose:** Stores flight search results and user selections

**Key Attributes:**
- flight_id: UUID - Primary identifier
- trip_id: UUID - Foreign key to Trip
- airline: string - Airline name
- price: decimal - Flight price
- departure_time: datetime - Departure timestamp
- arrival_time: datetime - Arrival timestamp
- duration: integer - Flight duration in minutes
- stops: integer - Number of stops

**Relationships:**
- Belongs to Trip
- Related to external booking systems

## HotelOption
**Purpose:** Accommodation options with booking details

**Key Attributes:**
- hotel_id: UUID - Primary identifier
- trip_id: UUID - Foreign key to Trip
- name: string - Hotel name
- price_per_night: decimal - Nightly rate
- location: Point - Geographic coordinates
- rating: float - Hotel rating (1-5)
- amenities: JSON - Available amenities

**Relationships:**
- Belongs to Trip
- Geographic relationship with activities

# Database Schema

> **Note**: For complete setup instructions, see [DATABASE_SETUP.md](../../packages/api/DATABASE_SETUP.md)
>
> For quick setup, see [QUICK_SETUP.md](../../packages/api/QUICK_SETUP.md)

## Overview

The Travel Companion database uses PostgreSQL (via Supabase) with the following main components:

- **Users & Authentication** - User accounts and authentication
- **Trip Planning** - Trips, itineraries, and planning workflow
- **Search Results** - Flights, hotels, activities discovered during planning
- **Row Level Security (RLS)** - User data isolation and security

## Setup Files

- **Users Schema**: `packages/api/src/travel_companion/core/database_setup.sql`
- **Trips Schema**: `packages/api/src/travel_companion/core/trips_schema.sql`
- **Setup Scripts**: `packages/api/scripts/`

## Core Tables

### Users and Authentication

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    travel_preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Trip Planning

```sql
-- Trip status enum
CREATE TYPE trip_status AS ENUM ('draft', 'planning', 'confirmed', 'completed', 'cancelled');

-- Main trips table
CREATE TABLE trips (
    trip_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    destination VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_budget NUMERIC(10,2) NOT NULL,
    traveler_count INTEGER DEFAULT 1,
    status trip_status DEFAULT 'draft',
    preferences JSONB DEFAULT '{}',
    itinerary_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### JSONB Field Structures

#### trips.preferences
```json
{
  "travel_class": "economy",
  "accommodation_type": "hotel",
  "currency": "USD",
  "destination_details": {
    "city": "Paris",
    "country": "France",
    "country_code": "FR",
    "airport_code": "CDG",
    "latitude": 48.8566,
    "longitude": 2.3522
  }
}
```

#### trips.itinerary_data
Complete `ItineraryOutput` structure from TravelPlannerAgent with geocoded coordinates:

**Coordinate Structure** (added in v1.1 - Story 3.6):
All location-based entities now include a `coordinates` object:
```json
{
  "latitude": 41.9009,
  "longitude": 12.4833,
  "geocoding_status": "success",
  "geocoded_at": "2025-10-26T14:30:00Z",
  "geocoding_error_message": null
}
```

Field specifications:
- `latitude`: DECIMAL(10, 8) range (-90 to 90)
- `longitude`: DECIMAL(11, 8) range (-180 to 180)
- `geocoding_status`: `"success"`, `"failed"`, or `"pending"`
- `geocoded_at`: ISO 8601 timestamp
- `geocoding_error_message`: Present only when status = "failed"

**Complete Structure:**
```json
{
  "destination_city": {
    "name": "Rome",
    "country": "Italy",
    "coordinates": {
      "latitude": 41.9028,
      "longitude": 12.4964,
      "geocoding_status": "success",
      "geocoded_at": "2025-10-26T14:30:00Z"
    }
  },
  "activities": [
    {
      "day": 1,
      "time": "10:00 AM",
      "name": "Visit Trevi Fountain",
      "location": "Trevi Fountain, Rome, Italy",
      "coordinates": {
        "latitude": 41.9009,
        "longitude": 12.4833,
        "geocoding_status": "success",
        "geocoded_at": "2025-10-26T14:30:00Z"
      },
      "description": "Iconic 18th-century fountain",
      "category": "cultural",
      "estimated_duration_minutes": 60,
      "estimated_cost": 0.0
    }
  ],
  "accommodations": [
    {
      "name": "Hotel Quirinale",
      "location": "Via Nazionale, 7, Rome",
      "coordinates": {
        "latitude": 41.9010,
        "longitude": 12.4926,
        "geocoding_status": "success"
      },
      "check_in_date": "2025-11-01",
      "check_out_date": "2025-11-05",
      "room_type": "Double Room",
      "estimated_price_per_night": 150.00
    }
  ],
  "restaurants": [
    {
      "day": 1,
      "meal": "dinner",
      "name": "Trattoria da Enzo",
      "location": "Via dei Vascellari, 29, Rome",
      "coordinates": {
        "latitude": 41.8897,
        "longitude": 12.4707,
        "geocoding_status": "success"
      },
      "cuisine": "Italian",
      "estimated_cost_per_person": 30.00
    }
  ],
  "flights": {
    "outbound": {
      "departure_airport": "JFK",
      "departure_location": "New York, USA",
      "departure_coordinates": {
        "latitude": 40.6413,
        "longitude": -73.7781,
        "geocoding_status": "success"
      },
      "arrival_airport": "FCO",
      "arrival_location": "Rome, Italy",
      "arrival_coordinates": {
        "latitude": 41.8003,
        "longitude": 12.2389,
        "geocoding_status": "success"
      }
    }
  },
  "budget_breakdown": {
    "flights": 800.00,
    "accommodations": 600.00,
    "activities": 150.00,
    "food": 240.00,
    "total": 2000.00,
    "currency": "USD"
  }
}
```

**Geocoding Indexes** (added in migration `add_geocoding_schema.sql`):
- GIN index on `itinerary_data` for efficient JSONB queries
- Expression index for destination coordinates
- Partial index for geocoding failures (monitoring)

-- Flight Options (normalized for comparison)
CREATE TABLE flight_options (
    flight_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID REFERENCES trips(trip_id) ON DELETE CASCADE,
    external_id VARCHAR(255), -- API provider's ID
    airline VARCHAR(100) NOT NULL,
    flight_number VARCHAR(20),
    origin VARCHAR(10) NOT NULL, -- Airport code
    destination VARCHAR(10) NOT NULL,
    departure_time TIMESTAMP WITH TIME ZONE NOT NULL,
    arrival_time TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INTEGER NOT NULL,
    stops INTEGER DEFAULT 0,
    price DECIMAL(10,2) NOT NULL,
    currency CHAR(3) DEFAULT 'USD',
    booking_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Hotel Options
CREATE TABLE hotel_options (
    hotel_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID REFERENCES trips(trip_id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    address TEXT,
    location POINT NOT NULL, -- PostGIS point for geographic queries
    price_per_night DECIMAL(10,2) NOT NULL,
    currency CHAR(3) DEFAULT 'USD',
    rating DECIMAL(2,1) CHECK (rating >= 1 AND rating <= 5),
    amenities JSONB DEFAULT '[]',
    photos JSONB DEFAULT '[]',
    booking_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Activity Options
CREATE TABLE activity_options (
    activity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID REFERENCES trips(trip_id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category activity_category NOT NULL,
    location POINT,
    duration_minutes INTEGER,
    price DECIMAL(10,2),
    currency CHAR(3) DEFAULT 'USD',
    rating DECIMAL(2,1),
    booking_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TYPE activity_category AS ENUM (
    'cultural', 'adventure', 'food', 'entertainment', 
    'nature', 'shopping', 'relaxation', 'nightlife'
);

-- Workflow State Tracking
CREATE TABLE workflow_states (
    state_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID REFERENCES trips(trip_id) ON DELETE CASCADE,
    current_step VARCHAR(100) NOT NULL,
    step_data JSONB DEFAULT '{}',
    completed_steps JSONB DEFAULT '[]',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for Performance
CREATE INDEX idx_trips_user_id ON trips(user_id);
CREATE INDEX idx_trips_dates ON trips(start_date, end_date);
CREATE INDEX idx_flight_options_trip ON flight_options(trip_id);
CREATE INDEX idx_hotel_options_trip ON hotel_options(trip_id);
CREATE INDEX idx_hotel_options_location ON hotel_options USING GIST(location);
CREATE INDEX idx_activity_options_trip ON activity_options(trip_id);
CREATE INDEX idx_activity_options_category ON activity_options(category);
CREATE INDEX idx_workflow_states_trip ON workflow_states(trip_id);

-- Enable Row Level Security
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE flight_options ENABLE ROW LEVEL SECURITY;
ALTER TABLE hotel_options ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_options ENABLE ROW LEVEL SECURITY;

-- RLS Policies (users can only see their own data)
CREATE POLICY user_trips_policy ON trips
    FOR ALL USING (user_id = auth.uid());
    
CREATE POLICY user_flight_options_policy ON flight_options
    FOR ALL USING (trip_id IN (SELECT trip_id FROM trips WHERE user_id = auth.uid()));
    
CREATE POLICY user_hotel_options_policy ON hotel_options
    FOR ALL USING (trip_id IN (SELECT trip_id FROM trips WHERE user_id = auth.uid()));
    
CREATE POLICY user_activity_options_policy ON activity_options
    FOR ALL USING (trip_id IN (SELECT trip_id FROM trips WHERE user_id = auth.uid()));
```

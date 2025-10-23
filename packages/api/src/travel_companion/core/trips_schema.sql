-- Database setup for Trip Planning
-- This file contains the schema for trip planning and itinerary management

-- Enable necessary extensions (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create trip_status enum type
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'trip_status') THEN
        CREATE TYPE trip_status AS ENUM ('draft', 'planning', 'confirmed', 'completed', 'cancelled');
    END IF;
END $$;

-- Create activity_category enum type
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'activity_category') THEN
        CREATE TYPE activity_category AS ENUM (
            'cultural', 'adventure', 'food', 'entertainment',
            'nature', 'shopping', 'relaxation', 'nightlife'
        );
    END IF;
END $$;

-- Trip Planning Sessions
CREATE TABLE IF NOT EXISTS trips (
    trip_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    destination VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_budget NUMERIC(10,2) NOT NULL CHECK (total_budget > 0),
    traveler_count INTEGER DEFAULT 1 CHECK (traveler_count >= 1 AND traveler_count <= 20),
    status trip_status DEFAULT 'draft',
    preferences JSONB DEFAULT '{}',
    itinerary_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT valid_date_range CHECK (end_date > start_date)
);

-- Flight Options (normalized for comparison)
CREATE TABLE IF NOT EXISTS flight_options (
    flight_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(trip_id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    airline VARCHAR(100) NOT NULL,
    flight_number VARCHAR(20),
    origin VARCHAR(10) NOT NULL,
    destination VARCHAR(10) NOT NULL,
    departure_time TIMESTAMP WITH TIME ZONE NOT NULL,
    arrival_time TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    stops INTEGER DEFAULT 0 CHECK (stops >= 0),
    price NUMERIC(10,2) NOT NULL CHECK (price > 0),
    currency CHAR(3) DEFAULT 'USD',
    booking_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Hotel Options
CREATE TABLE IF NOT EXISTS hotel_options (
    hotel_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(trip_id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    address TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    price_per_night NUMERIC(10,2) NOT NULL CHECK (price_per_night > 0),
    currency CHAR(3) DEFAULT 'USD',
    rating DECIMAL(2,1) CHECK (rating >= 0 AND rating <= 5),
    amenities JSONB DEFAULT '[]',
    photos JSONB DEFAULT '[]',
    booking_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Activity Options
CREATE TABLE IF NOT EXISTS activity_options (
    activity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(trip_id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category activity_category NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    location VARCHAR(255),
    duration_minutes INTEGER CHECK (duration_minutes > 0),
    price NUMERIC(10,2) CHECK (price >= 0),
    currency CHAR(3) DEFAULT 'USD',
    rating DECIMAL(2,1) CHECK (rating >= 0 AND rating <= 5),
    booking_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workflow State Tracking
CREATE TABLE IF NOT EXISTS workflow_states (
    state_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(trip_id) ON DELETE CASCADE,
    current_step VARCHAR(100) NOT NULL,
    step_data JSONB DEFAULT '{}',
    completed_steps JSONB DEFAULT '[]',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Apply updated_at trigger to trips table
DROP TRIGGER IF EXISTS update_trips_updated_at ON trips;
CREATE TRIGGER update_trips_updated_at
    BEFORE UPDATE ON trips
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply updated_at trigger to workflow_states table
DROP TRIGGER IF EXISTS update_workflow_states_updated_at ON workflow_states;
CREATE TRIGGER update_workflow_states_updated_at
    BEFORE UPDATE ON workflow_states
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_trips_user_id ON trips(user_id);
CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);
CREATE INDEX IF NOT EXISTS idx_trips_dates ON trips(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_trips_created_at ON trips(created_at);

CREATE INDEX IF NOT EXISTS idx_flight_options_trip ON flight_options(trip_id);
CREATE INDEX IF NOT EXISTS idx_flight_options_departure ON flight_options(departure_time);

CREATE INDEX IF NOT EXISTS idx_hotel_options_trip ON hotel_options(trip_id);
CREATE INDEX IF NOT EXISTS idx_hotel_options_price ON hotel_options(price_per_night);

CREATE INDEX IF NOT EXISTS idx_activity_options_trip ON activity_options(trip_id);
CREATE INDEX IF NOT EXISTS idx_activity_options_category ON activity_options(category);

CREATE INDEX IF NOT EXISTS idx_workflow_states_trip ON workflow_states(trip_id);

-- Enable Row Level Security
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE flight_options ENABLE ROW LEVEL SECURITY;
ALTER TABLE hotel_options ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_options ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_states ENABLE ROW LEVEL SECURITY;

-- RLS Policies for trips table
DROP POLICY IF EXISTS "Users can view their own trips" ON trips;
CREATE POLICY "Users can view their own trips" ON trips
    FOR SELECT USING (auth.uid()::text = user_id::text);

DROP POLICY IF EXISTS "Users can insert their own trips" ON trips;
CREATE POLICY "Users can insert their own trips" ON trips
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);

DROP POLICY IF EXISTS "Users can update their own trips" ON trips;
CREATE POLICY "Users can update their own trips" ON trips
    FOR UPDATE USING (auth.uid()::text = user_id::text);

DROP POLICY IF EXISTS "Users can delete their own trips" ON trips;
CREATE POLICY "Users can delete their own trips" ON trips
    FOR DELETE USING (auth.uid()::text = user_id::text);

-- RLS Policies for flight_options (access via trip ownership)
DROP POLICY IF EXISTS "Users can view flight options for their trips" ON flight_options;
CREATE POLICY "Users can view flight options for their trips" ON flight_options
    FOR SELECT USING (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

DROP POLICY IF EXISTS "Users can insert flight options for their trips" ON flight_options;
CREATE POLICY "Users can insert flight options for their trips" ON flight_options
    FOR INSERT WITH CHECK (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

DROP POLICY IF EXISTS "Users can update flight options for their trips" ON flight_options;
CREATE POLICY "Users can update flight options for their trips" ON flight_options
    FOR UPDATE USING (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

DROP POLICY IF EXISTS "Users can delete flight options for their trips" ON flight_options;
CREATE POLICY "Users can delete flight options for their trips" ON flight_options
    FOR DELETE USING (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

-- RLS Policies for hotel_options (access via trip ownership)
DROP POLICY IF EXISTS "Users can view hotel options for their trips" ON hotel_options;
CREATE POLICY "Users can view hotel options for their trips" ON hotel_options
    FOR SELECT USING (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

DROP POLICY IF EXISTS "Users can insert hotel options for their trips" ON hotel_options;
CREATE POLICY "Users can insert hotel options for their trips" ON hotel_options
    FOR INSERT WITH CHECK (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

DROP POLICY IF EXISTS "Users can update hotel options for their trips" ON hotel_options;
CREATE POLICY "Users can update hotel options for their trips" ON hotel_options
    FOR UPDATE USING (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

DROP POLICY IF EXISTS "Users can delete hotel options for their trips" ON hotel_options;
CREATE POLICY "Users can delete hotel options for their trips" ON hotel_options
    FOR DELETE USING (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

-- RLS Policies for activity_options (access via trip ownership)
DROP POLICY IF EXISTS "Users can view activity options for their trips" ON activity_options;
CREATE POLICY "Users can view activity options for their trips" ON activity_options
    FOR SELECT USING (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

DROP POLICY IF EXISTS "Users can insert activity options for their trips" ON activity_options;
CREATE POLICY "Users can insert activity options for their trips" ON activity_options
    FOR INSERT WITH CHECK (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

DROP POLICY IF EXISTS "Users can update activity options for their trips" ON activity_options;
CREATE POLICY "Users can update activity options for their trips" ON activity_options
    FOR UPDATE USING (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

DROP POLICY IF EXISTS "Users can delete activity options for their trips" ON activity_options;
CREATE POLICY "Users can delete activity options for their trips" ON activity_options
    FOR DELETE USING (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

-- RLS Policies for workflow_states (access via trip ownership)
DROP POLICY IF EXISTS "Users can view workflow states for their trips" ON workflow_states;
CREATE POLICY "Users can view workflow states for their trips" ON workflow_states
    FOR SELECT USING (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

DROP POLICY IF EXISTS "Users can insert workflow states for their trips" ON workflow_states;
CREATE POLICY "Users can insert workflow states for their trips" ON workflow_states
    FOR INSERT WITH CHECK (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

DROP POLICY IF EXISTS "Users can update workflow states for their trips" ON workflow_states;
CREATE POLICY "Users can update workflow states for their trips" ON workflow_states
    FOR UPDATE USING (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

DROP POLICY IF EXISTS "Users can delete workflow states for their trips" ON workflow_states;
CREATE POLICY "Users can delete workflow states for their trips" ON workflow_states
    FOR DELETE USING (
        trip_id IN (SELECT trip_id FROM trips WHERE auth.uid()::text = user_id::text)
    );

-- Grant appropriate permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON trips TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON flight_options TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON hotel_options TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON activity_options TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON workflow_states TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Add comments for documentation
COMMENT ON TABLE trips IS 'Main trips table storing user trip plans and itineraries';
COMMENT ON COLUMN trips.preferences IS 'JSONB field storing travel_class, accommodation_type, currency, and destination_details';
COMMENT ON COLUMN trips.itinerary_data IS 'JSONB field storing the complete ItineraryOutput structure from TravelPlannerAgent';

COMMENT ON TABLE flight_options IS 'Flight options discovered or saved for trips';
COMMENT ON TABLE hotel_options IS 'Hotel/accommodation options discovered or saved for trips';
COMMENT ON TABLE activity_options IS 'Activity and attraction options for trips';
COMMENT ON TABLE workflow_states IS 'Workflow execution state tracking for trip planning process';

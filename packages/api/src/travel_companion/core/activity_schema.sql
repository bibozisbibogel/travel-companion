-- Database schema for Activity & Attraction Agent
-- This file contains the schema for activity options storage

-- Enable PostGIS extension for geographic operations
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Activity category enum matching the Python enum
DO $$ BEGIN
    CREATE TYPE activity_category AS ENUM (
        'cultural',
        'adventure', 
        'food',
        'entertainment',
        'nature',
        'shopping',
        'relaxation',
        'nightlife'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Activity options table for storing activity search results
CREATE TABLE IF NOT EXISTS activity_options (
    activity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category activity_category NOT NULL,
    location JSONB NOT NULL, -- Store location data as JSONB for flexibility
    location_point GEOGRAPHY(POINT, 4326), -- PostGIS point for spatial queries
    duration_minutes INTEGER,
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    currency CHAR(3) DEFAULT 'USD',
    rating DECIMAL(2,1) CHECK (rating >= 0 AND rating <= 5),
    review_count INTEGER DEFAULT 0,
    images JSONB DEFAULT '[]',
    booking_url TEXT,
    provider VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create function to update location_point from location JSONB
CREATE OR REPLACE FUNCTION update_location_point()
RETURNS TRIGGER AS $$
BEGIN
    -- Extract latitude and longitude from JSONB and create PostGIS point
    IF NEW.location ? 'latitude' AND NEW.location ? 'longitude' THEN
        NEW.location_point = ST_SetSRID(
            ST_MakePoint(
                (NEW.location->>'longitude')::FLOAT,
                (NEW.location->>'latitude')::FLOAT
            ),
            4326
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update location_point when location changes
CREATE TRIGGER activity_location_point_trigger
    BEFORE INSERT OR UPDATE ON activity_options
    FOR EACH ROW
    EXECUTE FUNCTION update_location_point();

-- Trigger for updated_at
CREATE TRIGGER update_activity_options_updated_at
    BEFORE UPDATE ON activity_options
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Performance indexes for activity searches
CREATE INDEX IF NOT EXISTS idx_activity_options_trip_id ON activity_options(trip_id);
CREATE INDEX IF NOT EXISTS idx_activity_options_category ON activity_options(category);
CREATE INDEX IF NOT EXISTS idx_activity_options_provider ON activity_options(provider);
CREATE INDEX IF NOT EXISTS idx_activity_options_rating ON activity_options(rating DESC);
CREATE INDEX IF NOT EXISTS idx_activity_options_price ON activity_options(price);
CREATE INDEX IF NOT EXISTS idx_activity_options_created_at ON activity_options(created_at DESC);

-- Spatial index for location-based queries (PostGIS GIST index)
CREATE INDEX IF NOT EXISTS idx_activity_options_location_point 
    ON activity_options USING GIST (location_point);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_activity_options_category_rating 
    ON activity_options(category, rating DESC);
CREATE INDEX IF NOT EXISTS idx_activity_options_trip_category 
    ON activity_options(trip_id, category);

-- Index for external_id lookups (deduplication)
CREATE INDEX IF NOT EXISTS idx_activity_options_external_provider 
    ON activity_options(external_id, provider);

-- Partial indexes for optimization
CREATE INDEX IF NOT EXISTS idx_activity_options_high_rated 
    ON activity_options(rating DESC, review_count DESC) 
    WHERE rating >= 4.0;

CREATE INDEX IF NOT EXISTS idx_activity_options_recent 
    ON activity_options(created_at DESC) 
    WHERE created_at >= NOW() - INTERVAL '30 days';

-- Enable Row Level Security (RLS)
ALTER TABLE activity_options ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only access activities for their own trips
-- Note: This assumes trips table has user_id field for ownership
CREATE POLICY "Users can view their trip activities" ON activity_options
    FOR SELECT 
    USING (
        trip_id IN (
            SELECT trip_id FROM trips WHERE user_id = auth.uid()::UUID
        )
    );

CREATE POLICY "Users can insert activities for their trips" ON activity_options
    FOR INSERT 
    WITH CHECK (
        trip_id IN (
            SELECT trip_id FROM trips WHERE user_id = auth.uid()::UUID
        )
    );

CREATE POLICY "Users can update their trip activities" ON activity_options
    FOR UPDATE 
    USING (
        trip_id IN (
            SELECT trip_id FROM trips WHERE user_id = auth.uid()::UUID
        )
    );

CREATE POLICY "Users can delete their trip activities" ON activity_options
    FOR DELETE 
    USING (
        trip_id IN (
            SELECT trip_id FROM trips WHERE user_id = auth.uid()::UUID
        )
    );

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON activity_options TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Create view for activity statistics
CREATE OR REPLACE VIEW activity_stats AS
SELECT 
    category,
    COUNT(*) as total_activities,
    AVG(rating) as avg_rating,
    AVG(price) as avg_price,
    MIN(price) as min_price,
    MAX(price) as max_price,
    COUNT(DISTINCT provider) as provider_count
FROM activity_options
GROUP BY category;

-- Grant access to view
GRANT SELECT ON activity_stats TO authenticated;

-- Function for searching activities within radius using PostGIS
CREATE OR REPLACE FUNCTION search_activities_within_radius(
    center_lat FLOAT,
    center_lng FLOAT,
    radius_meters INT DEFAULT 25000, -- 25km default
    activity_category TEXT DEFAULT NULL,
    max_results INT DEFAULT 50
)
RETURNS TABLE (
    activity_id UUID,
    name VARCHAR(255),
    category activity_category,
    distance_meters FLOAT,
    rating DECIMAL(2,1),
    price DECIMAL(10,2),
    provider VARCHAR(50)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ao.activity_id,
        ao.name,
        ao.category,
        ST_Distance(
            ao.location_point,
            ST_SetSRID(ST_MakePoint(center_lng, center_lat), 4326)
        ) as distance_meters,
        ao.rating,
        ao.price,
        ao.provider
    FROM activity_options ao
    WHERE 
        ST_DWithin(
            ao.location_point,
            ST_SetSRID(ST_MakePoint(center_lng, center_lat), 4326),
            radius_meters
        )
        AND (activity_category IS NULL OR ao.category::TEXT = activity_category)
    ORDER BY distance_meters ASC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION search_activities_within_radius TO authenticated;
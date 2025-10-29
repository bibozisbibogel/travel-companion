-- Migration: Add geocoding support to itinerary_data JSON schema
-- Date: 2025-10-26
-- Story: 3.6 - Geocoding Integration for Precise Activity Location Mapping
--
-- This migration documents the enhanced JSON schema for itinerary_data
-- to include geocoded coordinates for all location-based entities.
--
-- Note: Since itinerary_data is JSONB, no ALTER TABLE is needed.
-- The schema is self-documenting and backward compatible.

-- =============================================================================
-- SCHEMA DOCUMENTATION
-- =============================================================================

COMMENT ON COLUMN trips.itinerary_data IS
'JSONB field storing the complete ItineraryOutput structure from TravelPlannerAgent.
Enhanced with geocoding coordinates for all locations.

Expected structure with geocoding:
{
  "destination_city": {
    "name": "Rome",
    "country": "Italy",
    "coordinates": {
      "latitude": 41.9028,
      "longitude": 12.4964,
      "geocoding_status": "success",
      "geocoded_at": "2025-10-26T14:30:00Z",
      "geocoding_error_message": null
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
        "geocoded_at": "2025-10-26T14:30:00Z",
        "geocoding_error_message": null
      },
      "description": "...",
      "category": "cultural",
      "estimated_duration_minutes": 60,
      "estimated_cost": 0.0,
      "booking_required": false
    }
  ],
  "accommodations": [
    {
      "name": "Hotel Quirinale",
      "location": "Via Nazionale, 7, Rome",
      "coordinates": {
        "latitude": 41.9010,
        "longitude": 12.4926,
        "geocoding_status": "success",
        "geocoded_at": "2025-10-26T14:30:00Z",
        "geocoding_error_message": null
      },
      "check_in_date": "2025-11-01",
      "check_out_date": "2025-11-05",
      "total_nights": 4,
      "room_type": "Double Room",
      "estimated_price_per_night": 150.00,
      "total_price": 600.00,
      "amenities": ["WiFi", "Breakfast"]
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
        "geocoding_status": "success",
        "geocoded_at": "2025-10-26T14:30:00Z",
        "geocoding_error_message": null
      },
      "cuisine": "Italian",
      "estimated_cost_per_person": 30.00,
      "total_cost": 60.00
    }
  ],
  "flights": {
    "outbound": {
      "departure_airport": "JFK",
      "departure_location": "New York, USA",
      "departure_coordinates": {
        "latitude": 40.6413,
        "longitude": -73.7781,
        "geocoding_status": "success",
        "geocoded_at": "2025-10-26T14:30:00Z"
      },
      "arrival_airport": "FCO",
      "arrival_location": "Rome, Italy",
      "arrival_coordinates": {
        "latitude": 41.8003,
        "longitude": 12.2389,
        "geocoding_status": "success",
        "geocoded_at": "2025-10-26T14:30:00Z"
      }
    },
    "return": { /* similar structure */ }
  }
}

Coordinate field specifications:
- latitude: DECIMAL(10, 8) range (-90 to 90)
- longitude: DECIMAL(11, 8) range (-180 to 180)
- geocoding_status: ENUM(''success'', ''failed'', ''pending'')
- geocoded_at: TIMESTAMP with timezone (ISO 8601 format)
- geocoding_error_message: TEXT (nullable, present only on errors)
';

-- =============================================================================
-- PERFORMANCE INDEXES
-- =============================================================================

-- Create GIN index on itinerary_data JSONB for faster queries
-- This enables efficient queries on geocoding_status, coordinates, etc.
CREATE INDEX IF NOT EXISTS idx_trips_itinerary_data_gin
    ON trips USING gin (itinerary_data);

-- Partial index for trips with geocoding failures (for monitoring)
CREATE INDEX IF NOT EXISTS idx_trips_geocoding_failures
    ON trips USING gin (itinerary_data)
    WHERE itinerary_data @> '{"activities": [{"coordinates": {"geocoding_status": "failed"}}]}';

-- Expression index for extracting destination coordinates (for map centering)
CREATE INDEX IF NOT EXISTS idx_trips_destination_coordinates
    ON trips ((itinerary_data->'destination_city'->'coordinates'->>'latitude'),
              (itinerary_data->'destination_city'->'coordinates'->>'longitude'));

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Function to extract all locations with failed geocoding from a trip
CREATE OR REPLACE FUNCTION get_geocoding_failures(trip_data JSONB)
RETURNS TABLE (
    location_type TEXT,
    location_name TEXT,
    location_address TEXT,
    error_message TEXT
) AS $$
BEGIN
    -- Extract failed geocoding from activities
    RETURN QUERY
    SELECT
        'activity'::TEXT,
        elem->>'name',
        elem->>'location',
        elem->'coordinates'->>'geocoding_error_message'
    FROM jsonb_array_elements(trip_data->'activities') AS elem
    WHERE (elem->'coordinates'->>'geocoding_status') = 'failed';

    -- Extract failed geocoding from accommodations
    RETURN QUERY
    SELECT
        'accommodation'::TEXT,
        elem->>'name',
        elem->>'location',
        elem->'coordinates'->>'geocoding_error_message'
    FROM jsonb_array_elements(trip_data->'accommodations') AS elem
    WHERE (elem->'coordinates'->>'geocoding_status') = 'failed';

    -- Extract failed geocoding from restaurants
    RETURN QUERY
    SELECT
        'restaurant'::TEXT,
        elem->>'name',
        elem->>'location',
        elem->'coordinates'->>'geocoding_error_message'
    FROM jsonb_array_elements(trip_data->'restaurants') AS elem
    WHERE (elem->'coordinates'->>'geocoding_status') = 'failed';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION get_geocoding_failures(JSONB) IS
'Extracts all locations with failed geocoding from trip itinerary data';

-- Function to count geocoding success rate for a trip
CREATE OR REPLACE FUNCTION calculate_geocoding_success_rate(trip_data JSONB)
RETURNS NUMERIC AS $$
DECLARE
    total_locations INTEGER := 0;
    successful_locations INTEGER := 0;
BEGIN
    -- Count activities
    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE (elem->'coordinates'->>'geocoding_status') = 'success')
    INTO total_locations, successful_locations
    FROM jsonb_array_elements(trip_data->'activities') AS elem;

    -- Count accommodations
    SELECT
        total_locations + COUNT(*),
        successful_locations + COUNT(*) FILTER (WHERE (elem->'coordinates'->>'geocoding_status') = 'success')
    INTO total_locations, successful_locations
    FROM jsonb_array_elements(trip_data->'accommodations') AS elem;

    -- Count restaurants
    SELECT
        total_locations + COUNT(*),
        successful_locations + COUNT(*) FILTER (WHERE (elem->'coordinates'->>'geocoding_status') = 'success')
    INTO total_locations, successful_locations
    FROM jsonb_array_elements(trip_data->'restaurants') AS elem;

    -- Calculate percentage
    IF total_locations = 0 THEN
        RETURN 0;
    END IF;

    RETURN ROUND((successful_locations::NUMERIC / total_locations::NUMERIC) * 100, 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION calculate_geocoding_success_rate(JSONB) IS
'Calculates the percentage of successfully geocoded locations in a trip (0-100)';

-- =============================================================================
-- EXAMPLE QUERIES
-- =============================================================================

-- Example 1: Find all trips with geocoding failures
-- SELECT trip_id, name,
--        get_geocoding_failures(itinerary_data)
-- FROM trips
-- WHERE itinerary_data @> '{"activities": [{"coordinates": {"geocoding_status": "failed"}}]}';

-- Example 2: Calculate geocoding success rate for a trip
-- SELECT trip_id, name,
--        calculate_geocoding_success_rate(itinerary_data) as success_rate_percent
-- FROM trips
-- WHERE trip_id = 'your-trip-id';

-- Example 3: Find all activities within a geographic bounding box (requires coordinates)
-- SELECT trip_id,
--        elem->>'name' as activity_name,
--        (elem->'coordinates'->>'latitude')::DECIMAL as lat,
--        (elem->'coordinates'->>'longitude')::DECIMAL as lng
-- FROM trips,
--      jsonb_array_elements(itinerary_data->'activities') AS elem
-- WHERE (elem->'coordinates'->>'latitude')::DECIMAL BETWEEN 41.8 AND 42.0
--   AND (elem->'coordinates'->>'longitude')::DECIMAL BETWEEN 12.4 AND 12.6;

-- Example 4: Get all trips with destination city coordinates
-- SELECT trip_id,
--        name,
--        itinerary_data->'destination_city'->>'name' as city,
--        (itinerary_data->'destination_city'->'coordinates'->>'latitude')::DECIMAL as lat,
--        (itinerary_data->'destination_city'->'coordinates'->>'longitude')::DECIMAL as lng
-- FROM trips
-- WHERE itinerary_data->'destination_city'->'coordinates' IS NOT NULL;

-- =============================================================================
-- ROLLBACK (if needed)
-- =============================================================================

-- To remove the indexes:
-- DROP INDEX IF EXISTS idx_trips_itinerary_data_gin;
-- DROP INDEX IF EXISTS idx_trips_geocoding_failures;
-- DROP INDEX IF EXISTS idx_trips_destination_coordinates;

-- To remove helper functions:
-- DROP FUNCTION IF EXISTS get_geocoding_failures(JSONB);
-- DROP FUNCTION IF EXISTS calculate_geocoding_success_rate(JSONB);

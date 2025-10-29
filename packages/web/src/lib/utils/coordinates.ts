/**
 * Coordinate utility functions for handling geocoding failures and fallback logic
 */

import type { Location } from "@/lib/types/map";

interface CoordinateFallbackOptions {
  defaultCenter?: { lat: number; lng: number };
  offsetRadius?: number; // In degrees (approx 0.01 = ~1km)
}

/**
 * Get coordinates with fallback behavior for failed geocoding
 *
 * If geocoding failed, returns the destination center coordinates.
 * If no destination center is provided, returns a default (0, 0).
 *
 * @param location - Location object that may have failed geocoding
 * @param options - Fallback options including default center
 * @returns Coordinates to use for marker placement
 */
export function getCoordinatesWithFallback(
  location: Location,
  options: CoordinateFallbackOptions = {}
): { lat: number; lng: number } {
  const { defaultCenter = { lat: 0, lng: 0 } } = options;

  // If geocoding succeeded or status is not set, use the coordinates
  if (!location.geocoding_status || location.geocoding_status === 'success') {
    return {
      lat: location.latitude,
      lng: location.longitude,
    };
  }

  // If geocoding failed, use the default center (destination city)
  if (location.geocoding_status === 'failed') {
    return defaultCenter;
  }

  // If geocoding is pending, also use default center
  return defaultCenter;
}

/**
 * Check if a location has valid geocoded coordinates
 *
 * @param location - Location object to check
 * @returns true if location has successfully geocoded coordinates
 */
export function hasValidCoordinates(location: Location): boolean {
  if (!location.geocoding_status || location.geocoding_status === 'success') {
    return isValidLatLng(location.latitude, location.longitude);
  }
  return false;
}

/**
 * Validate that latitude and longitude are within valid ranges
 *
 * @param lat - Latitude value
 * @param lng - Longitude value
 * @returns true if coordinates are valid
 */
export function isValidLatLng(lat: number, lng: number): boolean {
  return (
    typeof lat === 'number' &&
    typeof lng === 'number' &&
    !isNaN(lat) &&
    !isNaN(lng) &&
    lat >= -90 &&
    lat <= 90 &&
    lng >= -180 &&
    lng <= 180
  );
}

/**
 * Calculate distance between two coordinates using Haversine formula
 *
 * @param coord1 - First coordinate
 * @param coord2 - Second coordinate
 * @returns Distance in kilometers
 */
export function calculateDistance(
  coord1: { lat: number; lng: number },
  coord2: { lat: number; lng: number }
): number {
  const R = 6371; // Earth's radius in kilometers
  const dLat = toRadians(coord2.lat - coord1.lat);
  const dLng = toRadians(coord2.lng - coord1.lng);

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRadians(coord1.lat)) *
      Math.cos(toRadians(coord2.lat)) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Convert degrees to radians
 */
function toRadians(degrees: number): number {
  return degrees * (Math.PI / 180);
}

/**
 * Map component types and interfaces for interactive trip visualization
 */

export interface Location {
  latitude: number;
  longitude: number;
  address?: string;
  place_id?: string;
  geocoding_status?: 'success' | 'failed' | 'pending';
  geocoded_at?: string | null;
  geocoding_error_message?: string | null;
}

export type ActivityCategory =
  | "adventure"
  | "cultural"
  | "relaxation"
  | "dining"
  | "nightlife"
  | "shopping";

export type TransportMode = "walk" | "drive" | "transit";

export interface ActivityMarker {
  activity_id: string;
  name: string;
  category: ActivityCategory;
  location: Location;
  time: string;
  duration: number;
  description: string;
  day: number;
}

export interface AccommodationMarker {
  hotel_id: string;
  name: string;
  location: Location;
  rating: number;
  price_per_night: number;
  address?: string;
  contact?: string;
}

export interface RouteSegment {
  origin: Location;
  destination: Location;
  distance: number;
  duration: number;
  mode: TransportMode;
}

export interface DayRoute {
  day: number;
  segments: RouteSegment[];
  totalDistance: number;
  totalDuration: number;
}

export type MapStyle = "standard" | "satellite" | "terrain";

export interface MapConfig {
  apiKey: string;
  defaultZoom: number;
  minZoom: number;
  maxZoom: number;
  gestureHandling: "cooperative" | "greedy" | "none" | "auto";
}

export const CATEGORY_COLORS: Record<ActivityCategory, string> = {
  adventure: "#3B82F6",
  cultural: "#8B5CF6",
  relaxation: "#10B981",
  dining: "#F59E0B",
  nightlife: "#EC4899",
  shopping: "#14B8A6",
};

export const ACCOMMODATION_COLOR = "#EF4444";

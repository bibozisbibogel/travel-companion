/**
 * Trip Detail Page - Day-by-Day Itinerary Timeline Visualization
 * Story 3.2: Day-by-Day Itinerary Timeline Visualization
 * Story 3.5: Migrated from /app/itinerary to dynamic route
 */

'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import { ItineraryTimeline } from '@/components/itinerary';
import { IFullTripItinerary } from '@/lib/types';
import { apiClient } from '@/lib/api';
import { Loader2, AlertCircle } from 'lucide-react';
import { MainLayout } from '@/components/layouts';
import { LazyMapLoader } from '@/components/maps';
import { MapTimelineProvider } from '@/contexts/MapTimelineContext';
import type { ActivityMarker, AccommodationMarker, DayRoute } from '@/lib/types/map';

/**
 * City coordinates mapping for common destinations
 * TODO: Replace with proper geocoding API (Google Geocoding API or similar)
 */
const CITY_COORDINATES: Record<string, { lat: number; lng: number }> = {
  'New York City': { lat: 40.7128, lng: -74.0060 },
  'New York': { lat: 40.7128, lng: -74.0060 },
  'Rome': { lat: 41.9028, lng: 12.4964 },
  'Paris': { lat: 48.8566, lng: 2.3522 },
  'London': { lat: 51.5074, lng: -0.1278 },
  'Tokyo': { lat: 35.6762, lng: 139.6503 },
  'Barcelona': { lat: 41.3851, lng: 2.1734 },
  'Amsterdam': { lat: 52.3676, lng: 4.9041 },
  'Berlin': { lat: 52.5200, lng: 13.4050 },
  'Dubai': { lat: 25.2048, lng: 55.2708 },
  'Singapore': { lat: 1.3521, lng: 103.8198 },
  'Sydney': { lat: -33.8688, lng: 151.2093 },
  'Los Angeles': { lat: 34.0522, lng: -118.2437 },
  'Miami': { lat: 25.7617, lng: -80.1918 },
  'Bangkok': { lat: 13.7563, lng: 100.5018 },
};

/**
 * Transform itinerary data to map marker format
 *
 * Uses geocoded coordinates from the API response for precise location mapping.
 * Falls back to city center coordinates if geocoding failed or is unavailable.
 */
function transformItineraryToMapData(itinerary: IFullTripItinerary) {
  const activities: ActivityMarker[] = [];
  const accommodations: AccommodationMarker[] = [];
  const routes: DayRoute[] = [];

  // Get destination city coordinates from geocoded data or fallback to hardcoded
  const destinationCity = itinerary.trip.destination.city;
  const geocodedCoords = itinerary.trip.destination.coordinates;

  // Use geocoded coordinates if available and successful, otherwise fallback
  const cityCoords = (geocodedCoords && geocodedCoords.geocoding_status === 'success')
    ? { lat: geocodedCoords.latitude, lng: geocodedCoords.longitude }
    : CITY_COORDINATES[destinationCity] || { lat: 40.7128, lng: -74.0060 }; // Default to NYC

  console.log(`Map using coordinates for: ${destinationCity}`, cityCoords,
              geocodedCoords ? `(geocoded: ${geocodedCoords.geocoding_status})` : '(fallback)');

  // Transform activities from each day
  itinerary.itinerary.forEach((dayPlan) => {
    dayPlan.activities.forEach((activity, index) => {
      // Only add activities with location data
      if (activity.location || activity.title) {
        const activityLocation = activity.location ||
                                `${destinationCity}, ${itinerary.trip.destination.country}`;

        // Use geocoded coordinates if available and successful, otherwise fallback to city center
        const activityCoords = activity.coordinates;
        let latitude: number;
        let longitude: number;

        if (activityCoords && activityCoords.geocoding_status === 'success') {
          // Use precise geocoded coordinates
          latitude = activityCoords.latitude;
          longitude = activityCoords.longitude;
        } else {
          // Fallback: spread activities around city center with small random offset
          const latOffset = (Math.random() - 0.5) * 0.02; // ~1km radius
          const lngOffset = (Math.random() - 0.5) * 0.02;
          latitude = cityCoords.lat + latOffset;
          longitude = cityCoords.lng + lngOffset;
        }

        activities.push({
          activity_id: `${dayPlan.day}-${index}`,
          name: activity.title,
          category: activity.category,
          location: {
            latitude,
            longitude,
            address: activityLocation,
          },
          time: activity.time_start || '00:00',
          duration: activity.duration_minutes || 60,
          description: activity.description || '',
          day: dayPlan.day,
        });
      }
    });
  });

  // Add accommodation marker
  if (itinerary.accommodation) {
    const accommodationCoords = itinerary.accommodation.coordinates;

    // Use geocoded coordinates if available, otherwise fallback to city center
    let latitude: number;
    let longitude: number;

    if (accommodationCoords && accommodationCoords.geocoding_status === 'success') {
      latitude = accommodationCoords.latitude;
      longitude = accommodationCoords.longitude;
    } else {
      // Fallback to city center
      latitude = cityCoords.lat;
      longitude = cityCoords.lng;
    }

    accommodations.push({
      hotel_id: 'main-hotel',
      name: itinerary.accommodation.name,
      location: {
        latitude,
        longitude,
        address: `${itinerary.accommodation.address.street}, ${itinerary.accommodation.address.city}`,
      },
      rating: itinerary.accommodation.rating,
      price_per_night: parseFloat(itinerary.accommodation.price_per_night),
      address: `${itinerary.accommodation.address.street}, ${itinerary.accommodation.address.postal_code}`,
    });
  }

  // Calculate trip center (use destination city coordinates)
  const tripCenter = { lat: cityCoords.lat, lng: cityCoords.lng };

  return { activities, accommodations, routes, tripCenter };
}

export default function TripDetailPage() {
  const params = useParams();
  const tripId = params.trip_id as string;
  const [itinerary, setItinerary] = useState<IFullTripItinerary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Transform itinerary data for map visualization
  const mapData = useMemo(() => {
    if (!itinerary) return null;
    return transformItineraryToMapData(itinerary);
  }, [itinerary]);

  useEffect(() => {
    const loadItinerary = async () => {
      try {
        setLoading(true);
        console.log('Loading trip details for:', tripId);

        // Fetch trip details from API
        const response = await apiClient.getTripById(tripId);

        // Extract the trip data from the SuccessResponse wrapper
        const tripData = response.data;

        // If the trip has a plan, use it
        if (tripData?.plan) {
          setItinerary(tripData.plan);
        } else {
          // No plan available yet - trip might be in draft status
          throw new Error('Trip has no itinerary plan yet. Please complete trip planning first.');
        }
      } catch (err) {
        console.error('Failed to load trip:', err);
        setError(err instanceof Error ? err.message : 'Failed to load trip details');
      } finally {
        setLoading(false);
      }
    };

    if (tripId) {
      loadItinerary();
    }
  }, [tripId]);

  if (loading) {
    return (
      <MainLayout className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading your itinerary...</p>
        </div>
      </MainLayout>
    );
  }

  if (error) {
    return (
      <MainLayout className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 mb-2 text-center">
            Error Loading Itinerary
          </h2>
          <p className="text-gray-600 text-center">{error}</p>
        </div>
      </MainLayout>
    );
  }

  if (!itinerary) {
    return (
      <MainLayout className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-600">No itinerary data available</p>
      </MainLayout>
    );
  }

  return (
    <MapTimelineProvider>
      <MainLayout className="min-h-screen bg-gray-50">
        <div className="container mx-auto px-4 py-8">
          {/* Map Section */}
          {mapData && (
            <div className="mb-8 h-[500px] rounded-lg overflow-hidden shadow-lg">
              <LazyMapLoader
                activities={mapData.activities}
                accommodations={mapData.accommodations}
                routes={mapData.routes}
                tripCenter={mapData.tripCenter}
              />
            </div>
          )}

          {/* Timeline Section */}
          <ItineraryTimeline itinerary={itinerary} />
        </div>
      </MainLayout>
    </MapTimelineProvider>
  );
}

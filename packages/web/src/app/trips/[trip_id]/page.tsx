/**
 * Trip Detail Page - Day-by-Day Itinerary Timeline Visualization
 * Story 3.2: Day-by-Day Itinerary Timeline Visualization
 * Story 3.5: Migrated from /app/itinerary to dynamic route
 */

'use client';

import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { ItineraryTimeline } from '@/components/itinerary';
import { IFullTripItinerary } from '@/lib/types';
import { apiClient } from '@/lib/api';
import { Loader2, AlertCircle } from 'lucide-react';
import { MainLayout } from '@/components/layouts';
import { LazyMapLoader } from '@/components/maps';
import { MapTimelineProvider, useMapTimeline } from '@/contexts/MapTimelineContext';
import { transformItineraryResponse } from '@/lib/itineraryUtils';
import type { ActivityMarker, AccommodationMarker, DayRoute } from '@/lib/types/map';
import { fetchDayRoute, type RoutePolyline } from '@/lib/geoapifyRouting';

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

// Inner component that has access to MapTimelineContext
function TripDetailContent({ tripId }: { tripId: string }) {
  const [itinerary, setItinerary] = useState<IFullTripItinerary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentDayNumber, setCurrentDayNumber] = useState<number | null>(1); // null = all days view
  const [routePolylines, setRoutePolylines] = useState<RoutePolyline[]>([]);
  const [loadingRoutes, setLoadingRoutes] = useState(false);
  // Cache routes by day number to avoid refetching when switching between days
  const [routeCache, setRouteCache] = useState<Record<number, RoutePolyline>>({});

  // Get selectedDay from MapTimelineContext
  const { selectedDay } = useMapTimeline();

  // Sync selectedDay from context with currentDayNumber for route fetching
  useEffect(() => {
    console.log(`🔗 [page.tsx] MapTimeline selectedDay changed to: ${selectedDay}`);
    setCurrentDayNumber(selectedDay);
  }, [selectedDay]);

  // Log routePolylines changes
  useEffect(() => {
    console.log(`🛣️ [page.tsx] routePolylines STATE changed:`, routePolylines.length, 'routes');
    if (routePolylines.length > 0) {
      routePolylines.forEach((route, idx) => {
        console.log(`  Route ${idx}: ${route.coordinates.length} coords, ${(route.distance / 1000).toFixed(1)}km`);
      });
    }
  }, [routePolylines]);

  // Log currentDayNumber changes
  useEffect(() => {
    console.log(`🎯 [page.tsx] currentDayNumber STATE: ${currentDayNumber}`);
  }, [currentDayNumber]);

  // Handle day change from ItineraryTimeline - memoized to prevent infinite loops
  const handleDayChange = useCallback((dayNumber: number | null) => {
    console.log(`🔄 [page.tsx] handleDayChange CALLED with: ${dayNumber}`);
    console.log(`🔄 [page.tsx] About to call setCurrentDayNumber(${dayNumber})`);
    setCurrentDayNumber(dayNumber);
  }, []);

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
          // Transform the backend response to match frontend expectations
          // This extracts meals from dining activities and distributes accommodation per day
          const transformedPlan = transformItineraryResponse(tripData.plan);
          setItinerary(transformedPlan);
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

  // Fetch routes for the currently selected day
  useEffect(() => {
    const fetchRoutesForDay = async () => {
      console.log(`🗺️ [page.tsx] fetchRoutesForDay EFFECT FIRED`);
      console.log(`🗺️ [page.tsx] currentDayNumber: ${currentDayNumber}`);
      console.log(`🗺️ [page.tsx] mapData exists: ${!!mapData}`);
      console.log(`🗺️ [page.tsx] routeCache:`, routeCache);

      if (!mapData || !currentDayNumber) {
        // No specific day selected (all days view) - clear routes
        console.log('🗺️ [page.tsx] No day selected or no mapData - clearing routes');
        setRoutePolylines([]);
        return;
      }

      // ALWAYS clear routes first before fetching/setting new ones
      console.log(`🧹 [page.tsx] Clearing existing routes before Day ${currentDayNumber}`);
      setRoutePolylines([]);

      // Small delay to ensure clearing is processed
      await new Promise(resolve => setTimeout(resolve, 10));

      // Check cache first
      if (routeCache[currentDayNumber]) {
        console.log(`✅ [page.tsx] Using cached route for Day ${currentDayNumber}`);
        const cachedRoute = routeCache[currentDayNumber];
        console.log(`✅ [page.tsx] Setting single cached route: ${cachedRoute.coordinates.length} coords`);
        setRoutePolylines([cachedRoute]);
        return;
      }

      setLoadingRoutes(true);
      console.log(`📍 Fetching NEW route for Day ${currentDayNumber}`);

      try {
        // Get activities for the current day
        const dayActivities = mapData.activities.filter(
          activity => activity.day === currentDayNumber
        );

        console.log(`Day ${currentDayNumber}: Found ${dayActivities.length} activities`,
          dayActivities.map(a => ({ name: a.name, time: a.time, day: a.day }))
        );

        if (dayActivities.length === 0) {
          console.log(`❌ Day ${currentDayNumber}: No activities found`);
          setRoutePolylines([]);
          return;
        }

        // Sort activities by time
        const sortedActivities = dayActivities.sort((a, b) => {
          return a.time.localeCompare(b.time);
        });

        // Create waypoints from activities with detailed logging
        const locations = sortedActivities.map((activity, idx) => {
          const coord = {
            latitude: activity.location.latitude,
            longitude: activity.location.longitude
          };
          console.log(`  📍 Waypoint ${idx + 1}: ${activity.name} at [${coord.latitude}, ${coord.longitude}]`);
          return coord;
        });

        console.log(`Day ${currentDayNumber}: Activity waypoints summary:`, locations);

        // Add accommodation at the start and end if available
        // But only if no activities are already at the accommodation location
        if (mapData.accommodations.length > 0) {
          const accommodation = mapData.accommodations[0]!;
          const accommodationLocation = {
            latitude: accommodation.location.latitude,
            longitude: accommodation.location.longitude
          };

          // Check if any activity is already at accommodation location (within 50 meters)
          const hasActivityAtAccommodation = locations.some(loc => {
            const distance = Math.sqrt(
              Math.pow((loc.latitude - accommodationLocation.latitude) * 111000, 2) +
              Math.pow((loc.longitude - accommodationLocation.longitude) * 85000, 2)
            );
            return distance < 50; // 50 meter threshold
          });

          if (hasActivityAtAccommodation) {
            console.log(`Day ${currentDayNumber}: Activity already at accommodation, not adding duplicate waypoints`);
          } else {
            locations.unshift(accommodationLocation);
            locations.push(accommodationLocation);
            console.log(`Day ${currentDayNumber}: Added accommodation at start and end`, accommodationLocation);
          }
        }

        console.log(`Day ${currentDayNumber}: Total waypoints (with accommodation): ${locations.length}`);

        // Fetch route for the day
        if (locations.length >= 2) {
          const route = await fetchDayRoute(locations, 'walk');
          if (route) {
            console.log(`✅ Day ${currentDayNumber}: Route fetched - ${route.coordinates.length} coords, ${route.distance}m`);
            console.log(`✅ Day ${currentDayNumber}: Setting SINGLE newly fetched route`);
            console.log(`✅ Day ${currentDayNumber}: Route details - distance: ${route.distance}m, coords: ${route.coordinates.length}`);
            setRoutePolylines([route]);
            // Cache the route
            setRouteCache(prev => ({ ...prev, [currentDayNumber]: route }));
          } else {
            console.warn(`❌ Day ${currentDayNumber}: Failed to fetch route`);
            setRoutePolylines([]);
          }
        }
      } catch (err) {
        console.error(`❌ Day ${currentDayNumber}: Error fetching routes:`, err);
        setRoutePolylines([]);
      } finally {
        setLoadingRoutes(false);
      }
    };

    fetchRoutesForDay();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentDayNumber, mapData]);

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
    <MainLayout className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Map Section - Overview with Routes for Current Day */}
        {mapData && (
          <div className="mb-8">
            <div className="mb-2">
              <h2 className="text-xl font-semibold text-gray-900">
                {(() => {
                  console.log(`📺 [page.tsx] RENDERING map title with currentDayNumber: ${currentDayNumber}`);
                  return currentDayNumber ? `Day ${currentDayNumber} Route Map` : 'Trip Overview Map';
                })()}
              </h2>
              <p className="text-sm text-gray-600">
                {currentDayNumber
                  ? `Showing route for Day ${currentDayNumber} activities`
                  : 'All activities across all days'}
              </p>
              {loadingRoutes && (
                <div className="flex items-center gap-2 text-sm text-blue-600 mt-1">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Loading route...</span>
                </div>
              )}
              {!loadingRoutes && routePolylines.length > 0 && routePolylines[0] && (
                <div className="flex items-center gap-2 text-sm text-green-600 mt-1">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span>Route loaded ({(routePolylines[0].distance / 1000).toFixed(1)} km)</span>
                </div>
              )}
            </div>
            <div className="h-[500px] rounded-lg overflow-hidden shadow-lg">
              <LazyMapLoader
                activities={mapData.activities}
                accommodations={mapData.accommodations}
                routes={mapData.routes}
                tripCenter={mapData.tripCenter}
                routePolylines={routePolylines}
              />
            </div>
          </div>
        )}

        {/* Timeline Section */}
        <ItineraryTimeline
          itinerary={itinerary}
          onDayChange={handleDayChange}
        />
      </div>
    </MainLayout>
  );
}

// Outer component that provides MapTimelineContext
export default function TripDetailPage() {
  const params = useParams();
  const tripId = params.trip_id as string;

  return (
    <MapTimelineProvider>
      <TripDetailContent tripId={tripId} />
    </MapTimelineProvider>
  );
}

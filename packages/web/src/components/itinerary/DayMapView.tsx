/**
 * DayMapView Component
 * Displays a map for a single day with routes between activities
 */

'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { LazyMapLoader } from '@/components/maps';
import { Loader2 } from 'lucide-react';
import { fetchDayRoute, type RoutePolyline } from '@/lib/geoapifyRouting';
import type { ActivityMarker, AccommodationMarker } from '@/lib/types/map';
import { IActivity, IAccommodation } from '@/lib/types';

interface DayMapViewProps {
  dayNumber: number;
  activities: IActivity[];
  accommodation?: IAccommodation;
  destinationCoords: { lat: number; lng: number };
}

/**
 * Transform activities to map markers
 */
function transformActivitiesToMarkers(
  activities: IActivity[],
  dayNumber: number,
  destinationCoords: { lat: number; lng: number }
): ActivityMarker[] {
  return activities.map((activity, index) => {
    const activityCoords = activity.coordinates;
    let latitude: number;
    let longitude: number;

    if (activityCoords && activityCoords.geocoding_status === 'success') {
      latitude = activityCoords.latitude;
      longitude = activityCoords.longitude;
    } else {
      // Fallback: spread activities around destination center
      const latOffset = (Math.random() - 0.5) * 0.02;
      const lngOffset = (Math.random() - 0.5) * 0.02;
      latitude = destinationCoords.lat + latOffset;
      longitude = destinationCoords.lng + lngOffset;
    }

    return {
      activity_id: `day${dayNumber}-${index}`,
      name: activity.title,
      category: activity.category,
      location: {
        latitude,
        longitude,
        address: activity.location || '',
      },
      time: activity.time_start || '00:00',
      duration: activity.duration_minutes || 60,
      description: activity.description || '',
      day: dayNumber,
    };
  });
}

/**
 * Transform accommodation to map marker
 */
function transformAccommodationToMarker(
  accommodation: IAccommodation,
  destinationCoords: { lat: number; lng: number }
): AccommodationMarker {
  const accommodationCoords = accommodation.coordinates;
  let latitude: number;
  let longitude: number;

  if (accommodationCoords && accommodationCoords.geocoding_status === 'success') {
    latitude = accommodationCoords.latitude;
    longitude = accommodationCoords.longitude;
  } else {
    latitude = destinationCoords.lat;
    longitude = destinationCoords.lng;
  }

  return {
    hotel_id: 'day-hotel',
    name: accommodation.name,
    location: {
      latitude,
      longitude,
      address: `${accommodation.address.street}, ${accommodation.address.city}`,
    },
    rating: accommodation.rating,
    price_per_night: parseFloat(accommodation.price_per_night),
    address: `${accommodation.address.street}, ${accommodation.address.postal_code}`,
  };
}

export const DayMapView: React.FC<DayMapViewProps> = ({
  dayNumber,
  activities,
  accommodation,
  destinationCoords,
}) => {
  const [routePolylines, setRoutePolylines] = useState<RoutePolyline[]>([]);
  const [loadingRoutes, setLoadingRoutes] = useState(false);

  console.log(`DayMapView for Day ${dayNumber} rendering:`, {
    activitiesCount: activities.length,
    hasAccommodation: !!accommodation,
    destinationCoords
  });

  // Transform data to map format
  const mapData = useMemo(() => {
    const activityMarkers = transformActivitiesToMarkers(
      activities,
      dayNumber,
      destinationCoords
    );

    const accommodationMarkers = accommodation
      ? [transformAccommodationToMarker(accommodation, destinationCoords)]
      : [];

    return {
      activities: activityMarkers,
      accommodations: accommodationMarkers,
      routes: [],
      tripCenter: destinationCoords,
    };
  }, [activities, accommodation, dayNumber, destinationCoords]);

  // Fetch routes for this day
  useEffect(() => {
    const fetchRoutes = async () => {
      if (mapData.activities.length === 0) {
        return;
      }

      setLoadingRoutes(true);
      console.log(`Day ${dayNumber}: Fetching route with ${mapData.activities.length} activities`);

      try {
        // Sort activities by time
        const sortedActivities = [...mapData.activities].sort((a, b) => {
          return a.time.localeCompare(b.time);
        });

        // Create waypoints from activities
        const locations = sortedActivities.map(activity => ({
          latitude: activity.location.latitude,
          longitude: activity.location.longitude
        }));

        // Add accommodation at the start and end if available
        if (mapData.accommodations.length > 0) {
          const accommodationLocation = {
            latitude: mapData.accommodations[0].location.latitude,
            longitude: mapData.accommodations[0].location.longitude
          };
          locations.unshift(accommodationLocation);
          locations.push(accommodationLocation);
          console.log(`Day ${dayNumber}: Added accommodation at start and end`);
        }

        console.log(`Day ${dayNumber}: Fetching route with ${locations.length} waypoints`);

        // Fetch route for the day
        if (locations.length >= 2) {
          const route = await fetchDayRoute(locations, 'walk');
          if (route) {
            console.log(`Day ${dayNumber}: Route fetched - ${route.coordinates.length} coordinates, ${route.distance}m`);
            setRoutePolylines([route]);
          } else {
            console.warn(`Day ${dayNumber}: Failed to fetch route`);
          }
        }
      } catch (err) {
        console.error(`Day ${dayNumber}: Failed to fetch routes:`, err);
      } finally {
        setLoadingRoutes(false);
      }
    };

    fetchRoutes();
  }, [mapData, dayNumber]);

  return (
    <div className="mt-4">
      <div className="mb-2">
        <h4 className="text-lg font-semibold text-gray-800">Day {dayNumber} Map</h4>
        {loadingRoutes && (
          <div className="flex items-center gap-2 text-sm text-blue-600">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Loading route...</span>
          </div>
        )}
        {!loadingRoutes && routePolylines.length > 0 && (
          <div className="flex items-center gap-2 text-sm text-green-600">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span>Route loaded ({(routePolylines[0].distance / 1000).toFixed(1)} km)</span>
          </div>
        )}
      </div>
      <div className="h-[400px] rounded-lg overflow-hidden shadow-lg border border-gray-200">
        <LazyMapLoader
          activities={mapData.activities}
          accommodations={mapData.accommodations}
          routes={mapData.routes}
          tripCenter={mapData.tripCenter}
          routePolylines={routePolylines}
        />
      </div>
    </div>
  );
};

export default DayMapView;

"use client";

import { useEffect, useState, useMemo, useRef } from "react";
import { DirectionsRenderer } from "@react-google-maps/api";
import type { DayRoute, TransportMode } from "@/lib/types/map";

interface RouteVisualizationProps {
  routes: DayRoute[];
  selectedDay: number | null;
  map: google.maps.Map | null;
}

// Route cache to avoid redundant API calls
const routeCache = new Map<string, google.maps.DirectionsResult>();

const DAY_ROUTE_COLORS = [
  "#3B82F6", // Blue
  "#8B5CF6", // Purple
  "#10B981", // Green
  "#F59E0B", // Orange
  "#EC4899", // Pink
  "#14B8A6", // Teal
  "#EF4444", // Red
  "#6366F1", // Indigo
  "#A855F7", // Violet
  "#06B6D4", // Cyan
];

const TRANSPORT_ICONS: Record<TransportMode, string> = {
  walk: "🚶",
  drive: "🚗",
  transit: "🚌",
};

export function RouteVisualization({
  routes,
  selectedDay,
  map,
}: RouteVisualizationProps) {
  const [directionsResults, setDirectionsResults] = useState<
    Map<number, google.maps.DirectionsResult>
  >(new Map());
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  const filteredRoutes = useMemo(() => {
    if (selectedDay === null) return routes;
    return routes.filter((route) => route.day === selectedDay);
  }, [routes, selectedDay]);

  useEffect(() => {
    if (!map || filteredRoutes.length === 0) return;

    // Debounce route fetching to avoid excessive API calls
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      const directionsService = new google.maps.DirectionsService();
      const newResults = new Map<number, google.maps.DirectionsResult>();

      const fetchRoutes = async () => {
        for (const dayRoute of filteredRoutes) {
          if (dayRoute.segments.length === 0) continue;

          // Create cache key based on route segments
          const cacheKey = `${dayRoute.day}-${dayRoute.segments.map((s) => `${s.origin.latitude},${s.origin.longitude}-${s.destination.latitude},${s.destination.longitude}`).join("|")}`;

          // Check cache first
          const cachedResult = routeCache.get(cacheKey);
          if (cachedResult) {
            newResults.set(dayRoute.day, cachedResult);
            continue;
          }

        const waypoints = dayRoute.segments.slice(1, -1).map((segment) => ({
          location: {
            lat: segment.origin.latitude,
            lng: segment.origin.longitude,
          },
          stopover: true,
        }));

        const origin = {
          lat: dayRoute.segments[0].origin.latitude,
          lng: dayRoute.segments[0].origin.longitude,
        };

        const destination = {
          lat: dayRoute.segments[dayRoute.segments.length - 1].destination
            .latitude,
          lng: dayRoute.segments[dayRoute.segments.length - 1].destination
            .longitude,
        };

        // Determine most common transport mode
        const modeCount: Record<TransportMode, number> = {
          walk: 0,
          drive: 0,
          transit: 0,
        };
        dayRoute.segments.forEach((segment) => {
          modeCount[segment.mode]++;
        });
        const travelMode = Object.entries(modeCount).sort(
          ([, a], [, b]) => b - a
        )[0][0] as TransportMode;

        const travelModeMap: Record<
          TransportMode,
          google.maps.TravelMode
        > = {
          walk: google.maps.TravelMode.WALKING,
          drive: google.maps.TravelMode.DRIVING,
          transit: google.maps.TravelMode.TRANSIT,
        };

          try {
            const result = await directionsService.route({
              origin,
              destination,
              waypoints,
              travelMode: travelModeMap[travelMode],
              optimizeWaypoints: false,
            });

            // Cache the result
            routeCache.set(cacheKey, result);
            newResults.set(dayRoute.day, result);
          } catch (error) {
            console.error(`Error fetching route for day ${dayRoute.day}:`, error);
          }
        }

        setDirectionsResults(newResults);
      };

      fetchRoutes();
    }, 300); // 300ms debounce delay

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [filteredRoutes, map]);

  return (
    <>
      {Array.from(directionsResults.entries()).map(([day, result]) => {
        const colorIndex = (day - 1) % DAY_ROUTE_COLORS.length;
        const color = DAY_ROUTE_COLORS[colorIndex];

        return (
          <DirectionsRenderer
            key={`route-day-${day}`}
            directions={result}
            options={{
              suppressMarkers: true, // We use custom markers
              polylineOptions: {
                strokeColor: color,
                strokeWeight: 4,
                strokeOpacity: 0.7,
              },
            }}
          />
        );
      })}
    </>
  );
}

interface RouteInfoProps {
  routes: DayRoute[];
  selectedDay: number | null;
}

export function RouteInfo({ routes, selectedDay }: RouteInfoProps) {
  const displayRoutes = useMemo(() => {
    if (selectedDay === null) return routes;
    return routes.filter((route) => route.day === selectedDay);
  }, [routes, selectedDay]);

  const formatDistance = (meters: number): string => {
    if (meters < 1000) return `${meters}m`;
    return `${(meters / 1000).toFixed(1)}km`;
  };

  const formatDuration = (minutes: number): string => {
    if (minutes < 60) return `${minutes}min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}min` : `${hours}h`;
  };

  if (displayRoutes.length === 0) return null;

  return (
    <div className="rounded-lg bg-white p-4 shadow-md">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">
        Travel Information
      </h3>
      <div className="space-y-2">
        {displayRoutes.map((route) => (
          <div
            key={route.day}
            className="rounded border border-gray-200 p-2 text-sm"
          >
            <div className="font-medium text-gray-900">Day {route.day}</div>
            <div className="mt-1 flex items-center gap-4 text-xs text-gray-600">
              <span>📏 {formatDistance(route.totalDistance)}</span>
              <span>⏱️ {formatDuration(route.totalDuration)}</span>
            </div>
            <div className="mt-1 flex gap-1">
              {Array.from(
                new Set(route.segments.map((s) => s.mode))
              ).map((mode) => (
                <span key={mode} className="text-base">
                  {TRANSPORT_ICONS[mode]}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

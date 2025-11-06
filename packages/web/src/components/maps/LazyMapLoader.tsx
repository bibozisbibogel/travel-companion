"use client";

import { lazy, Suspense } from "react";
import type {
  ActivityMarker,
  AccommodationMarker,
  DayRoute,
} from "@/lib/types/map";
import type { RoutePolyline } from "@/lib/geoapifyRouting";

// Lazy load the map component to reduce initial bundle size
const TripMapView = lazy(() =>
  import("./TripMapView").then((module) => ({ default: module.TripMapView }))
);

interface LazyMapLoaderProps {
  activities: ActivityMarker[];
  accommodations: AccommodationMarker[];
  routes: DayRoute[];
  tripCenter?: { lat: number; lng: number };
  routePolylines?: RoutePolyline[];
}

function MapLoadingFallback() {
  return (
    <div className="flex h-full items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-blue-500 border-r-transparent"></div>
        <p className="mt-4 text-gray-600">Loading map...</p>
      </div>
    </div>
  );
}

export function LazyMapLoader({
  activities,
  accommodations,
  routes,
  tripCenter,
  routePolylines,
}: LazyMapLoaderProps) {
  return (
    <Suspense fallback={<MapLoadingFallback />}>
      <TripMapView
        activities={activities}
        accommodations={accommodations}
        routes={routes}
        tripCenter={tripCenter}
        routePolylines={routePolylines}
      />
    </Suspense>
  );
}

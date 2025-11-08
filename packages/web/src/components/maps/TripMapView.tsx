"use client";

import { useEffect, useMemo } from "react";
import { InteractiveMap } from "./InteractiveMap";
import type { RoutePolyline } from "@/lib/geoapifyRouting";
import { DaySelector } from "./DaySelector";
import { MapLegend } from "./MapLegend";
import { ActivityMarker } from "./ActivityMarker";
import { AccommodationMarker } from "./AccommodationMarker";
import { RouteVisualization, RouteInfo } from "./RouteVisualization";
import { useMapTimeline } from "@/contexts/MapTimelineContext";
import type {
  ActivityMarker as ActivityMarkerType,
  AccommodationMarker as AccommodationMarkerType,
  DayRoute,
} from "@/lib/types/map";

interface TripMapViewProps {
  activities: ActivityMarkerType[];
  accommodations: AccommodationMarkerType[];
  routes: DayRoute[];
  tripCenter?: { lat: number; lng: number } | undefined;
  routePolylines?: RoutePolyline[];
}

export function TripMapView({
  activities,
  accommodations,
  routes,
  tripCenter,
  routePolylines = [],
}: TripMapViewProps) {
  const {
    selectedDay,
    setSelectedDay,
    highlightedActivityId,
    setHighlightedActivityId,
  } = useMapTimeline();

  console.log(`🗺️ [TripMapView] Rendering with selectedDay: ${selectedDay}, routePolylines: ${routePolylines.length}`);

  // Calculate total days from activities
  const totalDays = useMemo(() => {
    const days = activities.map((a) => a.day);
    return days.length > 0 ? Math.max(...days) : 0;
  }, [activities]);

  // Filter activities by selected day
  const filteredActivities = useMemo(() => {
    if (selectedDay === null) return activities;
    return activities.filter((activity) => activity.day === selectedDay);
  }, [activities, selectedDay]);

  const handleMarkerClick = (id: string, type: "activity" | "accommodation") => {
    if (type === "activity") {
      setHighlightedActivityId(id);
    }
  };

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      {/* Day Selector */}
      <div className="flex-shrink-0">
        <DaySelector
          totalDays={totalDays}
          selectedDay={selectedDay}
          onDaySelect={setSelectedDay}
          currentDay={null}
        />
      </div>

      {/* Map Container */}
      <div className="relative flex-1 rounded-lg overflow-hidden shadow-lg">
        <InteractiveMap
          activities={filteredActivities}
          accommodations={accommodations}
          selectedDay={selectedDay}
          center={tripCenter}
          onMarkerClick={handleMarkerClick}
          routes={routePolylines}
        />
        <MapLegend />
      </div>

      {/* Route Information */}
      {routes.length > 0 && (
        <div className="flex-shrink-0">
          <RouteInfo routes={routes} selectedDay={selectedDay} />
        </div>
      )}
    </div>
  );
}

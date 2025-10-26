"use client";

import { useCallback, useMemo, useState } from "react";
import { GoogleMap, useJsApiLoader } from "@react-google-maps/api";
import type {
  ActivityMarker,
  AccommodationMarker,
  MapStyle,
} from "@/lib/types/map";
import { mapStyles } from "./mapStyles";

const libraries: ("places" | "geometry" | "drawing")[] = ["places", "geometry"];

interface InteractiveMapProps {
  activities: ActivityMarker[];
  accommodations: AccommodationMarker[];
  selectedDay: number | null;
  center?: { lat: number; lng: number } | undefined;
  onMarkerClick?: (markerId: string, type: "activity" | "accommodation") => void;
}

const containerStyle = {
  width: "100%",
  height: "100%",
};

export function InteractiveMap({
  activities,
  accommodations,
  selectedDay,
  center,
  onMarkerClick,
}: InteractiveMapProps) {
  const [mapStyle, setMapStyle] = useState<MapStyle>("standard");
  const [map, setMap] = useState<google.maps.Map | null>(null);

  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
  
  const { isLoaded, loadError } = useJsApiLoader({
    id: "google-map-script",
    googleMapsApiKey: apiKey,
    libraries,
  });

  // Filter activities by selected day
  const filteredActivities = useMemo(() => {
    if (selectedDay === null) return activities;
    return activities.filter((activity) => activity.day === selectedDay);
  }, [activities, selectedDay]);

  // Calculate map center from markers
  const mapCenter = useMemo(() => {
    if (center) return center;

    const allLocations = [
      ...filteredActivities.map((a) => a.location),
      ...accommodations.map((h) => h.location),
    ];

    if (allLocations.length === 0) {
      return { lat: 0, lng: 0 };
    }

    const avgLat =
      allLocations.reduce((sum, loc) => sum + loc.latitude, 0) /
      allLocations.length;
    const avgLng =
      allLocations.reduce((sum, loc) => sum + loc.longitude, 0) /
      allLocations.length;

    return { lat: avgLat, lng: avgLng };
  }, [center, filteredActivities, accommodations]);

  const onLoad = useCallback((mapInstance: google.maps.Map) => {
    setMap(mapInstance);
  }, []);

  const onUnmount = useCallback(() => {
    setMap(null);
  }, []);

  const handleMapStyleChange = useCallback((style: MapStyle) => {
    setMapStyle(style);
  }, []);

  const getMapTypeId = useCallback((): google.maps.MapTypeId => {
    switch (mapStyle) {
      case "satellite":
        return google.maps.MapTypeId.SATELLITE;
      case "terrain":
        return google.maps.MapTypeId.TERRAIN;
      default:
        return google.maps.MapTypeId.ROADMAP;
    }
  }, [mapStyle]);

  if (loadError) {
    console.error("Google Maps load error:", loadError);
    return (
      <div className="flex h-full items-center justify-center bg-gray-100 p-4">
        <div className="text-center max-w-md">
          <p className="text-red-600 font-semibold mb-2">Error loading Google Maps</p>
          <p className="text-gray-600 text-sm mb-2">
            {loadError.message || "Failed to load Google Maps API"}
          </p>
          <p className="text-gray-500 text-xs">
            Please ensure billing is enabled in Google Cloud Console and the Maps JavaScript API is activated.
          </p>
        </div>
      </div>
    );
  }

  if (!isLoaded) {
    return (
      <div className="flex h-full items-center justify-center bg-gray-100">
        <div className="text-gray-600">Loading map...</div>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      <GoogleMap
        mapContainerStyle={containerStyle}
        center={mapCenter}
        zoom={13}
        onLoad={onLoad}
        onUnmount={onUnmount}
        options={{
          mapTypeId: getMapTypeId(),
          styles: mapStyle === "standard" ? mapStyles : null,
          gestureHandling: "cooperative",
          mapTypeControl: true,
          mapTypeControlOptions: {
            position: google.maps.ControlPosition.TOP_RIGHT,
          },
          fullscreenControl: true,
          fullscreenControlOptions: {
            position: google.maps.ControlPosition.RIGHT_TOP,
          },
          streetViewControl: false,
          zoomControl: true,
          zoomControlOptions: {
            position: google.maps.ControlPosition.RIGHT_CENTER,
          },
          minZoom: 3,
          maxZoom: 20,
          clickableIcons: true,
          disableDoubleClickZoom: false,
        }}
      >
        {/* Map controls for style switching - mobile optimized */}
        <div className="absolute left-2 top-2 z-10 flex gap-1 rounded-lg bg-white p-1.5 shadow-md sm:left-4 sm:top-4 sm:gap-2 sm:p-2">
          <button
            onClick={() => handleMapStyleChange("standard")}
            className={`touch-manipulation rounded px-2 py-1.5 text-xs font-medium sm:px-3 sm:py-2 sm:text-sm ${
              mapStyle === "standard"
                ? "bg-blue-500 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            Standard
          </button>
          <button
            onClick={() => handleMapStyleChange("satellite")}
            className={`touch-manipulation rounded px-2 py-1.5 text-xs font-medium sm:px-3 sm:py-2 sm:text-sm ${
              mapStyle === "satellite"
                ? "bg-blue-500 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            Satellite
          </button>
          <button
            onClick={() => handleMapStyleChange("terrain")}
            className={`touch-manipulation rounded px-2 py-1.5 text-xs font-medium sm:px-3 sm:py-2 sm:text-sm ${
              mapStyle === "terrain"
                ? "bg-blue-500 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            Terrain
          </button>
        </div>
      </GoogleMap>
    </div>
  );
}

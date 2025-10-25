"use client";

import { useEffect, useRef } from "react";
import { MarkerClusterer } from "@googlemaps/markerclusterer";
import type { ActivityMarker as ActivityMarkerType } from "@/lib/types/map";

interface MarkerClusterProps {
  map: google.maps.Map | null;
  activities: ActivityMarkerType[];
  onMarkerClick?: (activityId: string) => void;
}

export function MarkerCluster({
  map,
  activities,
  onMarkerClick,
}: MarkerClusterProps) {
  const clustererRef = useRef<MarkerClusterer | null>(null);
  const markersRef = useRef<google.maps.Marker[]>([]);

  useEffect(() => {
    if (!map) return;

    // Clear existing markers and clusterer
    if (clustererRef.current) {
      clustererRef.current.clearMarkers();
    }
    markersRef.current.forEach((marker) => marker.setMap(null));
    markersRef.current = [];

    // Create markers for activities
    const markers = activities.map((activity) => {
      const marker = new google.maps.Marker({
        position: {
          lat: activity.location.latitude,
          lng: activity.location.longitude,
        },
        map: map,
        title: activity.name,
      });

      // Add click listener
      if (onMarkerClick) {
        marker.addListener("click", () => {
          onMarkerClick(activity.activity_id);
        });
      }

      return marker;
    });

    markersRef.current = markers;

    // Create clusterer with custom styling
    const clusterer = new MarkerClusterer({
      map,
      markers,
      algorithmOptions: {
        maxZoom: 15, // Don't cluster at zoom levels above 15
        radius: 100, // Cluster radius in pixels
      },
      renderer: {
        render: ({ count, position }) => {
          // Custom cluster marker appearance
          const color = count > 20 ? "#EF4444" : count > 10 ? "#F59E0B" : "#3B82F6";

          return new google.maps.Marker({
            position,
            icon: {
              path: google.maps.SymbolPath.CIRCLE,
              fillColor: color,
              fillOpacity: 0.8,
              strokeColor: "#FFFFFF",
              strokeWeight: 3,
              scale: Math.min(20 + count / 2, 35),
            },
            label: {
              text: String(count),
              color: "#FFFFFF",
              fontSize: "12px",
              fontWeight: "bold",
            },
            zIndex: Number(google.maps.Marker.MAX_ZINDEX) + count,
          });
        },
      },
    });

    clustererRef.current = clusterer;

    // Cleanup function
    return () => {
      if (clustererRef.current) {
        clustererRef.current.clearMarkers();
      }
      markersRef.current.forEach((marker) => marker.setMap(null));
    };
  }, [map, activities, onMarkerClick]);

  return null; // This component doesn't render anything directly
}

"use client";

import { useEffect, useRef } from "react";
import type { RoutePolyline } from "@/lib/geoapifyRouting";

interface RouteLayerProps {
  routes: RoutePolyline[];
  map: google.maps.Map | null;
  color?: string;
  opacity?: number;
  weight?: number;
}

/**
 * RouteLayer component displays route polylines on Google Maps
 * Routes are fetched from Geoapify Routing API and rendered as polylines
 *
 * This component manually manages Google Maps Polyline objects to ensure
 * proper cleanup when routes change or component unmounts.
 */
export function RouteLayer({
  routes,
  map,
  color = "#4285F4",
  opacity = 0.8,
  weight = 4,
}: RouteLayerProps) {
  const polylinesRef = useRef<google.maps.Polyline[]>([]);

  useEffect(() => {
    console.log(`🎨 [RouteLayer] Component MOUNTED with ${routes.length} routes`);

    if (!map) {
      console.log('⚠️ [RouteLayer] Map not available yet');
      return;
    }

    // Clear any existing polylines first
    console.log(`🧹 [RouteLayer] Clearing ${polylinesRef.current.length} existing polylines`);
    polylinesRef.current.forEach((polyline, idx) => {
      console.log(`  Removing polyline ${idx} from map`);
      polyline.setMap(null);
    });
    polylinesRef.current = [];

    // Create new polylines
    if (routes.length > 0) {
      routes.forEach((route, idx) => {
        console.log(`🛣️ [RouteLayer] Creating polyline ${idx}: ${route.coordinates.length} coordinates, distance: ${route.distance}m`);
        console.log(`  First coord: [${route.coordinates[0]?.lat}, ${route.coordinates[0]?.lng}]`);
        console.log(`  Last coord: [${route.coordinates[route.coordinates.length - 1]?.lat}, ${route.coordinates[route.coordinates.length - 1]?.lng}]`);

        const polyline = new google.maps.Polyline({
          path: route.coordinates,
          strokeColor: color,
          strokeOpacity: opacity,
          strokeWeight: weight,
          geodesic: true,
          clickable: false,
          map: map,
        });

        polylinesRef.current.push(polyline);
        console.log(`✅ [RouteLayer] Polyline ${idx} added to map`);
      });
    }

    // Cleanup when component unmounts or routes change
    return () => {
      console.log(`🧹 [RouteLayer] Component UNMOUNTING - removing ${polylinesRef.current.length} polylines`);
      polylinesRef.current.forEach((polyline, idx) => {
        console.log(`  Removing polyline ${idx} from map`);
        polyline.setMap(null);
      });
      polylinesRef.current = [];
    };
  }, [map, routes, color, opacity, weight]);

  // This component doesn't render anything - it manages Google Maps objects directly
  return null;
}

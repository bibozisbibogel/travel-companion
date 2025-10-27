"use client";

import { Marker, InfoWindow } from "@react-google-maps/api";
import { useState, useCallback } from "react";

interface WarningMarkerProps {
  position: { lat: number; lng: number };
  name: string;
  errorMessage?: string | null;
  type: "activity" | "accommodation" | "restaurant";
}

/**
 * WarningMarker component displays a warning marker for locations where
 * geocoding failed. Shows a distinct warning icon and provides information
 * about the failure to the user.
 */
export function WarningMarker({
  position,
  name,
  errorMessage,
  type,
}: WarningMarkerProps) {
  const [showInfo, setShowInfo] = useState(false);

  const handleClick = useCallback(() => {
    setShowInfo(true);
  }, []);

  const handleClose = useCallback(() => {
    setShowInfo(false);
  }, []);

  // Warning icon: Yellow/amber marker with exclamation mark styling
  const icon = {
    path: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z",
    fillColor: "#F59E0B", // Amber-500
    fillOpacity: 1,
    strokeColor: "#DC2626", // Red-600 stroke for warning emphasis
    strokeWeight: 2,
    scale: 1.5,
    anchor: new google.maps.Point(12, 22),
  };

  const typeLabel = type === "activity"
    ? "Activity"
    : type === "accommodation"
    ? "Accommodation"
    : "Restaurant";

  return (
    <>
      <Marker
        position={position}
        onClick={handleClick}
        icon={icon}
        title={`Warning: ${name} - Approximate location`}
      />
      {showInfo && (
        <InfoWindow position={position} onCloseClick={handleClose}>
          <div className="max-w-xs p-2">
            <div className="flex items-start gap-2">
              <span className="text-2xl">⚠️</span>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900">
                  {name}
                </h3>
                <div className="mt-2 space-y-2">
                  <div className="rounded-md bg-amber-50 p-2 text-sm">
                    <p className="font-medium text-amber-800">
                      Location Approximate
                    </p>
                    <p className="mt-1 text-xs text-amber-700">
                      The exact coordinates for this {typeLabel.toLowerCase()} could not be
                      determined. The marker shows an approximate location based on
                      the destination city center.
                    </p>
                  </div>
                  {errorMessage && (
                    <div className="text-xs text-gray-600">
                      <span className="font-medium">Technical info:</span>{" "}
                      {errorMessage}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </InfoWindow>
      )}
    </>
  );
}

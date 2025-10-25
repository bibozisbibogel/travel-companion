"use client";

import { Marker, InfoWindow } from "@react-google-maps/api";
import { useState, useCallback } from "react";
import type { AccommodationMarker as AccommodationMarkerType } from "@/lib/types/map";
import { ACCOMMODATION_COLOR } from "@/lib/types/map";

interface AccommodationMarkerProps {
  accommodation: AccommodationMarkerType;
  onClick?: (id: string) => void;
}

export function AccommodationMarker({
  accommodation,
  onClick,
}: AccommodationMarkerProps) {
  const [showInfo, setShowInfo] = useState(false);

  const position = {
    lat: accommodation.location.latitude,
    lng: accommodation.location.longitude,
  };

  const handleClick = useCallback(() => {
    setShowInfo(true);
    onClick?.(accommodation.hotel_id);
  }, [accommodation.hotel_id, onClick]);

  const handleClose = useCallback(() => {
    setShowInfo(false);
  }, []);

  // Create custom icon for accommodation
  const icon = {
    path: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z",
    fillColor: ACCOMMODATION_COLOR,
    fillOpacity: 1,
    strokeColor: "#FFFFFF",
    strokeWeight: 2,
    scale: 1.5,
    anchor: new google.maps.Point(12, 22),
  };

  const renderStars = (rating: number) => {
    return "⭐".repeat(Math.floor(rating));
  };

  return (
    <>
      <Marker position={position} onClick={handleClick} icon={icon} />
      {showInfo && (
        <InfoWindow position={position} onCloseClick={handleClose}>
          <div className="max-w-xs p-2">
            <h3 className="text-lg font-semibold text-gray-900">
              {accommodation.name}
            </h3>
            <div className="mt-2 space-y-1 text-sm text-gray-600">
              <div className="flex items-center gap-1">
                <span>{renderStars(accommodation.rating)}</span>
                <span className="text-xs text-gray-500">
                  ({accommodation.rating})
                </span>
              </div>
              <div className="font-medium text-gray-900">
                ${accommodation.price_per_night} / night
              </div>
              {accommodation.address && (
                <div className="text-xs text-gray-500">
                  {accommodation.address}
                </div>
              )}
              {accommodation.contact && (
                <div className="text-xs text-gray-500">
                  {accommodation.contact}
                </div>
              )}
            </div>
          </div>
        </InfoWindow>
      )}
    </>
  );
}

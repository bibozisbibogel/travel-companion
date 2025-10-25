"use client";

import { Marker, InfoWindow } from "@react-google-maps/api";
import { useState, useCallback, useMemo } from "react";
import type {
  ActivityMarker as ActivityMarkerType,
  ActivityCategory,
} from "@/lib/types/map";
import { CATEGORY_COLORS } from "@/lib/types/map";

interface ActivityMarkerProps {
  activity: ActivityMarkerType;
  onClick?: (id: string) => void;
}

const CATEGORY_ICONS: Record<ActivityCategory, string> = {
  adventure: "🏔️",
  cultural: "🏛️",
  relaxation: "🧘",
  dining: "🍽️",
  nightlife: "🌃",
  shopping: "🛍️",
};

export function ActivityMarker({ activity, onClick }: ActivityMarkerProps) {
  const [showInfo, setShowInfo] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const position = {
    lat: activity.location.latitude,
    lng: activity.location.longitude,
  };

  const handleClick = useCallback(() => {
    setShowInfo(true);
    onClick?.(activity.activity_id);
  }, [activity.activity_id, onClick]);

  const handleClose = useCallback(() => {
    setShowInfo(false);
  }, []);

  const handleMouseOver = useCallback(() => {
    setIsHovered(true);
  }, []);

  const handleMouseOut = useCallback(() => {
    setIsHovered(false);
  }, []);

  // Create custom icon for activity with category color
  const icon = useMemo(() => {
    const color = CATEGORY_COLORS[activity.category];
    const scale = isHovered ? 1.8 : 1.5;

    return {
      path: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z",
      fillColor: color,
      fillOpacity: 1,
      strokeColor: "#FFFFFF",
      strokeWeight: 2,
      scale: scale,
      anchor: new google.maps.Point(12, 22),
    };
  }, [activity.category, isHovered]);

  const formatDuration = (minutes: number): string => {
    if (minutes < 60) return `${minutes}min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}min` : `${hours}h`;
  };

  return (
    <>
      <Marker
        position={position}
        onClick={handleClick}
        onMouseOver={handleMouseOver}
        onMouseOut={handleMouseOut}
        icon={icon}
      />
      {showInfo && (
        <InfoWindow position={position} onCloseClick={handleClose}>
          <div className="max-w-xs p-2">
            <div className="flex items-start gap-2">
              <span className="text-2xl">{CATEGORY_ICONS[activity.category]}</span>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900">
                  {activity.name}
                </h3>
                <div className="mt-1 space-y-1 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <span
                      className="inline-block h-3 w-3 rounded-full"
                      style={{
                        backgroundColor: CATEGORY_COLORS[activity.category],
                      }}
                    />
                    <span className="capitalize">{activity.category}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span>⏰ {activity.time}</span>
                    <span>•</span>
                    <span>⏱️ {formatDuration(activity.duration)}</span>
                  </div>
                  {activity.description && (
                    <p className="mt-2 text-sm text-gray-700">
                      {activity.description}
                    </p>
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

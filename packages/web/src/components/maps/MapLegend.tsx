"use client";

import { useState } from "react";
import type { ActivityCategory } from "@/lib/types/map";
import { CATEGORY_COLORS, ACCOMMODATION_COLOR } from "@/lib/types/map";

const CATEGORY_LABELS: Record<ActivityCategory, string> = {
  adventure: "Adventure",
  cultural: "Cultural",
  relaxation: "Relaxation",
  dining: "Dining",
  nightlife: "Nightlife",
  shopping: "Shopping",
};

const CATEGORY_ICONS: Record<ActivityCategory, string> = {
  adventure: "🏔️",
  cultural: "🏛️",
  relaxation: "🧘",
  dining: "🍽️",
  nightlife: "🌃",
  shopping: "🛍️",
};

export function MapLegend() {
  const [isExpanded, setIsExpanded] = useState(true);

  const toggleLegend = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div className="absolute bottom-4 right-4 z-10 rounded-lg bg-white shadow-lg sm:bottom-6 sm:right-6">
      <button
        onClick={toggleLegend}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 rounded-lg"
      >
        <span>Legend</span>
        <span className="text-xs">{isExpanded ? "▼" : "▶"}</span>
      </button>

      {isExpanded && (
        <div className="border-t border-gray-200 px-3 py-2">
          <div className="space-y-2">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Activities
            </div>
            {(Object.entries(CATEGORY_LABELS) as [ActivityCategory, string][]).map(
              ([category, label]) => (
                <div key={category} className="flex items-center gap-2 text-sm">
                  <span className="text-base">{CATEGORY_ICONS[category]}</span>
                  <div
                    className="h-3 w-3 rounded-full border border-white shadow-sm"
                    style={{ backgroundColor: CATEGORY_COLORS[category] }}
                  />
                  <span className="text-gray-700">{label}</span>
                </div>
              )
            )}

            <div className="mt-3 pt-2 border-t border-gray-200">
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Accommodation
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-base">🏨</span>
                <div
                  className="h-3 w-3 rounded-full border border-white shadow-sm"
                  style={{ backgroundColor: ACCOMMODATION_COLOR }}
                />
                <span className="text-gray-700">Hotels</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

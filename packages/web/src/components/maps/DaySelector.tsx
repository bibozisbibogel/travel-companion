"use client";

import { useMemo } from "react";

interface DaySelectorProps {
  totalDays: number;
  selectedDay: number | null;
  onDaySelect: (day: number | null) => void;
  currentDay?: number | null | undefined;
}

export function DaySelector({
  totalDays,
  selectedDay,
  onDaySelect,
  currentDay,
}: DaySelectorProps) {
  const days = useMemo(
    () => Array.from({ length: totalDays }, (_, i) => i + 1),
    [totalDays]
  );

  return (
    <div className="flex flex-col gap-2">
      <div className="text-sm font-medium text-gray-700">Filter by Day</div>
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => {
            console.log('🔘 [DaySelector] "All Days" button CLICKED');
            onDaySelect(null);
          }}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${
            selectedDay === null
              ? "bg-blue-500 text-white shadow-md"
              : "bg-white text-gray-700 hover:bg-gray-50 border border-gray-200"
          }`}
        >
          All Days
        </button>
        {days.map((day) => (
          <button
            key={day}
            onClick={() => {
              console.log(`🔘 [DaySelector] Day ${day} button CLICKED`);
              onDaySelect(day);
            }}
            className={`relative rounded-lg px-4 py-2 text-sm font-medium transition-all ${
              selectedDay === day
                ? "bg-blue-500 text-white shadow-md"
                : currentDay === day
                  ? "bg-blue-50 text-blue-700 border-2 border-blue-300"
                  : "bg-white text-gray-700 hover:bg-gray-50 border border-gray-200"
            }`}
          >
            Day {day}
            {currentDay === day && selectedDay !== day && (
              <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-blue-500" />
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

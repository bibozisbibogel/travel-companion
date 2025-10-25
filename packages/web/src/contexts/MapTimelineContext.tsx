"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

interface MapTimelineContextType {
  selectedDay: number | null;
  setSelectedDay: (day: number | null) => void;
  highlightedActivityId: string | null;
  setHighlightedActivityId: (id: string | null) => void;
  currentDay: number | null;
  setCurrentDay: (day: number | null) => void;
}

const MapTimelineContext = createContext<MapTimelineContextType | undefined>(
  undefined
);

export function MapTimelineProvider({ children }: { children: ReactNode }) {
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [highlightedActivityId, setHighlightedActivityId] = useState<
    string | null
  >(null);
  const [currentDay, setCurrentDay] = useState<number | null>(null);

  const handleSetSelectedDay = useCallback((day: number | null) => {
    setSelectedDay(day);
  }, []);

  const handleSetHighlightedActivityId = useCallback((id: string | null) => {
    setHighlightedActivityId(id);
  }, []);

  const handleSetCurrentDay = useCallback((day: number | null) => {
    setCurrentDay(day);
  }, []);

  return (
    <MapTimelineContext.Provider
      value={{
        selectedDay,
        setSelectedDay: handleSetSelectedDay,
        highlightedActivityId,
        setHighlightedActivityId: handleSetHighlightedActivityId,
        currentDay,
        setCurrentDay: handleSetCurrentDay,
      }}
    >
      {children}
    </MapTimelineContext.Provider>
  );
}

export function useMapTimeline() {
  const context = useContext(MapTimelineContext);
  if (context === undefined) {
    throw new Error("useMapTimeline must be used within a MapTimelineProvider");
  }
  return context;
}

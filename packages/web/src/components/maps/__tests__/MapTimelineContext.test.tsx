import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { MapTimelineProvider, useMapTimeline } from "@/contexts/MapTimelineContext";
import { ReactNode } from "react";

const wrapper = ({ children }: { children: ReactNode }) => (
  <MapTimelineProvider>{children}</MapTimelineProvider>
);

describe("MapTimelineContext", () => {
  it("provides default values", () => {
    const { result } = renderHook(() => useMapTimeline(), { wrapper });

    expect(result.current.selectedDay).toBeNull();
    expect(result.current.highlightedActivityId).toBeNull();
    expect(result.current.currentDay).toBeNull();
  });

  it("updates selectedDay when setSelectedDay is called", () => {
    const { result } = renderHook(() => useMapTimeline(), { wrapper });

    act(() => {
      result.current.setSelectedDay(3);
    });

    expect(result.current.selectedDay).toBe(3);
  });

  it("updates highlightedActivityId when setHighlightedActivityId is called", () => {
    const { result } = renderHook(() => useMapTimeline(), { wrapper });

    act(() => {
      result.current.setHighlightedActivityId("activity-123");
    });

    expect(result.current.highlightedActivityId).toBe("activity-123");
  });

  it("updates currentDay when setCurrentDay is called", () => {
    const { result } = renderHook(() => useMapTimeline(), { wrapper });

    act(() => {
      result.current.setCurrentDay(5);
    });

    expect(result.current.currentDay).toBe(5);
  });

  it("allows setting values back to null", () => {
    const { result } = renderHook(() => useMapTimeline(), { wrapper });

    act(() => {
      result.current.setSelectedDay(2);
      result.current.setHighlightedActivityId("activity-456");
      result.current.setCurrentDay(2);
    });

    expect(result.current.selectedDay).toBe(2);
    expect(result.current.highlightedActivityId).toBe("activity-456");
    expect(result.current.currentDay).toBe(2);

    act(() => {
      result.current.setSelectedDay(null);
      result.current.setHighlightedActivityId(null);
      result.current.setCurrentDay(null);
    });

    expect(result.current.selectedDay).toBeNull();
    expect(result.current.highlightedActivityId).toBeNull();
    expect(result.current.currentDay).toBeNull();
  });

  it("throws error when used outside provider", () => {
    expect(() => {
      renderHook(() => useMapTimeline());
    }).toThrow("useMapTimeline must be used within a MapTimelineProvider");
  });
});

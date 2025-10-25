import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RouteInfo } from "../RouteVisualization";
import type { DayRoute } from "@/lib/types/map";

const mockRoutes: DayRoute[] = [
  {
    day: 1,
    segments: [
      {
        origin: { latitude: 40.7128, longitude: -74.006 },
        destination: { latitude: 40.7580, longitude: -73.9855 },
        distance: 5000,
        duration: 30,
        mode: "walk",
      },
    ],
    totalDistance: 5000,
    totalDuration: 30,
  },
  {
    day: 2,
    segments: [
      {
        origin: { latitude: 40.7580, longitude: -73.9855 },
        destination: { latitude: 40.7489, longitude: -73.9680 },
        distance: 15000,
        duration: 120,
        mode: "drive",
      },
    ],
    totalDistance: 15000,
    totalDuration: 120,
  },
];

describe("RouteInfo", () => {
  it("renders route information for all days when selectedDay is null", () => {
    render(<RouteInfo routes={mockRoutes} selectedDay={null} />);

    expect(screen.getByText("Travel Information")).toBeInTheDocument();
    expect(screen.getByText("Day 1")).toBeInTheDocument();
    expect(screen.getByText("Day 2")).toBeInTheDocument();
  });

  it("renders route information for only selected day", () => {
    render(<RouteInfo routes={mockRoutes} selectedDay={1} />);

    expect(screen.getByText("Travel Information")).toBeInTheDocument();
    expect(screen.getByText("Day 1")).toBeInTheDocument();
    expect(screen.queryByText("Day 2")).not.toBeInTheDocument();
  });

  it("formats distance correctly for meters", () => {
    const shortRoute: DayRoute[] = [
      {
        day: 1,
        segments: [],
        totalDistance: 500,
        totalDuration: 10,
      },
    ];

    render(<RouteInfo routes={shortRoute} selectedDay={null} />);
    expect(screen.getByText(/500m/)).toBeInTheDocument();
  });

  it("formats distance correctly for kilometers", () => {
    render(<RouteInfo routes={mockRoutes} selectedDay={1} />);
    expect(screen.getByText(/5\.0km/)).toBeInTheDocument();
  });

  it("formats duration correctly for minutes", () => {
    render(<RouteInfo routes={mockRoutes} selectedDay={1} />);
    expect(screen.getByText(/30min/)).toBeInTheDocument();
  });

  it("formats duration correctly for hours and minutes", () => {
    render(<RouteInfo routes={mockRoutes} selectedDay={2} />);
    expect(screen.getByText(/2h/)).toBeInTheDocument();
  });

  it("displays transport mode icons", () => {
    render(<RouteInfo routes={mockRoutes} selectedDay={1} />);
    expect(screen.getByText("🚶")).toBeInTheDocument();
  });

  it("returns null when routes are empty", () => {
    const { container } = render(<RouteInfo routes={[]} selectedDay={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("returns null when selectedDay has no matching routes", () => {
    const { container } = render(<RouteInfo routes={mockRoutes} selectedDay={99} />);
    expect(container.firstChild).toBeNull();
  });
});

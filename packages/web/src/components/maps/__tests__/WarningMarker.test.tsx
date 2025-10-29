import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WarningMarker } from "../WarningMarker";

// Mock @react-google-maps/api
vi.mock("@react-google-maps/api", () => ({
  Marker: ({ position, onClick, icon, title, children }: any) => (
    <div
      data-testid="marker"
      data-position={JSON.stringify(position)}
      data-icon={JSON.stringify(icon)}
      title={title}
      onClick={onClick}
    >
      {children}
    </div>
  ),
  InfoWindow: ({ position, onCloseClick, children }: any) => (
    <div
      data-testid="info-window"
      data-position={JSON.stringify(position)}
      data-onclose={onCloseClick ? "true" : "false"}
    >
      <button onClick={onCloseClick} data-testid="close-button">
        Close
      </button>
      {children}
    </div>
  ),
}));

// Mock google.maps.Point
beforeEach(() => {
  global.google = {
    maps: {
      Point: class {
        constructor(public x: number, public y: number) {}
      },
    },
  } as any;
});

describe("WarningMarker", () => {
  const defaultProps = {
    position: { lat: 41.9009, lng: 12.4833 },
    name: "Test Location",
    type: "activity" as const,
  };

  it("renders marker with warning icon", () => {
    render(<WarningMarker {...defaultProps} />);

    const marker = screen.getByTestId("marker");
    expect(marker).toBeInTheDocument();

    // Check that icon has warning colors (amber fill, red stroke)
    const iconData = JSON.parse(marker.getAttribute("data-icon") || "{}");
    expect(iconData.fillColor).toBe("#F59E0B");
    expect(iconData.strokeColor).toBe("#DC2626");
  });

  it("displays correct title on marker", () => {
    render(<WarningMarker {...defaultProps} />);

    const marker = screen.getByTestId("marker");
    expect(marker).toHaveAttribute(
      "title",
      "Warning: Test Location - Approximate location"
    );
  });

  it("shows info window when marker is clicked", () => {
    render(<WarningMarker {...defaultProps} />);

    const marker = screen.getByTestId("marker");

    // Initially no info window
    expect(screen.queryByTestId("info-window")).not.toBeInTheDocument();

    // Click marker
    fireEvent.click(marker);

    // Info window should appear
    expect(screen.getByTestId("info-window")).toBeInTheDocument();
  });

  it("displays location name in info window", () => {
    render(<WarningMarker {...defaultProps} />);

    fireEvent.click(screen.getByTestId("marker"));

    expect(screen.getByText("Test Location")).toBeInTheDocument();
  });

  it("displays warning message in info window", () => {
    render(<WarningMarker {...defaultProps} />);

    fireEvent.click(screen.getByTestId("marker"));

    expect(screen.getByText("Location Approximate")).toBeInTheDocument();
    expect(
      screen.getByText(/The exact coordinates for this activity could not be determined/i)
    ).toBeInTheDocument();
  });

  it("displays error message when provided", () => {
    const propsWithError = {
      ...defaultProps,
      errorMessage: "ZERO_RESULTS: Address not found",
    };

    render(<WarningMarker {...propsWithError} />);

    fireEvent.click(screen.getByTestId("marker"));

    expect(screen.getByText("Technical info:")).toBeInTheDocument();
    expect(
      screen.getByText("ZERO_RESULTS: Address not found")
    ).toBeInTheDocument();
  });

  it("does not display error section when no error message provided", () => {
    render(<WarningMarker {...defaultProps} />);

    fireEvent.click(screen.getByTestId("marker"));

    expect(screen.queryByText("Technical info:")).not.toBeInTheDocument();
  });

  it("closes info window when close button is clicked", () => {
    render(<WarningMarker {...defaultProps} />);

    // Open info window
    fireEvent.click(screen.getByTestId("marker"));
    expect(screen.getByTestId("info-window")).toBeInTheDocument();

    // Close info window
    fireEvent.click(screen.getByTestId("close-button"));
    expect(screen.queryByTestId("info-window")).not.toBeInTheDocument();
  });

  it("displays correct type label for activity", () => {
    render(<WarningMarker {...defaultProps} type="activity" />);

    fireEvent.click(screen.getByTestId("marker"));

    expect(
      screen.getByText(/The exact coordinates for this activity/i)
    ).toBeInTheDocument();
  });

  it("displays correct type label for accommodation", () => {
    render(<WarningMarker {...defaultProps} type="accommodation" />);

    fireEvent.click(screen.getByTestId("marker"));

    expect(
      screen.getByText(/The exact coordinates for this accommodation/i)
    ).toBeInTheDocument();
  });

  it("displays correct type label for restaurant", () => {
    render(<WarningMarker {...defaultProps} type="restaurant" />);

    fireEvent.click(screen.getByTestId("marker"));

    expect(
      screen.getByText(/The exact coordinates for this restaurant/i)
    ).toBeInTheDocument();
  });

  it("displays warning emoji in info window", () => {
    render(<WarningMarker {...defaultProps} />);

    fireEvent.click(screen.getByTestId("marker"));

    expect(screen.getByText("⚠️")).toBeInTheDocument();
  });

  it("uses correct position for marker and info window", () => {
    const position = { lat: 51.5074, lng: -0.1278 };
    render(<WarningMarker {...defaultProps} position={position} />);

    const marker = screen.getByTestId("marker");
    const markerPosition = JSON.parse(
      marker.getAttribute("data-position") || "{}"
    );

    expect(markerPosition).toEqual(position);

    fireEvent.click(marker);

    const infoWindow = screen.getByTestId("info-window");
    const infoPosition = JSON.parse(
      infoWindow.getAttribute("data-position") || "{}"
    );

    expect(infoPosition).toEqual(position);
  });
});

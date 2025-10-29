import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MapLegend } from "../MapLegend";

describe("MapLegend", () => {
  it("renders with legend expanded by default", () => {
    render(<MapLegend />);

    expect(screen.getByText("Legend")).toBeInTheDocument();
    expect(screen.getByText("Activities")).toBeInTheDocument();
    expect(screen.getByText("Accommodation")).toBeInTheDocument();
  });

  it("shows all activity categories", () => {
    render(<MapLegend />);

    expect(screen.getByText("Transportation")).toBeInTheDocument();
    // Accommodation is filtered out from activities as it's shown separately in the hotels section
    expect(screen.getByText("Attraction")).toBeInTheDocument();
    expect(screen.getByText("Dining")).toBeInTheDocument();
    expect(screen.getByText("Exploration")).toBeInTheDocument();
    expect(screen.getByText("Entertainment")).toBeInTheDocument();
    expect(screen.getByText("Shopping")).toBeInTheDocument();
    expect(screen.getByText("Other")).toBeInTheDocument();
  });

  it("shows accommodation marker type", () => {
    render(<MapLegend />);

    expect(screen.getByText("Hotels")).toBeInTheDocument();
  });

  it("toggles legend visibility when clicked", () => {
    render(<MapLegend />);

    const legendButton = screen.getByText("Legend");

    // Initially expanded
    expect(screen.getByText("Activities")).toBeInTheDocument();

    // Click to collapse
    fireEvent.click(legendButton);
    expect(screen.queryByText("Activities")).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(legendButton);
    expect(screen.getByText("Activities")).toBeInTheDocument();
  });

  it("displays correct expand/collapse indicator", () => {
    render(<MapLegend />);

    const legendButton = screen.getByText("Legend");

    // Initially shows collapse indicator
    expect(screen.getByText("▼")).toBeInTheDocument();

    // Click to collapse
    fireEvent.click(legendButton);
    expect(screen.getByText("▶")).toBeInTheDocument();
  });
});

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DaySelector } from "../DaySelector";

describe("DaySelector", () => {
  it("renders all day buttons based on totalDays", () => {
    const onDaySelect = vi.fn();
    render(
      <DaySelector
        totalDays={5}
        selectedDay={null}
        onDaySelect={onDaySelect}
      />
    );

    expect(screen.getByText("All Days")).toBeInTheDocument();
    expect(screen.getByText("Day 1")).toBeInTheDocument();
    expect(screen.getByText("Day 2")).toBeInTheDocument();
    expect(screen.getByText("Day 3")).toBeInTheDocument();
    expect(screen.getByText("Day 4")).toBeInTheDocument();
    expect(screen.getByText("Day 5")).toBeInTheDocument();
  });

  it("highlights the selected day", () => {
    const onDaySelect = vi.fn();
    render(
      <DaySelector totalDays={3} selectedDay={2} onDaySelect={onDaySelect} />
    );

    const day2Button = screen.getByText("Day 2");
    expect(day2Button).toHaveClass("bg-blue-500");
  });

  it("highlights All Days when selectedDay is null", () => {
    const onDaySelect = vi.fn();
    render(
      <DaySelector totalDays={3} selectedDay={null} onDaySelect={onDaySelect} />
    );

    const allDaysButton = screen.getByText("All Days");
    expect(allDaysButton).toHaveClass("bg-blue-500");
  });

  it("calls onDaySelect when a day button is clicked", () => {
    const onDaySelect = vi.fn();
    render(
      <DaySelector totalDays={3} selectedDay={null} onDaySelect={onDaySelect} />
    );

    fireEvent.click(screen.getByText("Day 2"));
    expect(onDaySelect).toHaveBeenCalledWith(2);
  });

  it("calls onDaySelect with null when All Days is clicked", () => {
    const onDaySelect = vi.fn();
    render(
      <DaySelector totalDays={3} selectedDay={1} onDaySelect={onDaySelect} />
    );

    fireEvent.click(screen.getByText("All Days"));
    expect(onDaySelect).toHaveBeenCalledWith(null);
  });

  it("shows current day indicator when currentDay is provided", () => {
    const onDaySelect = vi.fn();
    render(
      <DaySelector
        totalDays={3}
        selectedDay={null}
        onDaySelect={onDaySelect}
        currentDay={2}
      />
    );

    const day2Button = screen.getByText("Day 2");
    expect(day2Button).toHaveClass("border-2", "border-blue-300");
  });
});

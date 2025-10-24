/**
 * Unit tests for DailyBudgetSummary component
 * Story 3.2: Day-by-Day Itinerary Timeline Visualization
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DailyBudgetSummary } from '../DailyBudgetSummary';

describe('DailyBudgetSummary', () => {
  const mockDailyCost = {
    activities: '71.00',
    meals: '70.00',
    accommodation: '117.00',
    total: '258.00',
  };

  const mockTripBudget = {
    total: '3000.00',
    spent: '2456.90',
    remaining: '543.10',
  };

  it('should render daily total cost', () => {
    render(<DailyBudgetSummary dailyCost={mockDailyCost} />);
    expect(screen.getByText('€258.00')).toBeInTheDocument();
  });

  it('should render all budget categories', () => {
    render(<DailyBudgetSummary dailyCost={mockDailyCost} />);

    expect(screen.getByText('Accommodation')).toBeInTheDocument();
    expect(screen.getByText('Meals')).toBeInTheDocument();
    expect(screen.getByText('Activities')).toBeInTheDocument();
  });

  it('should render category amounts', () => {
    render(<DailyBudgetSummary dailyCost={mockDailyCost} />);

    expect(screen.getByText('€117.00')).toBeInTheDocument();
    expect(screen.getByText('€70.00')).toBeInTheDocument();
    expect(screen.getByText('€71.00')).toBeInTheDocument();
  });

  it('should format currency correctly', () => {
    render(<DailyBudgetSummary dailyCost={mockDailyCost} currency="USD" />);

    expect(screen.getByText('$258.00')).toBeInTheDocument();
    expect(screen.getByText('$117.00')).toBeInTheDocument();
  });

  it('should show trip budget progress when provided', () => {
    render(
      <DailyBudgetSummary
        dailyCost={mockDailyCost}
        tripBudget={mockTripBudget}
      />
    );

    expect(screen.getByText('Trip Budget Progress')).toBeInTheDocument();
    expect(screen.getByText('€2,456.90')).toBeInTheDocument();
    expect(screen.getByText('€543.10')).toBeInTheDocument();
  });

  it('should calculate budget progress percentage correctly', () => {
    render(
      <DailyBudgetSummary
        dailyCost={mockDailyCost}
        tripBudget={mockTripBudget}
      />
    );

    // 2456.90 / 3000 * 100 = 81.9%
    expect(screen.getByText(/81\.9% of €3,000\.00 total budget/)).toBeInTheDocument();
  });

  it('should not show trip budget section when not provided', () => {
    render(<DailyBudgetSummary dailyCost={mockDailyCost} />);

    expect(screen.queryByText('Trip Budget Progress')).not.toBeInTheDocument();
  });

  it('should render progress bars for each category', () => {
    const { container } = render(<DailyBudgetSummary dailyCost={mockDailyCost} />);

    const progressBars = container.querySelectorAll('[role="progressbar"]');
    // 3 categories + 1 trip budget progress (if shown) = 3 or 4
    expect(progressBars.length).toBeGreaterThanOrEqual(3);
  });

  it('should handle zero costs correctly', () => {
    const zeroCost = {
      activities: '0.00',
      meals: '0.00',
      accommodation: '0.00',
      total: '0.00',
    };

    render(<DailyBudgetSummary dailyCost={zeroCost} />);

    // There will be multiple €0.00 (one for each category and total)
    const zeroElements = screen.getAllByText('€0.00');
    expect(zeroElements.length).toBeGreaterThan(0);
  });

  it('should display correct remaining budget', () => {
    render(
      <DailyBudgetSummary
        dailyCost={mockDailyCost}
        tripBudget={mockTripBudget}
      />
    );

    expect(screen.getByText('Remaining')).toBeInTheDocument();
    expect(screen.getByText('€543.10')).toBeInTheDocument();
  });
});

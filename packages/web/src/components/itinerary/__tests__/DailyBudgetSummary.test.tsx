/**
 * Unit tests for DailyBudgetSummary component
 * Story 3.2: Day-by-Day Itinerary Timeline Visualization
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DailyBudgetSummary } from '../DailyBudgetSummary';
import {
  IItineraryActivity,
  IAccommodationInfo,
  ActivityCategory,
} from '@/lib/types';

describe('DailyBudgetSummary', () => {
  const mockActivities: IItineraryActivity[] = [
    {
      time_start: '09:00',
      time_end: '12:00',
      category: 'attraction' as ActivityCategory,
      title: 'Museum Visit',
      description: 'Visit local museum',
      price: '25.00',
    },
    {
      time_start: '14:00',
      time_end: '17:00',
      category: 'exploration' as ActivityCategory,
      title: 'City Tour',
      description: 'Guided city tour',
      price: '46.00',
    },
    {
      time_start: '08:00',
      time_end: '09:00',
      category: 'dining' as ActivityCategory,
      title: 'Breakfast at Morning Cafe',
      description: 'French breakfast',
      price: '17.50',
    },
    {
      time_start: '13:00',
      time_end: '14:00',
      category: 'dining' as ActivityCategory,
      title: 'Lunch at Bistro',
      description: 'Italian lunch',
      price: '27.50',
    },
    {
      time_start: '19:00',
      time_end: '20:00',
      category: 'dining' as ActivityCategory,
      title: 'Dinner Place',
      description: 'Local dinner',
      price: '35.00',
    },
  ];

  const mockAccommodation: IAccommodationInfo = {
    name: 'Grand Hotel',
    rating: 4.5,
    stars: 4,
    address: {
      street: '123 Main St',
      city: 'Paris',
      region: 'Île-de-France',
      country: 'France',
    },
    amenities: ['WiFi', 'Pool'],
    price_per_night: '117.00',
    nights: 1,
    total_cost: '117.00',
  };

  const mockTripBudget = {
    total: '3000.00',
    spent: '2456.90',
    remaining: '543.10',
  };

  it('should render daily total cost', () => {
    // Activities: 25 + 46 = 71
    // Meals (dining activities): 17.5 + 27.5 + 35 = 80
    // Accommodation: 117
    // Total: 71 + 80 + 117 = 268
    render(
      <DailyBudgetSummary
        activities={mockActivities}
        accommodation={mockAccommodation}
      />
    );
    expect(screen.getByText('€268.00')).toBeInTheDocument();
  });

  it('should render all budget categories', () => {
    render(
      <DailyBudgetSummary
        activities={mockActivities}
        accommodation={mockAccommodation}
      />
    );

    expect(screen.getByText('Accommodation')).toBeInTheDocument();
    expect(screen.getByText('Meals')).toBeInTheDocument();
    expect(screen.getByText('Activities')).toBeInTheDocument();
  });

  it('should calculate and render category amounts', () => {
    render(
      <DailyBudgetSummary
        activities={mockActivities}
        accommodation={mockAccommodation}
      />
    );

    expect(screen.getByText('€117.00')).toBeInTheDocument(); // accommodation
    expect(screen.getByText('€80.00')).toBeInTheDocument(); // meals
    expect(screen.getByText('€71.00')).toBeInTheDocument(); // activities
  });

  it('should format currency correctly', () => {
    render(
      <DailyBudgetSummary
        activities={mockActivities}
        accommodation={mockAccommodation}
        currency="USD"
      />
    );

    expect(screen.getByText('$268.00')).toBeInTheDocument();
    expect(screen.getByText('$117.00')).toBeInTheDocument();
  });

  it('should show trip budget progress when provided', () => {
    render(
      <DailyBudgetSummary
        activities={mockActivities}
        accommodation={mockAccommodation}
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
        activities={mockActivities}
        accommodation={mockAccommodation}
        tripBudget={mockTripBudget}
      />
    );

    // 2456.90 / 3000 * 100 = 81.9%
    expect(screen.getByText(/81\.9% of €3,000\.00 total budget/)).toBeInTheDocument();
  });

  it('should not show trip budget section when not provided', () => {
    render(
      <DailyBudgetSummary
        activities={mockActivities}
        accommodation={mockAccommodation}
      />
    );

    expect(screen.queryByText('Trip Budget Progress')).not.toBeInTheDocument();
  });

  it('should render progress bars for each category', () => {
    const { container } = render(
      <DailyBudgetSummary
        activities={mockActivities}
        accommodation={mockAccommodation}
      />
    );

    const progressBars = container.querySelectorAll('[role="progressbar"]');
    // 3 categories = 3 progress bars
    expect(progressBars.length).toBe(3);
  });

  it('should handle zero costs correctly', () => {
    render(<DailyBudgetSummary activities={[]} />);

    // There will be multiple €0.00 (one for each category and total)
    const zeroElements = screen.getAllByText('€0.00');
    expect(zeroElements.length).toBeGreaterThan(0);
  });

  it('should display correct remaining budget', () => {
    render(
      <DailyBudgetSummary
        activities={mockActivities}
        accommodation={mockAccommodation}
        tripBudget={mockTripBudget}
      />
    );

    expect(screen.getByText('Remaining')).toBeInTheDocument();
    expect(screen.getByText('€543.10')).toBeInTheDocument();
  });

  it('should calculate totals from actual data arrays', () => {
    // Test calculation from activities (including dining) and accommodation
    // Activities: 25 + 46 = 71
    // Meals (dining activities): 17.5 + 27.5 + 35 = 80
    // Accommodation: 117
    // Total: 71 + 80 + 117 = 268
    render(
      <DailyBudgetSummary
        activities={mockActivities}
        accommodation={mockAccommodation}
      />
    );

    expect(screen.getByText('€268.00')).toBeInTheDocument(); // total
    expect(screen.getByText('€71.00')).toBeInTheDocument(); // activities
    expect(screen.getByText('€80.00')).toBeInTheDocument(); // meals
    expect(screen.getByText('€117.00')).toBeInTheDocument(); // accommodation
  });

  it('should handle activities without dining gracefully', () => {
    const nonDiningActivities = mockActivities.filter(a => a.category !== 'dining');
    render(<DailyBudgetSummary activities={nonDiningActivities} />);

    // Without dining activities, meals category should show 0
    const elements = screen.getAllByText(/€\d+\.\d+/);
    expect(elements.length).toBeGreaterThan(0);
  });

  it('should exclude accommodation cost on last day', () => {
    // On last day (checkout), accommodation should not be charged
    // Activities: 25 + 46 = 71
    // Meals: 17.5 + 27.5 + 35 = 80
    // Accommodation: 0 (last day)
    // Total: 71 + 80 = 151
    render(
      <DailyBudgetSummary
        activities={mockActivities}
        accommodation={mockAccommodation}
        isLastDay={true}
      />
    );

    expect(screen.getByText('€151.00')).toBeInTheDocument(); // total without accommodation
    expect(screen.getByText('€0.00')).toBeInTheDocument(); // accommodation should be 0
  });

  it('should multiply accommodation cost by traveler count', () => {
    // With 3 travelers, accommodation should be price_per_night × 3
    // Activities: 25 + 46 = 71 (price field, assumed to be total)
    // Meals: 17.5 + 27.5 + 35 = 80 (price field, assumed to be total)
    // Accommodation: 117 × 3 = 351
    // Total: 71 + 80 + 351 = 502
    render(
      <DailyBudgetSummary
        activities={mockActivities}
        accommodation={mockAccommodation}
        travelerCount={3}
      />
    );

    expect(screen.getByText('€502.00')).toBeInTheDocument(); // total with 3x accommodation
    expect(screen.getByText('€351.00')).toBeInTheDocument(); // accommodation × 3
  });

  it('should multiply cost_per_person by traveler count for meals and activities', () => {
    // Activities with cost_per_person instead of price
    const activitiesWithCostPerPerson: IItineraryActivity[] = [
      {
        time_start: '09:00',
        time_end: '12:00',
        category: 'attraction' as ActivityCategory,
        title: 'Museum Visit',
        description: 'Visit local museum',
        cost_per_person: 25,
      } as any,
      {
        time_start: '08:00',
        time_end: '09:00',
        category: 'dining' as ActivityCategory,
        title: 'Breakfast',
        description: 'Morning meal',
        cost_per_person: 15,
      } as any,
    ];

    // With 3 travelers:
    // Activities: 25 × 3 = 75
    // Meals: 15 × 3 = 45
    // Total: 75 + 45 = 120
    render(
      <DailyBudgetSummary
        activities={activitiesWithCostPerPerson}
        travelerCount={3}
      />
    );

    expect(screen.getByText('€120.00')).toBeInTheDocument(); // total
    expect(screen.getByText('€75.00')).toBeInTheDocument(); // activities × 3
    expect(screen.getByText('€45.00')).toBeInTheDocument(); // meals × 3
  });
});

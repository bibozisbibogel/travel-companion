/**
 * Unit tests for DailyBudgetSummary component
 * Story 3.2: Day-by-Day Itinerary Timeline Visualization
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DailyBudgetSummary } from '../DailyBudgetSummary';
import {
  IItineraryActivity,
  IMealRecommendation,
  IAccommodationInfo,
  ActivityCategory,
  MealType,
} from '@/lib/types';

describe('DailyBudgetSummary', () => {
  const mockActivities: IItineraryActivity[] = [
    {
      time_start: '09:00',
      time_end: '12:00',
      category: 'cultural' as ActivityCategory,
      title: 'Museum Visit',
      description: 'Visit local museum',
      price: '25.00',
    },
    {
      time_start: '14:00',
      time_end: '17:00',
      category: 'adventure' as ActivityCategory,
      title: 'City Tour',
      description: 'Guided city tour',
      price: '46.00',
    },
  ];

  const mockMeals: IMealRecommendation[] = [
    {
      restaurant_name: 'Morning Cafe',
      cuisine_type: 'French',
      meal_type: 'breakfast' as MealType,
      time: '08:00',
      price_range: '15-20',
    },
    {
      restaurant_name: 'Lunch Bistro',
      cuisine_type: 'Italian',
      meal_type: 'lunch' as MealType,
      time: '13:00',
      price_range: '25-30',
    },
    {
      restaurant_name: 'Dinner Place',
      cuisine_type: 'Local',
      meal_type: 'dinner' as MealType,
      time: '19:00',
      price_range: '30-40',
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
    // Meals: avg(15,20) + avg(25,30) + avg(30,40) = 17.5 + 27.5 + 35 = 80
    // Accommodation: 117
    // Total: 71 + 80 + 117 = 268
    render(
      <DailyBudgetSummary
        activities={mockActivities}
        meals={mockMeals}
        accommodation={mockAccommodation}
      />
    );
    expect(screen.getByText('€268.00')).toBeInTheDocument();
  });

  it('should render all budget categories', () => {
    render(
      <DailyBudgetSummary
        activities={mockActivities}
        meals={mockMeals}
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
        meals={mockMeals}
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
        meals={mockMeals}
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
        meals={mockMeals}
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
        meals={mockMeals}
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
        meals={mockMeals}
        accommodation={mockAccommodation}
      />
    );

    expect(screen.queryByText('Trip Budget Progress')).not.toBeInTheDocument();
  });

  it('should render progress bars for each category', () => {
    const { container } = render(
      <DailyBudgetSummary
        activities={mockActivities}
        meals={mockMeals}
        accommodation={mockAccommodation}
      />
    );

    const progressBars = container.querySelectorAll('[role="progressbar"]');
    // 3 categories = 3 progress bars
    expect(progressBars.length).toBe(3);
  });

  it('should handle zero costs correctly', () => {
    render(<DailyBudgetSummary activities={[]} meals={[]} />);

    // There will be multiple €0.00 (one for each category and total)
    const zeroElements = screen.getAllByText('€0.00');
    expect(zeroElements.length).toBeGreaterThan(0);
  });

  it('should display correct remaining budget', () => {
    render(
      <DailyBudgetSummary
        activities={mockActivities}
        meals={mockMeals}
        accommodation={mockAccommodation}
        tripBudget={mockTripBudget}
      />
    );

    expect(screen.getByText('Remaining')).toBeInTheDocument();
    expect(screen.getByText('€543.10')).toBeInTheDocument();
  });

  it('should calculate totals from actual data arrays', () => {
    // Test calculation from activities, meals, and accommodation arrays
    // Activities: 25 + 46 = 71
    // Meals: avg(15,20) + avg(25,30) + avg(30,40) = 17.5 + 27.5 + 35 = 80
    // Accommodation: 117
    // Total: 71 + 80 + 117 = 268
    render(
      <DailyBudgetSummary
        activities={mockActivities}
        meals={mockMeals}
        accommodation={mockAccommodation}
      />
    );

    expect(screen.getByText('€268.00')).toBeInTheDocument(); // total
    expect(screen.getByText('€71.00')).toBeInTheDocument(); // activities
    expect(screen.getByText('€80.00')).toBeInTheDocument(); // meals
    expect(screen.getByText('€117.00')).toBeInTheDocument(); // accommodation
  });

  it('should handle missing meals gracefully', () => {
    render(<DailyBudgetSummary activities={mockActivities} meals={[]} />);

    // Without meals, meals category should show 0
    const elements = screen.getAllByText(/€\d+\.\d+/);
    expect(elements.length).toBeGreaterThan(0);
  });
});

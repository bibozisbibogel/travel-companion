/**
 * Unit tests for MealCard component
 * Story 3.2: Day-by-Day Itinerary Timeline Visualization
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MealCard } from '../MealCard';
import type { IMealRecommendation } from '@/lib/types';

describe('MealCard', () => {
  const mockMeal: IMealRecommendation = {
    restaurant_name: 'Trattoria da Luigi',
    cuisine_type: 'Italian',
    meal_type: 'dinner',
    time: '19:30',
    price_range: '€€',
    rating: 4.5,
    location: 'Trastevere District',
    description: 'Authentic Roman cuisine in a charming family-run restaurant',
  };

  it('should render restaurant name', () => {
    render(<MealCard meal={mockMeal} />);
    expect(screen.getByText('Trattoria da Luigi')).toBeInTheDocument();
  });

  it('should render cuisine type', () => {
    render(<MealCard meal={mockMeal} />);
    expect(screen.getByText('Italian')).toBeInTheDocument();
  });

  it('should render formatted meal type', () => {
    render(<MealCard meal={mockMeal} />);
    expect(screen.getByText('Dinner')).toBeInTheDocument();
  });

  it('should render formatted time', () => {
    render(<MealCard meal={mockMeal} />);
    expect(screen.getByText('7:30 PM')).toBeInTheDocument();
  });

  it('should render price range', () => {
    render(<MealCard meal={mockMeal} />);
    expect(screen.getByText('€€')).toBeInTheDocument();
  });

  it('should render rating when provided', () => {
    render(<MealCard meal={mockMeal} />);
    expect(screen.getByText('4.5')).toBeInTheDocument();
  });

  it('should render location when provided', () => {
    render(<MealCard meal={mockMeal} />);
    expect(screen.getByText('Trastevere District')).toBeInTheDocument();
  });

  it('should render description when provided', () => {
    render(<MealCard meal={mockMeal} />);
    expect(
      screen.getByText('Authentic Roman cuisine in a charming family-run restaurant')
    ).toBeInTheDocument();
  });

  it('should apply correct badge color for breakfast', () => {
    const breakfastMeal = { ...mockMeal, meal_type: 'breakfast' as const };
    const { container } = render(<MealCard meal={breakfastMeal} />);
    expect(screen.getByText('Breakfast')).toBeInTheDocument();
    const badge = container.querySelector('.bg-yellow-100');
    expect(badge).toBeInTheDocument();
  });

  it('should apply correct badge color for lunch', () => {
    const lunchMeal = { ...mockMeal, meal_type: 'lunch' as const };
    const { container } = render(<MealCard meal={lunchMeal} />);
    expect(screen.getByText('Lunch')).toBeInTheDocument();
    const badge = container.querySelector('.bg-green-100');
    expect(badge).toBeInTheDocument();
  });

  it('should apply correct badge color for dinner', () => {
    const { container } = render(<MealCard meal={mockMeal} />);
    expect(screen.getByText('Dinner')).toBeInTheDocument();
    const badge = container.querySelector('.bg-orange-100');
    expect(badge).toBeInTheDocument();
  });

  it('should show expand button when description is long', () => {
    const longMeal = {
      ...mockMeal,
      description: 'A'.repeat(150),
    };

    render(<MealCard meal={longMeal} />);
    expect(screen.getByText('Show more')).toBeInTheDocument();
  });

  it('should expand and collapse description on button click', async () => {
    const user = userEvent.setup();
    const longMeal = {
      ...mockMeal,
      description: 'A'.repeat(150),
    };

    render(<MealCard meal={longMeal} />);

    const expandButton = screen.getByText('Show more');
    await user.click(expandButton);

    expect(screen.getByText('Show less')).toBeInTheDocument();

    const collapseButton = screen.getByText('Show less');
    await user.click(collapseButton);

    expect(screen.getByText('Show more')).toBeInTheDocument();
  });

  it('should render without optional fields', () => {
    const minimalMeal: IMealRecommendation = {
      restaurant_name: 'Pizzeria Napoli',
      cuisine_type: 'Pizza',
      meal_type: 'lunch',
      time: '12:00',
      price_range: '€',
    };

    render(<MealCard meal={minimalMeal} />);

    expect(screen.getByText('Pizzeria Napoli')).toBeInTheDocument();
    expect(screen.getByText('Pizza')).toBeInTheDocument();
    expect(screen.getByText('Lunch')).toBeInTheDocument();
  });
});

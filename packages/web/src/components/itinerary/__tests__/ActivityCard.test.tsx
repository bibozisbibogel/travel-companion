/**
 * Unit tests for ActivityCard component
 * Story 3.2: Day-by-Day Itinerary Timeline Visualization
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ActivityCard } from '../ActivityCard';
import type { IItineraryActivity } from '@/lib/types';

describe('ActivityCard', () => {
  const mockActivity: IItineraryActivity = {
    time_start: '09:00',
    time_end: '12:00',
    category: 'attraction',
    title: 'Colosseum Tour',
    description: 'Guided tour of the ancient Roman amphitheater',
    duration_minutes: 180,
    location: 'Piazza del Colosseo',
    price: '55.00',
  };

  it('should render activity title', () => {
    render(<ActivityCard activity={mockActivity} />);
    expect(screen.getByText('Colosseum Tour')).toBeInTheDocument();
  });

  it('should render activity category', () => {
    render(<ActivityCard activity={mockActivity} />);
    expect(screen.getByText('Attraction')).toBeInTheDocument();
  });

  it('should render activity description', () => {
    render(<ActivityCard activity={mockActivity} />);
    expect(screen.getByText('Guided tour of the ancient Roman amphitheater')).toBeInTheDocument();
  });

  it('should render formatted time range when duration is provided', () => {
    render(<ActivityCard activity={mockActivity} />);
    expect(screen.getByText(/9:00 AM - 12:00 PM/)).toBeInTheDocument();
  });

  it('should render duration in readable format', () => {
    render(<ActivityCard activity={mockActivity} />);
    expect(screen.getByText('3h')).toBeInTheDocument();
  });

  it('should render location when provided', () => {
    render(<ActivityCard activity={mockActivity} />);
    expect(screen.getByText('Piazza del Colosseo')).toBeInTheDocument();
  });

  it('should render formatted price when provided', () => {
    render(<ActivityCard activity={mockActivity} />);
    expect(screen.getByText('€55.00')).toBeInTheDocument();
  });

  it('should render price in specified currency', () => {
    render(<ActivityCard activity={mockActivity} currency="USD" />);
    expect(screen.getByText('$55.00')).toBeInTheDocument();
  });

  it('should show expand button when description is long', () => {
    const longActivity = {
      ...mockActivity,
      description: 'A'.repeat(150),
    };

    render(<ActivityCard activity={longActivity} />);
    expect(screen.getByText('Show more')).toBeInTheDocument();
  });

  it('should expand and collapse description on button click', async () => {
    const user = userEvent.setup();
    const longActivity = {
      ...mockActivity,
      description: 'A'.repeat(150),
      booking_info: 'Book in advance',
    };

    render(<ActivityCard activity={longActivity} />);

    const expandButton = screen.getByText('Show more');
    await user.click(expandButton);

    expect(screen.getByText('Show less')).toBeInTheDocument();
    expect(screen.getByText(/Book in advance/)).toBeInTheDocument();

    const collapseButton = screen.getByText('Show less');
    await user.click(collapseButton);

    expect(screen.getByText('Show more')).toBeInTheDocument();
  });

  it('should render without optional fields', () => {
    const minimalActivity: IItineraryActivity = {
      time_start: '09:00',
      time_end: null,
      category: 'exploration',
      title: 'City Walk',
      description: 'Walk around the city',
    };

    render(<ActivityCard activity={minimalActivity} />);

    expect(screen.getByText('City Walk')).toBeInTheDocument();
    expect(screen.getByText('Walk around the city')).toBeInTheDocument();
  });

  it('should apply correct background color based on category', () => {
    const { container } = render(<ActivityCard activity={mockActivity} />);
    const card = container.querySelector('.bg-purple-50');
    expect(card).toBeInTheDocument();
  });

  it('should show booking info when expanded', async () => {
    const user = userEvent.setup();
    const activityWithBooking = {
      ...mockActivity,
      description: 'A'.repeat(150),
      booking_info: 'Pre-booking required 24 hours in advance',
    };

    render(<ActivityCard activity={activityWithBooking} />);

    const expandButton = screen.getByText('Show more');
    await user.click(expandButton);

    expect(screen.getByText(/Pre-booking required 24 hours in advance/)).toBeInTheDocument();
  });
});

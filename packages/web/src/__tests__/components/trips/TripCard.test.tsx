/**
 * TripCard Component Tests
 * Story 3.5: User Trip List Dashboard
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TripCard } from '@/components/trips/TripCard';
import { ITripSummary } from '@/lib/types';

const mockTrip: ITripSummary = {
  trip_id: 'test-trip-123',
  user_id: 'user-123',
  name: 'Trip to Rome',
  description: 'Amazing week in Rome exploring ancient history',
  destination: {
    city: 'Rome',
    country: 'Italy',
  },
  requirements: {
    budget: 3000,
    currency: 'USD',
    start_date: '2025-06-01',
    end_date: '2025-06-07',
    travelers: 2,
  },
  status: 'confirmed',
  created_at: '2025-03-15T10:30:00Z',
  updated_at: '2025-03-15T10:30:00Z',
};

describe('TripCard', () => {
  it('renders trip card with all basic information', () => {
    render(<TripCard trip={mockTrip} />);

    expect(screen.getByText('Trip to Rome')).toBeInTheDocument();
    expect(screen.getByText(/Amazing week in Rome/)).toBeInTheDocument();
    expect(screen.getByText('Rome')).toBeInTheDocument();
    expect(screen.getByText('Italy')).toBeInTheDocument();
  });

  it('displays correct status badge', () => {
    render(<TripCard trip={mockTrip} />);
    expect(screen.getByText('Confirmed')).toBeInTheDocument();
  });

  it('displays draft status correctly', () => {
    const draftTrip = { ...mockTrip, status: 'draft' as const };
    render(<TripCard trip={draftTrip} />);
    expect(screen.getByText('Draft')).toBeInTheDocument();
  });

  it('displays planning status correctly', () => {
    const planningTrip = { ...mockTrip, status: 'planning' as const };
    render(<TripCard trip={planningTrip} />);
    expect(screen.getByText('Planning')).toBeInTheDocument();
  });

  it('displays completed status correctly', () => {
    const completedTrip = { ...mockTrip, status: 'completed' as const };
    render(<TripCard trip={completedTrip} />);
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('displays cancelled status correctly', () => {
    const cancelledTrip = { ...mockTrip, status: 'cancelled' as const };
    render(<TripCard trip={cancelledTrip} />);
    expect(screen.getByText('Cancelled')).toBeInTheDocument();
  });

  it('formats dates correctly', () => {
    render(<TripCard trip={mockTrip} />);
    expect(screen.getByText(/Jun 1, 2025 - Jun 7, 2025/)).toBeInTheDocument();
  });

  it('displays budget correctly', () => {
    render(<TripCard trip={mockTrip} />);
    expect(screen.getByText('$3,000')).toBeInTheDocument();
  });

  it('calculates and displays trip duration', () => {
    render(<TripCard trip={mockTrip} />);
    expect(screen.getByText('6 days')).toBeInTheDocument();
  });

  it('has correct link to trip detail page', () => {
    render(<TripCard trip={mockTrip} />);
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/trips/test-trip-123');
  });

  it('truncates long trip names', () => {
    const longNameTrip = {
      ...mockTrip,
      name: 'This is an extremely long trip name that should be truncated by CSS',
    };
    const { container } = render(<TripCard trip={longNameTrip} />);
    const heading = container.querySelector('h3');
    expect(heading).toHaveClass('line-clamp-1');
  });

  it('truncates long descriptions', () => {
    const longDescTrip = {
      ...mockTrip,
      description:
        'This is an extremely long description that should be truncated to two lines maximum by the CSS line-clamp utility class',
    };
    const { container } = render(<TripCard trip={longDescTrip} />);
    const description = container.querySelector('p.line-clamp-2');
    expect(description).toBeInTheDocument();
  });
});

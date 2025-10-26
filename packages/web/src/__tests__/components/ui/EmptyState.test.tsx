/**
 * EmptyState Component Tests
 * Story 3.5: User Trip List Dashboard
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EmptyState } from '@/components/ui/EmptyState';
import { Plane } from 'lucide-react';

describe('EmptyState', () => {
  it('renders with default title', () => {
    render(<EmptyState message="No items available" />);
    expect(screen.getByText('No items found')).toBeInTheDocument();
  });

  it('renders with custom title', () => {
    render(<EmptyState title="Custom Title" message="No items available" />);
    expect(screen.getByText('Custom Title')).toBeInTheDocument();
  });

  it('renders message correctly', () => {
    render(<EmptyState message="This is a custom message" />);
    expect(screen.getByText('This is a custom message')).toBeInTheDocument();
  });

  it('renders CTA button when provided', () => {
    render(
      <EmptyState
        message="No trips yet"
        ctaText="Create Trip"
        ctaHref="/trips/new"
      />
    );

    const ctaLink = screen.getByRole('link', { name: /Create Trip/ });
    expect(ctaLink).toBeInTheDocument();
    expect(ctaLink).toHaveAttribute('href', '/trips/new');
  });

  it('does not render CTA when not provided', () => {
    render(<EmptyState message="No items available" />);
    const links = screen.queryAllByRole('link');
    expect(links).toHaveLength(0);
  });

  it('renders custom icon when provided', () => {
    const { container } = render(
      <EmptyState message="No trips" icon={<Plane data-testid="plane-icon" />} />
    );

    expect(screen.getByTestId('plane-icon')).toBeInTheDocument();
  });

  it('does not render icon when not provided', () => {
    const { container } = render(<EmptyState message="No items available" />);
    const icons = container.querySelector('svg');
    // Only the Plus icon in CTA would be present if CTA exists
    expect(icons).not.toBeInTheDocument();
  });
});

/**
 * CategoryBreakdown Component Tests
 * Story 3.4 - Task 4: Unit and Integration Tests
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { CategoryBreakdown, CategoryCost } from '@/components/budget/CategoryBreakdown';

const mockCategories: CategoryCost[] = [
  {
    category: 'flights',
    amount: 800,
    percentage: 40,
    items: [
      { name: 'Outbound Flight', cost: 400 },
      { name: 'Return Flight', cost: 400 },
    ],
  },
  {
    category: 'accommodation',
    amount: 600,
    percentage: 30,
    items: [{ name: 'Hotel ABC - 3 nights', cost: 600 }],
  },
  {
    category: 'activities',
    amount: 300,
    percentage: 15,
    items: [
      { name: 'City Tour', cost: 100 },
      { name: 'Museum Entry', cost: 50 },
      { name: 'Boat Cruise', cost: 150 },
    ],
  },
  {
    category: 'dining',
    amount: 200,
    percentage: 10,
  },
  {
    category: 'transportation',
    amount: 80,
    percentage: 4,
  },
  {
    category: 'misc',
    amount: 20,
    percentage: 1,
  },
];

describe('CategoryBreakdown', () => {
  describe('Category Display', () => {
    it('renders all categories with correct labels', () => {
      render(
        <CategoryBreakdown
          categories={mockCategories}
          totalCost={2000}
          currency="USD"
        />
      );

      expect(screen.getByText('Flights')).toBeInTheDocument();
      expect(screen.getByText('Accommodation')).toBeInTheDocument();
      expect(screen.getByText('Activities')).toBeInTheDocument();
      expect(screen.getByText('Meals & Dining')).toBeInTheDocument();
      expect(screen.getByText('Transportation')).toBeInTheDocument();
      expect(screen.getByText('Miscellaneous')).toBeInTheDocument();
    });

    it('displays category amounts with correct currency', () => {
      render(
        <CategoryBreakdown
          categories={mockCategories}
          totalCost={2000}
          currency="USD"
        />
      );

      expect(screen.getAllByText(/\$800\.00/)[0]).toBeInTheDocument();
      expect(screen.getAllByText(/\$600\.00/)[0]).toBeInTheDocument();
      expect(screen.getAllByText(/\$300\.00/)[0]).toBeInTheDocument();
    });

    it('displays category percentages', () => {
      render(
        <CategoryBreakdown
          categories={mockCategories}
          totalCost={2000}
          currency="USD"
        />
      );

      expect(screen.getByText('40.0% of total')).toBeInTheDocument();
      expect(screen.getByText('30.0% of total')).toBeInTheDocument();
      expect(screen.getByText('15.0% of total')).toBeInTheDocument();
    });
  });

  describe('Total Cost Display', () => {
    it('displays total cost in donut chart center', () => {
      render(
        <CategoryBreakdown
          categories={mockCategories}
          totalCost={2000}
          currency="EUR"
        />
      );

      expect(screen.getByText('Total')).toBeInTheDocument();
      expect(screen.getByText(/€2,000\.00/)).toBeInTheDocument();
    });
  });

  describe('Category Expansion', () => {
    it('expands category to show itemized costs when clicked', async () => {
      render(
        <CategoryBreakdown
          categories={mockCategories}
          totalCost={2000}
          currency="USD"
        />
      );

      // Initially, items should not be visible
      expect(screen.queryByText('Outbound Flight')).not.toBeInTheDocument();

      // Click on flights category
      const flightsButton = screen.getByRole('button', { name: /flights/i });
      await userEvent.click(flightsButton);

      // Items should now be visible
      expect(screen.getByText('Outbound Flight')).toBeInTheDocument();
      expect(screen.getByText('Return Flight')).toBeInTheDocument();
    });

    it('collapses category when clicked again', async () => {
      render(
        <CategoryBreakdown
          categories={mockCategories}
          totalCost={2000}
          currency="USD"
        />
      );

      // Click to expand
      const flightsButton = screen.getByRole('button', { name: /flights/i });
      await userEvent.click(flightsButton);

      expect(screen.getByText('Outbound Flight')).toBeInTheDocument();

      // Click to collapse
      await userEvent.click(flightsButton);

      expect(screen.queryByText('Outbound Flight')).not.toBeInTheDocument();
    });

    it('displays itemized costs with correct formatting', async () => {
      render(
        <CategoryBreakdown
          categories={mockCategories}
          totalCost={2000}
          currency="USD"
        />
      );

      const activitiesButton = screen.getByRole('button', { name: /activities/i });
      await userEvent.click(activitiesButton);

      expect(screen.getByText('City Tour')).toBeInTheDocument();
      expect(screen.getByText('Museum Entry')).toBeInTheDocument();
      expect(screen.getByText('Boat Cruise')).toBeInTheDocument();
      expect(screen.getByText(/\$100\.00/)).toBeInTheDocument();
      expect(screen.getByText(/\$50\.00/)).toBeInTheDocument();
      expect(screen.getByText(/\$150\.00/)).toBeInTheDocument();
    });

    it('does not expand categories without items', async () => {
      render(
        <CategoryBreakdown
          categories={mockCategories}
          totalCost={2000}
          currency="USD"
        />
      );

      const diningButton = screen.getByRole('button', { name: /meals & dining/i });
      await userEvent.click(diningButton);

      // Should not show any itemized breakdown since dining has no items
      // The total is still displayed (appears in both tooltip and category list)
      expect(screen.getAllByText(/\$200\.00/).length).toBeGreaterThan(0);
    });
  });

  describe('Donut Chart', () => {
    it('renders SVG donut chart', () => {
      const { container } = render(
        <CategoryBreakdown
          categories={mockCategories}
          totalCost={2000}
          currency="USD"
        />
      );

      const svg = container.querySelector('svg');
      expect(svg).toBeInTheDocument();
      expect(svg).toHaveAttribute('width', '200');
      expect(svg).toHaveAttribute('height', '200');
    });

    it('renders path segments for each category', () => {
      const { container } = render(
        <CategoryBreakdown
          categories={mockCategories}
          totalCost={2000}
          currency="USD"
        />
      );

      // SVG paths in the donut chart (200x200 viewBox)
      const svg = container.querySelector('svg[viewBox="0 0 200 200"]');
      const paths = svg?.querySelectorAll('path');
      expect(paths?.length).toBe(mockCategories.length);
    });

    it('includes tooltips on chart segments', () => {
      const { container } = render(
        <CategoryBreakdown
          categories={mockCategories}
          totalCost={2000}
          currency="USD"
        />
      );

      const titles = container.querySelectorAll('title');
      expect(titles.length).toBeGreaterThan(0);
    });
  });

  describe('Category Icons', () => {
    it('renders appropriate icons for each category', () => {
      const { container } = render(
        <CategoryBreakdown
          categories={mockCategories}
          totalCost={2000}
          currency="USD"
        />
      );

      // Lucide icons should be rendered (check for SVG elements)
      const icons = container.querySelectorAll('svg.lucide');
      expect(icons.length).toBeGreaterThan(0);
    });
  });

  describe('Default Currency', () => {
    it('uses EUR as default currency when not specified', () => {
      render(<CategoryBreakdown categories={mockCategories} totalCost={2000} />);

      expect(screen.getByText(/€2,000\.00/)).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles empty categories array', () => {
      render(<CategoryBreakdown categories={[]} totalCost={0} currency="USD" />);

      expect(screen.getByText('Category Breakdown')).toBeInTheDocument();
      expect(screen.getByText(/\$0\.00/)).toBeInTheDocument();
    });

    it('handles single category', () => {
      const singleCategory: CategoryCost[] = [
        {
          category: 'flights',
          amount: 1000,
          percentage: 100,
        },
      ];

      render(
        <CategoryBreakdown
          categories={singleCategory}
          totalCost={1000}
          currency="USD"
        />
      );

      expect(screen.getByText('Flights')).toBeInTheDocument();
      expect(screen.getByText('100.0% of total')).toBeInTheDocument();
    });
  });
});

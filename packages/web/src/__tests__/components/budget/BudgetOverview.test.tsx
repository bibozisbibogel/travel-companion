/**
 * BudgetOverview Component Tests
 * Story 3.4 - Task 4: Unit and Integration Tests
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { BudgetOverview } from '@/components/budget/BudgetOverview';

describe('BudgetOverview', () => {
  describe('Budget Display', () => {
    it('renders total budget and estimated cost', () => {
      render(
        <BudgetOverview totalBudget={5000} estimatedCost={4500} currency="USD" />
      );

      expect(screen.getByText('Total Budget')).toBeInTheDocument();
      expect(screen.getByText('Estimated Cost')).toBeInTheDocument();
      expect(screen.getByText(/\$5,000\.00/)).toBeInTheDocument();
      expect(screen.getByText(/\$4,500\.00/)).toBeInTheDocument();
    });

    it('displays correct currency symbols', () => {
      const { rerender } = render(
        <BudgetOverview totalBudget={1000} estimatedCost={800} currency="EUR" />
      );

      expect(screen.getAllByText(/€/).length).toBeGreaterThan(0);

      rerender(
        <BudgetOverview totalBudget={1000} estimatedCost={800} currency="GBP" />
      );

      expect(screen.getAllByText(/£/).length).toBeGreaterThan(0);
    });
  });

  describe('Budget Calculations', () => {
    it('calculates remaining budget correctly when under budget', () => {
      render(
        <BudgetOverview totalBudget={5000} estimatedCost={4000} currency="USD" />
      );

      expect(screen.getByText('Remaining Budget')).toBeInTheDocument();
      expect(screen.getByText(/\$1,000\.00/)).toBeInTheDocument();
    });

    it('calculates over budget amount correctly', () => {
      render(
        <BudgetOverview totalBudget={5000} estimatedCost={5500} currency="USD" />
      );

      expect(screen.getAllByText('Over Budget')[0]).toBeInTheDocument();
      expect(screen.getByText(/-\$500\.00/)).toBeInTheDocument();
    });

    it('calculates utilization percentage correctly', () => {
      render(
        <BudgetOverview totalBudget={5000} estimatedCost={4500} currency="USD" />
      );

      expect(screen.getByText('90.0%')).toBeInTheDocument();
    });

    it('handles zero budget gracefully', () => {
      render(<BudgetOverview totalBudget={0} estimatedCost={0} currency="USD" />);

      expect(screen.getByText('0.0%')).toBeInTheDocument();
    });
  });

  describe('Budget Status Indicators', () => {
    it('shows "Under Budget" status when utilization < 95%', () => {
      render(
        <BudgetOverview totalBudget={5000} estimatedCost={4500} currency="USD" />
      );

      expect(screen.getByText('Under Budget')).toBeInTheDocument();
    });

    it('shows "At Budget" status when utilization between 95-100%', () => {
      render(
        <BudgetOverview totalBudget={5000} estimatedCost={4800} currency="USD" />
      );

      expect(screen.getByText('At Budget')).toBeInTheDocument();
    });

    it('shows "Over Budget" status when utilization > 100%', () => {
      render(
        <BudgetOverview totalBudget={5000} estimatedCost={5500} currency="USD" />
      );

      expect(screen.getAllByText('Over Budget').length).toBeGreaterThan(0);
    });

    it('displays warning message when over budget', () => {
      render(
        <BudgetOverview totalBudget={5000} estimatedCost={5500} currency="USD" />
      );

      expect(
        screen.getByText(/Your estimated trip cost exceeds your budget/i)
      ).toBeInTheDocument();
    });

    it('does not show warning when under budget', () => {
      render(
        <BudgetOverview totalBudget={5000} estimatedCost={4000} currency="USD" />
      );

      expect(
        screen.queryByText(/Your estimated trip cost exceeds your budget/i)
      ).not.toBeInTheDocument();
    });
  });

  describe('Progress Bar', () => {
    it('renders progress bar with correct aria attributes', () => {
      render(
        <BudgetOverview totalBudget={5000} estimatedCost={4500} currency="USD" />
      );

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '90');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');
    });

    it('caps progress bar width at 100% even when over budget', () => {
      render(
        <BudgetOverview totalBudget={5000} estimatedCost={6000} currency="USD" />
      );

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveStyle({ width: '100%' });
    });
  });

  describe('Default Currency', () => {
    it('uses EUR as default currency when not specified', () => {
      render(<BudgetOverview totalBudget={1000} estimatedCost={800} />);

      expect(screen.getAllByText(/€/).length).toBeGreaterThan(0);
    });
  });
});

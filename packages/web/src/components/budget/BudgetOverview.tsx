/**
 * BudgetOverview Component
 * Displays total trip budget vs. estimated cost with visual indicators
 * Story 3.4 - Task 1: Budget Overview Dashboard Component
 */

'use client';

import React from 'react';
import { DollarSign, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';
import { formatCurrency } from '@/lib/currencyUtils';

export interface BudgetOverviewProps {
  totalBudget: number;
  estimatedCost: number;
  currency?: string;
}

export type BudgetStatus = 'under' | 'at' | 'over';

export const BudgetOverview: React.FC<BudgetOverviewProps> = ({
  totalBudget,
  estimatedCost,
  currency = 'EUR',
}) => {
  /**
   * Calculate remaining budget (positive if under budget, negative if over)
   */
  const calculateRemainingBudget = (): number => {
    return totalBudget - estimatedCost;
  };

  /**
   * Calculate budget utilization percentage
   */
  const calculateUtilizationPercentage = (): number => {
    if (totalBudget === 0) return 0;
    return (estimatedCost / totalBudget) * 100;
  };

  /**
   * Determine budget status based on utilization
   * Under: < 95%, At: 95-100%, Over: > 100%
   */
  const getBudgetStatus = (): BudgetStatus => {
    const utilization = calculateUtilizationPercentage();
    if (utilization < 95) return 'under';
    if (utilization <= 100) return 'at';
    return 'over';
  };

  /**
   * Get status-specific styling
   */
  const getStatusStyles = (
    status: BudgetStatus
  ): {
    bgColor: string;
    textColor: string;
    icon: React.ReactNode;
    label: string;
  } => {
    switch (status) {
      case 'under':
        return {
          bgColor: 'bg-green-500',
          textColor: 'text-green-600',
          icon: <TrendingDown className="w-5 h-5" />,
          label: 'Under Budget',
        };
      case 'at':
        return {
          bgColor: 'bg-yellow-500',
          textColor: 'text-yellow-600',
          icon: <TrendingUp className="w-5 h-5" />,
          label: 'At Budget',
        };
      case 'over':
        return {
          bgColor: 'bg-red-500',
          textColor: 'text-red-600',
          icon: <AlertCircle className="w-5 h-5" />,
          label: 'Over Budget',
        };
    }
  };

  const remainingBudget = calculateRemainingBudget();
  const utilizationPercentage = calculateUtilizationPercentage();
  const budgetStatus = getBudgetStatus();
  const statusStyles = getStatusStyles(budgetStatus);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <DollarSign className="w-6 h-6 text-gray-700" />
          <h3 className="text-lg font-bold text-gray-900">Budget Overview</h3>
        </div>
        <div className={`flex items-center gap-2 ${statusStyles.textColor}`}>
          {statusStyles.icon}
          <span className="text-sm font-semibold">{statusStyles.label}</span>
        </div>
      </div>

      {/* Budget Comparison */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="text-sm text-gray-600 mb-1">Total Budget</div>
          <div className="text-2xl font-bold text-gray-900">
            {formatCurrency(totalBudget.toString(), currency)}
          </div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600 mb-1">Estimated Cost</div>
          <div className="text-2xl font-bold text-gray-900">
            {formatCurrency(estimatedCost.toString(), currency)}
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">
            Budget Utilization
          </span>
          <span className="text-sm font-bold text-gray-900">
            {utilizationPercentage.toFixed(1)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-4">
          <div
            className={`h-4 rounded-full transition-all duration-300 ${statusStyles.bgColor}`}
            style={{ width: `${Math.min(utilizationPercentage, 100)}%` }}
            role="progressbar"
            aria-valuenow={utilizationPercentage}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Budget utilization percentage"
          />
        </div>
      </div>

      {/* Remaining Budget */}
      <div
        className={`p-4 rounded-lg ${
          remainingBudget >= 0 ? 'bg-green-50' : 'bg-red-50'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">
            {remainingBudget >= 0 ? 'Remaining Budget' : 'Over Budget'}
          </span>
          <span
            className={`text-xl font-bold ${
              remainingBudget >= 0 ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {remainingBudget >= 0 ? '' : '-'}
            {formatCurrency(Math.abs(remainingBudget).toString(), currency)}
          </span>
        </div>
      </div>

      {/* Budget Status Message */}
      {budgetStatus === 'over' && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 mt-0.5" />
            <p className="text-sm text-red-800">
              Your estimated trip cost exceeds your budget. Consider reviewing
              cost optimization suggestions.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default BudgetOverview;

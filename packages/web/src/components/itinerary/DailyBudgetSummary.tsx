/**
 * DailyBudgetSummary Component
 * Displays daily cost breakdown with visual indicators
 * Story 3.2 - Task 5: Daily Budget Breakdown
 */

'use client';

import React from 'react';
import { DollarSign, TrendingUp, Hotel, Utensils, Compass } from 'lucide-react';
import { formatCurrency } from '@/lib/itineraryUtils';

interface BudgetCategory {
  label: string;
  amount: string;
  icon: React.ReactNode;
  color: string;
}

interface DailyBudgetSummaryProps {
  dailyCost: {
    activities: string;
    meals: string;
    accommodation: string;
    total: string;
  };
  currency?: string;
  tripBudget?: {
    total: string;
    spent: string;
    remaining: string;
  };
}

export const DailyBudgetSummary: React.FC<DailyBudgetSummaryProps> = ({
  dailyCost,
  currency = 'EUR',
  tripBudget,
}) => {
  const categories: BudgetCategory[] = [
    {
      label: 'Accommodation',
      amount: dailyCost.accommodation,
      icon: <Hotel className="w-4 h-4" />,
      color: 'text-indigo-600 bg-indigo-50',
    },
    {
      label: 'Meals',
      amount: dailyCost.meals,
      icon: <Utensils className="w-4 h-4" />,
      color: 'text-orange-600 bg-orange-50',
    },
    {
      label: 'Activities',
      amount: dailyCost.activities,
      icon: <Compass className="w-4 h-4" />,
      color: 'text-blue-600 bg-blue-50',
    },
  ];

  const calculatePercentage = (amount: string, total: string): number => {
    const amountNum = parseFloat(amount);
    const totalNum = parseFloat(total);
    if (totalNum === 0) return 0;
    return (amountNum / totalNum) * 100;
  };

  const calculateBudgetProgress = (): number => {
    if (!tripBudget) return 0;
    const spent = parseFloat(tripBudget.spent);
    const total = parseFloat(tripBudget.total);
    if (total === 0) return 0;
    return (spent / total) * 100;
  };

  const getBudgetStatusColor = (percentage: number): string => {
    if (percentage < 70) return 'bg-green-500';
    if (percentage < 90) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <DollarSign className="w-5 h-5 text-gray-700" />
        <h4 className="font-semibold text-gray-900">Daily Budget</h4>
      </div>

      {/* Daily Total */}
      <div className="mb-4 p-3 bg-gray-50 rounded-lg">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600">Total for this day</span>
          <span className="text-xl font-bold text-gray-900">
            {formatCurrency(dailyCost.total, currency)}
          </span>
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="space-y-3 mb-4">
        {categories.map((category) => {
          const amount = parseFloat(category.amount);
          const percentage = calculatePercentage(category.amount, dailyCost.total);

          return (
            <div key={category.label}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <div className={`p-1.5 rounded ${category.color}`}>
                    {category.icon}
                  </div>
                  <span className="text-sm font-medium text-gray-700">
                    {category.label}
                  </span>
                </div>
                <span className="text-sm font-semibold text-gray-900">
                  {formatCurrency(category.amount, currency)}
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${category.color.split(' ')[1]?.replace('bg-', 'bg-').replace('-50', '-500') || 'bg-gray-500'}`}
                  style={{ width: `${Math.min(percentage, 100)}%` }}
                  role="progressbar"
                  aria-valuenow={percentage}
                  aria-valuemin={0}
                  aria-valuemax={100}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Trip Budget Progress (if provided) */}
      {tripBudget && (
        <div className="pt-4 border-t border-gray-200">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-gray-600" />
            <span className="text-sm font-medium text-gray-700">Trip Budget Progress</span>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Spent</span>
              <span className="font-semibold text-gray-900">
                {formatCurrency(tripBudget.spent, currency)}
              </span>
            </div>

            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-all duration-300 ${getBudgetStatusColor(calculateBudgetProgress())}`}
                style={{ width: `${Math.min(calculateBudgetProgress(), 100)}%` }}
                role="progressbar"
                aria-valuenow={calculateBudgetProgress()}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Remaining</span>
              <span className="font-semibold text-green-600">
                {formatCurrency(tripBudget.remaining, currency)}
              </span>
            </div>

            <div className="text-xs text-gray-500 text-center">
              {calculateBudgetProgress().toFixed(1)}% of{' '}
              {formatCurrency(tripBudget.total, currency)} total budget
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DailyBudgetSummary;

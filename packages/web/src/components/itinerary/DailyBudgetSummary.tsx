/**
 * DailyBudgetSummary Component
 * Displays daily cost breakdown with visual indicators
 * Story 3.2 - Task 5: Daily Budget Breakdown
 */

'use client';

import React, { useMemo } from 'react';
import { DollarSign, TrendingUp, Hotel, Utensils, Compass } from 'lucide-react';
import { formatCurrency } from '@/lib/itineraryUtils';
import { IItineraryActivity, IAccommodationInfo } from '@/lib/types';

interface BudgetCategory {
  label: string;
  amount: number;
  icon: React.ReactNode;
  color: string;
}

interface DailyBudgetSummaryProps {
  activities: IItineraryActivity[];
  accommodation?: IAccommodationInfo;
  dailyCost?: {
    min: number;
    max: number;
    currency: string;
    breakdown?: string;
  };
  currency?: string;
  tripBudget?: {
    total: string;
    spent: string;
    remaining: string;
  };
  isLastDay?: boolean;
  travelerCount?: number;
}

export const DailyBudgetSummary: React.FC<DailyBudgetSummaryProps> = ({
  activities,
  accommodation,
  dailyCost,
  currency = 'EUR',
  tripBudget,
  isLastDay = false,
  travelerCount = 1,
}) => {
  // Calculate costs from actual data since backend breakdown is just descriptive text
  const breakdownCosts = useMemo(() => {
    // Calculate accommodation cost (excluding last day - checkout day with no night stay)
    // Use price_per_night × travelerCount (each traveler typically needs their own room)
    let accommodationTotal = 0;
    if (accommodation?.price_per_night && !isLastDay) {
      const parsed = parseFloat(accommodation.price_per_night);
      accommodationTotal = isNaN(parsed) ? 0 : parsed * travelerCount;
    }

    // Separate activities by category
    // Dining activities -> Meals budget category
    // Transportation activities -> Excluded from daily budget (trip-level costs like flights)
    // Everything else -> Activities budget category
    const diningActivities = activities.filter(activity => activity.category === 'dining');
    const transportationActivities = activities.filter(activity => activity.category === 'transportation');
    const actualActivities = activities.filter(
      activity => activity.category !== 'dining' && activity.category !== 'transportation'
    );

    // Calculate meals cost from dining activities
    // Multiply per-person costs by traveler count since everyone eats
    let mealsTotal = 0;
    mealsTotal = diningActivities.reduce((total, activity) => {
      const activityTyped = activity as any;

      // Prefer total_cost if backend already calculated for all travelers
      if (activityTyped.total_cost) {
        const parsed = parseFloat(activityTyped.total_cost);
        if (!isNaN(parsed)) return total + parsed;
      }

      // If cost_per_person is provided, multiply by traveler count
      if (activityTyped.cost_per_person) {
        const parsed = parseFloat(activityTyped.cost_per_person);
        if (!isNaN(parsed)) return total + (parsed * travelerCount);
      }

      // Check for explicit price field (assume it's total, not per-person)
      if (activity.price) {
        const parsed = parseFloat(activity.price);
        if (!isNaN(parsed)) return total + parsed;
      }

      // Fall back to cost estimates (average of min and max), multiply by travelers
      if (activityTyped.cost_estimate_min && activityTyped.cost_estimate_max) {
        const min = parseFloat(activityTyped.cost_estimate_min);
        const max = parseFloat(activityTyped.cost_estimate_max);
        if (!isNaN(min) && !isNaN(max)) {
          return total + ((min + max) / 2) * travelerCount;
        }
      }

      return total;
    }, 0);

    // Calculate activities cost (excluding dining and transportation)
    // Multiply per-person costs by traveler count for group activities
    let activitiesTotal = 0;
    activitiesTotal = actualActivities.reduce((total, activity) => {
      const activityTyped = activity as any;

      // Prefer total_cost if backend already calculated for all travelers
      if (activityTyped.total_cost) {
        const parsed = parseFloat(activityTyped.total_cost);
        if (!isNaN(parsed)) return total + parsed;
      }

      // If cost_per_person is provided, multiply by traveler count
      if (activityTyped.cost_per_person) {
        const parsed = parseFloat(activityTyped.cost_per_person);
        if (!isNaN(parsed)) return total + (parsed * travelerCount);
      }

      // Check for explicit price field (assume it's total, not per-person)
      if (activity.price) {
        const parsed = parseFloat(activity.price);
        if (!isNaN(parsed)) return total + parsed;
      }

      return total;
    }, 0);

    return {
      activities: activitiesTotal,
      meals: mealsTotal,
      accommodation: accommodationTotal,
    };
  }, [activities, accommodation, isLastDay, travelerCount]);

  const accommodationCost = breakdownCosts.accommodation;
  const mealsCost = breakdownCosts.meals;
  const activitiesCost = breakdownCosts.activities;
  const totalCost = accommodationCost + mealsCost + activitiesCost;

  const categories: BudgetCategory[] = [
    {
      label: 'Accommodation',
      amount: accommodationCost,
      icon: <Hotel className="w-4 h-4" />,
      color: 'text-indigo-600 bg-indigo-50',
    },
    {
      label: 'Meals',
      amount: mealsCost,
      icon: <Utensils className="w-4 h-4" />,
      color: 'text-orange-600 bg-orange-50',
    },
    {
      label: 'Activities',
      amount: activitiesCost,
      icon: <Compass className="w-4 h-4" />,
      color: 'text-blue-600 bg-blue-50',
    },
  ];

  const calculatePercentage = (amount: number, total: number): number => {
    if (total === 0) return 0;
    return (amount / total) * 100;
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
            {formatCurrency(totalCost.toString(), currency)}
          </span>
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="space-y-3 mb-4">
        {categories.map((category) => {
          const percentage = calculatePercentage(category.amount, totalCost);

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
                  {formatCurrency(category.amount.toString(), currency)}
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

/**
 * DailyBudgetSummary Component
 * Displays daily cost breakdown with visual indicators
 * Story 3.2 - Task 5: Daily Budget Breakdown
 */

'use client';

import React, { useMemo } from 'react';
import { DollarSign, Utensils, Compass } from 'lucide-react';
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
    // NOTE: Accommodation is now excluded from daily budget (shown in trip-level overview)

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
    };
  }, [activities, travelerCount]);

  const mealsCost = breakdownCosts.meals;
  const activitiesCost = breakdownCosts.activities;
  const totalCost = mealsCost + activitiesCost;

  const categories: BudgetCategory[] = [
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
      <div className="space-y-2">
        {categories.map((category) => {
          return (
            <div key={category.label}>
              <div className="flex items-center justify-between">
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
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default DailyBudgetSummary;

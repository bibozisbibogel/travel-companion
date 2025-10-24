/**
 * MealCard Component
 * Displays restaurant/meal recommendations integrated into the timeline
 * Story 3.2 - Task 3: Meal Recommendations Integration
 */

'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, MapPin, Clock, Star, Utensils } from 'lucide-react';
import { IMealRecommendation } from '@/lib/types';
import { formatTime } from '@/lib/itineraryUtils';

interface MealCardProps {
  meal: IMealRecommendation;
}

export const MealCard: React.FC<MealCardProps> = ({ meal }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getMealIcon = () => {
    return Utensils;
  };

  const getMealTypeBadgeColor = () => {
    switch (meal.meal_type) {
      case 'breakfast':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'lunch':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'dinner':
        return 'bg-orange-100 text-orange-800 border-orange-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const MealIcon = getMealIcon();

  return (
    <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow duration-200">
      <div className="flex items-start gap-3">
        {/* Meal Icon */}
        <div className="flex-shrink-0 mt-1">
          <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-sm">
            <MealIcon className="w-5 h-5 text-orange-600" />
          </div>
        </div>

        {/* Meal Content */}
        <div className="flex-grow min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex-grow">
              <h4 className="font-semibold text-gray-900 text-base leading-snug">
                {meal.restaurant_name}
              </h4>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <span
                  className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full border ${getMealTypeBadgeColor()}`}
                >
                  {meal.meal_type.charAt(0).toUpperCase() + meal.meal_type.slice(1)}
                </span>
                <span className="inline-block px-2 py-0.5 text-xs font-medium text-gray-600 bg-white rounded-full">
                  {meal.cuisine_type}
                </span>
              </div>
            </div>
          </div>

          {/* Meal Metadata */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-600 mb-2">
            <div className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              <span>{formatTime(meal.time)}</span>
            </div>

            <div className="flex items-center gap-1">
              <span className="font-medium">{meal.price_range}</span>
            </div>

            {meal.rating && (
              <div className="flex items-center gap-1">
                <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                <span className="font-medium">{meal.rating.toFixed(1)}</span>
              </div>
            )}

            {meal.location && (
              <div className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                <span className="truncate">{meal.location}</span>
              </div>
            )}
          </div>

          {/* Description */}
          {meal.description && (
            <>
              <p
                className={`text-sm text-gray-700 leading-relaxed ${
                  !isExpanded ? 'line-clamp-2' : ''
                }`}
              >
                {meal.description}
              </p>

              {/* Expand/Collapse Button */}
              {meal.description.length > 100 && (
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="mt-2 flex items-center gap-1 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
                  aria-label={isExpanded ? 'Show less' : 'Show more'}
                >
                  {isExpanded ? (
                    <>
                      <span>Show less</span>
                      <ChevronUp className="w-4 h-4" />
                    </>
                  ) : (
                    <>
                      <span>Show more</span>
                      <ChevronDown className="w-4 h-4" />
                    </>
                  )}
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default MealCard;

/**
 * DayCard Component
 * Main card component for each day in the itinerary with expand/collapse functionality
 * Story 3.2 - Task 7: Expand/Collapse Functionality
 */

'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Calendar, Sun, Sunset, Moon, CloudMoon } from 'lucide-react';
import { IDailyItinerary } from '@/lib/types';
import { ActivityCard } from './ActivityCard';
import { AccommodationCard } from './AccommodationCard';
import { DailyBudgetSummary } from './DailyBudgetSummary';
import {
  groupActivitiesByTimeOfDay,
  sortActivitiesByTime,
  formatDate,
  getTimeOfDayLabel,
} from '@/lib/itineraryUtils';

interface DayCardProps {
  day: IDailyItinerary;
  currency?: string;
  isFirstDay?: boolean;
  isLastDay?: boolean;
  tripBudget?: {
    total: string;
    spent: string;
    remaining: string;
  };
  defaultExpanded?: boolean;
  travelerCount?: number;
}

const TIME_OF_DAY_ICONS = {
  morning: Sun,
  afternoon: Sunset,
  evening: CloudMoon,
  night: Moon,
};

export const DayCard: React.FC<DayCardProps> = ({
  day,
  currency = 'EUR',
  isFirstDay = false,
  isLastDay = false,
  tripBudget,
  defaultExpanded = false,
  travelerCount = 1,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const sortedActivities = sortActivitiesByTime(day.activities);
  const groupedActivities = groupActivitiesByTimeOfDay(sortedActivities);

  const hasContent = day.activities.length > 0 || day.accommodation;

  // Summary info for collapsed view
  const activityCount = day.activities.length;

  return (
    <div className="bg-white border-2 border-gray-200 rounded-xl shadow-md hover:shadow-lg transition-shadow duration-200">
      {/* Day Header */}
      <div
        className="p-5 cursor-pointer select-none"
        onClick={() => setIsExpanded(!isExpanded)}
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsExpanded(!isExpanded);
          }
        }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Day Number Badge */}
            <div className="flex-shrink-0 w-14 h-14 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-md">
              <span className="text-white font-bold text-lg">Day {day.day}</span>
            </div>

            {/* Date and Title */}
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Calendar className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium text-gray-600">
                  {day.day_of_week}, {formatDate(day.date)}
                </span>
              </div>
              <h3 className="text-xl font-bold text-gray-900">{day.title}</h3>
            </div>
          </div>

          {/* Expand/Collapse Button */}
          <div className="flex items-center gap-4">
            {!isExpanded && (
              <div className="hidden sm:flex items-center gap-3 text-sm text-gray-600">
                <span>{activityCount} activities</span>
              </div>
            )}
            <button
              className="p-2 rounded-full hover:bg-gray-100 transition-colors"
              aria-label={isExpanded ? 'Collapse day' : 'Expand day'}
              onClick={(e) => {
                e.stopPropagation();
                setIsExpanded(!isExpanded);
              }}
            >
              {isExpanded ? (
                <ChevronUp className="w-6 h-6 text-gray-600" />
              ) : (
                <ChevronDown className="w-6 h-6 text-gray-600" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Day Content - Expanded View */}
      {isExpanded && hasContent && (
        <div className="px-5 pb-5">
          <div className="border-t border-gray-200 pt-5">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Main Content - Activities and Meals */}
              <div className="lg:col-span-2 space-y-6">
                {/* Activities by Time of Day */}
                {(['morning', 'afternoon', 'evening', 'night'] as const).map((timeOfDay) => {
                  const activitiesInSlot = groupedActivities[timeOfDay];
                  if (activitiesInSlot.length === 0) return null;

                  const TimeIcon = TIME_OF_DAY_ICONS[timeOfDay];

                  return (
                    <div key={timeOfDay}>
                      <div className="flex items-center gap-2 mb-3">
                        <TimeIcon className="w-5 h-5 text-gray-600" />
                        <h4 className="text-lg font-semibold text-gray-800">
                          {getTimeOfDayLabel(timeOfDay)}
                        </h4>
                        <div className="flex-grow h-px bg-gray-200 ml-2" />
                      </div>

                      <div className="space-y-3">
                        {activitiesInSlot.map((activity, index) => (
                          <ActivityCard
                            key={`${timeOfDay}-activity-${index}`}
                            activity={activity}
                            currency={currency}
                          />
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Sidebar - Accommodation and Budget */}
              <div className="space-y-4">
                {/* Accommodation */}
                {day.accommodation && (
                  <AccommodationCard
                    accommodation={day.accommodation}
                    currency={currency}
                    isFirstDay={isFirstDay}
                    isLastDay={isLastDay}
                  />
                )}

                {/* Daily Budget Summary */}
                <DailyBudgetSummary
                  activities={day.activities}
                  {...(day.accommodation && { accommodation: day.accommodation })}
                  {...(day.daily_cost && { dailyCost: day.daily_cost })}
                  currency={currency}
                  isLastDay={isLastDay}
                  travelerCount={travelerCount}
                  {...(tripBudget && { tripBudget })}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DayCard;

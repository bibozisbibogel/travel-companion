/**
 * ActivityCard Component
 * Displays individual activity information with category styling
 * Story 3.2 - Task 2: Activity Scheduling by Time of Day
 */

'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, MapPin, Clock, DollarSign } from 'lucide-react';
import { IItineraryActivity } from '@/lib/types';
import {
  ACTIVITY_ICONS,
  ACTIVITY_BG_LIGHT,
  calculateTimeRange,
  formatDuration,
  getCategoryLabel,
  formatCurrency,
} from '@/lib/itineraryUtils';

interface ActivityCardProps {
  activity: IItineraryActivity;
  currency?: string;
}

export const ActivityCard: React.FC<ActivityCardProps> = ({
  activity,
  currency = 'EUR',
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const Icon = ACTIVITY_ICONS[activity.category];
  const bgColor = ACTIVITY_BG_LIGHT[activity.category];

  const timeDisplay = activity.duration_minutes
    ? calculateTimeRange(activity.time_start, activity.duration_minutes)
    : activity.time_start;

  return (
    <div
      className={`${bgColor} border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow duration-200`}
    >
      <div className="flex items-start gap-3">
        {/* Category Icon */}
        <div className="flex-shrink-0 mt-1">
          <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-sm">
            <Icon className="w-5 h-5 text-gray-700" />
          </div>
        </div>

        {/* Activity Content */}
        <div className="flex-grow min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex-grow">
              <h4 className="font-semibold text-gray-900 text-base leading-snug">
                {activity.title}
              </h4>
              <span className="inline-block mt-1 px-2 py-0.5 text-xs font-medium text-gray-600 bg-white rounded-full">
                {getCategoryLabel(activity.category)}
              </span>
            </div>
          </div>

          {/* Activity Metadata */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-600 mb-2">
            <div className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              <span>{timeDisplay}</span>
            </div>

            {activity.duration_minutes && (
              <div className="flex items-center gap-1">
                <span className="font-medium">
                  {formatDuration(activity.duration_minutes)}
                </span>
              </div>
            )}

            {activity.location && (
              <div className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                <span className="truncate">{activity.location}</span>
              </div>
            )}

            {activity.price && (
              <div className="flex items-center gap-1">
                <DollarSign className="w-4 h-4" />
                <span className="font-medium">
                  {formatCurrency(activity.price, currency)}
                </span>
              </div>
            )}
          </div>

          {/* Brief Description */}
          <p
            className={`text-sm text-gray-700 leading-relaxed ${
              !isExpanded ? 'line-clamp-2' : ''
            }`}
          >
            {activity.description}
          </p>

          {/* Booking Info (when expanded) */}
          {isExpanded && activity.booking_info && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <p className="text-sm text-gray-600">
                <span className="font-medium">Booking Info:</span>{' '}
                {activity.booking_info}
              </p>
            </div>
          )}

          {/* Expand/Collapse Button */}
          {(activity.description.length > 100 || activity.booking_info) && (
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
        </div>
      </div>
    </div>
  );
};

export default ActivityCard;

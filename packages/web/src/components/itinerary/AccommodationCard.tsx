/**
 * AccommodationCard Component
 * Displays accommodation/hotel information for each day
 * Story 3.2 - Task 4: Accommodation Information Display
 */

'use client';

import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  MapPin,
  Star,
  Hotel,
  Check,
  Calendar,
} from 'lucide-react';
import { IAccommodationInfo } from '@/lib/types';
import { formatCurrency } from '@/lib/itineraryUtils';

interface AccommodationCardProps {
  accommodation: IAccommodationInfo;
  currency?: string;
  isFirstDay?: boolean;
  isLastDay?: boolean;
}

export const AccommodationCard: React.FC<AccommodationCardProps> = ({
  accommodation,
  currency = 'EUR',
  isFirstDay = false,
  isLastDay = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const renderStars = (count: number) => {
    return Array.from({ length: count }).map((_, i) => (
      <Star key={i} className="w-4 h-4 fill-yellow-400 text-yellow-400" />
    ));
  };

  const fullAddress = `${accommodation.address.street}, ${accommodation.address.city}, ${accommodation.address.region} ${accommodation.address.postal_code}, ${accommodation.address.country}`;

  return (
    <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow duration-200">
      <div className="flex items-start gap-3">
        {/* Hotel Icon */}
        <div className="flex-shrink-0 mt-1">
          <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-sm">
            <Hotel className="w-5 h-5 text-indigo-600" />
          </div>
        </div>

        {/* Accommodation Content */}
        <div className="flex-grow min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex-grow">
              <h4 className="font-semibold text-gray-900 text-base leading-snug">
                {accommodation.name}
              </h4>
              <div className="flex items-center gap-2 mt-1">
                <div className="flex items-center gap-0.5">
                  {renderStars(accommodation.stars)}
                </div>
                <span className="text-sm text-gray-600">
                  {accommodation.rating.toFixed(1)} rating
                </span>
              </div>
            </div>
          </div>

          {/* Check-in/Check-out Info */}
          {(isFirstDay || isLastDay) && (
            <div className="flex items-center gap-3 mb-3 p-2 bg-white rounded-md">
              {isFirstDay && accommodation.check_in && (
                <div className="flex items-center gap-1 text-sm text-gray-700">
                  <Calendar className="w-4 h-4 text-green-600" />
                  <span className="font-medium">Check-in:</span>
                  <span>{accommodation.check_in}</span>
                </div>
              )}
              {isLastDay && accommodation.check_out && (
                <div className="flex items-center gap-1 text-sm text-gray-700">
                  <Calendar className="w-4 h-4 text-red-600" />
                  <span className="font-medium">Check-out:</span>
                  <span>{accommodation.check_out}</span>
                </div>
              )}
            </div>
          )}

          {/* Location */}
          <div className="flex items-start gap-1 text-sm text-gray-600 mb-2">
            <MapPin className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <span className="line-clamp-1">{fullAddress}</span>
          </div>

          {/* Pricing */}
          <div className="flex items-center gap-4 text-sm mb-2">
            <span className="font-semibold text-gray-900">
              {formatCurrency(accommodation.price_per_night, currency)} / night
            </span>
            <span className="text-gray-600">
              {accommodation.nights} {accommodation.nights === 1 ? 'night' : 'nights'} total
            </span>
          </div>

          {/* Location Notes */}
          {accommodation.location_notes && (
            <p className="text-sm text-gray-700 mb-2 italic">
              {accommodation.location_notes}
            </p>
          )}

          {/* Amenities (collapsed by default) */}
          {isExpanded && (
            <div className="mt-3 pt-3 border-t border-indigo-200">
              <h5 className="text-sm font-semibold text-gray-900 mb-2">Amenities</h5>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {accommodation.amenities.map((amenity, index) => (
                  <div key={index} className="flex items-center gap-2 text-sm text-gray-700">
                    <Check className="w-4 h-4 text-green-600 flex-shrink-0" />
                    <span>{amenity}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Expand/Collapse Button */}
          {accommodation.amenities.length > 0 && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="mt-2 flex items-center gap-1 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
              aria-label={isExpanded ? 'Hide amenities' : 'Show amenities'}
            >
              {isExpanded ? (
                <>
                  <span>Hide amenities</span>
                  <ChevronUp className="w-4 h-4" />
                </>
              ) : (
                <>
                  <span>Show amenities ({accommodation.amenities.length})</span>
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

export default AccommodationCard;

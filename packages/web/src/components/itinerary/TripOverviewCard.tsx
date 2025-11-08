/**
 * TripOverviewCard Component
 * Displays trip-level costs: flights and accommodation summary
 */

'use client';

import React from 'react';
import {
  Plane,
  Hotel,
  MapPin,
  Star,
  Calendar,
  DollarSign,
} from 'lucide-react';
import { formatCurrency } from '@/lib/itineraryUtils';
import { IFlightDetails, IAccommodationInfo } from '@/lib/types';

interface TripOverviewCardProps {
  flights?: {
    outbound?: IFlightDetails;
    return_flight?: IFlightDetails;
    return?: IFlightDetails; // Backend sometimes uses 'return' instead of 'return_flight'
    total_cost?: string;
  };
  accommodation?: IAccommodationInfo;
  tripDates?: {
    start: string;
    end: string;
  };
  currency?: string;
}

export const TripOverviewCard: React.FC<TripOverviewCardProps> = ({
  flights,
  accommodation,
  tripDates,
  currency = 'EUR',
}) => {
  // Don't render if no data is available
  if (!flights && !accommodation) {
    return null;
  }

  // Debug logging
  console.log('TripOverviewCard - flights:', flights);
  console.log('TripOverviewCard - flights.outbound:', flights?.outbound);
  console.log('TripOverviewCard - flights.return_flight:', flights?.return_flight);

  // Handle both 'return' and 'return_flight' property names
  const returnFlight = flights?.return_flight || (flights as any)?.return;
  console.log('TripOverviewCard - returnFlight:', returnFlight);

  const formatDuration = (minutes: number): string => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  const getTimezoneCityName = (timezone: string): string => {
    // Extract city name from IANA timezone (e.g., "America/New_York" → "New York")
    const parts = timezone.split('/');
    if (parts.length < 2) return timezone;

    // Get the last part and replace underscores with spaces
    const cityPart = parts[parts.length - 1];
    if (!cityPart) return timezone;
    const cityName = cityPart.replace(/_/g, ' ');
    return cityName;
  };

  const formatFlightDateTime = (
    dateString: string,
    timeString: string,
    timezone?: string
  ): string => {
    try {
      // Combine date and time (time is in HH:MM format)
      const [hours, minutes] = timeString.split(':');
      const dateTimeStr = `${dateString}T${hours}:${minutes}:00`;
      const date = new Date(dateTimeStr);

      if (isNaN(date.getTime())) {
        return timeString;
      }

      // Format as "Nov 10, 9:00 AM"
      const formattedDateTime = date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });

      // Add timezone city name if available
      if (timezone) {
        const cityName = getTimezoneCityName(timezone);
        return `${formattedDateTime} ${cityName} Time`;
      }

      return formattedDateTime;
    } catch {
      return timeString;
    }
  };

  const flightCost = flights?.total_cost ? parseFloat(flights.total_cost) : 0;
  const accommodationCost = accommodation?.total_cost ? parseFloat(accommodation.total_cost) : 0;
  const totalTripCost = flightCost + accommodationCost;

  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-xl shadow-lg p-6 mb-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-blue-500 rounded-lg">
          <DollarSign className="w-6 h-6 text-white" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Trip Overview</h2>
          <p className="text-sm text-gray-600">
            {flights && accommodation
              ? 'Flights & Accommodation - Fixed Costs'
              : flights
              ? 'Flights - Fixed Costs'
              : 'Accommodation - Fixed Costs'}
          </p>
        </div>
      </div>

      {/* Total Trip Cost Summary */}
      {totalTripCost > 0 && (
        <div className="bg-white rounded-lg p-4 mb-6 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-lg font-semibold text-gray-700">
              Total Trip Costs
            </span>
            <span className="text-3xl font-bold text-blue-600">
              {formatCurrency(totalTripCost.toString(), currency)}
            </span>
          </div>
        </div>
      )}

      <div className={`grid grid-cols-1 ${flights && accommodation ? 'lg:grid-cols-2' : ''} gap-6`}>
        {/* Flights Section */}
        {flights && (
        <div className="bg-white rounded-lg p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Plane className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">Flights</h3>
          </div>

          {/* Outbound Flight */}
          {flights.outbound && (
          <div className="mb-4 pb-4 border-b border-gray-200">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-medium text-blue-600 bg-blue-100 px-2 py-1 rounded">
                OUTBOUND
              </span>
              <span className="text-sm text-gray-600">
                {flights.outbound.airline} {flights.outbound.flight_number}
              </span>
            </div>

            <div className="space-y-2">
              {/* Departure */}
              <div className="flex items-start gap-2">
                <span className="font-semibold text-gray-700 min-w-[80px]">Departure:</span>
                <div className="flex-1">
                  <div className="text-gray-900">
                    {flights.outbound.route.from_airport} -{' '}
                    {tripDates
                      ? formatFlightDateTime(
                          tripDates.start,
                          flights.outbound.departure.time,
                          flights.outbound.departure.timezone
                        )
                      : flights.outbound.departure.time}
                  </div>
                </div>
              </div>

              {/* Duration */}
              <div className="flex items-start gap-2">
                <span className="font-semibold text-gray-700 min-w-[80px]">Duration:</span>
                <div className="flex-1 text-gray-900">
                  {formatDuration(flights.outbound.duration_minutes)}
                </div>
              </div>

              {/* Arrival */}
              <div className="flex items-start gap-2">
                <span className="font-semibold text-gray-700 min-w-[80px]">Arrival:</span>
                <div className="flex-1">
                  <div className="text-gray-900">
                    {flights.outbound.route.to_airport} -{' '}
                    {tripDates
                      ? formatFlightDateTime(
                          tripDates.start,
                          flights.outbound.arrival.time,
                          flights.outbound.arrival.timezone
                        )
                      : flights.outbound.arrival.time}
                  </div>
                </div>
              </div>
            </div>

            {flights.outbound.stops > 0 && (
              <div className="text-xs text-orange-600 bg-orange-50 px-2 py-1 rounded inline-block">
                {flights.outbound.stops}{' '}
                {flights.outbound.stops === 1 ? 'stop' : 'stops'}
              </div>
            )}
          </div>
          )}

          {/* Return Flight */}
          {(() => {
            console.log('Checking returnFlight:', returnFlight);
            console.log('returnFlight truthy?', !!returnFlight);
            return returnFlight ? (
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-medium text-green-600 bg-green-100 px-2 py-1 rounded">
                RETURN
              </span>
              <span className="text-sm text-gray-600">
                {returnFlight.airline}{' '}
                {returnFlight.flight_number}
              </span>
            </div>

            <div className="space-y-2">
              {/* Departure */}
              <div className="flex items-start gap-2">
                <span className="font-semibold text-gray-700 min-w-[80px]">Departure:</span>
                <div className="flex-1">
                  <div className="text-gray-900">
                    {returnFlight.route.from_airport} -{' '}
                    {tripDates
                      ? formatFlightDateTime(
                          tripDates.end,
                          returnFlight.departure.time,
                          returnFlight.departure.timezone
                        )
                      : returnFlight.departure.time}
                  </div>
                </div>
              </div>

              {/* Duration */}
              <div className="flex items-start gap-2">
                <span className="font-semibold text-gray-700 min-w-[80px]">Duration:</span>
                <div className="flex-1 text-gray-900">
                  {formatDuration(returnFlight.duration_minutes)}
                </div>
              </div>

              {/* Arrival */}
              <div className="flex items-start gap-2">
                <span className="font-semibold text-gray-700 min-w-[80px]">Arrival:</span>
                <div className="flex-1">
                  <div className="text-gray-900">
                    {returnFlight.route.to_airport} -{' '}
                    {tripDates
                      ? formatFlightDateTime(
                          tripDates.end,
                          returnFlight.arrival.time,
                          returnFlight.arrival.timezone
                        )
                      : returnFlight.arrival.time}
                  </div>
                </div>
              </div>
            </div>

            {returnFlight.stops > 0 && (
              <div className="text-xs text-orange-600 bg-orange-50 px-2 py-1 rounded inline-block">
                {returnFlight.stops}{' '}
                {returnFlight.stops === 1 ? 'stop' : 'stops'}
              </div>
            )}
          </div>
            ) : null;
          })()}

          {/* Flight Cost */}
          {flights.total_cost && (
          <div className="pt-3 border-t border-gray-200">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">
                Total Flight Cost
              </span>
              <span className="text-xl font-bold text-gray-900">
                {formatCurrency(flights.total_cost, currency)}
              </span>
            </div>
          </div>
          )}
        </div>
        )}

        {/* Accommodation Section */}
        {accommodation && (
        <div className="bg-white rounded-lg p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Hotel className="w-5 h-5 text-indigo-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              Accommodation
            </h3>
          </div>

          <div className="space-y-3 mb-4">
            {/* Hotel Name and Rating */}
            <div>
              <h4 className="text-lg font-semibold text-gray-900 mb-1">
                {accommodation.name}
              </h4>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1">
                  {Array.from({ length: accommodation.stars }).map((_, i) => (
                    <Star
                      key={i}
                      className="w-4 h-4 fill-yellow-400 text-yellow-400"
                    />
                  ))}
                </div>
                <span className="text-sm text-gray-600">
                  Rating: {accommodation.rating.toFixed(1)}/5
                </span>
              </div>
            </div>

            {/* Address */}
            <div className="flex items-start gap-2">
              <MapPin className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-gray-700">
                <div>{accommodation.address.street}</div>
                <div>
                  {accommodation.address.city},{' '}
                  {accommodation.address.postal_code}
                </div>
                <div>
                  {accommodation.address.region},{' '}
                  {accommodation.address.country}
                </div>
              </div>
            </div>

            {/* Check-in/Check-out */}
            {(accommodation.check_in || accommodation.check_out) && (
              <div className="flex items-center gap-4 text-sm text-gray-700">
                {accommodation.check_in && (
                  <div className="flex items-center gap-1">
                    <Calendar className="w-4 h-4 text-gray-500" />
                    <span>Check-in: {accommodation.check_in}</span>
                  </div>
                )}
                {accommodation.check_out && (
                  <div className="flex items-center gap-1">
                    <Calendar className="w-4 h-4 text-gray-500" />
                    <span>Check-out: {accommodation.check_out}</span>
                  </div>
                )}
              </div>
            )}

            {/* Nights */}
            <div className="text-sm text-gray-700">
              <span className="font-medium">{accommodation.nights}</span>{' '}
              {accommodation.nights === 1 ? 'night' : 'nights'}
            </div>

            {/* Amenities */}
            {accommodation.amenities && accommodation.amenities.length > 0 && (
              <div>
                <div className="text-xs font-medium text-gray-600 mb-1">
                  Amenities:
                </div>
                <div className="flex flex-wrap gap-1">
                  {accommodation.amenities.slice(0, 6).map((amenity, index) => (
                    <span
                      key={index}
                      className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded"
                    >
                      {amenity}
                    </span>
                  ))}
                  {accommodation.amenities.length > 6 && (
                    <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                      +{accommodation.amenities.length - 6} more
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Accommodation Cost */}
          <div className="pt-3 border-t border-gray-200">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Per night</span>
                <span className="text-gray-900">
                  {formatCurrency(accommodation.price_per_night, currency)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">
                  Total Accommodation Cost
                </span>
                <span className="text-xl font-bold text-gray-900">
                  {formatCurrency(accommodation.total_cost, currency)}
                </span>
              </div>
            </div>
          </div>
        </div>
        )}
      </div>
    </div>
  );
};

export default TripOverviewCard;

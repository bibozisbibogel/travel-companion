/**
 * TripCard Component
 * Displays a summary card for a single trip
 * Story 3.5: User Trip List Dashboard
 */

'use client';

import React from 'react';
import Link from 'next/link';
import { ITripSummary, TripStatus } from '@/lib/types';
import { Calendar, MapPin, DollarSign } from 'lucide-react';

interface TripCardProps {
  trip: ITripSummary;
}

const STATUS_CONFIG: Record<
  TripStatus,
  { label: string; bgColor: string; textColor: string }
> = {
  draft: {
    label: 'Draft',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700',
  },
  planning: {
    label: 'Planning',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-700',
  },
  confirmed: {
    label: 'Confirmed',
    bgColor: 'bg-green-100',
    textColor: 'text-green-700',
  },
  completed: {
    label: 'Completed',
    bgColor: 'bg-purple-100',
    textColor: 'text-purple-700',
  },
  cancelled: {
    label: 'Cancelled',
    bgColor: 'bg-red-100',
    textColor: 'text-red-700',
  },
};

export function TripCard({ trip }: TripCardProps) {
  const statusConfig = STATUS_CONFIG[trip.status];

  // Format dates
  const startDate = new Date(trip.requirements.start_date).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
  const endDate = new Date(trip.requirements.end_date).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  // Calculate duration
  const start = new Date(trip.requirements.start_date);
  const end = new Date(trip.requirements.end_date);
  const duration = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));

  return (
    <Link href={`/trips/${trip.trip_id}`}>
      <div className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow duration-200 overflow-hidden cursor-pointer h-full">
        {/* Thumbnail/Preview placeholder */}
        <div className="h-48 bg-gradient-to-br from-blue-400 to-blue-600 relative">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-white text-center">
              <MapPin className="w-12 h-12 mx-auto mb-2 opacity-80" />
              <p className="text-2xl font-bold">{trip.destination.city}</p>
              <p className="text-sm opacity-90">{trip.destination.country}</p>
            </div>
          </div>
          {/* Status badge */}
          <div className="absolute top-3 right-3">
            <span
              className={`px-3 py-1 rounded-full text-xs font-semibold ${statusConfig.bgColor} ${statusConfig.textColor}`}
            >
              {statusConfig.label}
            </span>
          </div>
        </div>

        {/* Card content */}
        <div className="p-5">
          <h3 className="text-xl font-bold text-gray-900 mb-2 line-clamp-1">
            {trip.name}
          </h3>
          <p className="text-sm text-gray-600 mb-4 line-clamp-2 min-h-[2.5rem]">
            {trip.description}
          </p>

          {/* Trip details */}
          <div className="space-y-2">
            <div className="flex items-center text-sm text-gray-700">
              <Calendar className="w-4 h-4 mr-2 text-gray-400" />
              <span>
                {startDate} - {endDate}
              </span>
            </div>
            <div className="flex items-center text-sm text-gray-700">
              <Calendar className="w-4 h-4 mr-2 text-gray-400" />
              <span>{duration} days</span>
            </div>
            <div className="flex items-center text-sm text-gray-700">
              <DollarSign className="w-4 h-4 mr-2 text-gray-400" />
              <span>${Number(trip.requirements.budget).toLocaleString()}</span>
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}

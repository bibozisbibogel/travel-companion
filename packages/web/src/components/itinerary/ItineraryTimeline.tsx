/**
 * ItineraryTimeline Component
 * Main timeline component displaying the complete trip itinerary day by day
 * Story 3.2 - Task 1: Create Itinerary Timeline Component
 */

'use client';

import React, { useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  Printer,
  MapPin,
  Calendar as CalendarIcon,
} from 'lucide-react';
import { IFullTripItinerary } from '@/lib/types';
import { DayCard } from './DayCard';

interface ItineraryTimelineProps {
  itinerary: IFullTripItinerary;
}

export const ItineraryTimeline: React.FC<ItineraryTimelineProps> = ({ itinerary }) => {
  const [currentDayIndex, setCurrentDayIndex] = useState(0);
  const [allExpanded, setAllExpanded] = useState(false);

  const currentDay = itinerary.itinerary[currentDayIndex];
  const totalDays = itinerary.itinerary.length;

  const handlePreviousDay = () => {
    if (currentDayIndex > 0) {
      setCurrentDayIndex(currentDayIndex - 1);
      scrollToTop();
    }
  };

  const handleNextDay = () => {
    if (currentDayIndex < totalDays - 1) {
      setCurrentDayIndex(currentDayIndex + 1);
      scrollToTop();
    }
  };

  const handleJumpToDay = (dayIndex: number) => {
    setCurrentDayIndex(dayIndex);
    scrollToTop();
  };

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleExpandAll = () => {
    setAllExpanded(true);
  };

  const handleCollapseAll = () => {
    setAllExpanded(false);
  };

  const handlePrint = () => {
    window.print();
  };

  const currency = itinerary.trip.budget.currency;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Trip Header */}
      <div className="bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl shadow-lg p-6 mb-8 text-white">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <MapPin className="w-5 h-5" />
              <span className="text-sm font-medium opacity-90">Your Journey</span>
            </div>
            <h1 className="text-3xl font-bold mb-2">
              {itinerary.trip.destination.city}, {itinerary.trip.destination.country}
            </h1>
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1">
                <CalendarIcon className="w-4 h-4" />
                <span>
                  {itinerary.trip.dates.start} to {itinerary.trip.dates.end}
                </span>
              </div>
              <span>•</span>
              <span>{itinerary.trip.dates.duration_days} days</span>
              <span>•</span>
              <span>
                {itinerary.trip.travelers.count}{' '}
                {itinerary.trip.travelers.count === 1 ? 'traveler' : 'travelers'}
              </span>
            </div>
          </div>

          <div className="flex flex-col items-start md:items-end">
            <span className="text-sm font-medium opacity-90 mb-1">Total Budget</span>
            <span className="text-3xl font-bold">
              {new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency,
              }).format(parseFloat(itinerary.trip.budget.total))}
            </span>
            <span className="text-sm opacity-90">
              {new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency,
              }).format(parseFloat(itinerary.trip.budget.remaining))}{' '}
              remaining
            </span>
          </div>
        </div>
      </div>

      {/* Controls Bar */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          {/* Day Navigation */}
          <div className="flex items-center gap-3">
            <button
              onClick={handlePreviousDay}
              disabled={currentDayIndex === 0}
              className="p-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              aria-label="Previous day"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">Jump to:</span>
              <select
                value={currentDayIndex}
                onChange={(e) => handleJumpToDay(Number(e.target.value))}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {itinerary.itinerary.map((day, index) => (
                  <option key={index} value={index}>
                    Day {day.day} - {day.title}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleNextDay}
              disabled={currentDayIndex === totalDays - 1}
              className="p-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              aria-label="Next day"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>

          {/* View Controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={allExpanded ? handleCollapseAll : handleExpandAll}
              className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              {allExpanded ? (
                <>
                  <Minimize2 className="w-4 h-4" />
                  <span className="hidden sm:inline">Collapse All</span>
                </>
              ) : (
                <>
                  <Maximize2 className="w-4 h-4" />
                  <span className="hidden sm:inline">Expand All</span>
                </>
              )}
            </button>

            <button
              onClick={handlePrint}
              className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors print:hidden"
              aria-label="Print itinerary"
            >
              <Printer className="w-4 h-4" />
              <span className="hidden sm:inline">Print</span>
            </button>
          </div>
        </div>
      </div>

      {/* Timeline - Show All Days or Single Day */}
      <div className="space-y-6">
        {allExpanded ? (
          // Show all days when expanded
          itinerary.itinerary.map((day, index) => (
            <DayCard
              key={`day-${index}`}
              day={day}
              currency={currency}
              isFirstDay={index === 0}
              isLastDay={index === totalDays - 1}
              tripBudget={itinerary.trip.budget}
              defaultExpanded={true}
            />
          ))
        ) : currentDay ? (
          // Show only current day when not expanded
          <DayCard
            key={`day-${currentDayIndex}`}
            day={currentDay}
            currency={currency}
            isFirstDay={currentDayIndex === 0}
            isLastDay={currentDayIndex === totalDays - 1}
            tripBudget={itinerary.trip.budget}
            defaultExpanded={true}
          />
        ) : null}
      </div>

      {/* Progress Indicator */}
      {!allExpanded && (
        <div className="mt-8 bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Trip Progress</span>
            <span className="text-sm text-gray-600">
              Day {currentDayIndex + 1} of {totalDays}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-gradient-to-r from-blue-500 to-indigo-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${((currentDayIndex + 1) / totalDays) * 100}%` }}
              role="progressbar"
              aria-valuenow={currentDayIndex + 1}
              aria-valuemin={1}
              aria-valuemax={totalDays}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default ItineraryTimeline;

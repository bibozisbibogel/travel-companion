/**
 * Unit tests for itinerary utility functions
 * Story 3.2: Day-by-Day Itinerary Timeline Visualization
 */

import { describe, it, expect } from 'vitest';
import {
  getTimeOfDay,
  groupActivitiesByTimeOfDay,
  formatTime,
  formatDuration,
  calculateTimeRange,
  formatDate,
  formatCurrency,
  getCategoryLabel,
  getTimeOfDayLabel,
  sortActivitiesByTime,
  ACTIVITY_COLORS,
  ACTIVITY_BG_LIGHT,
} from '../itineraryUtils';
import type { IItineraryActivity } from '../types';

describe('itineraryUtils', () => {
  describe('getTimeOfDay', () => {
    it('should return morning for times between 5:00 and 11:59', () => {
      expect(getTimeOfDay('05:00')).toBe('morning');
      expect(getTimeOfDay('08:30')).toBe('morning');
      expect(getTimeOfDay('11:59')).toBe('morning');
    });

    it('should return afternoon for times between 12:00 and 16:59', () => {
      expect(getTimeOfDay('12:00')).toBe('afternoon');
      expect(getTimeOfDay('14:30')).toBe('afternoon');
      expect(getTimeOfDay('16:59')).toBe('afternoon');
    });

    it('should return evening for times between 17:00 and 20:59', () => {
      expect(getTimeOfDay('17:00')).toBe('evening');
      expect(getTimeOfDay('19:30')).toBe('evening');
      expect(getTimeOfDay('20:59')).toBe('evening');
    });

    it('should return night for times between 21:00 and 04:59', () => {
      expect(getTimeOfDay('21:00')).toBe('night');
      expect(getTimeOfDay('23:30')).toBe('night');
      expect(getTimeOfDay('00:00')).toBe('night');
      expect(getTimeOfDay('04:59')).toBe('night');
    });
  });

  describe('groupActivitiesByTimeOfDay', () => {
    const mockActivities: IItineraryActivity[] = [
      {
        time_start: '09:00',
        time_end: null,
        category: 'sightseeing',
        title: 'Morning Activity',
        description: 'Test',
      },
      {
        time_start: '14:00',
        time_end: null,
        category: 'cultural',
        title: 'Afternoon Activity',
        description: 'Test',
      },
      {
        time_start: '19:00',
        time_end: null,
        category: 'dining',
        title: 'Evening Activity',
        description: 'Test',
      },
      {
        time_start: '22:00',
        time_end: null,
        category: 'nightlife',
        title: 'Night Activity',
        description: 'Test',
      },
    ];

    it('should group activities by time of day', () => {
      const grouped = groupActivitiesByTimeOfDay(mockActivities);

      expect(grouped.morning).toHaveLength(1);
      expect(grouped.afternoon).toHaveLength(1);
      expect(grouped.evening).toHaveLength(1);
      expect(grouped.night).toHaveLength(1);
    });

    it('should return empty arrays for time slots with no activities', () => {
      const singleActivity: IItineraryActivity[] = [
        {
          time_start: '09:00',
          time_end: null,
          category: 'sightseeing',
          title: 'Morning Only',
          description: 'Test',
        },
      ];

      const grouped = groupActivitiesByTimeOfDay(singleActivity);

      expect(grouped.morning).toHaveLength(1);
      expect(grouped.afternoon).toHaveLength(0);
      expect(grouped.evening).toHaveLength(0);
      expect(grouped.night).toHaveLength(0);
    });
  });

  describe('formatTime', () => {
    it('should format 24-hour time to 12-hour format with AM/PM', () => {
      expect(formatTime('09:00')).toBe('9:00 AM');
      expect(formatTime('13:30')).toBe('1:30 PM');
      expect(formatTime('00:00')).toBe('12:00 AM');
      expect(formatTime('12:00')).toBe('12:00 PM');
    });

    it('should handle edge cases', () => {
      expect(formatTime('23:59')).toBe('11:59 PM');
      expect(formatTime('01:00')).toBe('1:00 AM');
    });
  });

  describe('formatDuration', () => {
    it('should format duration in minutes only when less than 60', () => {
      expect(formatDuration(30)).toBe('30m');
      expect(formatDuration(45)).toBe('45m');
    });

    it('should format duration in hours only when evenly divisible', () => {
      expect(formatDuration(60)).toBe('1h');
      expect(formatDuration(120)).toBe('2h');
      expect(formatDuration(180)).toBe('3h');
    });

    it('should format duration in hours and minutes when mixed', () => {
      expect(formatDuration(90)).toBe('1h 30m');
      expect(formatDuration(135)).toBe('2h 15m');
      expect(formatDuration(195)).toBe('3h 15m');
    });
  });

  describe('calculateTimeRange', () => {
    it('should return formatted start time when no duration provided', () => {
      expect(calculateTimeRange('09:00')).toBe('9:00 AM');
    });

    it('should calculate and format time range with duration', () => {
      expect(calculateTimeRange('09:00', 60)).toBe('9:00 AM - 10:00 AM');
      expect(calculateTimeRange('14:30', 90)).toBe('2:30 PM - 4:00 PM');
    });

    it('should handle time ranges crossing noon', () => {
      expect(calculateTimeRange('11:00', 120)).toBe('11:00 AM - 1:00 PM');
    });

    it('should handle time ranges crossing midnight', () => {
      const result = calculateTimeRange('23:00', 120);
      expect(result).toBe('11:00 PM - 1:00 AM');
    });
  });

  describe('formatDate', () => {
    it('should format ISO date string to readable format', () => {
      expect(formatDate('2025-10-18')).toBe('October 18, 2025');
      expect(formatDate('2025-01-01')).toBe('January 1, 2025');
      expect(formatDate('2025-12-31')).toBe('December 31, 2025');
    });
  });

  describe('formatCurrency', () => {
    it('should format currency with default EUR', () => {
      expect(formatCurrency('100.00')).toBe('€100.00');
      expect(formatCurrency('1000.50')).toBe('€1,000.50');
    });

    it('should format currency with specified currency code', () => {
      expect(formatCurrency('100.00', 'USD')).toBe('$100.00');
      expect(formatCurrency('100.00', 'GBP')).toBe('£100.00');
    });

    it('should handle decimal values correctly', () => {
      expect(formatCurrency('99.99', 'USD')).toBe('$99.99');
      expect(formatCurrency('1234.56', 'EUR')).toBe('€1,234.56');
    });
  });

  describe('getCategoryLabel', () => {
    it('should capitalize category names', () => {
      expect(getCategoryLabel('adventure')).toBe('Adventure');
      expect(getCategoryLabel('cultural')).toBe('Cultural');
      expect(getCategoryLabel('sightseeing')).toBe('Sightseeing');
    });
  });

  describe('getTimeOfDayLabel', () => {
    it('should return proper labels for time of day', () => {
      expect(getTimeOfDayLabel('morning')).toBe('Morning');
      expect(getTimeOfDayLabel('afternoon')).toBe('Afternoon');
      expect(getTimeOfDayLabel('evening')).toBe('Evening');
      expect(getTimeOfDayLabel('night')).toBe('Night');
    });
  });

  describe('sortActivitiesByTime', () => {
    it('should sort activities by start time ascending', () => {
      const activities: IItineraryActivity[] = [
        {
          time_start: '14:00',
          time_end: null,
          category: 'cultural',
          title: 'Afternoon',
          description: 'Test',
        },
        {
          time_start: '09:00',
          time_end: null,
          category: 'sightseeing',
          title: 'Morning',
          description: 'Test',
        },
        {
          time_start: '19:00',
          time_end: null,
          category: 'dining',
          title: 'Evening',
          description: 'Test',
        },
      ];

      const sorted = sortActivitiesByTime(activities);

      expect(sorted[0].time_start).toBe('09:00');
      expect(sorted[1].time_start).toBe('14:00');
      expect(sorted[2].time_start).toBe('19:00');
    });

    it('should sort by minutes when hours are the same', () => {
      const activities: IItineraryActivity[] = [
        {
          time_start: '09:30',
          time_end: null,
          category: 'cultural',
          title: 'Second',
          description: 'Test',
        },
        {
          time_start: '09:00',
          time_end: null,
          category: 'sightseeing',
          title: 'First',
          description: 'Test',
        },
      ];

      const sorted = sortActivitiesByTime(activities);

      expect(sorted[0].time_start).toBe('09:00');
      expect(sorted[1].time_start).toBe('09:30');
    });

    it('should not mutate the original array', () => {
      const activities: IItineraryActivity[] = [
        {
          time_start: '14:00',
          time_end: null,
          category: 'cultural',
          title: 'Afternoon',
          description: 'Test',
        },
        {
          time_start: '09:00',
          time_end: null,
          category: 'sightseeing',
          title: 'Morning',
          description: 'Test',
        },
      ];

      const original = [...activities];
      sortActivitiesByTime(activities);

      expect(activities).toEqual(original);
    });
  });

  describe('Color constants', () => {
    it('should have colors defined for all activity categories', () => {
      const categories = [
        'transportation',
        'accommodation',
        'attraction',
        'dining',
        'exploration',
        'entertainment',
        'shopping',
        'other',
      ];

      categories.forEach((category) => {
        expect(ACTIVITY_COLORS[category as keyof typeof ACTIVITY_COLORS]).toBeDefined();
        expect(ACTIVITY_BG_LIGHT[category as keyof typeof ACTIVITY_BG_LIGHT]).toBeDefined();
      });
    });

    it('should use valid hex color codes', () => {
      const hexColorRegex = /^#[0-9A-F]{6}$/i;

      Object.values(ACTIVITY_COLORS).forEach((color) => {
        expect(color).toMatch(hexColorRegex);
      });
    });
  });
});

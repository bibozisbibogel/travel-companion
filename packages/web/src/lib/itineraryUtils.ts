/**
 * Utility functions for itinerary timeline visualization
 */

import {
  ActivityCategory,
  TimeOfDay,
  IItineraryActivity,
  IMealRecommendation,
} from './types';
import {
  Compass,
  Landmark,
  Palmtree,
  Utensils,
  Music,
  ShoppingBag,
  Car,
  Camera,
  Theater,
  LucideIcon,
} from 'lucide-react';

/**
 * Color coding for activity categories as per Story 3.2 design system
 */
export const ACTIVITY_COLORS: Record<ActivityCategory, string> = {
  adventure: '#3B82F6', // Blue
  cultural: '#8B5CF6', // Purple
  relaxation: '#10B981', // Green
  dining: '#F59E0B', // Orange
  nightlife: '#EC4899', // Pink
  shopping: '#14B8A6', // Teal
  transportation: '#6B7280', // Gray
  sightseeing: '#3B82F6', // Blue
  entertainment: '#EC4899', // Pink
};

/**
 * Icon mapping for activity categories
 */
export const ACTIVITY_ICONS: Record<ActivityCategory, LucideIcon> = {
  adventure: Compass,
  cultural: Landmark,
  relaxation: Palmtree,
  dining: Utensils,
  nightlife: Music,
  shopping: ShoppingBag,
  transportation: Car,
  sightseeing: Camera,
  entertainment: Theater,
};

/**
 * Tailwind CSS class mapping for activity colors
 */
export const ACTIVITY_TAILWIND_COLORS: Record<ActivityCategory, string> = {
  adventure: 'bg-blue-500 text-blue-900 border-blue-300',
  cultural: 'bg-purple-500 text-purple-900 border-purple-300',
  relaxation: 'bg-green-500 text-green-900 border-green-300',
  dining: 'bg-orange-500 text-orange-900 border-orange-300',
  nightlife: 'bg-pink-500 text-pink-900 border-pink-300',
  shopping: 'bg-teal-500 text-teal-900 border-teal-300',
  transportation: 'bg-gray-400 text-gray-900 border-gray-300',
  sightseeing: 'bg-blue-500 text-blue-900 border-blue-300',
  entertainment: 'bg-pink-500 text-pink-900 border-pink-300',
};

/**
 * Light background colors for activity cards
 */
export const ACTIVITY_BG_LIGHT: Record<ActivityCategory, string> = {
  adventure: 'bg-blue-50',
  cultural: 'bg-purple-50',
  relaxation: 'bg-green-50',
  dining: 'bg-orange-50',
  nightlife: 'bg-pink-50',
  shopping: 'bg-teal-50',
  transportation: 'bg-gray-50',
  sightseeing: 'bg-blue-50',
  entertainment: 'bg-pink-50',
};

/**
 * Determine time of day from a time string (HH:MM format)
 */
export function getTimeOfDay(timeString: string): TimeOfDay {
  const hour = parseInt(timeString.split(':')[0], 10);

  if (hour >= 5 && hour < 12) return 'morning';
  if (hour >= 12 && hour < 17) return 'afternoon';
  if (hour >= 17 && hour < 21) return 'evening';
  return 'night';
}

/**
 * Group activities by time of day
 */
export function groupActivitiesByTimeOfDay(
  activities: IItineraryActivity[]
): Record<TimeOfDay, IItineraryActivity[]> {
  const grouped: Record<TimeOfDay, IItineraryActivity[]> = {
    morning: [],
    afternoon: [],
    evening: [],
    night: [],
  };

  activities.forEach((activity) => {
    const timeOfDay = getTimeOfDay(activity.time_start);
    grouped[timeOfDay].push(activity);
  });

  return grouped;
}

/**
 * Format time string to display format (e.g., "09:00" -> "9:00 AM")
 */
export function formatTime(timeString: string): string {
  const [hours, minutes] = timeString.split(':');
  const hour = parseInt(hours, 10);
  const period = hour >= 12 ? 'PM' : 'AM';
  const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;

  return `${displayHour}:${minutes} ${period}`;
}

/**
 * Format duration in minutes to readable string
 */
export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  if (hours === 0) return `${minutes}m`;
  if (remainingMinutes === 0) return `${hours}h`;
  return `${hours}h ${remainingMinutes}m`;
}

/**
 * Calculate estimated time range for an activity
 */
export function calculateTimeRange(
  startTime: string,
  durationMinutes?: number
): string {
  if (!durationMinutes) return formatTime(startTime);

  const [hours, minutes] = startTime.split(':').map(Number);
  const startDate = new Date(2000, 0, 1, hours, minutes);
  const endDate = new Date(startDate.getTime() + durationMinutes * 60000);

  const endHours = endDate.getHours();
  const endMinutes = endDate.getMinutes();
  const endTime = `${endHours.toString().padStart(2, '0')}:${endMinutes
    .toString()
    .padStart(2, '0')}`;

  return `${formatTime(startTime)} - ${formatTime(endTime)}`;
}

/**
 * Format date to display format (e.g., "2025-10-18" -> "October 18, 2025")
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

/**
 * Format currency amount
 */
export function formatCurrency(amount: string, currency: string = 'EUR'): string {
  const numAmount = parseFloat(amount);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
  }).format(numAmount);
}

/**
 * Get category label for display
 */
export function getCategoryLabel(category: ActivityCategory): string {
  return category.charAt(0).toUpperCase() + category.slice(1);
}

/**
 * Get time of day label for display
 */
export function getTimeOfDayLabel(timeOfDay: TimeOfDay): string {
  const labels: Record<TimeOfDay, string> = {
    morning: 'Morning',
    afternoon: 'Afternoon',
    evening: 'Evening',
    night: 'Night',
  };
  return labels[timeOfDay];
}

/**
 * Group meals by meal type
 */
export function groupMealsByType(
  meals: IMealRecommendation[]
): Record<string, IMealRecommendation[]> {
  const grouped: Record<string, IMealRecommendation[]> = {
    breakfast: [],
    lunch: [],
    dinner: [],
  };

  meals.forEach((meal) => {
    grouped[meal.meal_type].push(meal);
  });

  return grouped;
}

/**
 * Sort activities by time
 */
export function sortActivitiesByTime(
  activities: IItineraryActivity[]
): IItineraryActivity[] {
  return [...activities].sort((a, b) => {
    const timeA = a.time_start.split(':').map(Number);
    const timeB = b.time_start.split(':').map(Number);

    if (timeA[0] !== timeB[0]) return timeA[0] - timeB[0];
    return timeA[1] - timeB[1];
  });
}

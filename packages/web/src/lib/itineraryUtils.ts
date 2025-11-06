/**
 * Utility functions for itinerary timeline visualization
 */

import {
  ActivityCategory,
  TimeOfDay,
  IItineraryActivity,
  IMealRecommendation,
  IDailyItinerary,
  IFullTripItinerary,
  IAccommodationInfo,
  MealType,
} from './types';
import {
  Compass,
  Landmark,
  Utensils,
  ShoppingBag,
  Car,
  Theater,
  Hotel,
  MapPin,
  LucideIcon,
} from 'lucide-react';

/**
 * Color coding for activity categories (updated to match backend categories - Story 3.6)
 */
export const ACTIVITY_COLORS: Record<ActivityCategory, string> = {
  transportation: '#3B82F6', // Blue
  accommodation: '#EF4444', // Red
  attraction: '#8B5CF6', // Purple
  dining: '#F59E0B', // Amber
  exploration: '#10B981', // Green
  entertainment: '#EC4899', // Pink
  shopping: '#14B8A6', // Teal
  other: '#6B7280', // Gray
};

/**
 * Icon mapping for activity categories (updated to match backend categories - Story 3.6)
 */
export const ACTIVITY_ICONS: Record<ActivityCategory, LucideIcon> = {
  transportation: Car,
  accommodation: Hotel,
  attraction: Landmark,
  dining: Utensils,
  exploration: Compass,
  entertainment: Theater,
  shopping: ShoppingBag,
  other: MapPin,
};

/**
 * Tailwind CSS class mapping for activity colors (updated to match backend categories - Story 3.6)
 */
export const ACTIVITY_TAILWIND_COLORS: Record<ActivityCategory, string> = {
  transportation: 'bg-blue-500 text-blue-900 border-blue-300',
  accommodation: 'bg-red-500 text-red-900 border-red-300',
  attraction: 'bg-purple-500 text-purple-900 border-purple-300',
  dining: 'bg-amber-500 text-amber-900 border-amber-300',
  exploration: 'bg-green-500 text-green-900 border-green-300',
  entertainment: 'bg-pink-500 text-pink-900 border-pink-300',
  shopping: 'bg-teal-500 text-teal-900 border-teal-300',
  other: 'bg-gray-500 text-gray-900 border-gray-300',
};

/**
 * Light background colors for activity cards (updated to match backend categories - Story 3.6)
 */
export const ACTIVITY_BG_LIGHT: Record<ActivityCategory, string> = {
  transportation: 'bg-blue-50',
  accommodation: 'bg-red-50',
  attraction: 'bg-purple-50',
  dining: 'bg-amber-50',
  exploration: 'bg-green-50',
  entertainment: 'bg-pink-50',
  shopping: 'bg-teal-50',
  other: 'bg-gray-50',
};

/**
 * Determine time of day from a time string (HH:MM format)
 */
export function getTimeOfDay(timeString: string | null): TimeOfDay {
  if (!timeString) return 'morning'; // Default to morning if no time specified

  const hourStr = timeString.split(':')[0];
  if (!hourStr) return 'morning';

  const hour = parseInt(hourStr, 10);

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
export function formatTime(timeString: string | null): string {
  if (!timeString) return 'Time TBD';

  const [hours, minutes] = timeString.split(':');
  if (!hours || !minutes) return 'Time TBD';

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
  startTime: string | null,
  durationMinutes?: number
): string {
  if (!startTime) return 'Time TBD';
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
    const mealType = meal.meal_type;
    if (!grouped[mealType]) {
      grouped[mealType] = [];
    }
    grouped[mealType]!.push(meal);
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
    // Activities without time go to the end
    if (!a.time_start && !b.time_start) return 0;
    if (!a.time_start) return 1;
    if (!b.time_start) return -1;

    const timeA = a.time_start.split(':').map(Number);
    const timeB = b.time_start.split(':').map(Number);

    const hourA = timeA[0] ?? 0;
    const hourB = timeB[0] ?? 0;
    const minA = timeA[1] ?? 0;
    const minB = timeB[1] ?? 0;

    if (hourA !== hourB) return hourA - hourB;
    return minA - minB;
  });
}

/**
 * Extract meals from activities and convert to IMealRecommendation format
 * Backend returns meals as activities with category "dining"
 */
export function extractMealsFromActivities(
  activities: IItineraryActivity[]
): IMealRecommendation[] {
  return activities
    .filter((activity) => activity.category === 'dining')
    .map((activity): IMealRecommendation => {
      // Access the meal_type and venue fields that exist in dining activities
      const activityWithMeal = activity as any;
      const venue = activityWithMeal.venue || {};

      // Calculate price_range from cost estimate fields (backend uses cost_estimate_min/max)
      let priceRange = '';
      if (activityWithMeal.cost_estimate_min && activityWithMeal.cost_estimate_max) {
        priceRange = `${activityWithMeal.cost_estimate_min}-${activityWithMeal.cost_estimate_max}`;
      } else if (activityWithMeal.cost_estimate_min) {
        priceRange = activityWithMeal.cost_estimate_min;
      } else if (activityWithMeal.cost_per_person) {
        const cost = parseFloat(activityWithMeal.cost_per_person);
        // Estimate a range (±20%)
        const min = Math.floor(cost * 0.8);
        const max = Math.ceil(cost * 1.2);
        priceRange = `${min}-${max}`;
      } else if (activityWithMeal.total_cost) {
        priceRange = activityWithMeal.total_cost;
      } else if (activity.price) {
        priceRange = activity.price;
      }

      return {
        restaurant_name: venue.name || activity.title,
        cuisine_type: venue.cuisine || 'Local Cuisine',
        meal_type: (activityWithMeal.meal_type || 'lunch') as MealType,
        time: activity.time_start || '12:00',
        price_range: priceRange,
        rating: venue.rating,
        location: activity.location || venue.location,
        description: activity.description || undefined,
      };
    });
}

/**
 * Filter out dining activities from the activities list
 * Since meals are displayed separately, we don't want to show them twice
 */
export function filterOutDiningActivities(
  activities: IItineraryActivity[]
): IItineraryActivity[] {
  return activities.filter((activity) => activity.category !== 'dining');
}

/**
 * Parse the daily_cost.breakdown string to extract category costs
 * Format: "Attractions (51), Meals (69-96)" or "Activities (100), Accommodation (150)"
 */
export function parseDailyCostBreakdown(
  breakdown: string | undefined
): {
  activities: number;
  meals: number;
  accommodation: number;
} {
  const result = {
    activities: 0,
    meals: 0,
    accommodation: 0,
  };

  if (!breakdown) return result;

  // Match patterns like "Category (amount)" or "Category (min-max)"
  const regex = /(\w+)\s*\(([^)]+)\)/g;
  let match;

  while ((match = regex.exec(breakdown)) !== null) {
    const category = match[1]?.toLowerCase() || '';
    const valueStr = match[2] || '';

    // Parse the value (could be single number or range like "69-96")
    let value = 0;
    if (valueStr.includes('-')) {
      // It's a range, take the average
      const parts = valueStr.split('-');
      const min = parseFloat(parts[0] || '0');
      const max = parseFloat(parts[1] || '0');
      value = (min + max) / 2;
    } else {
      value = parseFloat(valueStr);
    }

    // Map category names to our structure
    if (category.includes('meal') || category.includes('food') || category.includes('dining')) {
      result.meals += value;
    } else if (
      category.includes('accommod') ||
      category.includes('hotel') ||
      category.includes('lodging')
    ) {
      result.accommodation += value;
    } else if (
      category.includes('activit') ||
      category.includes('attraction') ||
      category.includes('entertain') ||
      category.includes('tour')
    ) {
      result.activities += value;
    }
  }

  return result;
}

/**
 * Transform backend itinerary response to frontend format
 * Extracts meals from activities and distributes accommodation per day
 */
export function transformItineraryResponse(
  backendData: IFullTripItinerary
): IFullTripItinerary {
  const topLevelAccommodation = backendData.accommodation;

  const transformedItinerary: IDailyItinerary[] = backendData.itinerary.map((day) => {
    // Extract meals from dining activities
    const meals = extractMealsFromActivities(day.activities);

    // Filter out dining activities since they're now in meals
    const nonDiningActivities = filterOutDiningActivities(day.activities);

    // Distribute accommodation to each day (the same accommodation for all days)
    return {
      ...day,
      activities: nonDiningActivities,
      meals: meals.length > 0 ? meals : undefined,
      accommodation: topLevelAccommodation,
    };
  });

  return {
    ...backendData,
    itinerary: transformedItinerary,
  };
}

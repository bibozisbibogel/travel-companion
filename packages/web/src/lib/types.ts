/**
 * Shared TypeScript type definitions for the Travel Companion frontend
 */

export interface IUser {
  id: string;
  email: string;
  name: string;
  createdAt: string;
}

export interface ITripRequest {
  destination: string;
  origin?: string;
  startDate: string;
  endDate: string;
  budget?: {
    amount: number;
    currency: string;
  };
  travelers: {
    adults: number;
    children: number;
    infants: number;
  };
  preferences?: string[];
  dietaryRestrictions?: string[];
  accommodationTypes?: string[];
  cuisinePreferences?: string[];
}

export interface IFlightOption {
  id: string;
  airline: string;
  origin: string;
  destination: string;
  departureTime: string;
  arrivalTime: string;
  price: number;
  duration: string;
}

// Authentication Types
export interface ILoginRequest {
  email: string;
  password: string;
}

export interface IRegisterRequest {
  firstName: string;
  lastName?: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export interface IAuthResponse {
  // Backend actual response fields
  access_token?: string;
  token_type?: string;
  expires_in?: number;
  user?: IUser;
  // Error handling fields
  message?: string;
  errors?: Record<string, string[]>;
  detail?: { message?: string; error_code?: string };
}

// Form validation types
export interface IPasswordStrength {
  score: number; // 0-4
  feedback: {
    warning?: string;
    suggestions: string[];
  };
  isValid: boolean;
}

export interface IFormError {
  field: string;
  message: string;
}

// Travel Request Types
export interface ITravelPreference {
  id: string;
  label: string;
  icon: string;
  description?: string;
}

export interface IDestination {
  id: string;
  name: string;
  country: string;
  type: 'city' | 'region' | 'landmark';
  coordinates?: {
    lat: number;
    lng: number;
  };
}

export interface ITripPlanResponse {
  success: boolean;
  data?: {
    tripId: string;
    destination: string;
    itinerary: any;
    estimatedCost: number;
  };
  message?: string;
  errors?: Record<string, string[]>;
}

// API Client Configuration Types
export interface IRetryConfig {
  attempts: number;
  delay: number; // milliseconds
  retryOn: number[]; // HTTP status codes to retry on
}

export interface IApiRequestConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  data?: unknown;
  headers?: HeadersInit;
  timeout?: number;
  retryConfig?: IRetryConfig;
}

// Enhanced API Response Types
export interface IApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  errors?: Record<string, string[]>;
  meta?: {
    timestamp: string;
    requestId?: string;
    pagination?: {
      page: number;
      limit: number;
      total: number;
      totalPages: number;
    };
  };
}

// Hotel and Accommodation Types
export interface IHotelOption {
  id: string;
  name: string;
  address: string;
  city: string;
  country: string;
  rating: number;
  pricePerNight: number;
  currency: string;
  amenities: string[];
  images: string[];
  coordinates?: {
    lat: number;
    lng: number;
  };
}

// Activity and Experience Types
export interface IActivity {
  id: string;
  name: string;
  description: string;
  type: 'tour' | 'experience' | 'attraction' | 'restaurant' | 'entertainment';
  duration: string;
  price: number;
  currency: string;
  rating: number;
  location: string;
  coordinates?: {
    lat: number;
    lng: number;
  };
  availableTimes: string[];
}

// Complete Trip Itinerary Types
export interface IItineraryDay {
  date: string;
  dayNumber: number;
  activities: IActivity[];
  accommodation?: IHotelOption;
  transportation?: {
    type: 'flight' | 'train' | 'bus' | 'car' | 'walking';
    details: string;
    duration?: string;
    cost?: number;
  };
  estimatedBudget: {
    accommodation: number;
    activities: number;
    meals: number;
    transportation: number;
    total: number;
  };
}

export interface ICompleteItinerary {
  tripId: string;
  destination: string;
  startDate: string;
  endDate: string;
  totalDays: number;
  travelers: number;
  days: IItineraryDay[];
  flights: {
    outbound: IFlightOption[];
    return: IFlightOption[];
  };
  totalBudget: {
    flights: number;
    accommodation: number;
    activities: number;
    meals: number;
    transportation: number;
    total: number;
  };
  recommendations: {
    bestTimeToVisit: string;
    weatherInfo: string;
    localCurrency: string;
    timeZone: string;
    language: string;
    tips: string[];
  };
}

// Enhanced Itinerary Timeline Types (Story 3.2)
export type ActivityCategory =
  | 'adventure'
  | 'cultural'
  | 'relaxation'
  | 'dining'
  | 'nightlife'
  | 'shopping'
  | 'transportation'
  | 'sightseeing'
  | 'entertainment';

export type TimeOfDay = 'morning' | 'afternoon' | 'evening' | 'night';

export type MealType = 'breakfast' | 'lunch' | 'dinner';

export interface IItineraryActivity {
  time_start: string;
  time_end: string | null;
  category: ActivityCategory;
  title: string;
  description: string;
  duration_minutes?: number;
  location?: string;
  price?: string;
  booking_info?: string;
}

export interface IMealRecommendation {
  restaurant_name: string;
  cuisine_type: string;
  meal_type: MealType;
  time: string;
  price_range: string;
  rating?: number;
  location?: string;
  description?: string;
}

export interface IAccommodationInfo {
  name: string;
  rating: number;
  stars: number;
  address: {
    street: string;
    postal_code: string;
    city: string;
    region: string;
    country: string;
  };
  amenities: string[];
  price_per_night: string;
  nights: number;
  total_cost: string;
  location_notes?: string;
  check_in?: string;
  check_out?: string;
}

export interface IDailyItinerary {
  day: number;
  date: string;
  day_of_week: string;
  title: string;
  activities: IItineraryActivity[];
  meals?: IMealRecommendation[];
  accommodation?: IAccommodationInfo;
  daily_cost?: {
    activities: string;
    meals: string;
    accommodation: string;
    total: string;
  };
}

export interface IFlightDetails {
  airline: string;
  flight_number: string;
  route: {
    from_airport: string;
    to_airport: string;
  };
  departure: {
    time: string;
    timezone: string;
  };
  arrival: {
    time: string;
    timezone: string;
  };
  duration_minutes: number;
  stops: number;
  price_per_person: string;
  total_price: string;
}

export interface IFullTripItinerary {
  trip: {
    destination: {
      city: string;
      country: string;
    };
    dates: {
      start: string;
      end: string;
      duration_days: number;
    };
    travelers: {
      count: number;
      type: string;
    };
    budget: {
      total: string;
      currency: string;
      spent: string;
      remaining: string;
    };
  };
  flights: {
    outbound: IFlightDetails;
    return_flight: IFlightDetails;
    total_cost: string;
  };
  accommodation: IAccommodationInfo;
  itinerary: IDailyItinerary[];
}

// Trip List Types (Story 3.5)
export type TripStatus = 'draft' | 'planning' | 'confirmed' | 'completed' | 'cancelled';

export interface ITripSummary {
  trip_id: string;
  user_id: string;
  name: string;
  description: string | null;
  destination: {
    city: string;
    country: string;
  };
  requirements: {
    budget: number;
    currency: string;
    start_date: string;
    end_date: string;
    travelers: number;
    travel_class?: string;
    accommodation_type?: string;
  };
  status: TripStatus;
  created_at: string;
  updated_at: string;
}

export interface IPaginationMeta {
  page: number;
  per_page: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface IPaginatedResponse<T> {
  data: T;
  pagination: IPaginationMeta;
  message: string;
}
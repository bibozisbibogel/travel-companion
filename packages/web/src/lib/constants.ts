/**
 * Constants and data for Travel Companion application
 */

import type { ITravelPreference, IDestination } from './types'

// Travel preferences with icons
export const TRAVEL_PREFERENCES: ITravelPreference[] = [
  { id: 'adventure', label: 'Adventure & Outdoor', icon: '🏔️' },
  { id: 'culture', label: 'Culture & History', icon: '🏛️' },
  { id: 'relaxation', label: 'Beach & Relaxation', icon: '🏖️' },
  { id: 'food', label: 'Food & Culinary', icon: '🍜' },
  { id: 'nightlife', label: 'Nightlife & Entertainment', icon: '🌃' },
  { id: 'nature', label: 'Nature & Wildlife', icon: '🦋' },
  { id: 'shopping', label: 'Shopping & Fashion', icon: '🛍️' },
  { id: 'art', label: 'Art & Museums', icon: '🎨' },
  { id: 'sports', label: 'Sports & Events', icon: '⚽' },
  { id: 'wellness', label: 'Wellness & Spa', icon: '🧘' },
]

// Popular destinations (fallback data)
export const POPULAR_DESTINATIONS: IDestination[] = [
  {
    id: 'tokyo',
    name: 'Tokyo',
    country: 'Japan',
    type: 'city',
    coordinates: { lat: 35.6762, lng: 139.6503 },
  },
  {
    id: 'paris',
    name: 'Paris',
    country: 'France',
    type: 'city',
    coordinates: { lat: 48.8566, lng: 2.3522 },
  },
  {
    id: 'new-york',
    name: 'New York City',
    country: 'United States',
    type: 'city',
    coordinates: { lat: 40.7128, lng: -74.0060 },
  },
  {
    id: 'london',
    name: 'London',
    country: 'United Kingdom',
    type: 'city',
    coordinates: { lat: 51.5074, lng: -0.1278 },
  },
  {
    id: 'bali',
    name: 'Bali',
    country: 'Indonesia',
    type: 'region',
    coordinates: { lat: -8.3405, lng: 115.0920 },
  },
  {
    id: 'rome',
    name: 'Rome',
    country: 'Italy',
    type: 'city',
    coordinates: { lat: 41.9028, lng: 12.4964 },
  },
  {
    id: 'barcelona',
    name: 'Barcelona',
    country: 'Spain',
    type: 'city',
    coordinates: { lat: 41.3851, lng: 2.1734 },
  },
  {
    id: 'thailand',
    name: 'Thailand',
    country: 'Thailand',
    type: 'region',
    coordinates: { lat: 15.8700, lng: 100.9925 },
  },
]

// Budget ranges for quick selection
export const BUDGET_RANGES = [
  { label: 'Budget ($500 - $1,500)', min: 500, max: 1500 },
  { label: 'Mid-range ($1,500 - $5,000)', min: 1500, max: 5000 },
  { label: 'Luxury ($5,000 - $15,000)', min: 5000, max: 15000 },
  { label: 'Ultra Luxury ($15,000+)', min: 15000, max: 50000 },
]

// Traveler count options
export const TRAVELER_OPTIONS = [
  { value: 1, label: 'Solo traveler' },
  { value: 2, label: 'Couple' },
  { value: 3, label: 'Small group (3)' },
  { value: 4, label: 'Family (4)' },
  { value: 5, label: 'Group (5)' },
  { value: 6, label: 'Large group (6+)' },
]
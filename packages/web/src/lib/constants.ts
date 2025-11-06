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

// Currency options
export const CURRENCY_OPTIONS = [
  { value: 'USD', label: 'USD ($)', symbol: '$' },
  { value: 'EUR', label: 'EUR (€)', symbol: '€' },
  { value: 'GBP', label: 'GBP (£)', symbol: '£' },
  { value: 'JPY', label: 'JPY (¥)', symbol: '¥' },
  { value: 'CAD', label: 'CAD ($)', symbol: 'C$' },
  { value: 'AUD', label: 'AUD ($)', symbol: 'A$' },
  { value: 'CHF', label: 'CHF (Fr)', symbol: 'Fr' },
  { value: 'CNY', label: 'CNY (¥)', symbol: '¥' },
]

// Dietary restrictions
export const DIETARY_RESTRICTIONS = [
  { id: 'vegetarian', label: 'Vegetarian', icon: '🥗' },
  { id: 'vegan', label: 'Vegan', icon: '🌱' },
  { id: 'gluten-free', label: 'Gluten-Free', icon: '🌾' },
  { id: 'dairy-free', label: 'Dairy-Free', icon: '🥛' },
  { id: 'halal', label: 'Halal', icon: '☪️' },
  { id: 'kosher', label: 'Kosher', icon: '✡️' },
  { id: 'nut-allergy', label: 'Nut Allergy', icon: '🥜' },
  { id: 'seafood-allergy', label: 'Seafood Allergy', icon: '🦐' },
]

// Accommodation types
export const ACCOMMODATION_TYPES = [
  { id: 'hotel', label: 'Hotel', icon: '🏨' },
  { id: 'hostel', label: 'Hostel', icon: '🛏️' },
  { id: 'apartment', label: 'Apartment', icon: '🏢' },
  { id: 'resort', label: 'Resort', icon: '🏝️' },
  { id: 'villa', label: 'Villa', icon: '🏡' },
  { id: 'boutique', label: 'Boutique Hotel', icon: '✨' },
  { id: 'bnb', label: 'B&B', icon: '🏠' },
  { id: 'camping', label: 'Camping', icon: '⛺' },
]

// Cuisine preferences - mapped to geocoding API catering categories
// Only includes catering.restaurant.X subcategories (exact match to geocoding API)
export const CUISINE_PREFERENCES = [
  // Restaurant cuisine types - Asian
  { id: 'catering.restaurant.afghan', label: 'Afghan', icon: '🍖' },
  { id: 'catering.restaurant.chinese', label: 'Chinese', icon: '🥡' },
  { id: 'catering.restaurant.filipino', label: 'Filipino', icon: '🍛' },
  { id: 'catering.restaurant.indian', label: 'Indian', icon: '🍛' },
  { id: 'catering.restaurant.indonesian', label: 'Indonesian', icon: '🍛' },
  { id: 'catering.restaurant.japanese', label: 'Japanese', icon: '🍱' },
  { id: 'catering.restaurant.korean', label: 'Korean', icon: '🍜' },
  { id: 'catering.restaurant.malay', label: 'Malay', icon: '🍛' },
  { id: 'catering.restaurant.malaysian', label: 'Malaysian', icon: '🍛' },
  { id: 'catering.restaurant.nepalese', label: 'Nepalese', icon: '🍛' },
  { id: 'catering.restaurant.pakistani', label: 'Pakistani', icon: '🍛' },
  { id: 'catering.restaurant.taiwanese', label: 'Taiwanese', icon: '🍜' },
  { id: 'catering.restaurant.thai', label: 'Thai', icon: '🍜' },
  { id: 'catering.restaurant.vietnamese', label: 'Vietnamese', icon: '🍜' },
  { id: 'catering.restaurant.asian', label: 'Asian Fusion', icon: '🍜' },

  // Restaurant cuisine types - European
  { id: 'catering.restaurant.austrian', label: 'Austrian', icon: '🥨' },
  { id: 'catering.restaurant.balkan', label: 'Balkan', icon: '🍖' },
  { id: 'catering.restaurant.bavarian', label: 'Bavarian', icon: '🥨' },
  { id: 'catering.restaurant.belgian', label: 'Belgian', icon: '🍟' },
  { id: 'catering.restaurant.croatian', label: 'Croatian', icon: '🍖' },
  { id: 'catering.restaurant.czech', label: 'Czech', icon: '🍺' },
  { id: 'catering.restaurant.danish', label: 'Danish', icon: '🧈' },
  { id: 'catering.restaurant.european', label: 'European', icon: '🍽️' },
  { id: 'catering.restaurant.french', label: 'French', icon: '🥐' },
  { id: 'catering.restaurant.georgian', label: 'Georgian', icon: '🥟' },
  { id: 'catering.restaurant.german', label: 'German', icon: '🥨' },
  { id: 'catering.restaurant.greek', label: 'Greek', icon: '🫒' },
  { id: 'catering.restaurant.hungarian', label: 'Hungarian', icon: '🍲' },
  { id: 'catering.restaurant.irish', label: 'Irish', icon: '🍀' },
  { id: 'catering.restaurant.italian', label: 'Italian', icon: '🍝' },
  { id: 'catering.restaurant.portuguese', label: 'Portuguese', icon: '🍤' },
  { id: 'catering.restaurant.russian', label: 'Russian', icon: '🥟' },
  { id: 'catering.restaurant.spanish', label: 'Spanish', icon: '🥘' },
  { id: 'catering.restaurant.swedish', label: 'Swedish', icon: '🍽️' },
  { id: 'catering.restaurant.ukrainian', label: 'Ukrainian', icon: '🥟' },

  // Restaurant cuisine types - Mediterranean & Middle Eastern
  { id: 'catering.restaurant.african', label: 'African', icon: '🍽️' },
  { id: 'catering.restaurant.arab', label: 'Arab', icon: '🥙' },
  { id: 'catering.restaurant.ethiopian', label: 'Ethiopian', icon: '🍽️' },
  { id: 'catering.restaurant.lebanese', label: 'Lebanese', icon: '🥙' },
  { id: 'catering.restaurant.mediterranean', label: 'Mediterranean', icon: '🫒' },
  { id: 'catering.restaurant.moroccan', label: 'Moroccan', icon: '🍖' },
  { id: 'catering.restaurant.persian', label: 'Persian', icon: '🍖' },
  { id: 'catering.restaurant.syrian', label: 'Syrian', icon: '🥙' },
  { id: 'catering.restaurant.turkish', label: 'Turkish', icon: '🥙' },

  // Restaurant cuisine types - Americas
  { id: 'catering.restaurant.american', label: 'American', icon: '🍔' },
  { id: 'catering.restaurant.argentinian', label: 'Argentinian', icon: '🥩' },
  { id: 'catering.restaurant.bolivian', label: 'Bolivian', icon: '🥔' },
  { id: 'catering.restaurant.brazilian', label: 'Brazilian', icon: '🥩' },
  { id: 'catering.restaurant.caribbean', label: 'Caribbean', icon: '🌴' },
  { id: 'catering.restaurant.cuban', label: 'Cuban', icon: '🍖' },
  { id: 'catering.restaurant.hawaiian', label: 'Hawaiian', icon: '🍍' },
  { id: 'catering.restaurant.jamaican', label: 'Jamaican', icon: '🌶️' },
  { id: 'catering.restaurant.latin_american', label: 'Latin American', icon: '🌮' },
  { id: 'catering.restaurant.mexican', label: 'Mexican', icon: '🌮' },
  { id: 'catering.restaurant.peruvian', label: 'Peruvian', icon: '🐟' },
  { id: 'catering.restaurant.tex-mex', label: 'Tex-Mex', icon: '🌮' },

  // Restaurant specialty types
  { id: 'catering.restaurant.barbecue', label: 'BBQ', icon: '🍖' },
  { id: 'catering.restaurant.beef_bowl', label: 'Beef Bowl', icon: '🍜' },
  { id: 'catering.restaurant.burger', label: 'Burger Restaurant', icon: '🍔' },
  { id: 'catering.restaurant.chicken', label: 'Chicken Restaurant', icon: '🍗' },
  { id: 'catering.restaurant.chili', label: 'Chili Restaurant', icon: '🌶️' },
  { id: 'catering.restaurant.curry', label: 'Curry House', icon: '🍛' },
  { id: 'catering.restaurant.dumpling', label: 'Dumpling House', icon: '🥟' },
  { id: 'catering.restaurant.fish', label: 'Fish Restaurant', icon: '🐟' },
  { id: 'catering.restaurant.fish_and_chips', label: 'Fish & Chips Restaurant', icon: '🐟' },
  { id: 'catering.restaurant.friture', label: 'Friture', icon: '🍟' },
  { id: 'catering.restaurant.kebab', label: 'Kebab Restaurant', icon: '🥙' },
  { id: 'catering.restaurant.noodle', label: 'Noodle Restaurant', icon: '🍜' },
  { id: 'catering.restaurant.pita', label: 'Pita Restaurant', icon: '🥙' },
  { id: 'catering.restaurant.pizza', label: 'Pizzeria', icon: '🍕' },
  { id: 'catering.restaurant.ramen', label: 'Ramen Restaurant', icon: '🍜' },
  { id: 'catering.restaurant.sandwich', label: 'Sandwich Restaurant', icon: '🥪' },
  { id: 'catering.restaurant.seafood', label: 'Seafood', icon: '🦞' },
  { id: 'catering.restaurant.soup', label: 'Soup Restaurant', icon: '🍲' },
  { id: 'catering.restaurant.steak_house', label: 'Steakhouse', icon: '🥩' },
  { id: 'catering.restaurant.sushi', label: 'Sushi', icon: '🍣' },
  { id: 'catering.restaurant.tacos', label: 'Taco Restaurant', icon: '🌮' },
  { id: 'catering.restaurant.tapas', label: 'Tapas Restaurant', icon: '🍢' },
  { id: 'catering.restaurant.wings', label: 'Wings Restaurant', icon: '🍗' },

  // Restaurant general categories
  { id: 'catering.restaurant.international', label: 'International', icon: '🌍' },
  { id: 'catering.restaurant.oriental', label: 'Oriental', icon: '🍜' },
  { id: 'catering.restaurant.regional', label: 'Regional', icon: '🍽️' },
  { id: 'catering.restaurant.uzbek', label: 'Uzbek', icon: '🍖' },
  { id: 'catering.restaurant.western', label: 'Western', icon: '🍽️' },
]
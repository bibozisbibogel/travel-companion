/**
 * Data transformers for API requests
 * Converts frontend data formats to backend-expected formats
 */

import type { TravelRequestFormData } from './validation'

interface BackendTripPlanRequest {
  destination: {
    city: string
    country: string
    country_code: string
    airport_code?: string
    latitude?: number
    longitude?: number
  }
  requirements: {
    budget: string // Send as string, backend converts to Decimal
    currency: string
    start_date: string // ISO date format YYYY-MM-DD
    end_date: string // ISO date format YYYY-MM-DD
    travelers: number
    travel_class?: string
    accommodation_type?: string
  }
  preferences?: Record<string, string | number | boolean | string[]>
}

/**
 * Map frontend accommodation types to backend enum values
 */
function mapAccommodationType(type: string): string | undefined {
  const mapping: Record<string, string> = {
    'hotel': 'hotel',
    'hostel': 'hostel',
    'apartment': 'apartment',
    'resort': 'resort',
    'villa': 'vacation_rental',
    'boutique': 'hotel',
    'bnb': 'bed_and_breakfast',
    'camping': 'vacation_rental',
  }
  return mapping[type]
}

/**
 * Parse destination string into city and country
 * Examples: "Paris, France" -> {city: "Paris", country: "France"}
 */
function parseDestination(destination: string): { city: string; country: string } {
  const parts = destination.split(',').map(p => p.trim())

  if (parts.length >= 2 && parts[0] && parts[1]) {
    return { city: parts[0], country: parts[1] }
  }

  // Fallback: treat entire string as city
  return { city: destination, country: 'Unknown' }
}

/**
 * Get ISO country code from country name (basic mapping)
 * In production, this should use a proper country database
 */
function getCountryCode(country: string): string {
  const countryMap: Record<string, string> = {
    'france': 'FR',
    'italy': 'IT',
    'spain': 'ES',
    'japan': 'JP',
    'united states': 'US',
    'usa': 'US',
    'united kingdom': 'GB',
    'uk': 'GB',
    'germany': 'DE',
    'australia': 'AU',
    'canada': 'CA',
    'mexico': 'MX',
    'brazil': 'BR',
    'argentina': 'AR',
    'china': 'CN',
    'india': 'IN',
    'thailand': 'TH',
    'indonesia': 'ID',
    'greece': 'GR',
    'portugal': 'PT',
    'netherlands': 'NL',
    'switzerland': 'CH',
    'austria': 'AT',
    'belgium': 'BE',
    'sweden': 'SE',
    'norway': 'NO',
    'denmark': 'DK',
    'finland': 'FI',
    'ireland': 'IE',
    'poland': 'PL',
    'czech republic': 'CZ',
    'turkey': 'TR',
    'egypt': 'EG',
    'morocco': 'MA',
    'south africa': 'ZA',
    'kenya': 'KE',
    'uae': 'AE',
    'singapore': 'SG',
    'malaysia': 'MY',
    'south korea': 'KR',
    'new zealand': 'NZ',
  }

  const normalized = country.toLowerCase().trim()
  return countryMap[normalized] || 'XX'
}

/**
 * Transform frontend trip request to backend format
 */
export function transformTripRequestForBackend(
  formData: TravelRequestFormData
): BackendTripPlanRequest {
  const { city, country } = parseDestination(formData.destination)
  const countryCode = getCountryCode(country)

  // Calculate total travelers
  const totalTravelers = formData.travelers.adults +
                        formData.travelers.children +
                        formData.travelers.infants

  // Build preferences object
  const preferences: Record<string, string | number | boolean | string[]> = {}

  if (formData.preferences && formData.preferences.length > 0) {
    preferences.activity_types = formData.preferences
  }

  if (formData.dietaryRestrictions && formData.dietaryRestrictions.length > 0) {
    preferences.dietary_restrictions = formData.dietaryRestrictions
  }

  if (formData.cuisinePreferences && formData.cuisinePreferences.length > 0) {
    preferences.cuisine_preferences = formData.cuisinePreferences
  }

  if (formData.accommodationTypes && formData.accommodationTypes.length > 0) {
    preferences.accommodation_types = formData.accommodationTypes
  }

  if (formData.origin) {
    preferences.origin = formData.origin
  }

  // Add traveler breakdown to preferences as separate fields
  preferences.adults = formData.travelers.adults
  preferences.children = formData.travelers.children
  preferences.infants = formData.travelers.infants

  // Map accommodation type to backend enum
  const mappedAccommodation = formData.accommodationTypes?.[0]
    ? mapAccommodationType(formData.accommodationTypes[0])
    : undefined

  const baseRequest = {
    destination: {
      city,
      country,
      country_code: countryCode,
    },
    requirements: {
      // Convert budget to string for Decimal conversion on backend
      budget: String(formData.budget?.amount || 1000),
      // Ensure currency is uppercase
      currency: (formData.budget?.currency || 'USD').toUpperCase(),
      start_date: formData.startDate,
      end_date: formData.endDate,
      travelers: totalTravelers,
      // Map accommodation type to backend enum value
      ...(mappedAccommodation && { accommodation_type: mappedAccommodation }),
    },
  };

  return Object.keys(preferences).length > 0
    ? { ...baseRequest, preferences }
    : baseRequest;
}

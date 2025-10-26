/**
 * Trip Detail Page - Day-by-Day Itinerary Timeline Visualization
 * Story 3.2: Day-by-Day Itinerary Timeline Visualization
 * Story 3.5: Migrated from /app/itinerary to dynamic route
 */

'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { ItineraryTimeline } from '@/components/itinerary';
import { IFullTripItinerary } from '@/lib/types';
import { apiClient } from '@/lib/api';
import { Loader2, AlertCircle } from 'lucide-react';

// For demo purposes, we'll use sample data
// In production, this would fetch from the API using trip_id
const SAMPLE_ITINERARY: IFullTripItinerary = {
  trip: {
    destination: {
      city: 'Rome',
      country: 'Italy',
    },
    dates: {
      start: '2025-10-18',
      end: '2025-10-25',
      duration_days: 7,
    },
    travelers: {
      count: 2,
      type: 'adults',
    },
    budget: {
      total: '3000.00',
      currency: 'EUR',
      spent: '2456.90',
      remaining: '543.10',
    },
  },
  flights: {
    outbound: {
      airline: 'Air Canada',
      flight_number: 'AC8899',
      route: {
        from_airport: 'JFK',
        to_airport: 'FCO',
      },
      departure: {
        time: '09:00',
        timezone: 'America/New_York',
      },
      arrival: {
        time: '09:15',
        timezone: 'Europe/Rome',
      },
      duration_minutes: 1095,
      stops: 1,
      price_per_person: '408.45',
      total_price: '816.90',
    },
    return_flight: {
      airline: 'Air Canada',
      flight_number: 'AC8900',
      route: {
        from_airport: 'FCO',
        to_airport: 'JFK',
      },
      departure: {
        time: '11:30',
        timezone: 'Europe/Rome',
      },
      arrival: {
        time: '15:45',
        timezone: 'America/New_York',
      },
      duration_minutes: 615,
      stops: 1,
      price_per_person: '408.45',
      total_price: '816.90',
    },
    total_cost: '1633.80',
  },
  accommodation: {
    name: 'Hotel Artemide',
    rating: 4.8,
    stars: 4,
    address: {
      street: 'Via Nazionale, 22',
      postal_code: '00184',
      city: 'Roma',
      region: 'RM',
      country: 'Italy',
    },
    amenities: [
      'Air Conditioning',
      'Daily Housekeeping',
      'Central Location',
      'Near Termini Station',
    ],
    price_per_night: '117.00',
    nights: 7,
    total_cost: '819.00',
    location_notes: 'Centrally located near Via Nazionale, walking distance to major attractions',
    check_in: '15:00',
    check_out: '11:00',
  },
  itinerary: [
    {
      day: 1,
      date: '2025-10-18',
      day_of_week: 'Saturday',
      title: 'Arrival in Rome',
      activities: [
        {
          time_start: '09:15',
          time_end: null,
          category: 'transportation',
          title: 'Arrival at Fiumicino Airport (FCO)',
          description: 'Land at Rome Fiumicino Airport after overnight flight',
          duration_minutes: 30,
        },
        {
          time_start: '11:00',
          time_end: '12:00',
          category: 'transportation',
          title: 'Transfer to Hotel',
          description: 'Take Leonardo Express train from airport to Termini Station, then walk to hotel',
          duration_minutes: 60,
          price: '14.00',
        },
        {
          time_start: '15:00',
          time_end: null,
          category: 'sightseeing',
          title: 'Hotel Check-in',
          description: 'Check into Hotel Artemide and freshen up',
          duration_minutes: 30,
          location: 'Hotel Artemide, Via Nazionale',
        },
        {
          time_start: '16:30',
          time_end: '18:30',
          category: 'sightseeing',
          title: 'Evening Walk - Trevi Fountain',
          description:
            'Leisurely evening walk to the iconic Trevi Fountain. Toss a coin to ensure your return to Rome!',
          duration_minutes: 120,
          location: 'Trevi Fountain',
        },
      ],
      meals: [
        {
          restaurant_name: 'Pasta e Vino',
          cuisine_type: 'Italian',
          meal_type: 'dinner',
          time: '19:30',
          price_range: '€€',
          rating: 4.5,
          location: 'Near Trevi Fountain',
          description: 'Traditional Roman pasta dishes in a cozy atmosphere',
        },
      ],
      accommodation: {
        name: 'Hotel Artemide',
        rating: 4.8,
        stars: 4,
        address: {
          street: 'Via Nazionale, 22',
          postal_code: '00184',
          city: 'Roma',
          region: 'RM',
          country: 'Italy',
        },
        amenities: [
          'Air Conditioning',
          'Daily Housekeeping',
          'Central Location',
          'Near Termini Station',
        ],
        price_per_night: '117.00',
        nights: 7,
        total_cost: '819.00',
        location_notes: 'Centrally located near Via Nazionale',
        check_in: '15:00',
      },
      daily_cost: {
        activities: '14.00',
        meals: '40.00',
        accommodation: '117.00',
        total: '171.00',
      },
    },
    {
      day: 2,
      date: '2025-10-19',
      day_of_week: 'Sunday',
      title: 'Ancient Rome Exploration',
      activities: [
        {
          time_start: '09:00',
          time_end: '12:00',
          category: 'cultural',
          title: 'Colosseum & Roman Forum Tour',
          description:
            'Guided tour of the iconic Colosseum and ancient Roman Forum. Skip-the-line tickets included.',
          duration_minutes: 180,
          location: 'Colosseum',
          price: '55.00',
          booking_info: 'Pre-booked skip-the-line tickets required',
        },
        {
          time_start: '14:00',
          time_end: '16:00',
          category: 'cultural',
          title: 'Palatine Hill Visit',
          description: 'Explore the legendary birthplace of Rome with stunning city views',
          duration_minutes: 120,
          location: 'Palatine Hill',
          price: '16.00',
        },
        {
          time_start: '17:00',
          time_end: '18:30',
          category: 'relaxation',
          title: 'Sunset at Orange Garden',
          description: 'Enjoy panoramic sunset views of Rome from Giardino degli Aranci',
          duration_minutes: 90,
          location: 'Giardino degli Aranci, Aventine Hill',
        },
      ],
      meals: [
        {
          restaurant_name: 'Café Colosseum',
          cuisine_type: 'Italian Café',
          meal_type: 'breakfast',
          time: '08:00',
          price_range: '€',
          rating: 4.2,
          location: 'Near hotel',
        },
        {
          restaurant_name: 'Taverna dei Fori Imperiali',
          cuisine_type: 'Roman',
          meal_type: 'lunch',
          time: '13:00',
          price_range: '€€',
          rating: 4.6,
          location: 'Near Roman Forum',
          description: 'Authentic Roman cuisine with traditional recipes',
        },
        {
          restaurant_name: 'Flavio al Velavevodetto',
          cuisine_type: 'Roman',
          meal_type: 'dinner',
          time: '19:30',
          price_range: '€€€',
          rating: 4.7,
          location: 'Testaccio',
          description: 'Famous for cacio e pepe and traditional Roman dishes',
        },
      ],
      accommodation: {
        name: 'Hotel Artemide',
        rating: 4.8,
        stars: 4,
        address: {
          street: 'Via Nazionale, 22',
          postal_code: '00184',
          city: 'Roma',
          region: 'RM',
          country: 'Italy',
        },
        amenities: [
          'Air Conditioning',
          'Daily Housekeeping',
          'Central Location',
          'Near Termini Station',
        ],
        price_per_night: '117.00',
        nights: 7,
        total_cost: '819.00',
        location_notes: 'Centrally located near Via Nazionale',
      },
      daily_cost: {
        activities: '71.00',
        meals: '70.00',
        accommodation: '117.00',
        total: '258.00',
      },
    },
  ],
};

export default function TripDetailPage() {
  const params = useParams();
  const tripId = params.trip_id as string;
  const [itinerary, setItinerary] = useState<IFullTripItinerary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadItinerary = async () => {
      try {
        setLoading(true);
        console.log('Loading trip details for:', tripId);

        // Fetch trip details from API
        const response = await apiClient.getTripById(tripId);

        // Extract the trip data from the SuccessResponse wrapper
        const tripData = response.data;

        // If the trip has a plan, use it; otherwise fall back to sample data
        if (tripData?.plan) {
          setItinerary(tripData.plan);
        } else {
          // No plan available yet - trip might be in draft status
          console.warn('Trip has no itinerary plan yet, using sample data');
          setItinerary(SAMPLE_ITINERARY);
        }
      } catch (err) {
        console.error('Failed to load trip:', err);
        setError(err instanceof Error ? err.message : 'Failed to load trip details');
      } finally {
        setLoading(false);
      }
    };

    if (tripId) {
      loadItinerary();
    }
  }, [tripId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading your itinerary...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 mb-2 text-center">
            Error Loading Itinerary
          </h2>
          <p className="text-gray-600 text-center">{error}</p>
        </div>
      </div>
    );
  }

  if (!itinerary) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-600">No itinerary data available</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <ItineraryTimeline itinerary={itinerary} />
    </div>
  );
}

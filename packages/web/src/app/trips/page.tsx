/**
 * Trip List Dashboard Page
 * Displays all user trips with filtering, search, and pagination
 * Story 3.5: User Trip List Dashboard
 */

'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { TripCard } from '@/components/trips';
import { Pagination, EmptyState } from '@/components/ui';
import { apiClient } from '@/lib/api';
import { ITripSummary, IPaginationMeta, TripStatus } from '@/lib/types';
import { Loader2, AlertCircle, Search, Filter, Plane, X } from 'lucide-react';

const STATUS_OPTIONS: { value: TripStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All Trips' },
  { value: 'draft', label: 'Draft' },
  { value: 'planning', label: 'Planning' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
];

export default function TripsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // State
  const [trips, setTrips] = useState<ITripSummary[]>([]);
  const [pagination, setPagination] = useState<IPaginationMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<TripStatus | 'all'>('all');
  const [filteredTrips, setFilteredTrips] = useState<ITripSummary[]>([]);

  // Get page from URL or default to 1
  const currentPage = parseInt(searchParams.get('page') || '1', 10);

  // Fetch trips from API
  const fetchTrips = useCallback(async (page: number) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getUserTrips(page, 20);
      setTrips(response.data);
      setPagination(response.pagination);
    } catch (err) {
      console.error('Error fetching trips:', err);
      setError(err instanceof Error ? err.message : 'Failed to load trips');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load trips on mount and when page changes
  useEffect(() => {
    fetchTrips(currentPage);
  }, [currentPage, fetchTrips]);

  // Apply filters whenever trips, search, or status changes
  useEffect(() => {
    let filtered = [...trips];

    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter((trip) => trip.status === statusFilter);
    }

    // Apply search filter (search by name or destination)
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (trip) =>
          trip.name.toLowerCase().includes(query) ||
          trip.destination.city.toLowerCase().includes(query) ||
          trip.destination.country.toLowerCase().includes(query)
      );
    }

    setFilteredTrips(filtered);
  }, [trips, searchQuery, statusFilter]);

  // Handle page change
  const handlePageChange = (page: number) => {
    router.push(`/trips?page=${page}`);
  };

  // Handle retry
  const handleRetry = () => {
    fetchTrips(currentPage);
  };

  // Clear filters
  const handleClearFilters = () => {
    setSearchQuery('');
    setStatusFilter('all');
  };

  // Active filter count
  const activeFilterCount =
    (searchQuery.trim() ? 1 : 0) + (statusFilter !== 'all' ? 1 : 0);

  // Loading state
  if (loading && !trips.length) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-center py-32">
            <div className="text-center">
              <Loader2 className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
              <p className="text-gray-600">Loading your trips...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error && !trips.length) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-center py-32">
            <div className="bg-white rounded-lg shadow-lg p-8 max-w-md">
              <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
              <h2 className="text-xl font-bold text-gray-900 mb-2 text-center">
                Error Loading Trips
              </h2>
              <p className="text-gray-600 text-center mb-6">{error}</p>
              <button
                onClick={handleRetry}
                className="w-full px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">My Trips</h1>
          <p className="text-gray-600">Plan, manage, and track all your adventures</p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Search input */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="text"
                  placeholder="Search by destination or trip name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>

            {/* Status filter */}
            <div className="sm:w-48">
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as TripStatus | 'all')}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white"
                >
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Clear filters button */}
            {activeFilterCount > 0 && (
              <button
                onClick={handleClearFilters}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors flex items-center gap-2"
              >
                <X className="w-4 h-4" />
                Clear ({activeFilterCount})
              </button>
            )}
          </div>
        </div>

        {/* Trip grid or empty state */}
        {filteredTrips.length === 0 ? (
          <EmptyState
            title={
              trips.length === 0 ? 'No trips yet' : 'No trips match your filters'
            }
            message={
              trips.length === 0
                ? 'Start planning your next adventure! Create your first trip to begin.'
                : 'Try adjusting your search or filters to find what you are looking for.'
            }
            icon={<Plane className="w-16 h-16" />}
            ctaText={trips.length === 0 ? 'Create Your First Trip' : undefined}
            ctaHref={trips.length === 0 ? '/trips/new' : undefined}
          />
        ) : (
          <>
            {/* Trip cards grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
              {filteredTrips.map((trip) => (
                <TripCard key={trip.trip_id} trip={trip} />
              ))}
            </div>

            {/* Pagination - only show if not filtered */}
            {pagination && activeFilterCount === 0 && pagination.total_pages > 1 && (
              <Pagination
                pagination={pagination}
                onPageChange={handlePageChange}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}

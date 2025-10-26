/**
 * Custom hook for fetching and caching user trips data
 * Uses SWR for automatic caching, revalidation, and deduplication
 */

import useSWR from "swr";
import { apiClient } from "../lib/api";
import type { IPaginatedResponse, ITripSummary, IPaginationMeta } from "../lib/types";

interface UseTripsOptions {
  page?: number;
  perPage?: number;
  enabled?: boolean; // Only fetch when enabled is true
}

interface UseTripsResult {
  trips: ITripSummary[] | undefined;
  pagination: IPaginationMeta | undefined;
  hasTrips: boolean;
  isLoading: boolean;
  isError: boolean;
  error: Error | undefined;
  mutate: () => void; // Manual revalidation function
}

/**
 * Fetcher function for SWR
 */
const fetchUserTrips = async (
  _key: string,
  page: number,
  perPage: number
): Promise<IPaginatedResponse<ITripSummary[]>> => {
  return apiClient.getUserTrips(page, perPage);
};

/**
 * Hook to fetch and cache user trips
 *
 * @param options - Configuration options
 * @returns Trips data, loading state, and cache invalidation function
 *
 * @example
 * ```tsx
 * const { trips, hasTrips, isLoading } = useTrips({ page: 1, perPage: 20 });
 * ```
 */
export function useTrips(options: UseTripsOptions = {}): UseTripsResult {
  const { page = 1, perPage = 20, enabled = true } = options;

  const { data, error, isLoading, mutate } = useSWR(
    enabled ? ["user-trips", page, perPage] : null,
    ([, p, pp]) => fetchUserTrips("user-trips", p, pp),
    {
      revalidateOnFocus: false, // Don't refetch on window focus
      revalidateOnReconnect: false, // Don't refetch on reconnect
      dedupingInterval: 60000, // Dedupe requests within 60 seconds
      refreshInterval: 0, // No automatic refresh
    }
  );

  return {
    trips: data?.data,
    pagination: data?.pagination,
    hasTrips: (data?.data?.length ?? 0) > 0,
    isLoading,
    isError: !!error,
    error,
    mutate, // Expose mutate for manual cache invalidation
  };
}

/**
 * Hook to check if user has any trips (optimized version)
 * Only fetches first trip to minimize data transfer
 */
export function useHasTrips(enabled: boolean = true): {
  hasTrips: boolean;
  isLoading: boolean;
} {
  const { hasTrips, isLoading } = useTrips({
    page: 1,
    perPage: 1, // Only fetch 1 trip to check existence
    enabled,
  });

  return { hasTrips, isLoading };
}

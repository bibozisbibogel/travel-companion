"use client";

import { useState, useEffect } from "react";
import type { IFullTripItinerary } from "@/lib/types";

interface GeocodingFailure {
  tripId: string;
  destination: string;
  locationType: "activity" | "accommodation" | "restaurant" | "destination" | "flight";
  locationName: string;
  locationAddress?: string;
  errorMessage: string | null;
  failedAt: string | null;
  coordinates?: {
    latitude: number;
    longitude: number;
  };
}

/**
 * Debug page for monitoring geocoding failures
 *
 * Displays all locations where geocoding failed, allowing developers
 * to identify patterns and troubleshoot issues with the geocoding service.
 */
export default function GeocodingDebugPage() {
  const [trips, setTrips] = useState<IFullTripItinerary[]>([]);
  const [failures, setFailures] = useState<GeocodingFailure[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    // In production, this would fetch from an API endpoint
    // For now, we'll extract failures from trips in localStorage
    loadGeocodingFailures();
  }, []);

  const loadGeocodingFailures = () => {
    try {
      // This is a simplified implementation
      // In production, you'd fetch from /api/debug/geocoding-failures
      const failures: GeocodingFailure[] = [];

      // Extract from recent trips (this would come from API in production)
      const recentTrips = localStorage.getItem("recent_trips");
      if (recentTrips) {
        const trips: IFullTripItinerary[] = JSON.parse(recentTrips);

        trips.forEach((trip) => {
          const tripId = trip.trip?.destination?.city || "unknown";

          // Check destination coordinates
          if (trip.trip?.destination?.coordinates?.geocoding_status === "failed") {
            failures.push({
              tripId,
              destination: trip.trip.destination.city,
              locationType: "destination",
              locationName: `${trip.trip.destination.city}, ${trip.trip.destination.country}`,
              errorMessage: trip.trip.destination.coordinates.geocoding_error_message || null,
              failedAt: trip.trip.destination.coordinates.geocoded_at || null,
              coordinates: {
                latitude: trip.trip.destination.coordinates.latitude,
                longitude: trip.trip.destination.coordinates.longitude,
              },
            });
          }

          // Check accommodation
          if (trip.accommodation?.coordinates?.geocoding_status === "failed") {
            failures.push({
              tripId,
              destination: trip.trip.destination.city,
              locationType: "accommodation",
              locationName: trip.accommodation.name,
              locationAddress: `${trip.accommodation.address.street}, ${trip.accommodation.address.city}`,
              errorMessage: trip.accommodation.coordinates.geocoding_error_message || null,
              failedAt: trip.accommodation.coordinates.geocoded_at || null,
              coordinates: {
                latitude: trip.accommodation.coordinates.latitude,
                longitude: trip.accommodation.coordinates.longitude,
              },
            });
          }

          // Check activities
          trip.itinerary?.forEach((day) => {
            day.activities?.forEach((activity) => {
              if (activity.coordinates?.geocoding_status === "failed") {
                const failure: GeocodingFailure = {
                  tripId,
                  destination: trip.trip.destination.city,
                  locationType: "activity",
                  locationName: activity.title,
                  errorMessage: activity.coordinates.geocoding_error_message || null,
                  failedAt: activity.coordinates.geocoded_at || null,
                  coordinates: {
                    latitude: activity.coordinates.latitude,
                    longitude: activity.coordinates.longitude,
                  },
                };
                if (activity.location) {
                  failure.locationAddress = activity.location;
                }
                failures.push(failure);
              }

              // Check venue in activity
              if (activity.venue?.coordinates?.geocoding_status === "failed") {
                const failure: GeocodingFailure = {
                  tripId,
                  destination: trip.trip.destination.city,
                  locationType: "restaurant",
                  locationName: activity.venue.name,
                  errorMessage: activity.venue.coordinates.geocoding_error_message || null,
                  failedAt: activity.venue.coordinates.geocoded_at || null,
                  coordinates: {
                    latitude: activity.venue.coordinates.latitude,
                    longitude: activity.venue.coordinates.longitude,
                  },
                };
                if (activity.venue.location) {
                  failure.locationAddress = activity.venue.location;
                }
                failures.push(failure);
              }
            });
          });
        });
      }

      setFailures(failures);
    } catch (error) {
      console.error("Error loading geocoding failures:", error);
    } finally {
      setLoading(false);
    }
  };

  const filteredFailures = failures.filter((failure) => {
    const matchesFilter = filter === "all" || failure.locationType === filter;
    const matchesSearch =
      searchTerm === "" ||
      failure.locationName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      failure.destination.toLowerCase().includes(searchTerm.toLowerCase()) ||
      failure.errorMessage?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const stats = {
    total: failures.length,
    byType: {
      activity: failures.filter((f) => f.locationType === "activity").length,
      accommodation: failures.filter((f) => f.locationType === "accommodation").length,
      restaurant: failures.filter((f) => f.locationType === "restaurant").length,
      destination: failures.filter((f) => f.locationType === "destination").length,
      flight: failures.filter((f) => f.locationType === "flight").length,
    },
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-gray-600">Loading geocoding failures...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">
            Geocoding Debug Dashboard
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Monitor and troubleshoot geocoding failures across all trips
          </p>
        </div>

        {/* Stats Cards */}
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div className="rounded-lg bg-white p-4 shadow">
            <div className="text-sm font-medium text-gray-500">Total Failures</div>
            <div className="mt-2 text-3xl font-semibold text-red-600">
              {stats.total}
            </div>
          </div>
          <div className="rounded-lg bg-white p-4 shadow">
            <div className="text-sm font-medium text-gray-500">Activities</div>
            <div className="mt-2 text-3xl font-semibold text-blue-600">
              {stats.byType.activity}
            </div>
          </div>
          <div className="rounded-lg bg-white p-4 shadow">
            <div className="text-sm font-medium text-gray-500">Accommodations</div>
            <div className="mt-2 text-3xl font-semibold text-purple-600">
              {stats.byType.accommodation}
            </div>
          </div>
          <div className="rounded-lg bg-white p-4 shadow">
            <div className="text-sm font-medium text-gray-500">Restaurants</div>
            <div className="mt-2 text-3xl font-semibold text-amber-600">
              {stats.byType.restaurant}
            </div>
          </div>
          <div className="rounded-lg bg-white p-4 shadow">
            <div className="text-sm font-medium text-gray-500">Destinations</div>
            <div className="mt-2 text-3xl font-semibold text-green-600">
              {stats.byType.destination}
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-6 rounded-lg bg-white p-4 shadow">
          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="flex-1">
              <label htmlFor="search" className="sr-only">
                Search
              </label>
              <input
                type="text"
                id="search"
                placeholder="Search by location name, destination, or error message..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 sm:w-48"
              >
                <option value="all">All Types</option>
                <option value="activity">Activities</option>
                <option value="accommodation">Accommodations</option>
                <option value="restaurant">Restaurants</option>
                <option value="destination">Destinations</option>
                <option value="flight">Flights</option>
              </select>
            </div>
          </div>
        </div>

        {/* Failures Table */}
        <div className="overflow-hidden rounded-lg bg-white shadow">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Location Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Address
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Destination
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Error Message
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Failed At
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {filteredFailures.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                      {failures.length === 0
                        ? "No geocoding failures found! 🎉"
                        : "No results match your filters."}
                    </td>
                  </tr>
                ) : (
                  filteredFailures.map((failure, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="whitespace-nowrap px-6 py-4 text-sm">
                        <span
                          className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                            failure.locationType === "activity"
                              ? "bg-blue-100 text-blue-800"
                              : failure.locationType === "accommodation"
                              ? "bg-purple-100 text-purple-800"
                              : failure.locationType === "restaurant"
                              ? "bg-amber-100 text-amber-800"
                              : failure.locationType === "destination"
                              ? "bg-green-100 text-green-800"
                              : "bg-gray-100 text-gray-800"
                          }`}
                        >
                          {failure.locationType}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">
                        {failure.locationName}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {failure.locationAddress || "—"}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {failure.destination}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        <span className="font-mono text-xs">
                          {failure.errorMessage || "Unknown error"}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                        {failure.failedAt
                          ? new Date(failure.failedAt).toLocaleString()
                          : "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer Info */}
        <div className="mt-6 rounded-lg bg-blue-50 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-blue-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-700">
                <strong>Note:</strong> This dashboard shows geocoding failures from
                recent trips. In production, this data would be stored in a dedicated
                monitoring table and fetched via API endpoint{" "}
                <code className="rounded bg-blue-100 px-1 py-0.5 font-mono text-xs">
                  /api/debug/geocoding-failures
                </code>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

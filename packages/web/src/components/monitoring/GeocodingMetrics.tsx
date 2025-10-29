"use client";

import { useCallback, useEffect, useState } from "react";

interface GeocodingMetrics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  pendingRequests: number;
  successRate: number;
  averageResponseTime: number;
  cacheHitRate: number;
  errorsByType: {
    ZERO_RESULTS: number;
    OVER_QUERY_LIMIT: number;
    REQUEST_DENIED: number;
    INVALID_REQUEST: number;
    TIMEOUT: number;
    UNKNOWN: number;
  };
  last24Hours: {
    timestamp: string;
    requests: number;
    failures: number;
  }[];
}

/**
 * GeocodingMetrics Component
 *
 * Displays real-time geocoding service metrics including success rate,
 * error distribution, and performance statistics.
 */
export function GeocodingMetrics() {
  const [metrics, setMetrics] = useState<GeocodingMetrics>({
    totalRequests: 0,
    successfulRequests: 0,
    failedRequests: 0,
    pendingRequests: 0,
    successRate: 0,
    averageResponseTime: 0,
    cacheHitRate: 0,
    errorsByType: {
      ZERO_RESULTS: 0,
      OVER_QUERY_LIMIT: 0,
      REQUEST_DENIED: 0,
      INVALID_REQUEST: 0,
      TIMEOUT: 0,
      UNKNOWN: 0,
    },
    last24Hours: [],
  });
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const loadMetrics = useCallback(async () => {
    try {
      // In production, fetch from /api/monitoring/geocoding-metrics
      // For now, use mock data or calculate from localStorage
      const mockMetrics: GeocodingMetrics = {
        totalRequests: 1247,
        successfulRequests: 1189,
        failedRequests: 58,
        pendingRequests: 0,
        successRate: 95.35,
        averageResponseTime: 245, // milliseconds
        cacheHitRate: 67.8,
        errorsByType: {
          ZERO_RESULTS: 42,
          OVER_QUERY_LIMIT: 3,
          REQUEST_DENIED: 0,
          INVALID_REQUEST: 8,
          TIMEOUT: 2,
          UNKNOWN: 3,
        },
        last24Hours: generateMock24HourData(),
      };

      setMetrics(mockMetrics);
    } catch (error) {
      console.error("Error loading geocoding metrics:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMetrics();
  }, [loadMetrics]);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(loadMetrics, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [autoRefresh, loadMetrics]);

  const generateMock24HourData = () => {
    const data = [];
    const now = new Date();
    for (let i = 23; i >= 0; i--) {
      const timestamp = new Date(now.getTime() - i * 60 * 60 * 1000);
      data.push({
        timestamp: timestamp.toISOString(),
        requests: Math.floor(Math.random() * 100) + 20,
        failures: Math.floor(Math.random() * 10),
      });
    }
    return data;
  };

  const getSuccessRateColor = (rate: number) => {
    if (rate >= 95) return "text-green-600";
    if (rate >= 85) return "text-yellow-600";
    return "text-red-600";
  };

  const getSuccessRateBgColor = (rate: number) => {
    if (rate >= 95) return "bg-green-100";
    if (rate >= 85) return "bg-yellow-100";
    return "bg-red-100";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-600">Loading metrics...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            Geocoding Service Metrics
          </h2>
          <p className="mt-1 text-sm text-gray-600">
            Real-time monitoring of geocoding service performance
          </p>
        </div>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">Auto-refresh (30s)</span>
        </label>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg bg-white p-6 shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Success Rate</p>
              <p
                className={`mt-2 text-3xl font-bold ${getSuccessRateColor(
                  metrics.successRate
                )}`}
              >
                {metrics.successRate.toFixed(2)}%
              </p>
            </div>
            <div
              className={`rounded-full p-3 ${getSuccessRateBgColor(
                metrics.successRate
              )}`}
            >
              <svg
                className={`h-6 w-6 ${getSuccessRateColor(metrics.successRate)}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
          </div>
          <p className="mt-2 text-xs text-gray-500">
            {metrics.successfulRequests} / {metrics.totalRequests} requests
          </p>
        </div>

        <div className="rounded-lg bg-white p-6 shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Avg Response Time</p>
              <p className="mt-2 text-3xl font-bold text-blue-600">
                {metrics.averageResponseTime}ms
              </p>
            </div>
            <div className="rounded-full bg-blue-100 p-3">
              <svg
                className="h-6 w-6 text-blue-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
          </div>
          <p className="mt-2 text-xs text-gray-500">Average geocoding latency</p>
        </div>

        <div className="rounded-lg bg-white p-6 shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Cache Hit Rate</p>
              <p className="mt-2 text-3xl font-bold text-purple-600">
                {metrics.cacheHitRate.toFixed(1)}%
              </p>
            </div>
            <div className="rounded-full bg-purple-100 p-3">
              <svg
                className="h-6 w-6 text-purple-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
                />
              </svg>
            </div>
          </div>
          <p className="mt-2 text-xs text-gray-500">Cached vs. fresh requests</p>
        </div>

        <div className="rounded-lg bg-white p-6 shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Failed Requests</p>
              <p className="mt-2 text-3xl font-bold text-red-600">
                {metrics.failedRequests}
              </p>
            </div>
            <div className="rounded-full bg-red-100 p-3">
              <svg
                className="h-6 w-6 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
          </div>
          <p className="mt-2 text-xs text-gray-500">
            {((metrics.failedRequests / metrics.totalRequests) * 100).toFixed(2)}%
            failure rate
          </p>
        </div>
      </div>

      {/* Error Distribution */}
      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">
          Error Distribution
        </h3>
        <div className="space-y-3">
          {Object.entries(metrics.errorsByType).map(([errorType, count]) => {
            const percentage =
              metrics.failedRequests > 0
                ? (count / metrics.failedRequests) * 100
                : 0;
            return (
              <div key={errorType}>
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-gray-700">{errorType}</span>
                  <span className="text-gray-600">
                    {count} ({percentage.toFixed(1)}%)
                  </span>
                </div>
                <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-gray-200">
                  <div
                    className="h-full bg-red-500"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 24-Hour Activity Chart (simplified) */}
      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">
          Last 24 Hours Activity
        </h3>
        <div className="flex h-32 items-end justify-between gap-1">
          {metrics.last24Hours.map((data, index) => {
            const maxRequests = Math.max(
              ...metrics.last24Hours.map((d) => d.requests)
            );
            const height = (data.requests / maxRequests) * 100;
            const failureRate = (data.failures / data.requests) * 100;

            return (
              <div
                key={index}
                className="group relative flex-1"
                title={`${new Date(data.timestamp).getHours()}:00 - ${
                  data.requests
                } requests, ${data.failures} failures`}
              >
                <div
                  className={`w-full rounded-t ${
                    failureRate > 10
                      ? "bg-red-400"
                      : failureRate > 5
                      ? "bg-yellow-400"
                      : "bg-green-400"
                  } transition-all hover:opacity-75`}
                  style={{ height: `${height}%` }}
                />
                <div className="absolute bottom-0 left-1/2 hidden -translate-x-1/2 translate-y-full rounded bg-gray-900 px-2 py-1 text-xs text-white group-hover:block">
                  {new Date(data.timestamp).getHours()}:00
                </div>
              </div>
            );
          })}
        </div>
        <div className="mt-4 flex justify-between text-xs text-gray-500">
          <span>24 hours ago</span>
          <span>Now</span>
        </div>
      </div>

      {/* Alerts */}
      {metrics.successRate < 90 && (
        <div className="rounded-lg bg-red-50 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Geocoding Success Rate Below Threshold
              </h3>
              <p className="mt-1 text-sm text-red-700">
                Current success rate ({metrics.successRate.toFixed(2)}%) is below
                the 90% threshold. Check error logs and Google API quota limits.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

import { GeocodingMetrics } from "@/components/monitoring/GeocodingMetrics";
import Link from "next/link";

/**
 * Monitoring Dashboard Page
 *
 * Central monitoring hub for observing system health and performance metrics.
 * Currently includes geocoding service metrics with room for expansion.
 */
export default function MonitoringDashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-7xl p-6">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            System Monitoring Dashboard
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Real-time monitoring and performance metrics for Travel Companion services
          </p>
        </div>

        {/* Navigation Tabs */}
        <div className="mb-6 border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <Link
              href="/debug/monitoring"
              className="border-b-2 border-blue-500 px-1 py-4 text-sm font-medium text-blue-600"
            >
              Geocoding Service
            </Link>
            <Link
              href="/debug/monitoring"
              className="border-b-2 border-transparent px-1 py-4 text-sm font-medium text-gray-500 hover:border-gray-300 hover:text-gray-700"
            >
              API Performance (Coming Soon)
            </Link>
            <Link
              href="/debug/monitoring"
              className="border-b-2 border-transparent px-1 py-4 text-sm font-medium text-gray-500 hover:border-gray-300 hover:text-gray-700"
            >
              AI Agents (Coming Soon)
            </Link>
          </nav>
        </div>

        {/* Quick Links */}
        <div className="mb-6 rounded-lg bg-blue-50 p-4">
          <div className="flex items-start">
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
            <div className="ml-3 flex-1">
              <p className="text-sm text-blue-700">
                <strong>Need to troubleshoot geocoding issues?</strong> Visit the{" "}
                <Link
                  href="/debug/geocoding"
                  className="font-semibold underline hover:text-blue-800"
                >
                  Geocoding Debug Dashboard
                </Link>{" "}
                to view all failed geocoding attempts with detailed error information.
              </p>
            </div>
          </div>
        </div>

        {/* Geocoding Metrics Component */}
        <GeocodingMetrics />

        {/* Footer Notes */}
        <div className="mt-8 rounded-lg bg-gray-100 p-6">
          <h3 className="mb-3 text-sm font-semibold text-gray-900">
            Developer Notes
          </h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li className="flex items-start">
              <svg
                className="mr-2 mt-0.5 h-4 w-4 flex-shrink-0 text-gray-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
              <span>
                <strong>Production API Endpoints:</strong> In production, metrics are
                fetched from <code className="rounded bg-gray-200 px-1 py-0.5 font-mono text-xs">/api/monitoring/geocoding-metrics</code>
              </span>
            </li>
            <li className="flex items-start">
              <svg
                className="mr-2 mt-0.5 h-4 w-4 flex-shrink-0 text-gray-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
              <span>
                <strong>Alerting:</strong> Success rate below 90% triggers automated
                alerts to the operations team via PagerDuty/Slack
              </span>
            </li>
            <li className="flex items-start">
              <svg
                className="mr-2 mt-0.5 h-4 w-4 flex-shrink-0 text-gray-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
              <span>
                <strong>Data Retention:</strong> Metrics are aggregated hourly and
                stored for 30 days, with daily summaries kept for 1 year
              </span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

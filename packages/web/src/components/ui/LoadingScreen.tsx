'use client'

interface ILoadingScreenProps {
  message?: string
}

export default function LoadingScreen({ message = 'Creating Your Trip Plan...' }: ILoadingScreenProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900 bg-opacity-75 backdrop-blur-sm">
      <div className="text-center px-6 py-12 bg-white rounded-lg shadow-2xl max-w-md w-full mx-4">
        {/* Animated Icon */}
        <div className="flex justify-center mb-6">
          <div className="relative">
            {/* Outer rotating ring */}
            <div className="absolute inset-0 animate-spin">
              <svg className="w-24 h-24 text-blue-600" fill="none" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="3"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            </div>
            {/* Center icon */}
            <div className="flex items-center justify-center w-24 h-24">
              <svg
                className="w-12 h-12 text-blue-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
          </div>
        </div>

        {/* Loading Text */}
        <h2 className="text-2xl font-bold text-gray-900 mb-3">{message}</h2>
        <p className="text-gray-600 mb-6">
          This may take a moment as we craft the perfect itinerary for you...
        </p>

        {/* Progress Indicators */}
        <div className="space-y-3 text-left">
          <div className="flex items-center text-sm">
            <div className="w-5 h-5 mr-3 flex-shrink-0">
              <div className="w-5 h-5 bg-blue-600 rounded-full animate-pulse" />
            </div>
            <span className="text-gray-700">Analyzing your preferences</span>
          </div>
          <div className="flex items-center text-sm">
            <div className="w-5 h-5 mr-3 flex-shrink-0">
              <div className="w-5 h-5 bg-blue-600 rounded-full animate-pulse delay-150" />
            </div>
            <span className="text-gray-700">Finding the best options</span>
          </div>
          <div className="flex items-center text-sm">
            <div className="w-5 h-5 mr-3 flex-shrink-0">
              <div className="w-5 h-5 bg-blue-600 rounded-full animate-pulse delay-300" />
            </div>
            <span className="text-gray-700">Building your personalized itinerary</span>
          </div>
        </div>
      </div>
    </div>
  )
}

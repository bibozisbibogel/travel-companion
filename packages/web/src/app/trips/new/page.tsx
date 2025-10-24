import TripPreferencesForm from '@/components/forms/TripPreferencesForm'

export default function NewTripPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Create Your Perfect Trip</h1>
          <p className="text-lg text-gray-600">
            Tell us about your travel preferences and we&apos;ll create a personalized itinerary
          </p>
        </div>

        <TripPreferencesForm />
      </div>
    </div>
  )
}
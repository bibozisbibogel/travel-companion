import TripPreferencesForm from '@/components/forms/TripPreferencesForm'
import { MainLayout } from '@/components/layouts'

export default function NewTripPage() {
  return (
    <MainLayout containerClassName="max-w-5xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Create Your Perfect Trip</h1>
        <p className="text-lg text-gray-600">
          Tell us about your travel preferences and we&apos;ll create a personalized itinerary
        </p>
      </div>

      <TripPreferencesForm />
    </MainLayout>
  )
}
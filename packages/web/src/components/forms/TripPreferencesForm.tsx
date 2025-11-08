'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { travelRequestSchema, type TravelRequestFormData } from '../../lib/validation'
import { apiClient, ApiError } from '../../lib/api'
import { saveDraft, loadDraft, clearDraft, hasDraft } from '../../lib/draftStorage'
import { transformTripRequestForBackend } from '../../lib/apiTransformers'
import DestinationSearch from '../ui/DestinationSearch'
import DatePicker from '../ui/DatePicker'
import PreferencesSelector from '../ui/PreferencesSelector'
import MultiSelect from '../ui/MultiSelect'
import LoadingScreen from '../ui/LoadingScreen'
import {
  CURRENCY_OPTIONS,
  DIETARY_RESTRICTIONS,
  ACCOMMODATION_TYPES,
  CUISINE_PREFERENCES,
} from '../../lib/constants'
import type { IDestination } from '../../lib/types'

interface ITripPreferencesFormProps {
  onSuccess?: (tripId: string) => void
  className?: string
}

export default function TripPreferencesForm({
  onSuccess,
  className = '',
}: ITripPreferencesFormProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const [selectedDestination, setSelectedDestination] = useState<IDestination | null>(null)
  const [selectedOrigin, setSelectedOrigin] = useState<IDestination | null>(null)
  const [draftLoaded, setDraftLoaded] = useState(false)
  const [showDraftNotification, setShowDraftNotification] = useState(false)
  const router = useRouter()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    control,
    watch,
    setValue,
    setError,
    reset,
  } = useForm<TravelRequestFormData>({
    resolver: zodResolver(travelRequestSchema),
    defaultValues: {
      destination: '',
      origin: '',
      startDate: '',
      endDate: '',
      travelers: {
        adults: 2,
        children: 0,
        infants: 0,
      },
      budget: {
        amount: 2000,
        currency: 'USD',
      },
      preferences: [],
      dietaryRestrictions: [],
      accommodationTypes: [],
      cuisinePreferences: [],
    },
  })

  const startDate = watch('startDate')
  const budgetCurrency = watch('budget.currency') || 'USD'
  const currencySymbol = CURRENCY_OPTIONS.find(c => c.value === budgetCurrency)?.symbol || '$'

  // Load draft on mount
  useEffect(() => {
    if (hasDraft()) {
      const draft = loadDraft()
      if (draft) {
        reset(draft as TravelRequestFormData)
        setDraftLoaded(true)
        setShowDraftNotification(true)
        setTimeout(() => setShowDraftNotification(false), 5000)
      }
    }
  }, [reset])

  // Auto-save draft on form changes (debounced)
  const formData = watch()
  useEffect(() => {
    if (!draftLoaded) return

    const timer = setTimeout(() => {
      saveDraft(formData)
    }, 1000)

    return () => clearTimeout(timer)
  }, [formData, draftLoaded])

  const onSubmit = async (data: TravelRequestFormData) => {
    try {
      setIsLoading(true)
      setApiError(null)

      // Transform frontend data to backend format
      const backendRequest = transformTripRequestForBackend(data)
      console.log('Sending trip request:', JSON.stringify(backendRequest, null, 2))

      const startTime = Date.now()
      const response = await apiClient.planTrip(backendRequest as any)
      const endTime = Date.now()
      console.log(`Trip planning request took ${(endTime - startTime) / 1000} seconds`)
      console.log('Trip planning response:', response)

      // Extract trip ID from response - handle different response structures
      const tripId = response?.data?.tripId || (response as any)?.trip_id || (response as any)?.id

      if (tripId) {
        clearDraft()

        // Invalidate trips cache to refresh home page and trips list
        const { mutate } = await import('swr')
        mutate((key: any) => Array.isArray(key) && key[0] === 'user-trips')

        if (onSuccess) {
          onSuccess(tripId)
        } else {
          router.push(`/trips/${tripId}`)
        }
      } else {
        console.error('No trip ID in response:', response)
        setApiError('Trip created but unable to navigate. Please check your trips list.')
      }
    } catch (error) {
      console.error('Trip submission error:', error)
      if (error instanceof ApiError) {
        console.error('API Error details:', {
          status: error.status,
          message: error.message,
          data: error.data
        })
        if (error.status === 422) {
          // Check both error formats
          const validationErrors = error.data?.data?.errors || error.data?.errors
          console.error('Validation errors from backend:', validationErrors)

          if (Array.isArray(validationErrors)) {
            // New format: array of error objects
            validationErrors.forEach((err: any) => {
              console.error(`Field: ${err.field}, Message: ${err.message}`)
            })
            setApiError('Please check the form fields and try again.')
          } else if (validationErrors && typeof validationErrors === 'object') {
            // Old format: object with field names as keys
            Object.entries(validationErrors).forEach(([field, messages]) => {
              if (Array.isArray(messages) && messages.length > 0) {
                console.error(`Field: ${field}, Message: ${messages[0]}`)
                setError(field as keyof TravelRequestFormData, {
                  type: 'server',
                  message: messages[0],
                })
              }
            })
          } else {
            setApiError(error.message || 'Validation failed. Please check your input.')
          }
        } else {
          setApiError(error.message || 'An error occurred while planning your trip.')
        }
      } else {
        setApiError('Network error. Please check your connection and try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      {isLoading && <LoadingScreen />}
      <form onSubmit={handleSubmit(onSubmit)} className={`space-y-8 ${className}`}>
        {showDraftNotification && (
        <div className="rounded-md bg-blue-50 border border-blue-200 p-4 animate-slide-down" role="status">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-blue-800">
                Draft loaded! Your previous preferences have been restored.
              </p>
            </div>
          </div>
        </div>
      )}

      {apiError && (
        <div className="rounded-md bg-red-50 border border-red-200 p-4" role="alert">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-red-800">{apiError}</p>
            </div>
          </div>
        </div>
      )}

      {/* Destination and Origin Section */}
      <div className="space-y-6 p-6 bg-white rounded-lg border border-gray-200 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900">Where are you going?</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Origin <span className="text-gray-500 text-xs">Optional</span>
            </label>
            <Controller
              name="origin"
              control={control}
              render={({ field }) => (
                <DestinationSearch
                  value={field.value || ''}
                  onChange={(value, destination) => {
                    field.onChange(value)
                    setSelectedOrigin(destination || null)
                  }}
                  error={errors.origin?.message || ""}
                  placeholder="Where are you traveling from?"
                />
              )}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Destination <span className="text-red-500">*</span>
            </label>
            <Controller
              name="destination"
              control={control}
              render={({ field }) => (
                <DestinationSearch
                  value={field.value || ''}
                  onChange={(value, destination) => {
                    field.onChange(value)
                    setSelectedDestination(destination || null)
                  }}
                  error={errors.destination?.message || ""}
                  placeholder="Where would you like to travel?"
                />
              )}
            />
          </div>
        </div>
      </div>

      {/* Travel Dates Section */}
      <div className="space-y-6 p-6 bg-white rounded-lg border border-gray-200 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900">When are you traveling?</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Controller
            name="startDate"
            control={control}
            render={({ field }) => (
              <DatePicker
                id="startDate"
                label="Start Date"
                value={field.value || ''}
                onChange={field.onChange}
                error={errors.startDate?.message || ""}
                required={true}
              />
            )}
          />

          <Controller
            name="endDate"
            control={control}
            render={({ field }) => (
              <DatePicker
                id="endDate"
                label="End Date"
                value={field.value || ''}
                onChange={field.onChange}
                error={errors.endDate?.message || ""}
                required={true}
                {...(startDate && { minDate: startDate })}
              />
            )}
          />
        </div>
      </div>

      {/* Travelers Section */}
      <div className="space-y-6 p-6 bg-white rounded-lg border border-gray-200 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900">Who is traveling?</h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label htmlFor="adults" className="block text-sm font-medium text-gray-700 mb-2">
              Adults <span className="text-red-500">*</span>
            </label>
            <input
              {...register('travelers.adults', { valueAsNumber: true })}
              type="number"
              id="adults"
              min="1"
              max="20"
              className={`form-input ${errors.travelers?.adults ? 'border-red-300' : ''}`}
              aria-invalid={errors.travelers?.adults ? 'true' : 'false'}
            />
            {errors.travelers?.adults && (
              <p className="mt-2 text-sm text-red-600" role="alert">
                {errors.travelers.adults.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="children" className="block text-sm font-medium text-gray-700 mb-2">
              Children <span className="text-gray-500 text-xs">(2-12 years)</span>
            </label>
            <input
              {...register('travelers.children', { valueAsNumber: true })}
              type="number"
              id="children"
              min="0"
              max="20"
              className={`form-input ${errors.travelers?.children ? 'border-red-300' : ''}`}
            />
            {errors.travelers?.children && (
              <p className="mt-2 text-sm text-red-600" role="alert">
                {errors.travelers.children.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="infants" className="block text-sm font-medium text-gray-700 mb-2">
              Infants <span className="text-gray-500 text-xs">(&lt;2 years)</span>
            </label>
            <input
              {...register('travelers.infants', { valueAsNumber: true })}
              type="number"
              id="infants"
              min="0"
              max="20"
              className={`form-input ${errors.travelers?.infants ? 'border-red-300' : ''}`}
            />
            {errors.travelers?.infants && (
              <p className="mt-2 text-sm text-red-600" role="alert">
                {errors.travelers.infants.message}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Budget Section */}
      <div className="space-y-6 p-6 bg-white rounded-lg border border-gray-200 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900">What is your budget?</h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2">
            <label htmlFor="budget" className="block text-sm font-medium text-gray-700 mb-2">
              Amount <span className="text-gray-500 text-xs">Optional</span>
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <span className="text-gray-500 text-sm">{currencySymbol}</span>
              </div>
              <input
                {...register('budget.amount', { valueAsNumber: true })}
                type="number"
                id="budget"
                placeholder="Enter your budget"
                min="100"
                max="100000"
                step="100"
                className={`form-input pl-8 ${errors.budget?.amount ? 'border-red-300' : ''}`}
              />
            </div>
            {errors.budget?.amount && (
              <p className="mt-2 text-sm text-red-600" role="alert">
                {errors.budget.amount.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="currency" className="block text-sm font-medium text-gray-700 mb-2">
              Currency
            </label>
            <select
              {...register('budget.currency')}
              id="currency"
              className={`form-input ${errors.budget?.currency ? 'border-red-300' : ''}`}
            >
              {CURRENCY_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Activity Preferences Section */}
      <div className="space-y-6 p-6 bg-white rounded-lg border border-gray-200 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900">What interests you?</h3>

        <Controller
          name="preferences"
          control={control}
          render={({ field }) => (
            <PreferencesSelector
              value={field.value || []}
              onChange={field.onChange}
              error={errors.preferences?.message || ""}
            />
          )}
        />
      </div>

      {/* Dietary Restrictions Section */}
      <div className="space-y-6 p-6 bg-white rounded-lg border border-gray-200 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900">Dietary Requirements</h3>

        <Controller
          name="dietaryRestrictions"
          control={control}
          render={({ field }) => (
            <MultiSelect
              label="Dietary Restrictions"
              description="Select any dietary restrictions (optional)"
              options={DIETARY_RESTRICTIONS}
              value={field.value || []}
              onChange={field.onChange}
              error={errors.dietaryRestrictions?.message || ""}
              columns={4}
            />
          )}
        />
      </div>

      {/* Accommodation Preferences Section */}
      <div className="space-y-6 p-6 bg-white rounded-lg border border-gray-200 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900">Accommodation Preferences</h3>

        <Controller
          name="accommodationTypes"
          control={control}
          render={({ field }) => (
            <MultiSelect
              label="Accommodation Types"
              description="Select your preferred accommodation types (optional)"
              options={ACCOMMODATION_TYPES}
              value={field.value || []}
              onChange={field.onChange}
              error={errors.accommodationTypes?.message || ""}
              columns={4}
            />
          )}
        />
      </div>

      {/* Cuisine Preferences Section */}
      <div className="space-y-6 p-6 bg-white rounded-lg border border-gray-200 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900">Cuisine Preferences</h3>

        <Controller
          name="cuisinePreferences"
          control={control}
          render={({ field }) => (
            <MultiSelect
              label="Cuisine Types"
              description="What type of food do you enjoy? (optional)"
              options={CUISINE_PREFERENCES}
              value={field.value || []}
              onChange={field.onChange}
              error={errors.cuisinePreferences?.message || ""}
              columns={5}
              searchable={true}
              maxHeight="max-h-80"
            />
          )}
        />
      </div>

      {/* Submit Button */}
      <div className="flex flex-col sm:flex-row gap-4 pt-6">
        <button
          type="submit"
          disabled={isLoading || isSubmitting}
          className={`btn-primary flex-1 py-4 text-lg font-semibold ${
            (isLoading || isSubmitting) ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {isLoading || isSubmitting ? (
            <div className="flex items-center justify-center">
              <svg
                className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Creating Your Trip Plan...
            </div>
          ) : (
            'Generate Trip Itinerary'
          )}
        </button>
      </div>
    </form>
    </>
  )
}

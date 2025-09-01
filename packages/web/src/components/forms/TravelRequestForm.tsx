'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { travelRequestSchema, type TravelRequestFormData } from '../../lib/validation'
import { apiClient, ApiError } from '../../lib/api'
import DestinationSearch from '../ui/DestinationSearch'
import DatePicker from '../ui/DatePicker'
import PreferencesSelector from '../ui/PreferencesSelector'
import { BUDGET_RANGES, TRAVELER_OPTIONS } from '../../lib/constants'
import type { IDestination } from '../../lib/types'

interface ITravelRequestFormProps {
  onSuccess?: (tripId: string) => void
  className?: string
}

export default function TravelRequestForm({ onSuccess, className = '' }: ITravelRequestFormProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const [selectedDestination, setSelectedDestination] = useState<IDestination | null>(null)
  const router = useRouter()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    control,
    watch,
    setValue,
    setError,
  } = useForm<TravelRequestFormData>({
    resolver: zodResolver(travelRequestSchema),
    defaultValues: {
      travelers: 2,
      preferences: [],
    },
  })

  // Watch start date to set minimum end date
  const startDate = watch('startDate')

  const onSubmit = async (data: TravelRequestFormData) => {
    try {
      setIsLoading(true)
      setApiError(null)

      // Convert form data to API format
      const tripRequest = {
        destination: data.destination,
        startDate: data.startDate,
        endDate: data.endDate,
        budget: data.budget,
        travelers: data.travelers,
        preferences: data.preferences,
      }

      const response = await apiClient.planTrip(tripRequest)

      if (response.success && response.data) {
        // Redirect to trip details page or call success callback
        if (onSuccess) {
          onSuccess(response.data.tripId)
        } else {
          router.push(`/trips/${response.data.tripId}`)
        }
      } else {
        setApiError(response.message || 'Failed to create trip plan. Please try again.')
      }
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 422 && error.data?.errors) {
          // Handle validation errors from API
          Object.entries(error.data.errors).forEach(([field, messages]) => {
            if (Array.isArray(messages) && messages.length > 0) {
              setError(field as keyof TravelRequestFormData, {
                type: 'server',
                message: messages[0],
              })
            }
          })
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
    <form onSubmit={handleSubmit(onSubmit)} className={`space-y-8 ${className}`}>
      {/* API Error Alert */}
      {apiError && (
        <div className="rounded-md bg-red-50 border border-red-200 p-4" role="alert">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-red-800">{apiError}</p>
            </div>
          </div>
        </div>
      )}

      {/* Destination Search */}
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
              error={errors.destination?.message}
              placeholder="Where would you like to travel?"
            />
          )}
        />
      </div>

      {/* Travel Dates */}
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
              error={errors.startDate?.message}
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
              error={errors.endDate?.message}
              minDate={startDate || undefined}
            />
          )}
        />
      </div>

      {/* Travelers Count */}
      <div>
        <label htmlFor="travelers" className="block text-sm font-medium text-gray-700 mb-2">
          Number of Travelers <span className="text-red-500">*</span>
        </label>
        <select
          {...register('travelers', { valueAsNumber: true })}
          id="travelers"
          className={`form-input ${errors.travelers ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}`}
          aria-invalid={errors.travelers ? 'true' : 'false'}
          aria-describedby={errors.travelers ? 'travelers-error' : undefined}
        >
          {TRAVELER_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {errors.travelers && (
          <p id="travelers-error" className="mt-2 text-sm text-red-600" role="alert">
            {errors.travelers.message}
          </p>
        )}
      </div>

      {/* Budget */}
      <div>
        <label htmlFor="budget" className="block text-sm font-medium text-gray-700 mb-2">
          Budget (USD) <span className="text-gray-500 text-xs">Optional</span>
        </label>
        <div className="space-y-3">
          {/* Budget Range Buttons */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {BUDGET_RANGES.map((range) => {
              const currentBudget = watch('budget')
              const isSelected = currentBudget >= range.min && currentBudget <= range.max
              
              return (
                <button
                  key={range.label}
                  type="button"
                  onClick={() => setValue('budget', (range.min + range.max) / 2)}
                  className={`p-3 text-sm rounded-lg border-2 transition-all duration-200 ${
                    isSelected
                      ? 'border-primary-500 bg-primary-50 text-primary-700'
                      : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {range.label}
                </button>
              )
            })}
          </div>
          
          {/* Custom Budget Input */}
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <span className="text-gray-500 text-sm">$</span>
            </div>
            <input
              {...register('budget', { valueAsNumber: true })}
              type="number"
              id="budget"
              placeholder="Enter custom budget"
              min="100"
              max="100000"
              step="100"
              className={`form-input pl-8 ${errors.budget ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}`}
              aria-invalid={errors.budget ? 'true' : 'false'}
              aria-describedby={errors.budget ? 'budget-error' : undefined}
            />
          </div>
        </div>
        {errors.budget && (
          <p id="budget-error" className="mt-2 text-sm text-red-600" role="alert">
            {errors.budget.message}
          </p>
        )}
      </div>

      {/* Travel Preferences */}
      <Controller
        name="preferences"
        control={control}
        render={({ field }) => (
          <PreferencesSelector
            value={field.value || []}
            onChange={field.onChange}
            error={errors.preferences?.message}
          />
        )}
      />

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
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Creating Your Trip Plan...
            </div>
          ) : (
            '✨ Create My Trip Plan'
          )}
        </button>
        
        <button
          type="button"
          onClick={() => router.push('/destinations')}
          className="btn-outline py-4 px-6 text-sm"
        >
          Browse Destinations
        </button>
      </div>
    </form>
  )
}
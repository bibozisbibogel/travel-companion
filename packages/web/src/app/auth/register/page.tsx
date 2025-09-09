'use client'

import { useState, useMemo } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { registerSchema, type RegisterFormData, calculatePasswordStrength, getPasswordStrengthColor, getPasswordStrengthLabel } from '../../../lib/validation'
import { apiClient, ApiError } from '../../../lib/api'
import { CenteredLayout } from '../../../components/layouts'

export default function RegisterPage() {
  const [isLoading, setIsLoading] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const router = useRouter()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
    watch,
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  })

  // Watch the password field for real-time strength validation
  const password = watch('password', '')
  const passwordStrength = useMemo(() => calculatePasswordStrength(password), [password])

  const onSubmit = async (data: RegisterFormData) => {
    try {
      setIsLoading(true)
      setApiError(null)

      const response = await apiClient.register(data)
      
      // Debug: Log the response to see what we're actually getting
      console.log('Registration response:', response)

      if (response.access_token) {
        // Store the authentication token
        apiClient.setToken(response.access_token)
        
        // Redirect to home page or dashboard
        router.push('/')
      } else if (response.detail?.message) {
        setApiError(response.detail.message)
      } else {
        setApiError(response.message || 'Registration failed. Please try again.')
      }
    } catch (error) {
      console.error('Registration error:', error)
      if (error instanceof ApiError) {
        if (error.status === 422) {
          // Handle validation errors from API - check both formats
          const validationErrors = error.data?.data?.errors || error.data?.errors;
          
          if (Array.isArray(validationErrors)) {
            // New format: array of error objects
            validationErrors.forEach((err: any) => {
              if (err.field && err.message) {
                // Map backend field names to frontend field names
                let fieldName = err.field.replace('body -> ', '').replace('_', '');
                if (fieldName === 'firstname' || fieldName === 'lastname') {
                  // These errors should be shown as general errors since we have a single "name" field
                  setApiError(err.message);
                } else if (fieldName === 'email' || fieldName === 'password') {
                  setError(fieldName as keyof RegisterFormData, {
                    type: 'server',
                    message: err.message,
                  });
                }
              }
            });
          } else if (validationErrors && typeof validationErrors === 'object') {
            // Old format: object with field names as keys
            Object.entries(validationErrors).forEach(([field, messages]) => {
              if (Array.isArray(messages) && messages.length > 0) {
                setError(field as keyof RegisterFormData, {
                  type: 'server',
                  message: messages[0],
                })
              }
            })
          }
          
          // If no specific field errors were set, show the general message
          if (!validationErrors || (Array.isArray(validationErrors) && validationErrors.length === 0)) {
            setApiError(error.data?.message || 'Validation error occurred');
          }
        } else if (error.status === 409) {
          setApiError('An account with this email address already exists. Please try logging in instead.')
        } else {
          setApiError(error.message || 'An error occurred during registration. Please try again.')
        }
      } else {
        setApiError('Network error. Please check your connection and try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <CenteredLayout
      title="Create your account"
      subtitle="Start your travel planning journey with Travel Companion"
      maxWidth="max-w-md"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
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

        {/* Name Field */}
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
            Full name
          </label>
          <input
            {...register('name')}
            id="name"
            type="text"
            autoComplete="name"
            className={`form-input ${errors.name ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}`}
            placeholder="Enter your full name"
            aria-invalid={errors.name ? 'true' : 'false'}
            aria-describedby={errors.name ? 'name-error' : undefined}
          />
          {errors.name && (
            <p id="name-error" className="mt-2 text-sm text-red-600" role="alert">
              {errors.name.message}
            </p>
          )}
        </div>

        {/* Email Field */}
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
            Email address
          </label>
          <input
            {...register('email')}
            id="email"
            type="email"
            autoComplete="email"
            className={`form-input ${errors.email ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}`}
            placeholder="Enter your email address"
            aria-invalid={errors.email ? 'true' : 'false'}
            aria-describedby={errors.email ? 'email-error' : undefined}
          />
          {errors.email && (
            <p id="email-error" className="mt-2 text-sm text-red-600" role="alert">
              {errors.email.message}
            </p>
          )}
        </div>

        {/* Password Field with Strength Indicator */}
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
            Password
          </label>
          <input
            {...register('password')}
            id="password"
            type="password"
            autoComplete="new-password"
            className={`form-input ${errors.password ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}`}
            placeholder="Create a strong password"
            aria-invalid={errors.password ? 'true' : 'false'}
            aria-describedby={errors.password ? 'password-error' : 'password-strength'}
          />
          
          {/* Password Strength Indicator */}
          {password && (
            <div className="mt-2" id="password-strength">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-gray-700">Password strength:</span>
                <span className={`text-xs font-medium px-2 py-1 rounded ${getPasswordStrengthColor(passwordStrength.score)}`}>
                  {getPasswordStrengthLabel(passwordStrength.score)}
                </span>
              </div>
              
              {/* Progress Bar */}
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-300 ${
                    passwordStrength.score === 0 ? 'w-0' :
                    passwordStrength.score === 1 ? 'w-1/4 bg-red-500' :
                    passwordStrength.score === 2 ? 'w-2/4 bg-yellow-500' :
                    passwordStrength.score === 3 ? 'w-3/4 bg-blue-500' :
                    'w-full bg-green-500'
                  }`}
                />
              </div>

              {/* Feedback */}
              {passwordStrength.feedback.warning && (
                <p className="mt-1 text-xs text-orange-600">
                  {passwordStrength.feedback.warning}
                </p>
              )}
              {passwordStrength.feedback.suggestions.length > 0 && (
                <ul className="mt-1 text-xs text-gray-600">
                  {passwordStrength.feedback.suggestions.map((suggestion, index) => (
                    <li key={index}>• {suggestion}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {errors.password && (
            <p id="password-error" className="mt-2 text-sm text-red-600" role="alert">
              {errors.password.message}
            </p>
          )}
        </div>

        {/* Confirm Password Field */}
        <div>
          <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
            Confirm password
          </label>
          <input
            {...register('confirmPassword')}
            id="confirmPassword"
            type="password"
            autoComplete="new-password"
            className={`form-input ${errors.confirmPassword ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}`}
            placeholder="Confirm your password"
            aria-invalid={errors.confirmPassword ? 'true' : 'false'}
            aria-describedby={errors.confirmPassword ? 'confirmPassword-error' : undefined}
          />
          {errors.confirmPassword && (
            <p id="confirmPassword-error" className="mt-2 text-sm text-red-600" role="alert">
              {errors.confirmPassword.message}
            </p>
          )}
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isLoading || isSubmitting}
          className={`btn-primary w-full flex justify-center py-3 ${
            (isLoading || isSubmitting) ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {isLoading || isSubmitting ? (
            <div className="flex items-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Creating account...
            </div>
          ) : (
            '🚀 Create account'
          )}
        </button>

        {/* Sign In Link */}
        <div className="text-center">
          <p className="text-sm text-gray-600">
            Already have an account?{' '}
            <Link
              href="/auth/login"
              className="font-medium text-primary-600 hover:text-primary-500 transition-colors duration-200"
            >
              Sign in here
            </Link>
          </p>
        </div>
      </form>
    </CenteredLayout>
  )
}
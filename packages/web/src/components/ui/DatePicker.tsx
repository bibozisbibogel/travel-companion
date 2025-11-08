'use client'

import { useState, useEffect } from 'react'

interface IDatePickerProps {
  value: string
  onChange: (value: string) => void
  error?: string
  label: string
  placeholder?: string
  minDate?: string
  maxDate?: string
  className?: string
  id?: string
  required?: boolean
}

export default function DatePicker({
  value,
  onChange,
  error,
  label,
  placeholder = 'Select date',
  minDate,
  maxDate,
  className = '',
  id,
  required = false
}: IDatePickerProps) {
  const [displayValue, setDisplayValue] = useState('')

  // Format date for display
  useEffect(() => {
    if (value) {
      try {
        const date = new Date(value)
        if (!isNaN(date.getTime())) {
          setDisplayValue(date.toLocaleDateString('en-US', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric'
          }))
        }
      } catch {
        setDisplayValue('')
      }
    } else {
      setDisplayValue('')
    }
  }, [value])

  // Get default min/max dates
  const today = new Date().toISOString().split('T')[0]
  const oneYearFromNow = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000)
    .toISOString().split('T')[0]

  const effectiveMinDate = minDate || today
  const effectiveMaxDate = maxDate || oneYearFromNow

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value)
  }

  return (
    <div className="relative">
      <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-2">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      
      <div className="relative">
        <input
          type="date"
          id={id}
          value={value}
          onChange={handleDateChange}
          min={effectiveMinDate}
          max={effectiveMaxDate}
          className={`form-input pr-10 ${
            error ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''
          } ${className}`}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={error ? `${id}-error` : undefined}
        />
        
        {/* Calendar Icon */}
        <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
          <svg className="h-4 w-4 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </div>
      </div>

      {/* Display formatted date */}
      {displayValue && (
        <div className="mt-1 text-xs text-gray-500">
          {displayValue}
        </div>
      )}

      {/* Error Message */}
      {error && (
        <p id={`${id}-error`} className="mt-2 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
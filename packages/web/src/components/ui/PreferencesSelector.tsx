'use client'

import { TRAVEL_PREFERENCES } from '../../lib/constants'

interface IPreferencesSelectorProps {
  value: string[]
  onChange: (value: string[]) => void
  error?: string
  className?: string
}

export default function PreferencesSelector({
  value = [],
  onChange,
  error,
  className = ''
}: IPreferencesSelectorProps) {
  const togglePreference = (preferenceId: string) => {
    const newValue = value.includes(preferenceId)
      ? value.filter(id => id !== preferenceId)
      : [...value, preferenceId]
    
    onChange(newValue)
  }

  return (
    <div className={className}>
      <label className="block text-sm font-medium text-gray-700 mb-3">
        Travel Preferences
      </label>
      <p className="text-sm text-gray-600 mb-4">
        Select what interests you most (optional)
      </p>
      
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {TRAVEL_PREFERENCES.map((preference) => {
          const isSelected = value.includes(preference.id)
          
          return (
            <button
              key={preference.id}
              type="button"
              onClick={() => togglePreference(preference.id)}
              className={`
                relative p-3 rounded-lg border-2 text-center transition-all duration-200
                hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1
                ${isSelected 
                  ? 'border-primary-500 bg-primary-50 text-primary-700 shadow-sm' 
                  : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50'
                }
              `}
              aria-pressed={isSelected}
            >
              <div className="text-2xl mb-1">{preference.icon}</div>
              <div className="text-xs font-medium leading-tight">
                {preference.label}
              </div>
              
              {/* Selection indicator */}
              {isSelected && (
                <div className="absolute -top-1 -right-1 w-5 h-5 bg-primary-500 rounded-full flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </button>
          )
        })}
      </div>

      {value.length > 0 && (
        <div className="mt-3 text-sm text-gray-600">
          {value.length} preference{value.length !== 1 ? 's' : ''} selected
        </div>
      )}

      {error && (
        <p className="mt-2 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
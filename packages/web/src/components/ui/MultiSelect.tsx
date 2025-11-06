'use client'

import { useState } from 'react'

interface IMultiSelectOption {
  id: string
  label: string
  icon?: string
}

interface IMultiSelectProps {
  label: string
  description?: string
  options: IMultiSelectOption[]
  value: string[]
  onChange: (value: string[]) => void
  error?: string
  className?: string
  columns?: number
  searchable?: boolean
  maxHeight?: string
}

export default function MultiSelect({
  label,
  description,
  options,
  value = [],
  onChange,
  error,
  className = '',
  columns = 4,
  searchable = false,
  maxHeight = 'max-h-96',
}: IMultiSelectProps) {
  const [searchQuery, setSearchQuery] = useState('')

  const toggleOption = (optionId: string) => {
    const newValue = value.includes(optionId)
      ? value.filter(id => id !== optionId)
      : [...value, optionId]

    onChange(newValue)
  }

  const filteredOptions = searchable && searchQuery
    ? options.filter(option =>
        option.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        option.id.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : options

  const gridColsClass = {
    2: 'grid-cols-2',
    3: 'grid-cols-2 md:grid-cols-3',
    4: 'grid-cols-2 md:grid-cols-3 lg:grid-cols-4',
    5: 'grid-cols-2 md:grid-cols-3 lg:grid-cols-5',
    6: 'grid-cols-2 md:grid-cols-3 lg:grid-cols-6',
  }[columns] || 'grid-cols-2 md:grid-cols-3 lg:grid-cols-4'

  return (
    <div className={className}>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label}
      </label>
      {description && (
        <p className="text-sm text-gray-600 mb-4">
          {description}
        </p>
      )}

      {searchable && (
        <div className="mb-4">
          <input
            type="text"
            placeholder="Search cuisines..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
          {searchQuery && (
            <p className="text-xs text-gray-500 mt-2">
              Showing {filteredOptions.length} of {options.length} options
            </p>
          )}
        </div>
      )}

      <div className={`overflow-y-auto ${maxHeight}`}>
        <div className={`grid ${gridColsClass} gap-3`}>
          {filteredOptions.map((option) => {
          const isSelected = value.includes(option.id)

          return (
            <button
              key={option.id}
              type="button"
              onClick={() => toggleOption(option.id)}
              className={`
                relative p-3 rounded-lg border-2 text-center transition-all duration-200
                hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary-500
                ${isSelected
                  ? 'border-primary-500 bg-primary-50 text-primary-700 shadow-sm'
                  : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                }
              `}
              aria-pressed={isSelected}
            >
              {option.icon && (
                <div className="text-xl mb-1">{option.icon}</div>
              )}
              <div className="text-xs font-medium leading-tight">
                {option.label}
              </div>

              {isSelected && (
                <div className="absolute -top-1 -right-1 w-5 h-5 bg-primary-500 rounded-full">
                  <svg
                    className="w-3 h-3 text-white absolute top-1 left-1"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
              )}
            </button>
          )
        })}
        </div>
      </div>

      {value.length > 0 && (
        <div className="mt-3 text-sm text-gray-600">
          {value.length} selected
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

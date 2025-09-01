'use client'

import { useState, useEffect, useRef } from 'react'
import { apiClient } from '../../lib/api'
import type { IDestination } from '../../lib/types'
import { POPULAR_DESTINATIONS } from '../../lib/constants'

interface IDestinationSearchProps {
  value: string
  onChange: (value: string, destination?: IDestination) => void
  error?: string
  placeholder?: string
  className?: string
}

export default function DestinationSearch({ 
  value, 
  onChange, 
  error, 
  placeholder = "Where would you like to go?",
  className = ""
}: IDestinationSearchProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [suggestions, setSuggestions] = useState<IDestination[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)

  // Debounce search
  useEffect(() => {
    if (!value.trim()) {
      setSuggestions(POPULAR_DESTINATIONS.slice(0, 6))
      return
    }

    const searchTimeout = setTimeout(async () => {
      if (value.length >= 2) {
        try {
          setIsLoading(true)
          const results = await apiClient.searchDestinations(value)
          setSuggestions(results.slice(0, 8))
        } catch (error) {
          // Fallback to filtered popular destinations
          const filtered = POPULAR_DESTINATIONS.filter(dest => 
            dest.name.toLowerCase().includes(value.toLowerCase()) ||
            dest.country.toLowerCase().includes(value.toLowerCase())
          )
          setSuggestions(filtered.slice(0, 6))
        } finally {
          setIsLoading(false)
        }
      } else {
        setSuggestions([])
      }
    }, 300)

    return () => clearTimeout(searchTimeout)
  }, [value])

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1)
        break
      case 'Enter':
        e.preventDefault()
        if (selectedIndex >= 0 && suggestions[selectedIndex]) {
          selectDestination(suggestions[selectedIndex])
        }
        break
      case 'Escape':
        setIsOpen(false)
        setSelectedIndex(-1)
        break
    }
  }

  const selectDestination = (destination: IDestination) => {
    const displayName = destination.country === destination.name ? 
      destination.name : 
      `${destination.name}, ${destination.country}`
    onChange(displayName, destination)
    setIsOpen(false)
    setSelectedIndex(-1)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    onChange(newValue)
    setIsOpen(true)
    setSelectedIndex(-1)
  }

  const handleFocus = () => {
    setIsOpen(true)
    if (!value.trim()) {
      setSuggestions(POPULAR_DESTINATIONS.slice(0, 6))
    }
  }

  const handleBlur = (e: React.FocusEvent) => {
    // Delay closing to allow click on suggestions
    setTimeout(() => {
      if (!e.currentTarget.contains(document.activeElement)) {
        setIsOpen(false)
        setSelectedIndex(-1)
      }
    }, 200)
  }

  return (
    <div className="relative" onBlur={handleBlur}>
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleInputChange}
          onFocus={handleFocus}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={`form-input pr-10 ${error ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''} ${className}`}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={error ? 'destination-error' : undefined}
          autoComplete="off"
        />
        
        {/* Search/Loading Icon */}
        <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
          {isLoading ? (
            <svg className="animate-spin h-4 w-4 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          ) : (
            <svg className="h-4 w-4 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          )}
        </div>
      </div>

      {/* Suggestions Dropdown */}
      {isOpen && (
        <div className="absolute z-10 w-full mt-1 bg-white shadow-lg border border-gray-300 rounded-md py-1 max-h-60 overflow-auto">
          {suggestions.length > 0 ? (
            <ul ref={listRef} role="listbox" className="divide-y divide-gray-100">
              {!value.trim() && (
                <li className="px-4 py-2 text-sm text-gray-500 font-medium">
                  Popular destinations
                </li>
              )}
              {suggestions.map((destination, index) => {
                const displayName = destination.country === destination.name ? 
                  destination.name : 
                  `${destination.name}, ${destination.country}`
                
                return (
                  <li key={destination.id}>
                    <button
                      type="button"
                      onClick={() => selectDestination(destination)}
                      className={`w-full text-left px-4 py-2 hover:bg-gray-50 focus:bg-gray-50 focus:outline-none transition-colors ${
                        index === selectedIndex ? 'bg-primary-50 text-primary-600' : ''
                      }`}
                      role="option"
                      aria-selected={index === selectedIndex}
                    >
                      <div className="flex items-center">
                        <span className="mr-3 text-lg">
                          {destination.type === 'city' ? '🏙️' : 
                           destination.type === 'region' ? '🌍' : '📍'}
                        </span>
                        <div>
                          <div className="font-medium text-gray-900">
                            {destination.name}
                          </div>
                          {destination.country !== destination.name && (
                            <div className="text-sm text-gray-500">
                              {destination.country}
                            </div>
                          )}
                        </div>
                      </div>
                    </button>
                  </li>
                )
              })}
            </ul>
          ) : value.trim() && !isLoading ? (
            <div className="px-4 py-3 text-sm text-gray-500 text-center">
              No destinations found. Try a different search term.
            </div>
          ) : null}
        </div>
      )}

      {/* Error Message */}
      {error && (
        <p id="destination-error" className="mt-2 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
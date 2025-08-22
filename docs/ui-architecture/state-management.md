# State Management

## Store Structure

```
src/lib/store/
├── index.ts                 # Zustand store configuration
├── auth.ts                  # Authentication state slice
├── trip.ts                  # Trip planning state slice
├── ui.ts                    # UI state slice (modals, filters)
├── preferences.ts           # User preferences slice
└── types.ts                 # Store type definitions
```

## State Management Template

```typescript
import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

interface TripState {
  // Current trip data
  currentTrip: Trip | null
  tripResults: {
    flights: FlightOption[]
    hotels: HotelOption[]
    activities: ActivityOption[]
    restaurants: RestaurantOption[]
  }
  
  // Selection state
  selectedOptions: {
    flight?: FlightOption
    hotel?: HotelOption
    activities: ActivityOption[]
    restaurants: RestaurantOption[]
  }
  
  // UI state
  isLoading: boolean
  loadingStep?: 'searching' | 'processing' | 'optimizing'
  error: string | null
  
  // Filters and preferences
  filters: {
    budget: { min: number; max: number }
    flightPreferences: FlightFilters
    hotelPreferences: HotelFilters
    activityCategories: string[]
  }
  
  // Actions
  actions: {
    // Trip management
    createTrip: (request: TripRequest) => Promise<void>
    updateTrip: (tripId: string, updates: Partial<Trip>) => Promise<void>
    clearTrip: () => void
    
    // Results management
    setTripResults: (results: TripResults) => void
    updateResults: (category: 'flights' | 'hotels' | 'activities' | 'restaurants', items: any[]) => void
    
    // Selection management
    selectOption: (category: keyof TripState['selectedOptions'], option: any) => void
    clearSelection: (category: keyof TripState['selectedOptions']) => void
    
    // Filter management
    updateFilters: (category: string, filters: any) => void
    clearFilters: () => void
    
    // Loading and error management
    setLoading: (isLoading: boolean, step?: string) => void
    setError: (error: string | null) => void
  }
}

export const useTripStore = create<TripState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        currentTrip: null,
        tripResults: {
          flights: [],
          hotels: [],
          activities: [],
          restaurants: []
        },
        selectedOptions: {
          activities: [],
          restaurants: []
        },
        isLoading: false,
        error: null,
        filters: {
          budget: { min: 0, max: 10000 },
          flightPreferences: {
            maxStops: 2,
            preferredAirlines: [],
            timePreference: 'flexible'
          },
          hotelPreferences: {
            minRating: 3,
            amenities: [],
            location: 'city-center'
          },
          activityCategories: []
        },
        
        // Actions
        actions: {
          createTrip: async (request: TripRequest) => {
            set({ isLoading: true, error: null, loadingStep: 'searching' })
            
            try {
              const response = await apiClient.post('/trips/plan', request)
              const trip = response.data
              
              set({ 
                currentTrip: trip,
                isLoading: false,
                loadingStep: undefined
              })
            } catch (error) {
              set({ 
                error: error instanceof Error ? error.message : 'Failed to create trip',
                isLoading: false,
                loadingStep: undefined
              })
            }
          },
          
          updateTrip: async (tripId: string, updates: Partial<Trip>) => {
            set({ isLoading: true })
            
            try {
              const response = await apiClient.put(`/trips/${tripId}`, updates)
              set({ 
                currentTrip: response.data,
                isLoading: false
              })
            } catch (error) {
              set({ 
                error: error instanceof Error ? error.message : 'Failed to update trip',
                isLoading: false
              })
            }
          },
          
          clearTrip: () => {
            set({
              currentTrip: null,
              tripResults: {
                flights: [],
                hotels: [],
                activities: [],
                restaurants: []
              },
              selectedOptions: {
                activities: [],
                restaurants: []
              },
              error: null
            })
          },
          
          setTripResults: (results: TripResults) => {
            set({ tripResults: results })
          },
          
          updateResults: (category, items) => {
            set((state) => ({
              tripResults: {
                ...state.tripResults,
                [category]: items
              }
            }))
          },
          
          selectOption: (category, option) => {
            set((state) => {
              if (category === 'activities' || category === 'restaurants') {
                const currentSelections = state.selectedOptions[category] as any[]
                const isSelected = currentSelections.some(item => item.id === option.id)
                
                return {
                  selectedOptions: {
                    ...state.selectedOptions,
                    [category]: isSelected
                      ? currentSelections.filter(item => item.id !== option.id)
                      : [...currentSelections, option]
                  }
                }
              } else {
                return {
                  selectedOptions: {
                    ...state.selectedOptions,
                    [category]: option
                  }
                }
              }
            })
          },
          
          clearSelection: (category) => {
            set((state) => ({
              selectedOptions: {
                ...state.selectedOptions,
                [category]: category === 'activities' || category === 'restaurants' ? [] : undefined
              }
            }))
          },
          
          updateFilters: (category, filters) => {
            set((state) => ({
              filters: {
                ...state.filters,
                [category]: filters
              }
            }))
          },
          
          clearFilters: () => {
            set({
              filters: {
                budget: { min: 0, max: 10000 },
                flightPreferences: {
                  maxStops: 2,
                  preferredAirlines: [],
                  timePreference: 'flexible'
                },
                hotelPreferences: {
                  minRating: 3,
                  amenities: [],
                  location: 'city-center'
                },
                activityCategories: []
              }
            })
          },
          
          setLoading: (isLoading, step) => {
            set({ isLoading, loadingStep: step })
          },
          
          setError: (error) => {
            set({ error })
          }
        }
      }),
      {
        name: 'travel-companion-trip-store',
        partialize: (state) => ({
          currentTrip: state.currentTrip,
          selectedOptions: state.selectedOptions,
          filters: state.filters
        })
      }
    ),
    { name: 'TripStore' }
  )
)

// Selector hooks for better performance
export const useCurrentTrip = () => useTripStore((state) => state.currentTrip)
export const useTripResults = () => useTripStore((state) => state.tripResults)
export const useSelectedOptions = () => useTripStore((state) => state.selectedOptions)
export const useTripActions = () => useTripStore((state) => state.actions)
export const useFilters = () => useTripStore((state) => state.filters)
export const useTripLoading = () => useTripStore((state) => ({ isLoading: state.isLoading, loadingStep: state.loadingStep }))
```

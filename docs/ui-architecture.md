# Travel Companion Frontend Architecture Document

## Template and Framework Selection

### Framework Decision

**Selected Approach:** Next.js 14 with TypeScript starter template + Tailwind CSS

**Starter Template:** Next.js 14 App Router with TypeScript, ESLint, and Tailwind CSS
- **Template:** `npx create-next-app@latest travel-companion-web --typescript --tailwind --eslint --app`
- **Additional Starters:** shadcn/ui component library for travel-focused components

**Rationale:** 
- **Performance:** Next.js 14 App Router provides optimal loading with React Server Components
- **SEO Benefits:** Server-side rendering critical for travel planning discovery
- **Type Safety:** Full TypeScript integration matches backend API types
- **Proven Foundation:** Established patterns for complex state management and real-time features
- **Component Ecosystem:** Rich ecosystem for maps (Mapbox React), forms, and UI components

**Constraints & Considerations:**
- App Router pattern requires server/client component distinction
- Static generation not suitable for user-specific trip data
- Requires careful bundle splitting for map and PDF libraries

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2025-01-22 | v1.0 | Initial frontend architecture creation | Winston (Architect) |

## Frontend Tech Stack

This section aligns with and extends the main architecture document's technology choices, providing frontend-specific implementations.

### Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| **Framework** | Next.js | 14.1+ | React-based web application | App Router for performance, built-in optimization, excellent TypeScript support |
| **Language** | TypeScript | 5.3+ | Type-safe frontend development | Matches backend types, prevents runtime errors, excellent DX |
| **Styling** | Tailwind CSS | 3.4+ | Utility-first styling | Rapid development, consistent design system, mobile-first approach |
| **UI Library** | shadcn/ui | Latest | Component foundation | Accessible components, customizable, Tailwind-native |
| **State Management** | Zustand | 4.4+ | Client state management | Lightweight, TypeScript-first, simple patterns for travel data |
| **Routing** | Next.js App Router | Built-in | File-based routing | Server components, layout nesting, parallel routes for dashboard |
| **Build Tool** | Next.js/Turbopack | Built-in | Development and build | Fast refresh, optimized bundles, built-in optimizations |
| **HTTP Client** | Axios | 1.6+ | API communication | Interceptors for auth, request/response transformation |
| **Form Handling** | React Hook Form | 7.48+ | Form state and validation | Performance, TypeScript integration, minimal re-renders |
| **Map Integration** | Mapbox GL JS | 2.15+ | Interactive maps | Travel-focused features, customization, performance |
| **Animation** | Framer Motion | 10.16+ | Animations and transitions | Declarative animations, gesture support, React integration |
| **Testing** | Vitest + React Testing Library | Latest | Unit and integration testing | Fast, Vite-based, excellent React support |
| **E2E Testing** | Playwright | 1.40+ | End-to-end testing | Cross-browser, travel flow testing, screenshot comparison |
| **Component Library** | Headless UI | 1.7+ | Unstyled accessible components | Accessibility-first, full keyboard navigation |
| **Date Handling** | date-fns | 3.0+ | Date manipulation | Lightweight, immutable, excellent timezone support |
| **PDF Generation** | jsPDF + html2canvas | Latest | Client-side PDF export | Offline capability, full itinerary formatting |
| **Dev Tools** | Storybook | 7.6+ | Component development | Isolated development, documentation, testing |

## Project Structure

```
packages/web/                          # Next.js Frontend Application
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── globals.css               # Global Tailwind imports
│   │   ├── layout.tsx                # Root layout with providers
│   │   ├── page.tsx                  # Home page (travel request input)
│   │   ├── loading.tsx               # Global loading UI
│   │   ├── error.tsx                 # Global error boundary
│   │   ├── not-found.tsx             # 404 page
│   │   │
│   │   ├── auth/                     # Authentication pages
│   │   │   ├── login/
│   │   │   │   └── page.tsx          # Login form
│   │   │   ├── register/
│   │   │   │   └── page.tsx          # Registration form
│   │   │   └── layout.tsx            # Auth layout
│   │   │
│   │   ├── dashboard/                # User dashboard
│   │   │   ├── page.tsx              # Trip history and preferences
│   │   │   ├── profile/
│   │   │   │   └── page.tsx          # User profile management
│   │   │   └── layout.tsx            # Dashboard layout
│   │   │
│   │   ├── trips/                    # Trip planning and viewing
│   │   │   ├── new/
│   │   │   │   └── page.tsx          # New trip request form
│   │   │   ├── [trip_id]/
│   │   │   │   ├── page.tsx          # Trip results dashboard
│   │   │   │   ├── flights/
│   │   │   │   │   └── page.tsx      # Flight comparison view
│   │   │   │   ├── hotels/
│   │   │   │   │   └── page.tsx      # Hotel selection view
│   │   │   │   ├── activities/
│   │   │   │   │   └── page.tsx      # Activity browser
│   │   │   │   ├── restaurants/
│   │   │   │   │   └── page.tsx      # Restaurant finder
│   │   │   │   ├── budget/
│   │   │   │   │   └── page.tsx      # Budget tracker view
│   │   │   │   ├── map/
│   │   │   │   │   └── page.tsx      # Interactive map view
│   │   │   │   ├── itinerary/
│   │   │   │   │   └── page.tsx      # Final itinerary
│   │   │   │   └── loading.tsx       # Trip loading state
│   │   │   └── layout.tsx            # Trip planning layout
│   │   │
│   │   └── api/                      # API routes (if needed)
│   │       └── auth/                 # Client-side auth helpers
│   │
│   ├── components/                   # Reusable components
│   │   ├── ui/                       # Base UI components
│   │   │   ├── Button.tsx            # Button variants
│   │   │   ├── Card.tsx              # Card container
│   │   │   ├── Input.tsx             # Form inputs
│   │   │   ├── Modal.tsx             # Modal/dialog
│   │   │   ├── Tabs.tsx              # Tab navigation
│   │   │   ├── Badge.tsx             # Status badges
│   │   │   ├── Spinner.tsx           # Loading spinners
│   │   │   └── index.ts              # Component exports
│   │   │
│   │   ├── forms/                    # Form-specific components
│   │   │   ├── TravelRequestForm.tsx # Main travel input form
│   │   │   ├── FilterPanel.tsx       # Search refinement
│   │   │   ├── BudgetSlider.tsx      # Budget range selector
│   │   │   └── DateRangePicker.tsx   # Travel date selection
│   │   │
│   │   ├── travel/                   # Travel-specific components
│   │   │   ├── FlightCard.tsx        # Flight option display
│   │   │   ├── HotelCard.tsx         # Hotel option display
│   │   │   ├── ActivityCard.tsx      # Activity display
│   │   │   ├── RestaurantCard.tsx    # Restaurant display
│   │   │   ├── ItineraryTimeline.tsx # Day-by-day schedule
│   │   │   └── BudgetTracker.tsx     # Real-time budget display
│   │   │
│   │   ├── maps/                     # Map-related components
│   │   │   ├── InteractiveMap.tsx    # Main map component
│   │   │   ├── MapMarker.tsx         # Custom map markers
│   │   │   ├── RouteOverlay.tsx      # Route visualization
│   │   │   └── MapControls.tsx       # Map interaction controls
│   │   │
│   │   ├── layouts/                  # Layout components
│   │   │   ├── Header.tsx            # Main navigation header
│   │   │   ├── Footer.tsx            # Site footer
│   │   │   ├── Sidebar.tsx           # Dashboard sidebar
│   │   │   └── DashboardTabs.tsx     # Trip dashboard tabs
│   │   │
│   │   └── shared/                   # Shared utility components
│   │       ├── LoadingState.tsx      # Various loading states
│   │       ├── ErrorBoundary.tsx     # Error handling wrapper
│   │       ├── ProgressBar.tsx       # Trip planning progress
│   │       └── NotificationToast.tsx # Success/error notifications
│   │
│   ├── lib/                         # Utility libraries
│   │   ├── api/                     # API client configuration
│   │   │   ├── client.ts            # Axios configuration
│   │   │   ├── auth.ts              # Auth interceptors
│   │   │   ├── types.ts             # API response types
│   │   │   └── endpoints.ts         # API endpoint definitions
│   │   │
│   │   ├── store/                   # State management
│   │   │   ├── auth.ts              # Authentication state
│   │   │   ├── trip.ts              # Trip planning state
│   │   │   ├── ui.ts                # UI state (modals, filters)
│   │   │   └── index.ts             # Store configuration
│   │   │
│   │   ├── utils/                   # Utility functions
│   │   │   ├── formatting.ts        # Price, date formatting
│   │   │   ├── validation.ts        # Form validation helpers
│   │   │   ├── constants.ts         # App constants
│   │   │   ├── travel.ts            # Travel-specific utilities
│   │   │   └── pdf.ts               # PDF export utilities
│   │   │
│   │   ├── hooks/                   # Custom React hooks
│   │   │   ├── useAuth.ts           # Authentication hook
│   │   │   ├── useTrip.ts           # Trip data management
│   │   │   ├── useWebSocket.ts      # Real-time updates
│   │   │   ├── useLocalStorage.ts   # Persistent preferences
│   │   │   └── useMap.ts            # Map interaction hook
│   │   │
│   │   └── types/                   # TypeScript definitions
│   │       ├── api.ts               # API response types
│   │       ├── travel.ts            # Travel domain types
│   │       ├── user.ts              # User-related types
│   │       └── index.ts             # Type exports
│   │
│   ├── styles/                      # Styling
│   │   ├── globals.css              # Global styles and Tailwind
│   │   ├── components.css           # Component-specific styles
│   │   └── animations.css           # Animation utilities
│   │
│   └── __tests__/                   # Tests
│       ├── components/              # Component tests
│       ├── pages/                   # Page tests
│       ├── utils/                   # Utility tests
│       ├── setup.ts                 # Test configuration
│       └── mocks/                   # Mock data and handlers
│
├── public/                          # Static assets
│   ├── images/                      # Travel images and icons
│   ├── icons/                       # App icons and favicons
│   └── locales/                     # i18n JSON files (future)
│
├── .storybook/                      # Storybook configuration
│   ├── main.ts                      # Storybook config
│   └── preview.ts                   # Global story settings
│
├── stories/                         # Component stories
│   ├── components/                  # UI component stories
│   └── pages/                       # Page-level stories
│
├── package.json                     # Dependencies and scripts
├── next.config.js                   # Next.js configuration
├── tailwind.config.js               # Tailwind customization
├── tsconfig.json                    # TypeScript configuration
├── vitest.config.ts                 # Test configuration
├── playwright.config.ts             # E2E test configuration
└── Dockerfile                       # Container configuration
```

## Component Standards

### Component Template

```typescript
'use client'

import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

interface FlightCardProps {
  flight: FlightOption
  isSelected?: boolean
  onSelect?: (flightId: string) => void
  onCompare?: (flightId: string) => void
  className?: string
}

export const FlightCard = forwardRef<HTMLDivElement, FlightCardProps>(
  ({ flight, isSelected = false, onSelect, onCompare, className, ...props }, ref) => {
    const handleSelect = () => {
      onSelect?.(flight.flight_id)
    }

    const handleCompare = (e: React.MouseEvent) => {
      e.stopPropagation()
      onCompare?.(flight.flight_id)
    }

    return (
      <div
        ref={ref}
        className={cn(
          'rounded-lg border bg-card text-card-foreground shadow-sm transition-all duration-200',
          'hover:shadow-md hover:-translate-y-1',
          isSelected && 'ring-2 ring-primary ring-offset-2',
          'cursor-pointer',
          className
        )}
        onClick={handleSelect}
        role="button"
        tabIndex={0}
        aria-selected={isSelected}
        aria-label={`Flight ${flight.airline} departing ${flight.departure_time}`}
        {...props}
      >
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-sm font-medium leading-none">{flight.airline}</p>
              <p className="text-sm text-muted-foreground">{flight.flight_number}</p>
            </div>
            <div className="text-right">
              <p className="text-lg font-bold">${flight.price}</p>
              <p className="text-sm text-muted-foreground">{flight.currency}</p>
            </div>
          </div>
          
          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm">
              <p className="font-medium">{flight.departure_time}</p>
              <p className="text-muted-foreground">{flight.origin}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-muted-foreground">
                {Math.floor(flight.duration_minutes / 60)}h {flight.duration_minutes % 60}m
              </p>
              <p className="text-xs text-muted-foreground">
                {flight.stops === 0 ? 'Direct' : `${flight.stops} stop${flight.stops > 1 ? 's' : ''}`}
              </p>
            </div>
            <div className="text-right text-sm">
              <p className="font-medium">{flight.arrival_time}</p>
              <p className="text-muted-foreground">{flight.destination}</p>
            </div>
          </div>
          
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={handleCompare}>
              Compare
            </Button>
            <Button size="sm" disabled={isSelected}>
              {isSelected ? 'Selected' : 'Select Flight'}
            </Button>
          </div>
        </div>
      </div>
    )
  }
)

FlightCard.displayName = 'FlightCard'

export type { FlightCardProps }
```

### Naming Conventions

**Components:**
- PascalCase for component names: `FlightCard`, `TravelRequestForm`
- Props interfaces: `ComponentNameProps` (e.g., `FlightCardProps`)
- Event handlers: `handleActionName` (e.g., `handleSelect`, `handleFilterChange`)

**Files:**
- Component files: PascalCase matching component name
- Utility files: camelCase (e.g., `apiClient.ts`, `formatUtils.ts`)
- Hook files: camelCase with "use" prefix (e.g., `useAuth.ts`)
- Type definition files: camelCase (e.g., `travel.ts`, `api.ts`)

**CSS Classes:**
- Tailwind utility classes preferred
- Custom classes: kebab-case with component prefix (e.g., `flight-card-selected`)
- CSS custom properties: kebab-case (e.g., `--brand-primary`)

**State and Variables:**
- camelCase for variables and state: `selectedFlight`, `isLoading`
- UPPER_SNAKE_CASE for constants: `API_BASE_URL`, `MAX_TRAVELERS`
- Boolean variables: prefix with "is", "has", "can", "should" (e.g., `isSelected`, `hasError`)

## State Management

### Store Structure

```
src/lib/store/
├── index.ts                 # Zustand store configuration
├── auth.ts                  # Authentication state slice
├── trip.ts                  # Trip planning state slice
├── ui.ts                    # UI state slice (modals, filters)
├── preferences.ts           # User preferences slice
└── types.ts                 # Store type definitions
```

### State Management Template

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

## API Integration

### Service Template

```typescript
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { useAuthStore } from '@/lib/store/auth'

interface ApiError {
  message: string
  code?: string
  details?: unknown
}

interface ApiResponse<T = any> {
  success: boolean
  data: T
  error?: ApiError
  meta?: {
    total?: number
    page?: number
    limit?: number
  }
}

class ApiClient {
  private instance: AxiosInstance

  constructor(baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1') {
    this.instance = axios.create({
      baseURL,
      timeout: 30000, // 30 seconds for travel API calls
      headers: {
        'Content-Type': 'application/json'
      }
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request interceptor for authentication
    this.instance.interceptors.request.use(
      (config) => {
        const token = useAuthStore.getState().token
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor for error handling
    this.instance.interceptors.response.use(
      (response: AxiosResponse<ApiResponse>) => response,
      async (error) => {
        const originalRequest = error.config

        // Handle authentication errors
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true
          
          try {
            await this.refreshToken()
            const token = useAuthStore.getState().token
            originalRequest.headers.Authorization = `Bearer ${token}`
            return this.instance(originalRequest)
          } catch (refreshError) {
            useAuthStore.getState().actions.logout()
            window.location.href = '/auth/login'
            return Promise.reject(refreshError)
          }
        }

        // Handle rate limiting
        if (error.response?.status === 429) {
          const retryAfter = error.response.headers['retry-after'] || 1
          await new Promise(resolve => setTimeout(resolve, retryAfter * 1000))
          return this.instance(originalRequest)
        }

        return Promise.reject(this.normalizeError(error))
      }
    )
  }

  private normalizeError(error: any): ApiError {
    if (error.response?.data?.error) {
      return error.response.data.error
    }

    if (error.response?.data?.message) {
      return { message: error.response.data.message }
    }

    if (error.message) {
      return { message: error.message }
    }

    return { message: 'An unexpected error occurred' }
  }

  private async refreshToken(): Promise<void> {
    const refreshToken = useAuthStore.getState().refreshToken
    if (!refreshToken) {
      throw new Error('No refresh token available')
    }

    const response = await this.instance.post('/auth/refresh', {
      refresh_token: refreshToken
    })

    const { access_token, refresh_token } = response.data.data
    useAuthStore.getState().actions.setTokens(access_token, refresh_token)
  }

  // Generic API methods
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.instance.get<ApiResponse<T>>(url, config)
    return response.data.data
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.instance.post<ApiResponse<T>>(url, data, config)
    return response.data.data
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.instance.put<ApiResponse<T>>(url, data, config)
    return response.data.data
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.instance.delete<ApiResponse<T>>(url, config)
    return response.data.data
  }

  // Travel-specific methods
  async createTripPlan(request: TripRequest): Promise<Trip> {
    return this.post<Trip>('/trips/plan', request)
  }

  async getTripResults(tripId: string): Promise<TripResults> {
    return this.get<TripResults>(`/trips/${tripId}`)
  }

  async updateTripSelections(tripId: string, selections: TripSelections): Promise<Trip> {
    return this.put<Trip>(`/trips/${tripId}/selections`, selections)
  }

  async exportTripPDF(tripId: string): Promise<Blob> {
    const response = await this.instance.get(`/trips/${tripId}/export`, {
      responseType: 'blob'
    })
    return response.data
  }

  async getFlightDetails(flightId: string): Promise<FlightOption> {
    return this.get<FlightOption>(`/flights/${flightId}`)
  }

  async getHotelDetails(hotelId: string): Promise<HotelOption> {
    return this.get<HotelOption>(`/hotels/${hotelId}`)
  }

  async getUserTrips(page = 1, limit = 10): Promise<{ trips: Trip[]; total: number }> {
    return this.get<{ trips: Trip[]; total: number }>(`/users/trips?page=${page}&limit=${limit}`)
  }
}

export const apiClient = new ApiClient()

// React Query integration helpers
export const createTripMutation = (onSuccess?: (data: Trip) => void) => ({
  mutationFn: (request: TripRequest) => apiClient.createTripPlan(request),
  onSuccess,
  onError: (error: ApiError) => {
    console.error('Failed to create trip:', error.message)
  }
})

export const tripResultsQuery = (tripId: string) => ({
  queryKey: ['trip', tripId],
  queryFn: () => apiClient.getTripResults(tripId),
  enabled: !!tripId,
  refetchInterval: 5000, // Poll every 5 seconds during planning
  staleTime: 10000 // Consider data stale after 10 seconds
})
```

### API Client Configuration

```typescript
// lib/api/config.ts
import { apiClient } from './client'

// Environment-specific configuration
const API_CONFIG = {
  development: {
    baseURL: 'http://localhost:8000/api/v1',
    timeout: 30000,
    retries: 3
  },
  staging: {
    baseURL: 'https://api-staging.travelcompanion.com/api/v1',
    timeout: 20000,
    retries: 2
  },
  production: {
    baseURL: 'https://api.travelcompanion.com/api/v1',
    timeout: 15000,
    retries: 2
  }
}

const environment = process.env.NODE_ENV as keyof typeof API_CONFIG
const config = API_CONFIG[environment] || API_CONFIG.development

// Configure API client based on environment
apiClient.defaults.baseURL = config.baseURL
apiClient.defaults.timeout = config.timeout

// WebSocket configuration for real-time updates
export const WS_CONFIG = {
  url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',
  reconnectInterval: 3000,
  maxReconnectAttempts: 5
}

// Real-time trip planning updates
export class TripWebSocket {
  private ws: WebSocket | null = null
  private tripId: string | null = null
  private reconnectAttempts = 0

  connect(tripId: string, onUpdate: (data: any) => void) {
    this.tripId = tripId
    this.ws = new WebSocket(`${WS_CONFIG.url}/trips/${tripId}/updates`)

    this.ws.onopen = () => {
      console.log('Connected to trip updates')
      this.reconnectAttempts = 0
    }

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      onUpdate(data)
    }

    this.ws.onclose = () => {
      this.handleReconnect(onUpdate)
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  private handleReconnect(onUpdate: (data: any) => void) {
    if (this.reconnectAttempts < WS_CONFIG.maxReconnectAttempts && this.tripId) {
      this.reconnectAttempts++
      setTimeout(() => {
        this.connect(this.tripId!, onUpdate)
      }, WS_CONFIG.reconnectInterval)
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
      this.tripId = null
      this.reconnectAttempts = 0
    }
  }
}

export const tripWebSocket = new TripWebSocket()
```

## Routing

### Route Configuration

```typescript
// app/layout.tsx - Root layout with providers and global state
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Providers } from '@/components/providers'
import { Header } from '@/components/layouts/Header'
import { Footer } from '@/components/layouts/Footer'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Travel Companion - AI-Powered Trip Planning',
  description: 'Plan your perfect trip with AI-powered recommendations for flights, hotels, activities, and more.',
  keywords: 'travel planning, AI travel, trip planner, flights, hotels, activities',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={inter.className}>
      <body>
        <Providers>
          <div className="min-h-screen flex flex-col">
            <Header />
            <main className="flex-1">
              {children}
            </main>
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  )
}

// app/trips/[trip_id]/layout.tsx - Trip-specific layout with navigation
import { Suspense } from 'react'
import { TripNavigation } from '@/components/layouts/TripNavigation'
import { TripProvider } from '@/components/providers/TripProvider'
import { LoadingState } from '@/components/shared/LoadingState'

interface TripLayoutProps {
  children: React.ReactNode
  params: { trip_id: string }
}

export default function TripLayout({ children, params }: TripLayoutProps) {
  return (
    <TripProvider tripId={params.trip_id}>
      <div className="container mx-auto px-4 py-6">
        <TripNavigation tripId={params.trip_id} />
        <Suspense fallback={<LoadingState message="Loading trip data..." />}>
          <div className="mt-6">
            {children}
          </div>
        </Suspense>
      </div>
    </TripProvider>
  )
}

// lib/auth/ProtectedRoute.tsx - Route protection wrapper
'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store/auth'
import { LoadingState } from '@/components/shared/LoadingState'

interface ProtectedRouteProps {
  children: React.ReactNode
  requireAuth?: boolean
  redirectTo?: string
}

export function ProtectedRoute({ 
  children, 
  requireAuth = true,
  redirectTo = '/auth/login' 
}: ProtectedRouteProps) {
  const router = useRouter()
  const { isAuthenticated, isLoading, user } = useAuthStore()

  useEffect(() => {
    if (!isLoading && requireAuth && !isAuthenticated) {
      router.push(redirectTo)
    }
  }, [isAuthenticated, isLoading, requireAuth, router, redirectTo])

  if (isLoading) {
    return <LoadingState message="Checking authentication..." />
  }

  if (requireAuth && !isAuthenticated) {
    return null // Will redirect via useEffect
  }

  return <>{children}</>
}

// lib/hooks/useRouteGuard.ts - Route guard hook
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store/auth'
import { useTripStore } from '@/lib/store/trip'

interface RouteGuardOptions {
  requireAuth?: boolean
  requireTrip?: boolean
  allowedRoles?: string[]
}

export function useRouteGuard(options: RouteGuardOptions = {}) {
  const router = useRouter()
  const { isAuthenticated, user } = useAuthStore()
  const { currentTrip } = useTripStore()

  useEffect(() => {
    // Check authentication
    if (options.requireAuth && !isAuthenticated) {
      router.push('/auth/login')
      return
    }

    // Check user roles
    if (options.allowedRoles && user && !options.allowedRoles.includes(user.role)) {
      router.push('/unauthorized')
      return
    }

    // Check trip requirement
    if (options.requireTrip && !currentTrip) {
      router.push('/trips/new')
      return
    }
  }, [isAuthenticated, user, currentTrip, router, options])

  return {
    isAuthorized: (!options.requireAuth || isAuthenticated) &&
                 (!options.allowedRoles || (user && options.allowedRoles.includes(user.role))) &&
                 (!options.requireTrip || !!currentTrip)
  }
}

// app/trips/[trip_id]/page.tsx - Example protected route usage
'use client'

import { useParams } from 'next/navigation'
import { ProtectedRoute } from '@/lib/auth/ProtectedRoute'
import { TripDashboard } from '@/components/travel/TripDashboard'
import { useRouteGuard } from '@/lib/hooks/useRouteGuard'

export default function TripPage() {
  const params = useParams()
  const tripId = params.trip_id as string

  const { isAuthorized } = useRouteGuard({
    requireAuth: true,
    requireTrip: false // Trip will be loaded by component
  })

  if (!isAuthorized) {
    return null
  }

  return (
    <ProtectedRoute>
      <TripDashboard tripId={tripId} />
    </ProtectedRoute>
  )
}
```

## Styling Guidelines

### Styling Approach

**Primary Method:** Tailwind CSS with custom component classes for complex travel-specific components.

**Design System Integration:** Tailwind configured with Travel Companion design tokens, extended with shadcn/ui components for accessibility and consistency.

**Component Styling Pattern:**
- Tailwind utility classes for layout, spacing, and common styling
- CSS custom properties for theme values and dynamic styling
- Component-specific CSS classes for complex animations and travel-domain styling
- Conditional classes using `clsx` or `cn` utility for dynamic styling

### Global Theme Variables

```css
/* styles/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  /* Brand Colors - Travel Companion Theme */
  --brand-primary: #2563eb;
  --brand-secondary: #0ea5e9;
  --brand-accent: #10b981;
  
  /* Travel-specific Semantic Colors */
  --flight-color: #3b82f6;
  --hotel-color: #8b5cf6;
  --activity-color: #f59e0b;
  --restaurant-color: #ef4444;
  --budget-color: #10b981;
  
  /* Status Colors */
  --success: #059669;
  --warning: #d97706;
  --error: #dc2626;
  --info: #0ea5e9;
  
  /* Neutral Colors */
  --gray-50: #f8fafc;
  --gray-100: #f1f5f9;
  --gray-200: #e2e8f0;
  --gray-300: #cbd5e1;
  --gray-400: #94a3b8;
  --gray-500: #64748b;
  --gray-600: #475569;
  --gray-700: #334155;
  --gray-800: #1e293b;
  --gray-900: #0f172a;
  
  /* Background Colors */
  --background: #ffffff;
  --surface: #f8fafc;
  --card: #ffffff;
  --overlay: rgba(15, 23, 42, 0.8);
  
  /* Text Colors */
  --text-primary: var(--gray-900);
  --text-secondary: var(--gray-600);
  --text-tertiary: var(--gray-400);
  --text-inverse: #ffffff;
  
  /* Border Colors */
  --border-light: var(--gray-200);
  --border-medium: var(--gray-300);
  --border-strong: var(--gray-400);
  
  /* Spacing Scale (rem units) */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  --spacing-2xl: 3rem;
  --spacing-3xl: 4rem;
  
  /* Typography Scale */
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.5rem;
  --text-3xl: 1.875rem;
  --text-4xl: 2.25rem;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  
  /* Border Radius */
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;
  --radius-full: 9999px;
  
  /* Transitions */
  --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 300ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: 500ms cubic-bezier(0.4, 0, 0.2, 1);
  
  /* Layout Constraints */
  --container-sm: 640px;
  --container-md: 768px;
  --container-lg: 1024px;
  --container-xl: 1280px;
  --container-2xl: 1536px;
}

/* Dark Theme Variables */
[data-theme="dark"] {
  --background: var(--gray-900);
  --surface: var(--gray-800);
  --card: var(--gray-800);
  --overlay: rgba(0, 0, 0, 0.8);
  
  --text-primary: var(--gray-100);
  --text-secondary: var(--gray-300);
  --text-tertiary: var(--gray-500);
  
  --border-light: var(--gray-700);
  --border-medium: var(--gray-600);
  --border-strong: var(--gray-500);
}

/* Base Styles */
@layer base {
  * {
    box-sizing: border-box;
  }
  
  html {
    scroll-behavior: smooth;
    font-size: 16px;
  }
  
  body {
    background-color: var(--background);
    color: var(--text-primary);
    font-family: 'Inter', system-ui, sans-serif;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }
  
  /* Focus styles for accessibility */
  *:focus-visible {
    outline: 3px solid var(--brand-primary);
    outline-offset: 2px;
  }
}

/* Component Layer - Travel-specific components */
@layer components {
  /* Travel Card Base Styles */
  .travel-card {
    @apply bg-card rounded-lg border border-border-light p-6 shadow-sm transition-all duration-300;
    @apply hover:shadow-md hover:-translate-y-1;
  }
  
  .travel-card--selected {
    @apply ring-2 ring-brand-primary ring-offset-2;
  }
  
  .travel-card--flight {
    @apply border-l-4 border-l-flight-color;
  }
  
  .travel-card--hotel {
    @apply border-l-4 border-l-hotel-color;
  }
  
  .travel-card--activity {
    @apply border-l-4 border-l-activity-color;
  }
  
  .travel-card--restaurant {
    @apply border-l-4 border-l-restaurant-color;
  }
  
  /* Budget Tracker Styles */
  .budget-tracker {
    @apply bg-card rounded-lg p-4 border border-border-light;
  }
  
  .budget-bar {
    @apply h-2 rounded-full bg-gray-200 overflow-hidden;
  }
  
  .budget-progress {
    @apply h-full transition-all duration-500;
  }
  
  .budget-progress--under {
    @apply bg-success;
  }
  
  .budget-progress--at {
    @apply bg-warning;
  }
  
  .budget-progress--over {
    @apply bg-error;
  }
  
  /* Map Marker Styles */
  .map-marker {
    @apply w-8 h-8 rounded-full border-2 border-white shadow-lg cursor-pointer;
    @apply transition-transform duration-200 hover:scale-110;
  }
  
  .map-marker--flight {
    @apply bg-flight-color;
  }
  
  .map-marker--hotel {
    @apply bg-hotel-color;
  }
  
  .map-marker--activity {
    @apply bg-activity-color;
  }
  
  .map-marker--restaurant {
    @apply bg-restaurant-color;
  }
  
  /* Loading Animation */
  .loading-skeleton {
    @apply animate-pulse bg-gray-200 rounded;
  }
  
  /* Travel Input Field */
  .travel-input {
    @apply w-full px-4 py-3 border border-border-medium rounded-lg;
    @apply focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent;
    @apply transition-all duration-200;
  }
  
  /* Responsive Navigation */
  .nav-mobile {
    @apply fixed inset-x-0 bottom-0 bg-card border-t border-border-light;
    @apply flex items-center justify-around py-2 z-50;
  }
  
  .nav-item {
    @apply flex flex-col items-center p-2 rounded-lg transition-colors duration-200;
    @apply hover:bg-gray-100 active:bg-gray-200;
  }
  
  .nav-item--active {
    @apply text-brand-primary;
  }
}

/* Utility Layer - Custom utilities */
@layer utilities {
  /* Travel-specific spacing */
  .space-travel {
    @apply space-y-6 md:space-y-8;
  }
  
  /* Grid layouts for travel cards */
  .travel-grid {
    @apply grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3;
  }
  
  .travel-grid--flights {
    @apply grid-cols-1 lg:grid-cols-2;
  }
  
  /* Responsive text */
  .text-responsive-sm {
    @apply text-sm md:text-base;
  }
  
  .text-responsive-lg {
    @apply text-lg md:text-xl lg:text-2xl;
  }
  
  /* Safe area for mobile */
  .safe-area-bottom {
    padding-bottom: env(safe-area-inset-bottom);
  }
  
  /* Scroll behavior */
  .scroll-smooth {
    scroll-behavior: smooth;
  }
  
  /* Hide scrollbar but keep functionality */
  .hide-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
  
  .hide-scrollbar::-webkit-scrollbar {
    display: none;
  }
}

/* Print Styles */
@media print {
  .print-hidden {
    display: none !important;
  }
  
  .travel-card {
    break-inside: avoid;
    box-shadow: none;
    border: 1px solid var(--border-light);
  }
}

/* Reduced Motion */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

## Testing Requirements

### Component Test Template

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FlightCard } from '@/components/travel/FlightCard'
import type { FlightOption } from '@/lib/types/travel'

// Mock data
const mockFlight: FlightOption = {
  flight_id: 'flight-123',
  airline: 'American Airlines',
  flight_number: 'AA1234',
  price: 450.00,
  currency: 'USD',
  origin: 'JFK',
  destination: 'LAX',
  departure_time: '2024-06-01T10:00:00Z',
  arrival_time: '2024-06-01T13:30:00Z',
  duration_minutes: 330,
  stops: 0
}

// Mock handlers
const mockOnSelect = vi.fn()
const mockOnCompare = vi.fn()

describe('FlightCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders flight information correctly', () => {
    render(
      <FlightCard 
        flight={mockFlight}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    // Test basic information display
    expect(screen.getByText('American Airlines')).toBeInTheDocument()
    expect(screen.getByText('AA1234')).toBeInTheDocument()
    expect(screen.getByText('$450')).toBeInTheDocument()
    expect(screen.getByText('USD')).toBeInTheDocument()
    expect(screen.getByText('JFK')).toBeInTheDocument()
    expect(screen.getByText('LAX')).toBeInTheDocument()
    expect(screen.getByText('5h 30m')).toBeInTheDocument()
    expect(screen.getByText('Direct')).toBeInTheDocument()
  })

  it('handles flight selection correctly', async () => {
    const user = userEvent.setup()
    
    render(
      <FlightCard 
        flight={mockFlight}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    const card = screen.getByRole('button', { 
      name: /flight american airlines departing/i 
    })
    
    await user.click(card)
    
    expect(mockOnSelect).toHaveBeenCalledWith('flight-123')
    expect(mockOnSelect).toHaveBeenCalledTimes(1)
  })

  it('handles compare action without triggering selection', async () => {
    const user = userEvent.setup()
    
    render(
      <FlightCard 
        flight={mockFlight}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    const compareButton = screen.getByRole('button', { name: /compare/i })
    
    await user.click(compareButton)
    
    expect(mockOnCompare).toHaveBeenCalledWith('flight-123')
    expect(mockOnSelect).not.toHaveBeenCalled()
  })

  it('displays selected state correctly', () => {
    render(
      <FlightCard 
        flight={mockFlight}
        isSelected={true}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    const card = screen.getByRole('button', { 
      name: /flight american airlines departing/i 
    })
    
    expect(card).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText('Selected')).toBeInTheDocument()
    
    const selectButton = screen.getByRole('button', { name: /selected/i })
    expect(selectButton).toBeDisabled()
  })

  it('handles flights with stops correctly', () => {
    const flightWithStops = {
      ...mockFlight,
      stops: 1
    }

    render(
      <FlightCard 
        flight={flightWithStops}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    expect(screen.getByText('1 stop')).toBeInTheDocument()
  })

  it('handles flights with multiple stops correctly', () => {
    const flightWithMultipleStops = {
      ...mockFlight,
      stops: 2
    }

    render(
      <FlightCard 
        flight={flightWithMultipleStops}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    expect(screen.getByText('2 stops')).toBeInTheDocument()
  })

  it('supports keyboard navigation', async () => {
    const user = userEvent.setup()
    
    render(
      <FlightCard 
        flight={mockFlight}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    const card = screen.getByRole('button', { 
      name: /flight american airlines departing/i 
    })
    
    // Focus the card
    card.focus()
    expect(card).toHaveFocus()
    
    // Activate with Enter key
    await user.keyboard('{Enter}')
    expect(mockOnSelect).toHaveBeenCalledWith('flight-123')
    
    // Test Space key
    vi.clearAllMocks()
    await user.keyboard(' ')
    expect(mockOnSelect).toHaveBeenCalledWith('flight-123')
  })

  it('applies custom className correctly', () => {
    const customClass = 'custom-flight-card'
    
    render(
      <FlightCard 
        flight={mockFlight}
        className={customClass}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    const card = screen.getByRole('button', { 
      name: /flight american airlines departing/i 
    })
    
    expect(card).toHaveClass(customClass)
  })

  it('handles missing optional props gracefully', () => {
    render(<FlightCard flight={mockFlight} />)

    const card = screen.getByRole('button', { 
      name: /flight american airlines departing/i 
    })
    
    // Should render without crashing
    expect(card).toBeInTheDocument()
    expect(screen.getByText('American Airlines')).toBeInTheDocument()
  })
})

// Integration test example
describe('FlightCard Integration', () => {
  it('integrates with travel store correctly', async () => {
    const user = userEvent.setup()
    
    // Mock the travel store
    const mockUseTripStore = vi.fn(() => ({
      selectedOptions: { flight: null },
      actions: { selectOption: vi.fn() }
    }))

    vi.mock('@/lib/store/trip', () => ({
      useTripStore: mockUseTripStore
    }))

    const TestComponent = () => {
      const { selectedOptions, actions } = mockUseTripStore()
      
      return (
        <FlightCard 
          flight={mockFlight}
          isSelected={selectedOptions.flight?.flight_id === mockFlight.flight_id}
          onSelect={(flightId) => actions.selectOption('flight', mockFlight)}
        />
      )
    }

    render(<TestComponent />)

    const card = screen.getByRole('button', { 
      name: /flight american airlines departing/i 
    })
    
    await user.click(card)
    
    expect(mockUseTripStore().actions.selectOption).toHaveBeenCalledWith('flight', mockFlight)
  })
})
```

### Testing Best Practices

1. **Unit Tests**: Test individual components in isolation with mocked dependencies and comprehensive prop variations
2. **Integration Tests**: Test component interactions with state management, API clients, and routing
3. **E2E Tests**: Test critical user flows including trip planning, selection, and export workflows
4. **Coverage Goals**: Maintain 85%+ code coverage with focus on business logic and user interactions
5. **Test Structure**: Follow Arrange-Act-Assert pattern with descriptive test names and grouped scenarios
6. **Mock External Dependencies**: Mock API calls, geolocation, file downloads, and third-party libraries
7. **Accessibility Testing**: Include screen reader testing, keyboard navigation, and color contrast validation
8. **Performance Testing**: Test component rendering performance, memory leaks, and bundle size impact
9. **Visual Regression**: Use Playwright for screenshot comparison testing of complex travel components
10. **Real User Testing**: Complement automated tests with user testing sessions for travel planning workflows

## Environment Configuration

```bash
# .env.local - Development environment variables
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN=pk.your_mapbox_token
NEXT_PUBLIC_SENTRY_DSN=your_sentry_dsn
NEXT_PUBLIC_GA_TRACKING_ID=your_ga_id

# Environment flags
NEXT_PUBLIC_ENVIRONMENT=development
NEXT_PUBLIC_DEBUG_MODE=true
NEXT_PUBLIC_MOCK_API=false

# Feature flags
NEXT_PUBLIC_ENABLE_PDF_EXPORT=true
NEXT_PUBLIC_ENABLE_WEBSOCKETS=true
NEXT_PUBLIC_ENABLE_MAPS=true
NEXT_PUBLIC_ENABLE_ANALYTICS=false

# API Configuration
API_TIMEOUT=30000
MAX_RETRY_ATTEMPTS=3
CACHE_TTL=300000

# .env.production - Production environment variables
NEXT_PUBLIC_API_BASE_URL=https://api.travelcompanion.com/api/v1
NEXT_PUBLIC_WS_URL=wss://api.travelcompanion.com/ws
NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN=pk.your_production_mapbox_token
NEXT_PUBLIC_SENTRY_DSN=your_production_sentry_dsn
NEXT_PUBLIC_GA_TRACKING_ID=your_production_ga_id

# Production flags
NEXT_PUBLIC_ENVIRONMENT=production
NEXT_PUBLIC_DEBUG_MODE=false
NEXT_PUBLIC_MOCK_API=false

# All feature flags enabled in production
NEXT_PUBLIC_ENABLE_PDF_EXPORT=true
NEXT_PUBLIC_ENABLE_WEBSOCKETS=true
NEXT_PUBLIC_ENABLE_MAPS=true
NEXT_PUBLIC_ENABLE_ANALYTICS=true

# Optimized production settings
API_TIMEOUT=15000
MAX_RETRY_ATTEMPTS=2
CACHE_TTL=600000
```

## Frontend Developer Standards

### Critical Coding Rules

**Performance & Bundle Size:**
- Never import entire libraries - use tree-shaking and dynamic imports: `const Map = dynamic(() => import('@/components/maps/InteractiveMap'), { ssr: false })`
- Lazy load heavy components (maps, PDF generator) and non-critical features
- Use React.memo() for expensive re-renders in travel list components
- Implement proper loading states for all async operations

**Type Safety:**
- All props must have TypeScript interfaces - no `any` types allowed
- API responses must match backend TypeScript types exactly
- Use discriminated unions for component variants: `type CardVariant = 'flight' | 'hotel' | 'activity'`

**State Management:**
- Never mutate state directly - use Zustand actions for all state changes
- Keep component state minimal - lift shared state to Zustand stores
- Use proper dependency arrays in useEffect - avoid infinite re-renders

**API Integration:**
- All API calls must include error handling and loading states
- Use proper TypeScript types for API responses - never `any`
- Implement request cancellation for component unmounting: `useEffect(() => { const controller = new AbortController(); return () => controller.abort(); }, [])`

**Accessibility:**
- All interactive elements must be keyboard accessible with proper `tabIndex`
- Images require descriptive `alt` text, especially for travel photos and maps
- Form inputs must have associated labels: `<label htmlFor="destination">Destination</label>`
- Use proper ARIA labels for complex components: `aria-label`, `aria-describedby`

**Mobile & Responsive:**
- Test all components at 320px width minimum (iPhone SE)
- Use touch-friendly targets (44px minimum) for mobile interactions
- Implement proper swipe gestures for mobile card carousels
- Never rely on hover states for critical functionality

### Quick Reference

**Development Commands:**
```bash
# Start development server
npm run dev

# Run tests with watch mode
npm run test

# Run E2E tests
npm run test:e2e

# Build production bundle
npm run build

# Start production server
npm start

# Lint and format code
npm run lint
npm run format

# Analyze bundle size
npm run analyze
```

**Common Import Patterns:**
```typescript
// UI Components
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

// Travel Components
import { FlightCard } from '@/components/travel/FlightCard'
import { TripDashboard } from '@/components/travel/TripDashboard'

// Hooks and Utilities
import { useTripStore } from '@/lib/store/trip'
import { useAuth } from '@/lib/hooks/useAuth'
import { apiClient } from '@/lib/api/client'

// Types
import type { FlightOption, TripRequest } from '@/lib/types/travel'
import type { User } from '@/lib/types/user'
```

**File Naming Conventions:**
- Components: `PascalCase.tsx` (e.g., `FlightCard.tsx`)
- Hooks: `camelCase.ts` with "use" prefix (e.g., `useAuth.ts`)
- Utilities: `camelCase.ts` (e.g., `apiClient.ts`)
- Types: `camelCase.ts` (e.g., `travel.ts`)
- Pages: `page.tsx` (Next.js App Router)
- Layouts: `layout.tsx` (Next.js App Router)

**Project-Specific Patterns:**
```typescript
// Travel data formatting
import { formatPrice, formatDuration, formatDate } from '@/lib/utils/formatting'

// Error handling pattern
try {
  const result = await apiClient.createTripPlan(request)
  // Handle success
} catch (error) {
  if (error instanceof ApiError) {
    // Handle API errors
  } else {
    // Handle unexpected errors
  }
}

// State selection pattern
const { selectedFlight, actions } = useTripStore((state) => ({
  selectedFlight: state.selectedOptions.flight,
  actions: state.actions
}))

// Component prop validation
interface FlightCardProps {
  flight: FlightOption           // Required
  isSelected?: boolean          // Optional with default
  onSelect?: (id: string) => void // Optional callback
  className?: string            // Optional styling
}
```
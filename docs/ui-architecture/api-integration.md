# API Integration

## Service Template

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

## API Client Configuration

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

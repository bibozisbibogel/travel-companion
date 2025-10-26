/**
 * API client configuration for Travel Companion
 * Enhanced with timeout, retry logic, and comprehensive error handling
 */

import type { ILoginRequest, IRegisterRequest, IAuthResponse, ITripRequest, ITripPlanResponse, IDestination, IApiRequestConfig, IRetryConfig, IPaginatedResponse, ITripSummary, ITripDetailResponse } from './types'
import { getAuthToken, setAuthToken } from './auth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const DEFAULT_TIMEOUT = 30000; // 30 seconds
const DEFAULT_RETRY_ATTEMPTS = 3;
const DEFAULT_RETRY_DELAY = 1000; // 1 second

export class ApiClient {
  private baseUrl: string;
  private token: string | null = null;
  private timeout: number;
  private retryConfig: IRetryConfig;

  constructor(
    baseUrl: string = API_BASE_URL,
    timeout: number = DEFAULT_TIMEOUT,
    retryConfig: IRetryConfig = {
      attempts: DEFAULT_RETRY_ATTEMPTS,
      delay: DEFAULT_RETRY_DELAY,
      retryOn: [408, 429, 500, 502, 503, 504]
    }
  ) {
    this.baseUrl = baseUrl;
    this.timeout = timeout;
    this.retryConfig = retryConfig;

    // Initialize token from cookie if available
    if (typeof window !== 'undefined') {
      this.token = getAuthToken();
    }
  }

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== 'undefined') {
      setAuthToken(token);
    }
  }

  getHeaders(additionalHeaders?: HeadersInit): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    // Merge additional headers if provided
    if (additionalHeaders) {
      if (Array.isArray(additionalHeaders)) {
        // Convert array format to object
        additionalHeaders.forEach(([key, value]) => {
          headers[key] = value;
        });
      } else {
        Object.assign(headers, additionalHeaders);
      }
    }
    
    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }
    
    return headers;
  }

  private async sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private shouldRetry(status: number, attempt: number): boolean {
    return (
      attempt < this.retryConfig.attempts &&
      this.retryConfig.retryOn.includes(status)
    );
  }

  private createTimeoutController(timeout: number): { controller: AbortController; cleanup: () => void } {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const cleanup = () => {
      clearTimeout(timeoutId);
    };

    return { controller, cleanup };
  }

  private async makeRequest<T>(
    endpoint: string, 
    config: IApiRequestConfig = {}
  ): Promise<T> {
    const {
      method = 'GET',
      data,
      headers: additionalHeaders,
      timeout = this.timeout,
      retryConfig = this.retryConfig
    } = config;

    let lastError: Error;
    
    for (let attempt = 0; attempt < retryConfig.attempts; attempt++) {
      let cleanup: (() => void) | undefined;
      try {
        const timeoutController = this.createTimeoutController(timeout);
        cleanup = timeoutController.cleanup;

        const fetchConfig: RequestInit = {
          method,
          headers: this.getHeaders(additionalHeaders),
          signal: timeoutController.controller.signal,
        };

        if (data && method !== 'GET') {
          fetchConfig.body = JSON.stringify(data);
        }

        // Debug logging
        if (endpoint.includes('login')) {
          console.log('[API] Request details:', {
            url: `${this.baseUrl}${endpoint}`,
            method,
            headers: fetchConfig.headers,
            hasBody: !!fetchConfig.body
          });
        }

        const response = await fetch(`${this.baseUrl}${endpoint}`, fetchConfig);

        // Clean up timeout on successful fetch
        cleanup();
        cleanup = undefined;

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const error = new ApiError(
            response.status,
            errorData.message || `API request failed: ${response.status}`,
            errorData
          );

          if (this.shouldRetry(response.status, attempt)) {
            lastError = error;
            await this.sleep(retryConfig.delay * Math.pow(2, attempt)); // Exponential backoff
            continue;
          }

          throw error;
        }

        return response.json();
      } catch (error) {
        // Clean up timeout on error
        if (cleanup) {
          cleanup();
        }

        if (error instanceof ApiError) {
          throw error;
        }

        // Handle timeout and network errors
        const networkError = new ApiError(
          0,
          error instanceof Error ? error.message : 'Network error occurred',
          { originalError: error }
        );

        if (attempt < retryConfig.attempts - 1) {
          lastError = networkError;
          await this.sleep(retryConfig.delay * Math.pow(2, attempt));
          continue;
        }

        throw networkError;
      }
    }

    throw lastError!;
  }

  async get<T>(endpoint: string, config?: Omit<IApiRequestConfig, 'method' | 'data'>): Promise<T> {
    return this.makeRequest<T>(endpoint, { ...config, method: 'GET' });
  }

  async post<T>(endpoint: string, data: unknown, config?: Omit<IApiRequestConfig, 'method' | 'data'>): Promise<T> {
    return this.makeRequest<T>(endpoint, { ...config, method: 'POST', data });
  }

  async put<T>(endpoint: string, data: unknown, config?: Omit<IApiRequestConfig, 'method' | 'data'>): Promise<T> {
    return this.makeRequest<T>(endpoint, { ...config, method: 'PUT', data });
  }

  async delete<T>(endpoint: string, config?: Omit<IApiRequestConfig, 'method' | 'data'>): Promise<T> {
    return this.makeRequest<T>(endpoint, { ...config, method: 'DELETE' });
  }

  // Authentication methods
  async login(credentials: ILoginRequest): Promise<IAuthResponse> {
    // Temporarily clear token for login request
    const existingToken = this.token;
    this.token = null;

    try {
      console.log('[API] Login request:', { email: credentials.email, hasPassword: !!credentials.password });
      const response = await this.post<IAuthResponse>('/api/v1/users/login', credentials);
      console.log('[API] Login success:', { hasToken: !!response.access_token });
      return response;
    } catch (error) {
      console.error('[API] Login failed:', error);
      throw error;
    } finally {
      // Restore token if login fails
      this.token = existingToken;
    }
  }

  async register(userData: IRegisterRequest): Promise<IAuthResponse> {
    // Temporarily clear token for registration request
    const existingToken = this.token;
    this.token = null;

    try {
      const { confirmPassword, firstName, lastName, ...restData } = userData;

      const registrationData = {
        ...restData,
        first_name: firstName,
        // Send null instead of empty string if no last name provided
        last_name: lastName || null
      };

      return await this.post<IAuthResponse>('/api/v1/users/register', registrationData);
    } finally {
      // Restore token if registration fails
      this.token = existingToken;
    }
  }

  async logout(): Promise<void> {
    this.setToken(null);
  }

  // User profile methods
  async getCurrentUser(): Promise<any> {
    return this.get<any>('/api/v1/users/me');
  }

  // Travel planning methods
  async planTrip(tripRequest: ITripRequest): Promise<ITripPlanResponse> {
    // Trip planning can take longer, so use extended timeout and no retries
    return this.post<ITripPlanResponse>('/api/v1/trips/plan', tripRequest, {
      timeout: 180000, // 3 minutes (backend takes 2-2.5 minutes)
      retryConfig: {
        attempts: 1, // No retries for trip planning
        delay: 0,
        retryOn: []
      }
    });
  }

  async searchDestinations(query: string): Promise<IDestination[]> {
    return this.get<IDestination[]>(`/api/v1/destinations/search?q=${encodeURIComponent(query)}`);
  }

  async getPopularDestinations(): Promise<IDestination[]> {
    return this.get<IDestination[]>('/api/v1/destinations/popular');
  }

  // Itinerary methods
  async getItinerary(tripId: string): Promise<any> {
    return this.get<any>(`/api/v1/trips/${tripId}/itinerary`);
  }

  // Trip list methods (Story 3.5)
  async getUserTrips(page: number = 1, perPage: number = 20): Promise<IPaginatedResponse<ITripSummary[]>> {
    return this.get<IPaginatedResponse<ITripSummary[]>>(
      `/api/v1/trips?page=${page}&per_page=${perPage}`
    );
  }

  // Trip detail method
  async getTripById(tripId: string): Promise<ITripDetailResponse> {
    return this.get<ITripDetailResponse>(`/api/v1/trips/${tripId}`);
  }
}

// Custom API Error class for better error handling
export class ApiError extends Error {
  public readonly timestamp: Date;
  public readonly isRetryable: boolean;

  constructor(
    public status: number,
    message: string,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiError';
    this.timestamp = new Date();
    this.isRetryable = [408, 429, 500, 502, 503, 504].includes(status);
  }

  override toString(): string {
    return `${this.name} [${this.status}]: ${this.message} (${this.timestamp.toISOString()})`;
  }

  toJSON() {
    return {
      name: this.name,
      status: this.status,
      message: this.message,
      data: this.data,
      timestamp: this.timestamp.toISOString(),
      isRetryable: this.isRetryable,
    };
  }
}

export const apiClient = new ApiClient();
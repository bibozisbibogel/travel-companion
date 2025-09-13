import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ApiClient, ApiError } from '../../lib/api'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

// Mock AbortController for timeout tests
class MockAbortController {
  public signal: AbortSignal
  private controller: AbortController

  constructor() {
    this.controller = new AbortController()
    this.signal = this.controller.signal
  }

  abort() {
    this.controller.abort()
  }
}

if (!global.AbortController) {
  global.AbortController = MockAbortController as any
}

describe('ApiClient', () => {
  let apiClient: ApiClient
  
  beforeEach(() => {
    mockFetch.mockClear()
    localStorageMock.getItem.mockClear()
    localStorageMock.setItem.mockClear()
    localStorageMock.removeItem.mockClear()
    apiClient = new ApiClient('http://localhost:8000', 5000, {
      attempts: 2,
      delay: 100,
      retryOn: [500, 502, 503, 504]
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Token Management', () => {
    it('should initialize token from localStorage', () => {
      localStorageMock.getItem.mockReturnValue('existing-token')
      new ApiClient()
      expect(localStorageMock.getItem).toHaveBeenCalledWith('auth_token')
    })

    it('should set token in localStorage', () => {
      const token = 'new-token'
      apiClient.setToken(token)
      expect(localStorageMock.setItem).toHaveBeenCalledWith('auth_token', token)
    })

    it('should remove token from localStorage when set to null', () => {
      apiClient.setToken(null)
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('auth_token')
    })

    it('should include Authorization header when token is set', () => {
      apiClient.setToken('test-token')
      const headers = apiClient.getHeaders()
      expect(headers).toEqual({
        'Content-Type': 'application/json',
        Authorization: 'Bearer test-token',
      })
    })

    it('should not include Authorization header when no token', () => {
      const headers = apiClient.getHeaders()
      expect(headers).toEqual({
        'Content-Type': 'application/json',
      })
    })

    it('should merge additional headers correctly', () => {
      const additionalHeaders = { 'X-Custom-Header': 'custom-value' }
      const headers = apiClient.getHeaders(additionalHeaders)
      expect(headers).toEqual({
        'Content-Type': 'application/json',
        'X-Custom-Header': 'custom-value',
      })
    })

    it('should handle array format headers', () => {
      const additionalHeaders: [string, string][] = [['X-Array-Header', 'array-value']]
      const headers = apiClient.getHeaders(additionalHeaders)
      expect(headers).toEqual({
        'Content-Type': 'application/json',
        'X-Array-Header': 'array-value',
      })
    })
  })

  describe('HTTP Methods', () => {
    it('should make successful GET request', async () => {
      const mockData = { id: 1, name: 'Test' }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      })

      const result = await apiClient.get('/test')
      
      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/test', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: expect.any(AbortSignal),
      })
      expect(result).toEqual(mockData)
    })

    it('should make successful POST request', async () => {
      const postData = { name: 'New Item' }
      const mockResponse = { id: 1, ...postData }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await apiClient.post('/items', postData)
      
      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/items', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(postData),
        signal: expect.any(AbortSignal),
      })
      expect(result).toEqual(mockResponse)
    })

    it('should throw ApiError for failed requests', async () => {
      const errorResponse = { message: 'Not found' }
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => errorResponse,
      })

      await expect(apiClient.get('/nonexistent')).rejects.toThrow(ApiError)
    })

    it('should handle network errors gracefully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => { throw new Error('JSON parse error') },
      })

      await expect(apiClient.get('/error')).rejects.toThrow(ApiError)
    })

    it('should retry failed requests with retryable status codes', async () => {
      const mockData = { id: 1, name: 'Success after retry' }
      
      // First call fails with 500
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ message: 'Internal server error' }),
      })
      
      // Second call succeeds
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      })

      const result = await apiClient.get('/test')
      
      expect(mockFetch).toHaveBeenCalledTimes(2)
      expect(result).toEqual(mockData)
    })

    it('should not retry non-retryable status codes', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ message: 'Bad request' }),
      })

      await expect(apiClient.get('/test')).rejects.toThrow(ApiError)
      expect(mockFetch).toHaveBeenCalledTimes(1)
    })

    it('should handle timeout errors', async () => {
      // Mock fetch to simulate AbortController timeout
      mockFetch.mockImplementation(() => {
        return new Promise((resolve, reject) => {
          setTimeout(() => {
            const error = new Error('The operation was aborted.')
            error.name = 'AbortError'
            reject(error)
          }, 10)
        })
      })

      const shortTimeoutClient = new ApiClient('http://localhost:8000', 5)
      
      await expect(shortTimeoutClient.get('/test')).rejects.toThrow()
    })

    it('should support PUT and DELETE methods', async () => {
      const putData = { id: 1, name: 'Updated' }
      const deleteResponse = { success: true }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => putData,
      })
      
      const putResult = await apiClient.put('/items/1', putData)
      expect(putResult).toEqual(putData)
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => deleteResponse,
      })
      
      const deleteResult = await apiClient.delete('/items/1')
      expect(deleteResult).toEqual(deleteResponse)
    })
  })

  describe('Authentication Methods', () => {
    it('should login successfully', async () => {
      const loginData = { email: 'test@example.com', password: 'password' }
      const mockResponse = { 
        success: true, 
        token: 'auth-token',
        user: { id: '1', email: 'test@example.com', name: 'Test User' }
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await apiClient.login(loginData)
      
      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/v1/users/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginData),
        signal: expect.any(AbortSignal),
      })
      expect(result).toEqual(mockResponse)
    })

    it('should register successfully', async () => {
      const registerData = { 
        firstName: 'Test',
        lastName: 'User',
        email: 'test@example.com', 
        password: 'Password123!',
        confirmPassword: 'Password123!'
      }
      const mockResponse = { 
        access_token: 'auth-token',
        token_type: 'bearer',
        expires_in: 3600,
        user: { id: '1', email: 'test@example.com', firstName: 'Test', lastName: 'User' }
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await apiClient.register(registerData)
      
      // Should exclude confirmPassword from the request and transform to API format
      const expectedData = { 
        first_name: 'Test',
        last_name: 'User',
        email: 'test@example.com', 
        password: 'Password123!'
      }
      
      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/v1/users/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: expect.stringContaining('"first_name":"Test"'),
        signal: expect.any(AbortSignal),
      })
      // Also verify the body contains all expected fields
      const callBody = JSON.parse((mockFetch as any).mock.calls[0][1].body)
      expect(callBody).toEqual(expectedData)
      expect(result).toEqual(mockResponse)
    })

    it('should logout and clear token', async () => {
      apiClient.setToken('some-token')
      await apiClient.logout()
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('auth_token')
    })

    it('should handle login errors', async () => {
      const loginData = { email: 'test@example.com', password: 'wrongpassword' }
      const errorResponse = { message: 'Invalid credentials' }
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => errorResponse,
      })

      await expect(apiClient.login(loginData)).rejects.toThrow(ApiError)
    })

    it('should handle registration errors', async () => {
      const registerData = { 
        firstName: 'Test',
        lastName: 'User',
        email: 'existing@example.com', 
        password: 'Password123!',
        confirmPassword: 'Password123!'
      }
      const errorResponse = { 
        message: 'Email already exists',
        errors: { email: ['Email is already taken'] }
      }
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => errorResponse,
      })

      await expect(apiClient.register(registerData)).rejects.toThrow(ApiError)
    })
  })

  describe('Travel Planning Methods', () => {
    it('should plan trip successfully', async () => {
      const tripRequest = {
        destination: 'Tokyo, Japan',
        startDate: '2024-12-01',
        endDate: '2024-12-07',
        budget: 3000,
        travelers: 2,
        preferences: ['culture', 'food']
      }
      const mockResponse = {
        success: true,
        data: {
          tripId: 'trip-123',
          destination: 'Tokyo, Japan',
          itinerary: { days: [] },
          estimatedCost: 2800
        }
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await apiClient.planTrip(tripRequest)
      
      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/v1/trips/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tripRequest),
        signal: expect.any(AbortSignal),
      })
      expect(result).toEqual(mockResponse)
    })

    it('should search destinations successfully', async () => {
      const mockDestinations = [
        { id: 'tokyo', name: 'Tokyo', country: 'Japan', type: 'city' },
        { id: 'kyoto', name: 'Kyoto', country: 'Japan', type: 'city' }
      ]
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockDestinations,
      })

      const result = await apiClient.searchDestinations('Japan')
      
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/destinations/search?q=Japan',
        {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
          signal: expect.any(AbortSignal),
        }
      )
      expect(result).toEqual(mockDestinations)
    })

    it('should get popular destinations successfully', async () => {
      const mockDestinations = [
        { id: 'paris', name: 'Paris', country: 'France', type: 'city' },
        { id: 'london', name: 'London', country: 'UK', type: 'city' }
      ]
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockDestinations,
      })

      const result = await apiClient.getPopularDestinations()
      
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/destinations/popular',
        {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
          signal: expect.any(AbortSignal),
        }
      )
      expect(result).toEqual(mockDestinations)
    })

    it('should handle trip planning errors', async () => {
      const tripRequest = {
        destination: 'Invalid',
        startDate: '2024-12-01',
        endDate: '2024-12-07',
        travelers: 2
      }
      const errorResponse = { message: 'Invalid destination' }
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => errorResponse,
      })

      await expect(apiClient.planTrip(tripRequest)).rejects.toThrow(ApiError)
    })
  })
})

describe('ApiError', () => {
  it('should create error with correct properties', () => {
    const error = new ApiError(404, 'Not found', { detail: 'Resource not found' })
    expect(error.name).toBe('ApiError')
    expect(error.status).toBe(404)
    expect(error.message).toBe('Not found')
    expect(error.data).toEqual({ detail: 'Resource not found' })
    expect(error.timestamp).toBeInstanceOf(Date)
    expect(error.isRetryable).toBe(false)
  })

  it('should be instanceof Error', () => {
    const error = new ApiError(500, 'Server error')
    expect(error instanceof Error).toBe(true)
  })

  it('should identify retryable errors correctly', () => {
    const retryableError = new ApiError(500, 'Server error')
    expect(retryableError.isRetryable).toBe(true)

    const nonRetryableError = new ApiError(404, 'Not found')
    expect(nonRetryableError.isRetryable).toBe(false)
  })

  it('should override toString method correctly', () => {
    const error = new ApiError(400, 'Bad request')
    const stringified = error.toString()
    expect(stringified).toContain('ApiError [400]: Bad request')
    expect(stringified).toMatch(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)
  })

  it('should serialize to JSON correctly', () => {
    const error = new ApiError(500, 'Server error', { code: 'INTERNAL_ERROR' })
    const json = error.toJSON()
    expect(json).toHaveProperty('name', 'ApiError')
    expect(json).toHaveProperty('status', 500)
    expect(json).toHaveProperty('message', 'Server error')
    expect(json).toHaveProperty('data', { code: 'INTERNAL_ERROR' })
    expect(json).toHaveProperty('timestamp')
    expect(json).toHaveProperty('isRetryable', true)
  })
})
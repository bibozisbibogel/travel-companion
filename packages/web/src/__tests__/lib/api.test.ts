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

describe('ApiClient', () => {
  let apiClient: ApiClient
  
  beforeEach(() => {
    mockFetch.mockClear()
    localStorageMock.getItem.mockClear()
    localStorageMock.setItem.mockClear()
    localStorageMock.removeItem.mockClear()
    apiClient = new ApiClient('http://localhost:8000')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Token Management', () => {
    it('should initialize token from localStorage', () => {
      localStorageMock.getItem.mockReturnValue('existing-token')
      const client = new ApiClient()
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
      const errorResponse = {}
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => { throw new Error('JSON parse error') },
      })

      await expect(apiClient.get('/error')).rejects.toThrow(ApiError)
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
      })
      expect(result).toEqual(mockResponse)
    })

    it('should register successfully', async () => {
      const registerData = { 
        name: 'Test User',
        email: 'test@example.com', 
        password: 'Password123!',
        confirmPassword: 'Password123!'
      }
      const mockResponse = { 
        success: true, 
        token: 'auth-token',
        user: { id: '1', email: 'test@example.com', name: 'Test User' }
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await apiClient.register(registerData)
      
      // Should exclude confirmPassword from the request
      const expectedData = { 
        name: 'Test User',
        email: 'test@example.com', 
        password: 'Password123!'
      }
      
      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/v1/users/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(expectedData),
      })
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
        name: 'Test User',
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
})

describe('ApiError', () => {
  it('should create error with correct properties', () => {
    const error = new ApiError(404, 'Not found', { detail: 'Resource not found' })
    expect(error.name).toBe('ApiError')
    expect(error.status).toBe(404)
    expect(error.message).toBe('Not found')
    expect(error.data).toEqual({ detail: 'Resource not found' })
  })

  it('should be instanceof Error', () => {
    const error = new ApiError(500, 'Server error')
    expect(error instanceof Error).toBe(true)
  })
})
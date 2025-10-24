import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, renderHook } from '@testing-library/react'
import { act } from 'react'
import { useRouter } from 'next/navigation'
import { AuthProvider, useAuth } from '../../contexts/AuthContext'
import { apiClient, ApiError } from '../../lib/api'
import type { LoginFormData, RegisterFormData } from '../../lib/validation'

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(),
}))

// Mock API client
vi.mock('../../lib/api', () => {
  class MockApiError extends Error {
    public readonly timestamp: Date
    public readonly isRetryable: boolean

    constructor(public status: number, message: string, public data?: any) {
      super(message)
      this.name = 'ApiError'
      this.timestamp = new Date()
      this.isRetryable = [408, 429, 500, 502, 503, 504].includes(status)
    }
  }

  return {
    apiClient: {
      login: vi.fn(),
      register: vi.fn(),
      getCurrentUser: vi.fn(),
      setToken: vi.fn(),
    },
    ApiError: MockApiError,
  }
})

const mockRouter = {
  push: vi.fn(),
  replace: vi.fn(),
  prefetch: vi.fn(),
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(useRouter as any).mockReturnValue(mockRouter)
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  describe('Initial State', () => {
    it('should initialize with null user when no token exists', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

      // Wait for loading to complete
      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
      expect(result.current.error).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
    })

    it('should throw error when useAuth is used outside AuthProvider', () => {
      // Suppress console.error for this test
      const originalError = console.error
      console.error = vi.fn()

      expect(() => {
        renderHook(() => useAuth())
      }).toThrow('useAuth must be used within an AuthProvider')

      console.error = originalError
    })
  })

  describe('Session Restoration', () => {
    it('should restore session from localStorage on mount', async () => {
      const mockUser = {
        id: 'user-123',
        email: 'test@example.com',
        firstName: 'Test',
        lastName: 'User'
      }

      localStorage.setItem('auth_token', 'test-token')
      ;(apiClient.getCurrentUser as any).mockResolvedValue(mockUser)

      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(apiClient.setToken).toHaveBeenCalledWith('test-token')
      expect(apiClient.getCurrentUser).toHaveBeenCalled()
      expect(result.current.user).toEqual({
        id: mockUser.id,
        email: mockUser.email,
        name: 'Test User',
        firstName: mockUser.firstName,
        lastName: mockUser.lastName,
      })
      expect(result.current.isAuthenticated).toBe(true)
    })

    it('should handle invalid token on session restoration', async () => {
      localStorage.setItem('auth_token', 'invalid-token')
      const mockError = new (ApiError as any)(401, 'Unauthorized')
      ;(apiClient.getCurrentUser as any).mockRejectedValue(mockError)

      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
      expect(localStorage.getItem('auth_token')).toBeNull()
    })

    it('should not restore session when no token exists', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(apiClient.getCurrentUser).not.toHaveBeenCalled()
      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
    })
  })

  describe('Login', () => {
    it('should successfully login user', async () => {
      const mockResponse = {
        access_token: 'test-token',
        token_type: 'bearer',
        expires_in: 3600,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          firstName: 'Test',
          lastName: 'User'
        }
      }
      ;(apiClient.login as any).mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      const loginData: LoginFormData = {
        email: 'test@example.com',
        password: 'Password123!'
      }

      await act(async () => {
        await result.current.login(loginData)
      })

      expect(apiClient.login).toHaveBeenCalledWith(loginData)
      expect(apiClient.setToken).toHaveBeenCalledWith('test-token')
      expect(result.current.user).toEqual({
        id: mockResponse.user.id,
        email: mockResponse.user.email,
        name: 'Test User',
        firstName: mockResponse.user.firstName,
        lastName: mockResponse.user.lastName,
      })
      expect(result.current.isAuthenticated).toBe(true)
      expect(mockRouter.push).toHaveBeenCalledWith('/')
    })

    it.skip('should handle login with 401 error', async () => {
      const mockError = new (ApiError as any)(401, 'Invalid credentials')
      ;(apiClient.login as any).mockRejectedValue(mockError)

      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      const loginData: LoginFormData = {
        email: 'test@example.com',
        password: 'wrongpassword'
      }

      try {
        await act(async () => {
          await result.current.login(loginData)
        })
      } catch (error) {
        // Error is expected
      }

      // Wait for error state to be set
      await waitFor(() => {
        expect(result.current.error).toBe('Invalid email or password')
      }, { timeout: 3000 })

      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
    })

    it.skip('should handle network error during login', async () => {
      const mockError = new Error('Network error')
      ;(apiClient.login as any).mockRejectedValue(mockError)

      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      const loginData: LoginFormData = {
        email: 'test@example.com',
        password: 'Password123!'
      }

      try {
        await act(async () => {
          await result.current.login(loginData)
        })
      } catch (error) {
        // Error is expected
      }

      // Wait for error state to be set
      await waitFor(() => {
        expect(result.current.error).toBe('Network error')
      }, { timeout: 3000 })
    })
  })

  describe('Register', () => {
    it('should successfully register user', async () => {
      const mockResponse = {
        access_token: 'test-token',
        token_type: 'bearer',
        expires_in: 3600,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          firstName: 'Test',
          lastName: 'User'
        }
      }
      ;(apiClient.register as any).mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      const registerData: RegisterFormData = {
        email: 'test@example.com',
        password: 'Password123!',
        confirmPassword: 'Password123!',
        firstName: 'Test',
        lastName: 'User'
      }

      await act(async () => {
        await result.current.register(registerData)
      })

      expect(apiClient.register).toHaveBeenCalledWith(registerData)
      expect(apiClient.setToken).toHaveBeenCalledWith('test-token')
      expect(result.current.user).toEqual({
        id: mockResponse.user.id,
        email: mockResponse.user.email,
        name: 'Test User',
        firstName: mockResponse.user.firstName,
        lastName: mockResponse.user.lastName,
      })
      expect(result.current.isAuthenticated).toBe(true)
      expect(mockRouter.push).toHaveBeenCalledWith('/')
    })

    it.skip('should handle registration API error', async () => {
      const mockError = new (ApiError as any)(409, 'Email already exists')
      ;(apiClient.register as any).mockRejectedValue(mockError)

      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      const registerData: RegisterFormData = {
        email: 'existing@example.com',
        password: 'Password123!',
        confirmPassword: 'Password123!',
        firstName: 'Test',
        lastName: 'User'
      }

      try {
        await act(async () => {
          await result.current.register(registerData)
        })
      } catch (error) {
        // Error is expected
      }

      // Wait for error state to be set
      await waitFor(() => {
        expect(result.current.error).toBe('Email already exists')
      }, { timeout: 3000 })

      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
    })
  })

  describe('Logout', () => {
    it('should clear user state and token on logout', async () => {
      const mockResponse = {
        access_token: 'test-token',
        token_type: 'bearer',
        expires_in: 3600,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          firstName: 'Test',
          lastName: 'User'
        }
      }
      ;(apiClient.login as any).mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Login first
      const loginData: LoginFormData = {
        email: 'test@example.com',
        password: 'Password123!'
      }

      await act(async () => {
        await result.current.login(loginData)
      })

      expect(result.current.isAuthenticated).toBe(true)

      // Now logout
      act(() => {
        result.current.logout()
      })

      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
      expect(apiClient.setToken).toHaveBeenCalledWith(null)
      expect(localStorage.getItem('auth_token')).toBeNull()
      expect(mockRouter.push).toHaveBeenCalledWith('/auth/login')
    })

    it('should clear draft data on logout', () => {
      localStorage.setItem('trip-preferences-draft', JSON.stringify({ destination: 'Paris' }))
      localStorage.setItem('trip-preferences-draft-timestamp', new Date().toISOString())

      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

      act(() => {
        result.current.logout()
      })

      expect(localStorage.getItem('trip-preferences-draft')).toBeNull()
      expect(localStorage.getItem('trip-preferences-draft-timestamp')).toBeNull()
    })
  })

  describe('Refresh User', () => {
    it('should refresh user data', async () => {
      const initialUser = {
        id: 'user-123',
        email: 'test@example.com',
        firstName: 'Test',
        lastName: 'User'
      }

      const updatedUser = {
        id: 'user-123',
        email: 'test@example.com',
        firstName: 'Updated',
        lastName: 'Name'
      }

      localStorage.setItem('auth_token', 'test-token')
      ;(apiClient.getCurrentUser as any)
        .mockResolvedValueOnce(initialUser)
        .mockResolvedValueOnce(updatedUser)

      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user?.firstName).toBe('Test')

      // Refresh user
      await act(async () => {
        await result.current.refreshUser()
      })

      expect(result.current.user?.firstName).toBe('Updated')
      expect(result.current.user?.name).toBe('Updated Name')
    })
  })

  describe('Error Handling', () => {
    it.skip('should clear error state with clearError', async () => {
      const mockError = new (ApiError as any)(401, 'Invalid credentials')
      ;(apiClient.login as any).mockRejectedValue(mockError)

      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      const loginData: LoginFormData = {
        email: 'test@example.com',
        password: 'wrongpassword'
      }

      try {
        await act(async () => {
          await result.current.login(loginData)
        })
      } catch (error) {
        // Error is expected
      }

      // Wait for error state to be set
      await waitFor(() => {
        expect(result.current.error).toBeTruthy()
      }, { timeout: 3000 })

      act(() => {
        result.current.clearError()
      })

      expect(result.current.error).toBeNull()
    })
  })

  describe('Context Integration', () => {
    it('should provide auth state to child components', async () => {
      const mockUser = {
        id: 'user-123',
        email: 'test@example.com',
        firstName: 'Test',
        lastName: 'User'
      }

      localStorage.setItem('auth_token', 'test-token')
      ;(apiClient.getCurrentUser as any).mockResolvedValue(mockUser)

      function TestComponent() {
        const { user, isAuthenticated, loading } = useAuth()

        if (loading) return <div>Loading...</div>
        if (!isAuthenticated) return <div>Not authenticated</div>

        return <div>Welcome, {user?.firstName}!</div>
      }

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      expect(screen.getByText('Loading...')).toBeInTheDocument()

      await waitFor(() => {
        expect(screen.getByText('Welcome, Test!')).toBeInTheDocument()
      })
    })
  })
})

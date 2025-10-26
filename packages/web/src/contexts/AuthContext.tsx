'use client'

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient, ApiError } from '../lib/api'
import type { LoginFormData, RegisterFormData } from '../lib/validation'

interface User {
  id: string
  email: string
  name?: string
  firstName?: string
  lastName?: string
}

interface AuthContextType {
  user: User | null
  loading: boolean
  error: string | null
  login: (credentials: LoginFormData) => Promise<void>
  register: (data: RegisterFormData) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
  isAuthenticated: boolean
  clearError: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  /**
   * Fetch current user profile from API
   */
  const fetchCurrentUser = useCallback(async () => {
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null

      if (!token) {
        setUser(null)
        setLoading(false)
        return
      }

      // Set token in apiClient
      apiClient.setToken(token)

      // Fetch user profile
      const userData = await apiClient.getCurrentUser()

      setUser({
        id: userData.id || userData.user_id,
        email: userData.email,
        name: userData.name || `${userData.firstName || ''} ${userData.lastName || ''}`.trim(),
        firstName: userData.firstName,
        lastName: userData.lastName,
      })
      setError(null)
    } catch (err) {
      console.error('Failed to fetch current user:', err)
      // If token is invalid, clear it
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        localStorage.removeItem('auth_token')
        apiClient.setToken(null)
        setUser(null)
      }
      setError('Failed to restore session')
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Initialize auth state on mount
   */
  useEffect(() => {
    fetchCurrentUser()
  }, [fetchCurrentUser])

  /**
   * Login user with credentials
   */
  const login = useCallback(async (credentials: LoginFormData) => {
    try {
      setLoading(true)
      setError(null)

      const response = await apiClient.login(credentials)

      if (response.access_token) {
        // Store token
        apiClient.setToken(response.access_token)

        // Set user data
        if (response.user) {
          setUser({
            id: response.user.id || response.user.user_id,
            email: response.user.email,
            name: response.user.name || `${response.user.firstName || ''} ${response.user.lastName || ''}`.trim(),
            firstName: response.user.firstName,
            lastName: response.user.lastName,
          })
        } else {
          // Fetch user profile if not included in login response
          await fetchCurrentUser()
        }

        // Redirect to trips page
        router.push('/trips')
      } else {
        throw new Error(response.detail?.message || 'Login failed')
      }
    } catch (err) {
      console.error('Login error:', err)
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setError('Invalid email or password')
        } else {
          setError(err.message || 'Login failed. Please try again.')
        }
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('An unexpected error occurred')
      }
      throw err
    } finally {
      setLoading(false)
    }
  }, [router, fetchCurrentUser])

  /**
   * Register new user
   */
  const register = useCallback(async (data: RegisterFormData) => {
    try {
      setLoading(true)
      setError(null)

      const response = await apiClient.register(data)

      if (response.access_token) {
        // Store token
        apiClient.setToken(response.access_token)

        // Set user data
        if (response.user) {
          setUser({
            id: response.user.id || response.user.user_id,
            email: response.user.email,
            name: response.user.name || `${response.user.firstName || ''} ${response.user.lastName || ''}`.trim(),
            firstName: response.user.firstName,
            lastName: response.user.lastName,
          })
        } else {
          await fetchCurrentUser()
        }

        // Redirect to home
        router.push('/')
      } else {
        throw new Error(response.detail?.message || 'Registration failed')
      }
    } catch (err) {
      console.error('Registration error:', err)
      if (err instanceof ApiError) {
        setError(err.message || 'Registration failed. Please try again.')
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('An unexpected error occurred')
      }
      throw err
    } finally {
      setLoading(false)
    }
  }, [router, fetchCurrentUser])

  /**
   * Logout user and clear session
   */
  const logout = useCallback(() => {
    // Clear user state
    setUser(null)
    setError(null)

    // Clear token from storage and apiClient
    localStorage.removeItem('auth_token')
    apiClient.setToken(null)

    // Clear any draft data
    localStorage.removeItem('trip-preferences-draft')
    localStorage.removeItem('trip-preferences-draft-timestamp')

    // Redirect to login
    router.push('/auth/login')
  }, [router])

  /**
   * Refresh user data
   */
  const refreshUser = useCallback(async () => {
    await fetchCurrentUser()
  }, [fetchCurrentUser])

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const value: AuthContextType = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    refreshUser,
    isAuthenticated: !!user,
    clearError,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/**
 * Hook to use auth context
 */
export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

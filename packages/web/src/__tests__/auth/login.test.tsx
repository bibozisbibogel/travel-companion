import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { act } from 'react'
import { useRouter } from 'next/navigation'
import LoginPage from '../../app/auth/login/page'
import { apiClient, ApiError } from '../../lib/api'

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(),
}))

// Mock API client with proper ApiError implementation
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
      setToken: vi.fn(),
    },
    ApiError: MockApiError,
  }
})

// Mock AuthContext
const mockLogin = vi.fn()
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    loading: false,
    error: null,
    login: mockLogin,
    register: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
    isAuthenticated: false,
    clearError: vi.fn(),
  }),
}))

// Mock CenteredLayout
vi.mock('../../components/layouts', () => ({
  CenteredLayout: ({ children, title, subtitle }: any) => (
    <div data-testid="centered-layout">
      <h1>{title}</h1>
      <p>{subtitle}</p>
      {children}
    </div>
  ),
}))

const mockRouter = {
  push: vi.fn(),
  replace: vi.fn(),
  prefetch: vi.fn(),
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(useRouter as any).mockReturnValue(mockRouter)

    // Wire mockLogin to call apiClient.login, setToken, and router.push like real AuthContext
    mockLogin.mockImplementation(async (credentials) => {
      const response = await apiClient.login(credentials)
      if (response.access_token) {
        apiClient.setToken(response.access_token)
        // Real AuthContext redirects to /trips after login, not /
        mockRouter.push('/trips')
      }
    })
  })

  it('should render login form with all fields', () => {
    render(<LoginPage />)
    
    expect(screen.getByText('Welcome back')).toBeInTheDocument()
    expect(screen.getByText('Sign in to your Travel Companion account')).toBeInTheDocument()
    expect(screen.getByLabelText('Email address')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('should display validation errors for empty fields', async () => {
    render(<LoginPage />)
    
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText('Email is required')).toBeInTheDocument()
      expect(screen.getByText('Password is required')).toBeInTheDocument()
    })
  })

  it('should validate email format and prevent API calls with invalid email', async () => {
    render(<LoginPage />)
    
    const emailInput = screen.getByLabelText('Email address')
    const passwordInput = screen.getByLabelText('Password')
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    // Submit with invalid email format
    fireEvent.change(emailInput, { target: { value: 'invalid-email' } })
    fireEvent.change(passwordInput, { target: { value: 'ValidPassword123!' } })
    fireEvent.click(submitButton)
    
    // Wait and verify API was not called (form validation should prevent submission)
    await new Promise(resolve => setTimeout(resolve, 100))
    expect(apiClient.login).not.toHaveBeenCalled()
    
    // Now test with valid email to confirm form works when validation passes
    fireEvent.change(emailInput, { target: { value: 'valid@example.com' } })
    fireEvent.click(submitButton)
    
    // API should be called with valid data
    await waitFor(() => {
      expect(apiClient.login).toHaveBeenCalledWith({
        email: 'valid@example.com',
        password: 'ValidPassword123!'
      })
    })
  })

  it('should validate password length and prevent API calls with short password', async () => {
    render(<LoginPage />)
    
    const emailInput = screen.getByLabelText('Email address')
    const passwordInput = screen.getByLabelText('Password')
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    // Submit with short password
    await act(async () => {
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'short' } })
      fireEvent.click(submitButton)
    })
    
    // Verify API was not called (validation should prevent submission)
    await waitFor(() => {
      expect(apiClient.login).not.toHaveBeenCalled()
    })
    
    // Test with valid password to confirm form works
    await act(async () => {
      fireEvent.change(passwordInput, { target: { value: 'ValidPassword123!' } })
      fireEvent.click(submitButton)
    })
    
    // API should be called with valid data
    await waitFor(() => {
      expect(apiClient.login).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'ValidPassword123!'
      })
    })
  })

  it('should handle successful login', async () => {
    const mockResponse = {
      access_token: 'test-token',
      token_type: 'bearer',
      expires_in: 3600,
      user: { id: '1', email: 'test@example.com', firstName: 'Test', lastName: 'User' }
    }
    ;(apiClient.login as any).mockResolvedValue(mockResponse)
    
    render(<LoginPage />)
    
    const emailInput = screen.getByLabelText('Email address')
    const passwordInput = screen.getByLabelText('Password')
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'Password123!' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(apiClient.login).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'Password123!'
      })
      expect(apiClient.setToken).toHaveBeenCalledWith('test-token')
      expect(mockRouter.push).toHaveBeenCalledWith('/trips')
    })
  })

  it('should handle login failure with 401 error', async () => {
    const mockError = new (ApiError as any)(401, 'Unauthorized')
    ;(apiClient.login as any).mockRejectedValue(mockError)
    
    render(<LoginPage />)
    
    const emailInput = screen.getByLabelText('Email address')
    const passwordInput = screen.getByLabelText('Password')
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'wrongpassword' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText('Invalid email or password. Please check your credentials and try again.')).toBeInTheDocument()
    })
  })

  it('should handle validation errors from API', async () => {
    const mockError = new (ApiError as any)(422, 'Validation failed', {
      errors: {
        email: ['Email format is invalid'],
        password: ['Password is too weak']
      }
    })
    ;(apiClient.login as any).mockRejectedValue(mockError)
    
    render(<LoginPage />)
    
    const emailInput = screen.getByLabelText('Email address')
    const passwordInput = screen.getByLabelText('Password')
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'Password123!' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText('Email format is invalid')).toBeInTheDocument()
      expect(screen.getByText('Password is too weak')).toBeInTheDocument()
    })
  })

  it('should show loading state during submission', async () => {
    let resolvePromise: (value: any) => void
    const mockPromise = new Promise(resolve => {
      resolvePromise = resolve
    })
    ;(apiClient.login as any).mockReturnValue(mockPromise)
    
    render(<LoginPage />)
    
    const emailInput = screen.getByLabelText('Email address')
    const passwordInput = screen.getByLabelText('Password')
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    await act(async () => {
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'Password123!' } })
      fireEvent.click(submitButton)
    })
    
    await waitFor(() => {
      expect(screen.getByText('Signing in...')).toBeInTheDocument()
      expect(submitButton).toBeDisabled()
    })

    // Resolve the promise to clean up and flush state updates
    await act(async () => {
      resolvePromise!({ success: true, token: 'test' })
    })
  })

  it('should render forgot password and sign up links', () => {
    render(<LoginPage />)
    
    expect(screen.getByText('Forgot your password?')).toBeInTheDocument()
    expect(screen.getByText('Create one now')).toBeInTheDocument()
  })

  it('should have proper accessibility attributes', () => {
    render(<LoginPage />)
    
    const emailInput = screen.getByLabelText('Email address')
    const passwordInput = screen.getByLabelText('Password')
    
    expect(emailInput).toHaveAttribute('type', 'email')
    expect(emailInput).toHaveAttribute('autoComplete', 'email')
    expect(passwordInput).toHaveAttribute('type', 'password')
    expect(passwordInput).toHaveAttribute('autoComplete', 'current-password')
  })
})

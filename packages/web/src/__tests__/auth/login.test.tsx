import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { useRouter } from 'next/navigation'
import LoginPage from '../../app/auth/login/page'
import { apiClient } from '../../lib/api'

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(),
}))

// Mock API client
vi.mock('../../lib/api', () => ({
  apiClient: {
    login: vi.fn(),
    setToken: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string, public data?: any) {
      super(message)
      this.name = 'ApiError'
    }
  },
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

  it('should display validation error for invalid email', async () => {
    render(<LoginPage />)
    
    const emailInput = screen.getByLabelText('Email address')
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    fireEvent.change(emailInput, { target: { value: 'invalid-email' } })
    fireEvent.blur(emailInput)
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/valid email/i)).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('should display validation error for short password', async () => {
    render(<LoginPage />)
    
    const emailInput = screen.getByLabelText('Email address')
    const passwordInput = screen.getByLabelText('Password')
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'short' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText('Password must be at least 8 characters long')).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('should handle successful login', async () => {
    const mockResponse = {
      success: true,
      token: 'test-token',
      user: { id: '1', email: 'test@example.com', name: 'Test User' }
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
      expect(mockRouter.push).toHaveBeenCalledWith('/')
    })
  })

  it('should handle login failure with 401 error', async () => {
    const mockError = {
      name: 'ApiError',
      status: 401,
      message: 'Unauthorized'
    }
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
    const mockError = {
      name: 'ApiError',
      status: 422,
      message: 'Validation failed',
      data: {
        errors: {
          email: ['Email format is invalid'],
          password: ['Password is too weak']
        }
      }
    }
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
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'Password123!' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText('Signing in...')).toBeInTheDocument()
      expect(submitButton).toBeDisabled()
    })

    // Resolve the promise to clean up
    resolvePromise!({ success: true, token: 'test' })
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
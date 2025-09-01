import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { useRouter } from 'next/navigation'
import RegisterPage from '../../app/auth/register/page'
import { apiClient, ApiError } from '../../lib/api'

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(),
}))

// Mock API client
vi.mock('../../lib/api', () => ({
  apiClient: {
    register: vi.fn(),
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

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(useRouter as any).mockReturnValue(mockRouter)
  })

  it('should render registration form with all fields', () => {
    render(<RegisterPage />)
    
    expect(screen.getByText('Create your account')).toBeInTheDocument()
    expect(screen.getByText('Start your travel planning journey with Travel Companion')).toBeInTheDocument()
    expect(screen.getByLabelText('Full name')).toBeInTheDocument()
    expect(screen.getByLabelText('Email address')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByLabelText('Confirm password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
  })

  it('should display validation errors for empty fields', async () => {
    render(<RegisterPage />)
    
    const submitButton = screen.getByRole('button', { name: /create account/i })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText('Name is required')).toBeInTheDocument()
      expect(screen.getByText('Email is required')).toBeInTheDocument()
      expect(screen.getByText('Password is required')).toBeInTheDocument()
      expect(screen.getByText('Please confirm your password')).toBeInTheDocument()
    })
  })

  it('should validate password requirements', async () => {
    render(<RegisterPage />)
    
    const nameInput = screen.getByLabelText('Full name')
    const emailInput = screen.getByLabelText('Email address')
    const passwordInput = screen.getByLabelText('Password')
    const confirmPasswordInput = screen.getByLabelText('Confirm password')
    const submitButton = screen.getByRole('button', { name: /create account/i })
    
    fireEvent.change(nameInput, { target: { value: 'Test User' } })
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'weakpassword' } })
    fireEvent.change(confirmPasswordInput, { target: { value: 'weakpassword' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText('Password must contain at least one uppercase letter')).toBeInTheDocument()
    })
  })

  it('should show password strength indicator', async () => {
    render(<RegisterPage />)
    
    const passwordInput = screen.getByLabelText('Password')
    
    fireEvent.change(passwordInput, { target: { value: 'weak' } })
    
    await waitFor(() => {
      expect(screen.getByText('Password strength:')).toBeInTheDocument()
      expect(screen.getByText('Weak')).toBeInTheDocument()
    })
    
    fireEvent.change(passwordInput, { target: { value: 'StrongPassword123!' } })
    
    await waitFor(() => {
      expect(screen.getByText('Strong')).toBeInTheDocument()
    })
  })

  it('should validate password confirmation', async () => {
    render(<RegisterPage />)
    
    const passwordInput = screen.getByLabelText('Password')
    const confirmPasswordInput = screen.getByLabelText('Confirm password')
    const submitButton = screen.getByRole('button', { name: /create account/i })
    
    fireEvent.change(passwordInput, { target: { value: 'Password123!' } })
    fireEvent.change(confirmPasswordInput, { target: { value: 'DifferentPassword123!' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText("Passwords don't match")).toBeInTheDocument()
    })
  })

  it('should handle successful registration', async () => {
    const mockResponse = {
      success: true,
      token: 'test-token',
      user: { id: '1', email: 'test@example.com', name: 'Test User' }
    }
    ;(apiClient.register as any).mockResolvedValue(mockResponse)
    
    render(<RegisterPage />)
    
    const nameInput = screen.getByLabelText('Full name')
    const emailInput = screen.getByLabelText('Email address')
    const passwordInput = screen.getByLabelText('Password')
    const confirmPasswordInput = screen.getByLabelText('Confirm password')
    const submitButton = screen.getByRole('button', { name: /create account/i })
    
    fireEvent.change(nameInput, { target: { value: 'Test User' } })
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'Password123!' } })
    fireEvent.change(confirmPasswordInput, { target: { value: 'Password123!' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(apiClient.register).toHaveBeenCalledWith({
        name: 'Test User',
        email: 'test@example.com',
        password: 'Password123!',
        confirmPassword: 'Password123!'
      })
      expect(apiClient.setToken).toHaveBeenCalledWith('test-token')
      expect(mockRouter.push).toHaveBeenCalledWith('/')
    })
  })

  it('should handle registration failure with 409 error (email exists)', async () => {
    const mockError = new ApiError(409, 'Email already exists')
    ;(apiClient.register as any).mockRejectedValue(mockError)
    
    render(<RegisterPage />)
    
    const nameInput = screen.getByLabelText('Full name')
    const emailInput = screen.getByLabelText('Email address')
    const passwordInput = screen.getByLabelText('Password')
    const confirmPasswordInput = screen.getByLabelText('Confirm password')
    const submitButton = screen.getByRole('button', { name: /create account/i })
    
    fireEvent.change(nameInput, { target: { value: 'Test User' } })
    fireEvent.change(emailInput, { target: { value: 'existing@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'Password123!' } })
    fireEvent.change(confirmPasswordInput, { target: { value: 'Password123!' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText('An account with this email address already exists. Please try logging in instead.')).toBeInTheDocument()
    })
  })

  it('should handle validation errors from API', async () => {
    const mockError = new ApiError(422, 'Validation failed', {
      errors: {
        email: ['Email is already taken'],
        name: ['Name is too short']
      }
    })
    ;(apiClient.register as any).mockRejectedValue(mockError)
    
    render(<RegisterPage />)
    
    const nameInput = screen.getByLabelText('Full name')
    const emailInput = screen.getByLabelText('Email address')
    const passwordInput = screen.getByLabelText('Password')
    const confirmPasswordInput = screen.getByLabelText('Confirm password')
    const submitButton = screen.getByRole('button', { name: /create account/i })
    
    fireEvent.change(nameInput, { target: { value: 'Test User' } })
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'Password123!' } })
    fireEvent.change(confirmPasswordInput, { target: { value: 'Password123!' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText('Email is already taken')).toBeInTheDocument()
      expect(screen.getByText('Name is too short')).toBeInTheDocument()
    })
  })

  it('should show loading state during submission', async () => {
    ;(apiClient.register as any).mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))
    
    render(<RegisterPage />)
    
    const nameInput = screen.getByLabelText('Full name')
    const emailInput = screen.getByLabelText('Email address')
    const passwordInput = screen.getByLabelText('Password')
    const confirmPasswordInput = screen.getByLabelText('Confirm password')
    const submitButton = screen.getByRole('button', { name: /create account/i })
    
    fireEvent.change(nameInput, { target: { value: 'Test User' } })
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'Password123!' } })
    fireEvent.change(confirmPasswordInput, { target: { value: 'Password123!' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText('Creating account...')).toBeInTheDocument()
      expect(submitButton).toBeDisabled()
    })
  })

  it('should render sign in link', () => {
    render(<RegisterPage />)
    
    expect(screen.getByText('Sign in here')).toBeInTheDocument()
  })

  it('should have proper accessibility attributes', () => {
    render(<RegisterPage />)
    
    const nameInput = screen.getByLabelText('Full name')
    const emailInput = screen.getByLabelText('Email address')
    const passwordInput = screen.getByLabelText('Password')
    const confirmPasswordInput = screen.getByLabelText('Confirm password')
    
    expect(nameInput).toHaveAttribute('type', 'text')
    expect(nameInput).toHaveAttribute('autoComplete', 'name')
    expect(emailInput).toHaveAttribute('type', 'email')
    expect(emailInput).toHaveAttribute('autoComplete', 'email')
    expect(passwordInput).toHaveAttribute('type', 'password')
    expect(passwordInput).toHaveAttribute('autoComplete', 'new-password')
    expect(confirmPasswordInput).toHaveAttribute('type', 'password')
    expect(confirmPasswordInput).toHaveAttribute('autoComplete', 'new-password')
  })

  it('should show password strength feedback with suggestions', async () => {
    render(<RegisterPage />)
    
    const passwordInput = screen.getByLabelText('Password')
    
    fireEvent.change(passwordInput, { target: { value: 'password' } })
    
    await waitFor(() => {
      expect(screen.getByText('• Add uppercase letters')).toBeInTheDocument()
      expect(screen.getByText('• Add numbers')).toBeInTheDocument()
      expect(screen.getByText('• Add special characters (!@#$%^&*)')).toBeInTheDocument()
    })
  })
})
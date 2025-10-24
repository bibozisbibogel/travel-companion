import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import TripPreferencesForm from '../../components/forms/TripPreferencesForm'
import * as draftStorage from '../../lib/draftStorage'
import * as api from '../../lib/api'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
}))

// Mock API client
vi.mock('../../lib/api', () => ({
  apiClient: {
    planTrip: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    constructor(public message: string, public status: number, public data?: unknown) {
      super(message)
    }
  },
}))

// Mock draft storage
vi.mock('../../lib/draftStorage', () => ({
  saveDraft: vi.fn(),
  loadDraft: vi.fn(),
  clearDraft: vi.fn(),
  hasDraft: vi.fn(),
  getDraftTimestamp: vi.fn(),
}))

describe('TripPreferencesForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(draftStorage, 'hasDraft').mockReturnValue(false)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders all form sections', () => {
    render(<TripPreferencesForm />)

    expect(screen.getByText('Where are you going?')).toBeInTheDocument()
    expect(screen.getByText('When are you traveling?')).toBeInTheDocument()
    expect(screen.getByText('Who is traveling?')).toBeInTheDocument()
    expect(screen.getByText('What is your budget?')).toBeInTheDocument()
    expect(screen.getByText('What interests you?')).toBeInTheDocument()
    expect(screen.getByText('Dietary Requirements')).toBeInTheDocument()
    expect(screen.getByText('Accommodation Preferences')).toBeInTheDocument()
    expect(screen.getByText('Cuisine Preferences')).toBeInTheDocument()
  })

  it('validates required fields on submit', async () => {
    render(<TripPreferencesForm />)

    const submitButton = screen.getByRole('button', { name: /generate trip itinerary/i })
    await userEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/destination is required/i)).toBeInTheDocument()
      expect(screen.getByText(/start date is required/i)).toBeInTheDocument()
      expect(screen.getByText(/end date is required/i)).toBeInTheDocument()
    })
  })

  it('validates traveler inputs', async () => {
    render(<TripPreferencesForm />)

    const adultsInput = screen.getByLabelText(/adults/i)
    await userEvent.clear(adultsInput)
    await userEvent.type(adultsInput, '0')

    const submitButton = screen.getByRole('button', { name: /generate trip itinerary/i })
    await userEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/at least 1 adult traveler is required/i)).toBeInTheDocument()
    })
  })

  it('validates date range (end date must be after start date)', async () => {
    render(<TripPreferencesForm />)

    const tomorrow = new Date()
    tomorrow.setDate(tomorrow.getDate() + 1)
    const today = new Date()

    const startDateInput = screen.getByLabelText(/start date/i)
    const endDateInput = screen.getByLabelText(/end date/i)

    await userEvent.type(startDateInput, tomorrow.toISOString().split('T')[0])
    await userEvent.type(endDateInput, today.toISOString().split('T')[0])

    const submitButton = screen.getByRole('button', { name: /generate trip itinerary/i })
    await userEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/end date must be after start date/i)).toBeInTheDocument()
    })
  })

  it('validates budget amount', async () => {
    render(<TripPreferencesForm />)

    const budgetInput = screen.getByPlaceholderText(/enter your budget/i)
    await userEvent.clear(budgetInput)
    await userEvent.type(budgetInput, '50')

    const submitButton = screen.getByRole('button', { name: /generate trip itinerary/i })
    await userEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/budget must be at least 100/i)).toBeInTheDocument()
    })
  })

  it('loads draft on mount if available', async () => {
    const mockDraft = {
      destination: 'Paris',
      origin: 'New York',
      startDate: '2025-11-01',
      endDate: '2025-11-07',
      travelers: { adults: 2, children: 1, infants: 0 },
      budget: { amount: 3000, currency: 'EUR' },
    }

    vi.spyOn(draftStorage, 'hasDraft').mockReturnValue(true)
    vi.spyOn(draftStorage, 'loadDraft').mockReturnValue(mockDraft)

    render(<TripPreferencesForm />)

    await waitFor(() => {
      expect(screen.getByText(/draft loaded/i)).toBeInTheDocument()
    })
  })

  it('clears draft on successful submission', async () => {
    const mockResponse = {
      success: true,
      data: { tripId: '123' },
    }

    vi.spyOn(api.apiClient, 'planTrip').mockResolvedValue(mockResponse)

    render(<TripPreferencesForm />)

    const destinationInput = screen.getByPlaceholderText(/where would you like to travel/i)
    await userEvent.type(destinationInput, 'Tokyo')

    const tomorrow = new Date()
    tomorrow.setDate(tomorrow.getDate() + 1)
    const nextWeek = new Date()
    nextWeek.setDate(nextWeek.getDate() + 7)

    const startDateInput = screen.getByLabelText(/start date/i)
    const endDateInput = screen.getByLabelText(/end date/i)

    await userEvent.type(startDateInput, tomorrow.toISOString().split('T')[0])
    await userEvent.type(endDateInput, nextWeek.toISOString().split('T')[0])

    const submitButton = screen.getByRole('button', { name: /generate trip itinerary/i })
    await userEvent.click(submitButton)

    await waitFor(() => {
      expect(draftStorage.clearDraft).toHaveBeenCalled()
    })
  })

  it('displays API errors to the user', async () => {
    const mockError = new api.ApiError('Failed to create trip', 500)
    vi.spyOn(api.apiClient, 'planTrip').mockRejectedValue(mockError)

    render(<TripPreferencesForm />)

    const destinationInput = screen.getByPlaceholderText(/where would you like to travel/i)
    await userEvent.type(destinationInput, 'Tokyo')

    const tomorrow = new Date()
    tomorrow.setDate(tomorrow.getDate() + 1)
    const nextWeek = new Date()
    nextWeek.setDate(nextWeek.getDate() + 7)

    const startDateInput = screen.getByLabelText(/start date/i)
    const endDateInput = screen.getByLabelText(/end date/i)

    await userEvent.type(startDateInput, tomorrow.toISOString().split('T')[0])
    await userEvent.type(endDateInput, nextWeek.toISOString().split('T')[0])

    const submitButton = screen.getByRole('button', { name: /generate trip itinerary/i })
    await userEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/failed to create trip/i)
    })
  })

  it('disables submit button while loading', async () => {
    vi.spyOn(api.apiClient, 'planTrip').mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 1000))
    )

    render(<TripPreferencesForm />)

    const destinationInput = screen.getByPlaceholderText(/where would you like to travel/i)
    await userEvent.type(destinationInput, 'Tokyo')

    const tomorrow = new Date()
    tomorrow.setDate(tomorrow.getDate() + 1)
    const nextWeek = new Date()
    nextWeek.setDate(nextWeek.getDate() + 7)

    const startDateInput = screen.getByLabelText(/start date/i)
    const endDateInput = screen.getByLabelText(/end date/i)

    await userEvent.type(startDateInput, tomorrow.toISOString().split('T')[0])
    await userEvent.type(endDateInput, nextWeek.toISOString().split('T')[0])

    const submitButton = screen.getByRole('button', { name: /generate trip itinerary/i })
    await userEvent.click(submitButton)

    expect(submitButton).toBeDisabled()
  })
})

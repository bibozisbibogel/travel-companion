# Testing Requirements

## Component Test Template

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FlightCard } from '@/components/travel/FlightCard'
import type { FlightOption } from '@/lib/types/travel'

// Mock data
const mockFlight: FlightOption = {
  flight_id: 'flight-123',
  airline: 'American Airlines',
  flight_number: 'AA1234',
  price: 450.00,
  currency: 'USD',
  origin: 'JFK',
  destination: 'LAX',
  departure_time: '2024-06-01T10:00:00Z',
  arrival_time: '2024-06-01T13:30:00Z',
  duration_minutes: 330,
  stops: 0
}

// Mock handlers
const mockOnSelect = vi.fn()
const mockOnCompare = vi.fn()

describe('FlightCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders flight information correctly', () => {
    render(
      <FlightCard 
        flight={mockFlight}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    // Test basic information display
    expect(screen.getByText('American Airlines')).toBeInTheDocument()
    expect(screen.getByText('AA1234')).toBeInTheDocument()
    expect(screen.getByText('$450')).toBeInTheDocument()
    expect(screen.getByText('USD')).toBeInTheDocument()
    expect(screen.getByText('JFK')).toBeInTheDocument()
    expect(screen.getByText('LAX')).toBeInTheDocument()
    expect(screen.getByText('5h 30m')).toBeInTheDocument()
    expect(screen.getByText('Direct')).toBeInTheDocument()
  })

  it('handles flight selection correctly', async () => {
    const user = userEvent.setup()
    
    render(
      <FlightCard 
        flight={mockFlight}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    const card = screen.getByRole('button', { 
      name: /flight american airlines departing/i 
    })
    
    await user.click(card)
    
    expect(mockOnSelect).toHaveBeenCalledWith('flight-123')
    expect(mockOnSelect).toHaveBeenCalledTimes(1)
  })

  it('handles compare action without triggering selection', async () => {
    const user = userEvent.setup()
    
    render(
      <FlightCard 
        flight={mockFlight}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    const compareButton = screen.getByRole('button', { name: /compare/i })
    
    await user.click(compareButton)
    
    expect(mockOnCompare).toHaveBeenCalledWith('flight-123')
    expect(mockOnSelect).not.toHaveBeenCalled()
  })

  it('displays selected state correctly', () => {
    render(
      <FlightCard 
        flight={mockFlight}
        isSelected={true}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    const card = screen.getByRole('button', { 
      name: /flight american airlines departing/i 
    })
    
    expect(card).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText('Selected')).toBeInTheDocument()
    
    const selectButton = screen.getByRole('button', { name: /selected/i })
    expect(selectButton).toBeDisabled()
  })

  it('handles flights with stops correctly', () => {
    const flightWithStops = {
      ...mockFlight,
      stops: 1
    }

    render(
      <FlightCard 
        flight={flightWithStops}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    expect(screen.getByText('1 stop')).toBeInTheDocument()
  })

  it('handles flights with multiple stops correctly', () => {
    const flightWithMultipleStops = {
      ...mockFlight,
      stops: 2
    }

    render(
      <FlightCard 
        flight={flightWithMultipleStops}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    expect(screen.getByText('2 stops')).toBeInTheDocument()
  })

  it('supports keyboard navigation', async () => {
    const user = userEvent.setup()
    
    render(
      <FlightCard 
        flight={mockFlight}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    const card = screen.getByRole('button', { 
      name: /flight american airlines departing/i 
    })
    
    // Focus the card
    card.focus()
    expect(card).toHaveFocus()
    
    // Activate with Enter key
    await user.keyboard('{Enter}')
    expect(mockOnSelect).toHaveBeenCalledWith('flight-123')
    
    // Test Space key
    vi.clearAllMocks()
    await user.keyboard(' ')
    expect(mockOnSelect).toHaveBeenCalledWith('flight-123')
  })

  it('applies custom className correctly', () => {
    const customClass = 'custom-flight-card'
    
    render(
      <FlightCard 
        flight={mockFlight}
        className={customClass}
        onSelect={mockOnSelect}
        onCompare={mockOnCompare}
      />
    )

    const card = screen.getByRole('button', { 
      name: /flight american airlines departing/i 
    })
    
    expect(card).toHaveClass(customClass)
  })

  it('handles missing optional props gracefully', () => {
    render(<FlightCard flight={mockFlight} />)

    const card = screen.getByRole('button', { 
      name: /flight american airlines departing/i 
    })
    
    // Should render without crashing
    expect(card).toBeInTheDocument()
    expect(screen.getByText('American Airlines')).toBeInTheDocument()
  })
})

// Integration test example
describe('FlightCard Integration', () => {
  it('integrates with travel store correctly', async () => {
    const user = userEvent.setup()
    
    // Mock the travel store
    const mockUseTripStore = vi.fn(() => ({
      selectedOptions: { flight: null },
      actions: { selectOption: vi.fn() }
    }))

    vi.mock('@/lib/store/trip', () => ({
      useTripStore: mockUseTripStore
    }))

    const TestComponent = () => {
      const { selectedOptions, actions } = mockUseTripStore()
      
      return (
        <FlightCard 
          flight={mockFlight}
          isSelected={selectedOptions.flight?.flight_id === mockFlight.flight_id}
          onSelect={(flightId) => actions.selectOption('flight', mockFlight)}
        />
      )
    }

    render(<TestComponent />)

    const card = screen.getByRole('button', { 
      name: /flight american airlines departing/i 
    })
    
    await user.click(card)
    
    expect(mockUseTripStore().actions.selectOption).toHaveBeenCalledWith('flight', mockFlight)
  })
})
```

## Testing Best Practices

1. **Unit Tests**: Test individual components in isolation with mocked dependencies and comprehensive prop variations
2. **Integration Tests**: Test component interactions with state management, API clients, and routing
3. **E2E Tests**: Test critical user flows including trip planning, selection, and export workflows
4. **Coverage Goals**: Maintain 85%+ code coverage with focus on business logic and user interactions
5. **Test Structure**: Follow Arrange-Act-Assert pattern with descriptive test names and grouped scenarios
6. **Mock External Dependencies**: Mock API calls, geolocation, file downloads, and third-party libraries
7. **Accessibility Testing**: Include screen reader testing, keyboard navigation, and color contrast validation
8. **Performance Testing**: Test component rendering performance, memory leaks, and bundle size impact
9. **Visual Regression**: Use Playwright for screenshot comparison testing of complex travel components
10. **Real User Testing**: Complement automated tests with user testing sessions for travel planning workflows

import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import LoadingScreen from '../LoadingScreen'

describe('LoadingScreen', () => {
  it('should render with default message', () => {
    render(<LoadingScreen />)
    expect(screen.getByText('Creating Your Trip Plan...')).toBeInTheDocument()
  })

  it('should render with custom message', () => {
    render(<LoadingScreen message="Processing your request..." />)
    expect(screen.getByText('Processing your request...')).toBeInTheDocument()
  })

  it('should display progress indicators', () => {
    render(<LoadingScreen />)
    expect(screen.getByText('Analyzing your preferences')).toBeInTheDocument()
    expect(screen.getByText('Finding the best options')).toBeInTheDocument()
    expect(screen.getByText('Building your personalized itinerary')).toBeInTheDocument()
  })

  it('should have loading animation elements', () => {
    const { container } = render(<LoadingScreen />)
    const spinners = container.querySelectorAll('.animate-spin')
    expect(spinners.length).toBeGreaterThan(0)
  })

  it('should display helper text', () => {
    render(<LoadingScreen />)
    expect(
      screen.getByText('This may take a moment as we craft the perfect itinerary for you...')
    ).toBeInTheDocument()
  })
})

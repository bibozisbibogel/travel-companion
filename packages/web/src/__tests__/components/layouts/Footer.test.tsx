import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Footer from '../../../components/layouts/Footer'

describe('Footer Component', () => {
  it('should render brand logo and current year', () => {
    render(<Footer />)
    
    expect(screen.getByText('Travel Companion')).toBeInTheDocument()
    expect(screen.getByText('🧳')).toBeInTheDocument()
    
    const currentYear = new Date().getFullYear()
    expect(screen.getByText(new RegExp(currentYear.toString()))).toBeInTheDocument()
  })

  it('should render all footer sections with correct links', () => {
    render(<Footer />)
    
    // Travel Planning section
    expect(screen.getByText('Travel Planning')).toBeInTheDocument()
    expect(screen.getByText('Plan New Trip')).toBeInTheDocument()
    expect(screen.getByText('My Trips')).toBeInTheDocument()
    expect(screen.getByText('Popular Destinations')).toBeInTheDocument()
    expect(screen.getByText('Travel Guides')).toBeInTheDocument()

    // Account section
    expect(screen.getByText('Account')).toBeInTheDocument()
    expect(screen.getByText('Login')).toBeInTheDocument()
    expect(screen.getByText('Sign Up')).toBeInTheDocument()
    expect(screen.getByText('My Profile')).toBeInTheDocument()
    expect(screen.getByText('Travel Preferences')).toBeInTheDocument()

    // Support section
    expect(screen.getByText('Support')).toBeInTheDocument()
    expect(screen.getByText('Help Center')).toBeInTheDocument()
    expect(screen.getByText('Contact Us')).toBeInTheDocument()
    expect(screen.getByText('FAQ')).toBeInTheDocument()
    expect(screen.getByText('Send Feedback')).toBeInTheDocument()

    // Company section
    expect(screen.getByText('Company')).toBeInTheDocument()
    expect(screen.getByText('About Us')).toBeInTheDocument()
    expect(screen.getByText('Privacy Policy')).toBeInTheDocument()
    expect(screen.getByText('Terms of Service')).toBeInTheDocument()
    expect(screen.getByText('Careers')).toBeInTheDocument()
  })

  it('should render newsletter subscription section', () => {
    render(<Footer />)
    
    expect(screen.getByText('Stay updated with travel tips')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Enter your email')).toBeInTheDocument()
    expect(screen.getByText('Subscribe')).toBeInTheDocument()
    expect(screen.getByText(/Get the latest travel guides/)).toBeInTheDocument()
  })

  it('should render social media links', () => {
    render(<Footer />)
    
    expect(screen.getByLabelText('Follow us on Twitter')).toBeInTheDocument()
    expect(screen.getByLabelText('Follow us on Facebook')).toBeInTheDocument()
    expect(screen.getByLabelText('Follow us on Instagram')).toBeInTheDocument()
  })

  it('should have proper form structure for newsletter', () => {
    render(<Footer />)
    
    const emailInput = screen.getByLabelText('Email address')
    expect(emailInput).toHaveAttribute('type', 'email')
    expect(emailInput).toHaveAttribute('required')
    expect(emailInput).toHaveAttribute('autoComplete', 'email')
    
    const subscribeButton = screen.getByRole('button', { name: 'Subscribe' })
    expect(subscribeButton).toHaveAttribute('type', 'submit')
  })

  it('should apply custom className when provided', () => {
    render(<Footer className="custom-footer-class" />)
    
    const footer = screen.getByRole('contentinfo')
    expect(footer).toHaveClass('custom-footer-class')
  })

  it('should have correct link hrefs', () => {
    render(<Footer />)
    
    const planTripLink = screen.getByRole('link', { name: 'Plan New Trip' })
    expect(planTripLink).toHaveAttribute('href', '/trips/new')
    
    const loginLink = screen.getByRole('link', { name: 'Login' })
    expect(loginLink).toHaveAttribute('href', '/auth/login')
    
    const helpLink = screen.getByRole('link', { name: 'Help Center' })
    expect(helpLink).toHaveAttribute('href', '/help')
  })

  it('should have proper semantic structure', () => {
    render(<Footer />)
    
    const footer = screen.getByRole('contentinfo')
    expect(footer).toBeInTheDocument()
    
    // Check for proper heading structure - includes newsletter section
    const headings = screen.getAllByRole('heading', { level: 3 })
    expect(headings.length).toBeGreaterThanOrEqual(4) // At least four main sections
    
    expect(screen.getByRole('heading', { name: 'Travel Planning' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Account' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Support' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Company' })).toBeInTheDocument()
  })

  it('should render copyright message correctly', () => {
    render(<Footer />)
    
    expect(screen.getByText(/All rights reserved/)).toBeInTheDocument()
    expect(screen.getByText(/Built with ❤️ for travelers worldwide/)).toBeInTheDocument()
  })
})
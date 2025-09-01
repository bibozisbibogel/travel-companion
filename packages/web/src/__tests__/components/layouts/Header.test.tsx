import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import Header from '../../../components/layouts/Header'

// Mock Next.js navigation
const mockPush = vi.fn()
const mockPathname = '/'

vi.mock('next/navigation', () => ({
  usePathname: () => mockPathname,
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
}))

describe('Header Component', () => {
  const mockUser = {
    id: '1',
    email: 'test@example.com',
    name: 'Test User'
  }

  const mockOnLogout = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render brand logo and navigation', () => {
    render(<Header />)
    
    expect(screen.getByText('Travel Companion')).toBeInTheDocument()
    expect(screen.getByText('🧳')).toBeInTheDocument()
    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.getByText('Plan Trip')).toBeInTheDocument()
  })

  it('should show login/signup buttons when user is not authenticated', () => {
    render(<Header />)
    
    expect(screen.getByText('Login')).toBeInTheDocument()
    expect(screen.getByText('Sign Up')).toBeInTheDocument()
    expect(screen.queryByText('My Trips')).not.toBeInTheDocument()
  })

  it('should show user info and logout when authenticated', () => {
    render(<Header user={mockUser} onLogout={mockOnLogout} />)
    
    expect(screen.getByText('Test User')).toBeInTheDocument()
    expect(screen.getByText('Logout')).toBeInTheDocument()
    expect(screen.getByText('My Trips')).toBeInTheDocument()
    expect(screen.queryByText('Login')).not.toBeInTheDocument()
  })

  it('should show user initial when name is not provided', () => {
    const userWithoutName = { id: '1', email: 'test@example.com' }
    render(<Header user={userWithoutName} onLogout={mockOnLogout} />)
    
    expect(screen.getByText('T')).toBeInTheDocument() // First letter of email
    expect(screen.getByText('test@example.com')).toBeInTheDocument()
  })

  it('should call onLogout when logout button is clicked', () => {
    render(<Header user={mockUser} onLogout={mockOnLogout} />)
    
    const logoutButton = screen.getByText('Logout')
    fireEvent.click(logoutButton)
    
    expect(mockOnLogout).toHaveBeenCalledTimes(1)
  })

  it('should toggle mobile menu when hamburger button is clicked', () => {
    render(<Header user={mockUser} onLogout={mockOnLogout} />)
    
    // Mobile menu should not be visible initially
    expect(screen.queryByText('Open main menu')).toBeInTheDocument()
    
    // Click hamburger button
    const menuButton = screen.getByLabelText('Toggle navigation menu')
    fireEvent.click(menuButton)
    
    // Mobile menu should be visible
    const mobileMenu = screen.getByRole('navigation')
    expect(within(mobileMenu).getByText('Home')).toBeInTheDocument()
  })

  it('should render navigation links with proper structure', () => {
    render(<Header />)
    
    const planTripLink = screen.getByRole('link', { name: /✈️ Plan Trip/i })
    expect(planTripLink).toBeInTheDocument()
    expect(planTripLink).toHaveAttribute('href', '/trips/new')
    
    const homeLink = screen.getByRole('link', { name: /🏠 Home/i })
    expect(homeLink).toBeInTheDocument()
    expect(homeLink).toHaveAttribute('href', '/')
  })

  it('should have proper accessibility attributes', () => {
    render(<Header />)
    
    const menuButton = screen.getByLabelText('Toggle navigation menu')
    expect(menuButton).toHaveAttribute('aria-expanded', 'false')
    
    fireEvent.click(menuButton)
    expect(menuButton).toHaveAttribute('aria-expanded', 'true')
  })

  it('should close mobile menu when navigation link is clicked', () => {
    render(<Header />)
    
    // Open mobile menu
    const menuButton = screen.getByLabelText('Toggle navigation menu')
    fireEvent.click(menuButton)
    expect(menuButton).toHaveAttribute('aria-expanded', 'true')
    
    // Click a navigation link - get all links and click one in mobile menu
    const homeLinks = screen.getAllByText('Home')
    if (homeLinks.length > 1) {
      fireEvent.click(homeLinks[1])
    }
    
    // Menu should be closed
    expect(menuButton).toHaveAttribute('aria-expanded', 'false')
  })

  it('should show correct navigation structure', () => {
    render(<Header />)
    
    // Check desktop navigation
    const nav = screen.getByRole('navigation')
    expect(within(nav).getByText('🏠')).toBeInTheDocument()
    expect(within(nav).getByText('✈️')).toBeInTheDocument()
  })
})
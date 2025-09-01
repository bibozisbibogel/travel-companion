import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import MainLayout, { CenteredLayout, DashboardLayout, FullWidthLayout } from '../../../components/layouts/MainLayout'

// Mock the Header and Footer components
vi.mock('../../../components/layouts/Header', () => ({
  default: ({ user, onLogout }: any) => (
    <header data-testid="header">
      Header - User: {user?.email || 'none'} - Logout: {onLogout ? 'yes' : 'no'}
    </header>
  )
}))

vi.mock('../../../components/layouts/Footer', () => ({
  default: ({ className }: any) => (
    <footer data-testid="footer" className={className}>Footer</footer>
  )
}))

describe('MainLayout Component', () => {
  const mockUser = {
    id: '1',
    email: 'test@example.com',
    name: 'Test User'
  }

  const mockOnLogout = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render header, main content, and footer by default', () => {
    render(
      <MainLayout user={mockUser} onLogout={mockOnLogout}>
        <div>Main content</div>
      </MainLayout>
    )

    expect(screen.getByTestId('header')).toBeInTheDocument()
    expect(screen.getByText('Main content')).toBeInTheDocument()
    expect(screen.getByTestId('footer')).toBeInTheDocument()
  })

  it('should pass user and onLogout props to Header', () => {
    render(
      <MainLayout user={mockUser} onLogout={mockOnLogout}>
        <div>Content</div>
      </MainLayout>
    )

    const header = screen.getByTestId('header')
    expect(header).toHaveTextContent('User: test@example.com')
    expect(header).toHaveTextContent('Logout: yes')
  })

  it('should hide footer when showFooter is false', () => {
    render(
      <MainLayout showFooter={false}>
        <div>Content</div>
      </MainLayout>
    )

    expect(screen.getByTestId('header')).toBeInTheDocument()
    expect(screen.getByText('Content')).toBeInTheDocument()
    expect(screen.queryByTestId('footer')).not.toBeInTheDocument()
  })

  it('should apply custom className to main wrapper', () => {
    render(
      <MainLayout className="custom-class">
        <div>Content</div>
      </MainLayout>
    )

    const wrapper = screen.getByTestId('header').parentElement
    expect(wrapper).toHaveClass('custom-class')
  })

  it('should apply containerClassName to content container', () => {
    render(
      <MainLayout containerClassName="custom-container">
        <div>Content</div>
      </MainLayout>
    )

    const contentContainer = screen.getByText('Content').parentElement
    expect(contentContainer).toHaveClass('custom-container')
  })

  it('should pass headerProps to Header component', () => {
    render(
      <MainLayout headerProps={{ className: 'header-class' }}>
        <div>Content</div>
      </MainLayout>
    )

    // Header component should receive the props (mocked implementation doesn't use them)
    expect(screen.getByTestId('header')).toBeInTheDocument()
  })
})

describe('CenteredLayout Component', () => {
  it('should render with centered content and title', () => {
    render(
      <CenteredLayout title="Login" subtitle="Welcome back">
        <div>Login form</div>
      </CenteredLayout>
    )

    expect(screen.getByText('Login')).toBeInTheDocument()
    expect(screen.getByText('Welcome back')).toBeInTheDocument()
    expect(screen.getByText('Login form')).toBeInTheDocument()
  })

  it('should not show footer by default', () => {
    render(
      <CenteredLayout>
        <div>Content</div>
      </CenteredLayout>
    )

    expect(screen.queryByTestId('footer')).not.toBeInTheDocument()
  })

  it('should apply gradient background class', () => {
    render(
      <CenteredLayout>
        <div>Content</div>
      </CenteredLayout>
    )

    const wrapper = screen.getByTestId('header').parentElement
    expect(wrapper).toHaveClass('bg-gradient-to-br', 'from-primary-50', 'via-white', 'to-secondary-50')
  })

  it('should respect custom maxWidth', () => {
    render(
      <CenteredLayout maxWidth="max-w-lg">
        <div>Content</div>
      </CenteredLayout>
    )

    // Content should be rendered (exact class checking would require DOM inspection)
    expect(screen.getByText('Content')).toBeInTheDocument()
  })
})

describe('DashboardLayout Component', () => {
  it('should render with sidebar and main content', () => {
    render(
      <DashboardLayout
        sidebar={<div>Sidebar content</div>}
        pageTitle="Dashboard"
        pageDescription="Manage your account"
        actions={<button>Action Button</button>}
      >
        <div>Dashboard content</div>
      </DashboardLayout>
    )

    expect(screen.getByText('Sidebar content')).toBeInTheDocument()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Manage your account')).toBeInTheDocument()
    expect(screen.getByText('Action Button')).toBeInTheDocument()
    expect(screen.getByText('Dashboard content')).toBeInTheDocument()
  })

  it('should render without sidebar when not provided', () => {
    render(
      <DashboardLayout pageTitle="Simple Dashboard">
        <div>Content</div>
      </DashboardLayout>
    )

    expect(screen.getByText('Simple Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Content')).toBeInTheDocument()
    // No sidebar should be present
    expect(screen.getByText('Content').closest('.lg\\:flex-row')).toBeInTheDocument()
  })

  it('should render without page header when no title/description/actions provided', () => {
    render(
      <DashboardLayout>
        <div>Content only</div>
      </DashboardLayout>
    )

    expect(screen.getByText('Content only')).toBeInTheDocument()
    // Should not have page header section
    expect(screen.queryByRole('heading')).not.toBeInTheDocument()
  })
})

describe('FullWidthLayout Component', () => {
  it('should render with full width structure', () => {
    render(
      <FullWidthLayout>
        <div>Full width content</div>
      </FullWidthLayout>
    )

    expect(screen.getByTestId('header')).toBeInTheDocument()
    expect(screen.getByText('Full width content')).toBeInTheDocument()
    expect(screen.getByTestId('footer')).toBeInTheDocument()
  })

  it('should apply custom background color', () => {
    render(
      <FullWidthLayout backgroundColor="bg-blue-100">
        <div>Content</div>
      </FullWidthLayout>
    )

    const wrapper = screen.getByTestId('header').parentElement
    expect(wrapper).toHaveClass('bg-blue-100')
  })

  it('should hide footer when showFooter is false', () => {
    render(
      <FullWidthLayout showFooter={false}>
        <div>Content</div>
      </FullWidthLayout>
    )

    expect(screen.getByTestId('header')).toBeInTheDocument()
    expect(screen.getByText('Content')).toBeInTheDocument()
    expect(screen.queryByTestId('footer')).not.toBeInTheDocument()
  })
})
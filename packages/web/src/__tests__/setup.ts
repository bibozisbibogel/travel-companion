import '@testing-library/jest-dom'
import { vi } from 'vitest'
import React from 'react'

// Mock Next.js router
const mockRouter = {
  push: vi.fn(),
  replace: vi.fn(),
  prefetch: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  refresh: vi.fn(),
  pathname: '/',
  route: '/',
  query: {},
  asPath: '/',
}

vi.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}))

// Mock Next.js Image component
vi.mock('next/image', () => ({
  default: ({ src, alt, ...props }: any) => {
    // Return a simple img element for testing
    return { src, alt, ...props }
  },
}))

// Mock Next.js Link to avoid prefetch/state updates during tests
vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: any) => {
    return React.createElement('a', { href, ...props }, children)
  },
}))

// Mock lucide-react icons to avoid rendering issues in tests
vi.mock('lucide-react', () => {
  const mockIcon = ({ 'data-testid': testId, className, ...props }: any) =>
    React.createElement('svg', {
      'data-testid': testId || 'mock-icon',
      className,
      ...props
    })

  return {
    Loader2: mockIcon,
    AlertCircle: mockIcon,
    Search: mockIcon,
    Filter: mockIcon,
    Plane: mockIcon,
    X: mockIcon,
    Plus: mockIcon,
    ChevronLeft: mockIcon,
    ChevronRight: mockIcon,
    ChevronDown: mockIcon,
    ChevronUp: mockIcon,
    Calendar: mockIcon,
    MapPin: mockIcon,
    DollarSign: mockIcon,
    Clock: mockIcon,
    Star: mockIcon,
    TrendingUp: mockIcon,
    TrendingDown: mockIcon,
    Sun: mockIcon,
    Moon: mockIcon,
    CloudMoon: mockIcon,
    Sunset: mockIcon,
    MoreHorizontal: mockIcon,
    // Activity category icons (Story 3.6)
    Car: mockIcon,
    Hotel: mockIcon,
    Compass: mockIcon,
    Landmark: mockIcon,
    Utensils: mockIcon,
    ShoppingBag: mockIcon,
    Theater: mockIcon,
    LucideIcon: mockIcon,
  }
})

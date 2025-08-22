# Routing

## Route Configuration

```typescript
// app/layout.tsx - Root layout with providers and global state
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Providers } from '@/components/providers'
import { Header } from '@/components/layouts/Header'
import { Footer } from '@/components/layouts/Footer'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Travel Companion - AI-Powered Trip Planning',
  description: 'Plan your perfect trip with AI-powered recommendations for flights, hotels, activities, and more.',
  keywords: 'travel planning, AI travel, trip planner, flights, hotels, activities',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={inter.className}>
      <body>
        <Providers>
          <div className="min-h-screen flex flex-col">
            <Header />
            <main className="flex-1">
              {children}
            </main>
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  )
}

// app/trips/[trip_id]/layout.tsx - Trip-specific layout with navigation
import { Suspense } from 'react'
import { TripNavigation } from '@/components/layouts/TripNavigation'
import { TripProvider } from '@/components/providers/TripProvider'
import { LoadingState } from '@/components/shared/LoadingState'

interface TripLayoutProps {
  children: React.ReactNode
  params: { trip_id: string }
}

export default function TripLayout({ children, params }: TripLayoutProps) {
  return (
    <TripProvider tripId={params.trip_id}>
      <div className="container mx-auto px-4 py-6">
        <TripNavigation tripId={params.trip_id} />
        <Suspense fallback={<LoadingState message="Loading trip data..." />}>
          <div className="mt-6">
            {children}
          </div>
        </Suspense>
      </div>
    </TripProvider>
  )
}

// lib/auth/ProtectedRoute.tsx - Route protection wrapper
'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store/auth'
import { LoadingState } from '@/components/shared/LoadingState'

interface ProtectedRouteProps {
  children: React.ReactNode
  requireAuth?: boolean
  redirectTo?: string
}

export function ProtectedRoute({ 
  children, 
  requireAuth = true,
  redirectTo = '/auth/login' 
}: ProtectedRouteProps) {
  const router = useRouter()
  const { isAuthenticated, isLoading, user } = useAuthStore()

  useEffect(() => {
    if (!isLoading && requireAuth && !isAuthenticated) {
      router.push(redirectTo)
    }
  }, [isAuthenticated, isLoading, requireAuth, router, redirectTo])

  if (isLoading) {
    return <LoadingState message="Checking authentication..." />
  }

  if (requireAuth && !isAuthenticated) {
    return null // Will redirect via useEffect
  }

  return <>{children}</>
}

// lib/hooks/useRouteGuard.ts - Route guard hook
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store/auth'
import { useTripStore } from '@/lib/store/trip'

interface RouteGuardOptions {
  requireAuth?: boolean
  requireTrip?: boolean
  allowedRoles?: string[]
}

export function useRouteGuard(options: RouteGuardOptions = {}) {
  const router = useRouter()
  const { isAuthenticated, user } = useAuthStore()
  const { currentTrip } = useTripStore()

  useEffect(() => {
    // Check authentication
    if (options.requireAuth && !isAuthenticated) {
      router.push('/auth/login')
      return
    }

    // Check user roles
    if (options.allowedRoles && user && !options.allowedRoles.includes(user.role)) {
      router.push('/unauthorized')
      return
    }

    // Check trip requirement
    if (options.requireTrip && !currentTrip) {
      router.push('/trips/new')
      return
    }
  }, [isAuthenticated, user, currentTrip, router, options])

  return {
    isAuthorized: (!options.requireAuth || isAuthenticated) &&
                 (!options.allowedRoles || (user && options.allowedRoles.includes(user.role))) &&
                 (!options.requireTrip || !!currentTrip)
  }
}

// app/trips/[trip_id]/page.tsx - Example protected route usage
'use client'

import { useParams } from 'next/navigation'
import { ProtectedRoute } from '@/lib/auth/ProtectedRoute'
import { TripDashboard } from '@/components/travel/TripDashboard'
import { useRouteGuard } from '@/lib/hooks/useRouteGuard'

export default function TripPage() {
  const params = useParams()
  const tripId = params.trip_id as string

  const { isAuthorized } = useRouteGuard({
    requireAuth: true,
    requireTrip: false // Trip will be loaded by component
  })

  if (!isAuthorized) {
    return null
  }

  return (
    <ProtectedRoute>
      <TripDashboard tripId={tripId} />
    </ProtectedRoute>
  )
}
```

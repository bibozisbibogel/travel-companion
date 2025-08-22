# Project Structure

```
packages/web/                          # Next.js Frontend Application
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── globals.css               # Global Tailwind imports
│   │   ├── layout.tsx                # Root layout with providers
│   │   ├── page.tsx                  # Home page (travel request input)
│   │   ├── loading.tsx               # Global loading UI
│   │   ├── error.tsx                 # Global error boundary
│   │   ├── not-found.tsx             # 404 page
│   │   │
│   │   ├── auth/                     # Authentication pages
│   │   │   ├── login/
│   │   │   │   └── page.tsx          # Login form
│   │   │   ├── register/
│   │   │   │   └── page.tsx          # Registration form
│   │   │   └── layout.tsx            # Auth layout
│   │   │
│   │   ├── dashboard/                # User dashboard
│   │   │   ├── page.tsx              # Trip history and preferences
│   │   │   ├── profile/
│   │   │   │   └── page.tsx          # User profile management
│   │   │   └── layout.tsx            # Dashboard layout
│   │   │
│   │   ├── trips/                    # Trip planning and viewing
│   │   │   ├── new/
│   │   │   │   └── page.tsx          # New trip request form
│   │   │   ├── [trip_id]/
│   │   │   │   ├── page.tsx          # Trip results dashboard
│   │   │   │   ├── flights/
│   │   │   │   │   └── page.tsx      # Flight comparison view
│   │   │   │   ├── hotels/
│   │   │   │   │   └── page.tsx      # Hotel selection view
│   │   │   │   ├── activities/
│   │   │   │   │   └── page.tsx      # Activity browser
│   │   │   │   ├── restaurants/
│   │   │   │   │   └── page.tsx      # Restaurant finder
│   │   │   │   ├── budget/
│   │   │   │   │   └── page.tsx      # Budget tracker view
│   │   │   │   ├── map/
│   │   │   │   │   └── page.tsx      # Interactive map view
│   │   │   │   ├── itinerary/
│   │   │   │   │   └── page.tsx      # Final itinerary
│   │   │   │   └── loading.tsx       # Trip loading state
│   │   │   └── layout.tsx            # Trip planning layout
│   │   │
│   │   └── api/                      # API routes (if needed)
│   │       └── auth/                 # Client-side auth helpers
│   │
│   ├── components/                   # Reusable components
│   │   ├── ui/                       # Base UI components
│   │   │   ├── Button.tsx            # Button variants
│   │   │   ├── Card.tsx              # Card container
│   │   │   ├── Input.tsx             # Form inputs
│   │   │   ├── Modal.tsx             # Modal/dialog
│   │   │   ├── Tabs.tsx              # Tab navigation
│   │   │   ├── Badge.tsx             # Status badges
│   │   │   ├── Spinner.tsx           # Loading spinners
│   │   │   └── index.ts              # Component exports
│   │   │
│   │   ├── forms/                    # Form-specific components
│   │   │   ├── TravelRequestForm.tsx # Main travel input form
│   │   │   ├── FilterPanel.tsx       # Search refinement
│   │   │   ├── BudgetSlider.tsx      # Budget range selector
│   │   │   └── DateRangePicker.tsx   # Travel date selection
│   │   │
│   │   ├── travel/                   # Travel-specific components
│   │   │   ├── FlightCard.tsx        # Flight option display
│   │   │   ├── HotelCard.tsx         # Hotel option display
│   │   │   ├── ActivityCard.tsx      # Activity display
│   │   │   ├── RestaurantCard.tsx    # Restaurant display
│   │   │   ├── ItineraryTimeline.tsx # Day-by-day schedule
│   │   │   └── BudgetTracker.tsx     # Real-time budget display
│   │   │
│   │   ├── maps/                     # Map-related components
│   │   │   ├── InteractiveMap.tsx    # Main map component
│   │   │   ├── MapMarker.tsx         # Custom map markers
│   │   │   ├── RouteOverlay.tsx      # Route visualization
│   │   │   └── MapControls.tsx       # Map interaction controls
│   │   │
│   │   ├── layouts/                  # Layout components
│   │   │   ├── Header.tsx            # Main navigation header
│   │   │   ├── Footer.tsx            # Site footer
│   │   │   ├── Sidebar.tsx           # Dashboard sidebar
│   │   │   └── DashboardTabs.tsx     # Trip dashboard tabs
│   │   │
│   │   └── shared/                   # Shared utility components
│   │       ├── LoadingState.tsx      # Various loading states
│   │       ├── ErrorBoundary.tsx     # Error handling wrapper
│   │       ├── ProgressBar.tsx       # Trip planning progress
│   │       └── NotificationToast.tsx # Success/error notifications
│   │
│   ├── lib/                         # Utility libraries
│   │   ├── api/                     # API client configuration
│   │   │   ├── client.ts            # Axios configuration
│   │   │   ├── auth.ts              # Auth interceptors
│   │   │   ├── types.ts             # API response types
│   │   │   └── endpoints.ts         # API endpoint definitions
│   │   │
│   │   ├── store/                   # State management
│   │   │   ├── auth.ts              # Authentication state
│   │   │   ├── trip.ts              # Trip planning state
│   │   │   ├── ui.ts                # UI state (modals, filters)
│   │   │   └── index.ts             # Store configuration
│   │   │
│   │   ├── utils/                   # Utility functions
│   │   │   ├── formatting.ts        # Price, date formatting
│   │   │   ├── validation.ts        # Form validation helpers
│   │   │   ├── constants.ts         # App constants
│   │   │   ├── travel.ts            # Travel-specific utilities
│   │   │   └── pdf.ts               # PDF export utilities
│   │   │
│   │   ├── hooks/                   # Custom React hooks
│   │   │   ├── useAuth.ts           # Authentication hook
│   │   │   ├── useTrip.ts           # Trip data management
│   │   │   ├── useWebSocket.ts      # Real-time updates
│   │   │   ├── useLocalStorage.ts   # Persistent preferences
│   │   │   └── useMap.ts            # Map interaction hook
│   │   │
│   │   └── types/                   # TypeScript definitions
│   │       ├── api.ts               # API response types
│   │       ├── travel.ts            # Travel domain types
│   │       ├── user.ts              # User-related types
│   │       └── index.ts             # Type exports
│   │
│   ├── styles/                      # Styling
│   │   ├── globals.css              # Global styles and Tailwind
│   │   ├── components.css           # Component-specific styles
│   │   └── animations.css           # Animation utilities
│   │
│   └── __tests__/                   # Tests
│       ├── components/              # Component tests
│       ├── pages/                   # Page tests
│       ├── utils/                   # Utility tests
│       ├── setup.ts                 # Test configuration
│       └── mocks/                   # Mock data and handlers
│
├── public/                          # Static assets
│   ├── images/                      # Travel images and icons
│   ├── icons/                       # App icons and favicons
│   └── locales/                     # i18n JSON files (future)
│
├── .storybook/                      # Storybook configuration
│   ├── main.ts                      # Storybook config
│   └── preview.ts                   # Global story settings
│
├── stories/                         # Component stories
│   ├── components/                  # UI component stories
│   └── pages/                       # Page-level stories
│
├── package.json                     # Dependencies and scripts
├── next.config.js                   # Next.js configuration
├── tailwind.config.js               # Tailwind customization
├── tsconfig.json                    # TypeScript configuration
├── vitest.config.ts                 # Test configuration
├── playwright.config.ts             # E2E test configuration
└── Dockerfile                       # Container configuration
```

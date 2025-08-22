 Master AI Frontend Generation Prompt

  Based on your Travel Companion frontend
  specification, here's a comprehensive,
  copy-paste ready prompt optimized for AI code
  generation tools:

  # Travel Companion Frontend Generation -
  Complete System

  ## PROJECT CONTEXT & TECH STACK

  You are building a Travel Companion web
  application - an AI-powered multi-agent travel
  planning system that creates comprehensive
  itineraries from natural language input. The
  system coordinates flights, hotels, activities,
  restaurants, and budget tracking through an
  intuitive conversational interface.

  **Tech Stack:**
  - Next.js 14+ with TypeScript
  - Tailwind CSS for styling
  - React hooks for state management
  - Mapbox/Google Maps for interactive mapping
  - FastAPI backend with LangGraph multi-agent
  system
  - Supabase for authentication and data storage

  **UI Framework:** Custom design system built on
  Tailwind, emphasizing clean modern aesthetics
  with travel-inspired but professional styling.

  ## HIGH-LEVEL GOAL

  Create a responsive, accessible travel planning
  interface that transforms complex multi-agent AI
   results into an intuitive, visual experience.
  The interface should feel like consulting with a
   knowledgeable travel agent while providing
  transparency into AI reasoning and comprehensive
   comparison tools.

  ## DETAILED STEP-BY-STEP INSTRUCTIONS

  ### 1. Core Layout Structure
  1. Create a responsive layout with sticky header
   navigation
  2. Implement 12-column grid system (24px gutters
   desktop, 16px mobile)
  3. Use Inter font family as primary typeface
  4. Apply the defined color palette: Primary
  #2563eb, Secondary #0ea5e9, Accent #10b981

  ### 2. Natural Language Travel Input Component
  1. Create `TravelInputField` component with
  large, prominent textarea
  2. Include placeholder text: "Where would you
  like to go? (e.g., 'Plan a 5-day family trip to
  Tokyo in March under $4000')"
  3. Add example prompt suggestions below input
  field
  4. Implement auto-expanding textarea with
  character count
  5. Include voice input button (microphone icon)
  for accessibility
  6. Add processing state with loading spinner and
   "AI agents are planning your trip..." message

  ### 3. Results Dashboard Layout
  1. Create tabbed interface with: Overview, Map
  View, Budget, Timeline
  2. Implement filter sidebar with categories:
  Flights, Hotels, Activities, Dining
  3. Design card-based layout for results with
  consistent spacing
  4. Add sort/filter controls: Price, Rating,
  Distance, Duration
  5. Include save/favorite functionality with
  heart icons
  6. Make sidebar collapsible on smaller screens,
  convert to bottom sheet on mobile

  ### 4. Flight Comparison Component
  1. Create `FlightCard` component showing:
  airline, price, duration, stops
  2. Implement sortable table with columns:
  Departure, Arrival, Duration, Price, Airline
  3. Add expandable detail sections showing
  baggage fees, seat selection
  4. Include price trend indicators and
  alternative date suggestions
  5. Design mobile-optimized card stack with swipe
   navigation
  6. Add "Select Flight" buttons that update total
   budget

  ### 5. Interactive Map Integration
  1. Integrate map component with hotel,
  restaurant, and activity markers
  2. Use color-coded pins: Hotels (blue),
  Restaurants (orange), Activities (green)
  3. Implement marker clustering for dense areas
  4. Add day-by-day itinerary overlay with route
  visualization
  5. Create info windows with quick details and
  "Add to Itinerary" buttons
  6. Make map full-screen on mobile with overlay
  controls

  ### 6. Budget Tracking Component
  1. Create real-time budget tracker with visual
  progress bar
  2. Show category breakdown: Flights 40%, Hotels
  35%, Activities 15%, Food 10%
  3. Implement over/under budget visual indicators
   with color coding
  4. Add cost optimization suggestions when over
  budget
  5. Include currency conversion selector with
  live rates
  6. Design mobile-condensed view with expandable
  details

  ### 7. Component States & Interactions
  1. Implement hover states for all interactive
  elements (cards lift slightly)
  2. Add loading skeleton screens for API data
  fetching
  3. Create success animations for booking
  confirmations (checkmark with bounce)
  4. Design error states with clear messaging and
  retry options
  5. Add empty states with helpful guidance for no
   results

  ### 8. Mobile Responsiveness
  1. Stack cards vertically on mobile (< 768px)
  2. Convert sidebar filters to bottom sheet modal
  3. Make map full-screen overlay on mobile
  4. Use larger touch targets (minimum 44px)
  5. Implement swipe gestures for card navigation
  6. Add pull-to-refresh functionality

  ## CODE EXAMPLES & CONSTRAINTS

  **API Integration Pattern:**
  ```typescript
  const planTrip = async (request: string) => {
    const response = await
  fetch('/api/v1/plan-trip', {
      method: 'POST',
      headers: { 'Content-Type':
  'application/json' },
      body: JSON.stringify({ request, user_id:
  user.id })
    });
    return response.json();
  };

  Component Structure Example:
  interface TravelRequest {
    destination: string;
    startDate: Date;
    endDate: Date;
    budget: number;
    travelers: number;
    preferences: string[];
  }

  Styling Constraints:
  - Use Tailwind utility classes exclusively
  - Follow 4px spacing scale (4, 8, 12, 16, 24,
  32, 48, 64px)
  - Maintain WCAG AA contrast ratios (4.5:1
  minimum)
  - All animations under 500ms duration
  - Use system font stack with Inter as primary

  DO NOT:
  - Use any CSS-in-JS libraries or
  styled-components
  - Include external icon libraries beyond
  Heroicons
  - Create overly complex state management (prefer
   React hooks)
  - Add features not specified in the requirements
  - Use deprecated React patterns (class
  components, componentDidMount)

  DEFINE STRICT SCOPE

  Files to Create:
  - components/TravelInputField.tsx - Main travel
  request input
  - components/ResultsDashboard.tsx - Results
  overview and tabs
  - components/FlightCard.tsx - Individual flight
  option display
  - components/BudgetTracker.tsx - Real-time
  budget monitoring
  - components/InteractiveMap.tsx - Map with
  markers and routes
  - pages/index.tsx - Home page layout
  - pages/results.tsx - Results page layout
  - styles/globals.css - Global Tailwind styles

  Files to Leave Untouched:
  - Any existing API routes or backend code
  - Database schema or Supabase configurations
  - Authentication components (unless specified)
  - Any existing utility functions or hooks
  - Package.json dependencies (ask before adding
  new packages)

  Development Priorities:
  1. Mobile-first responsive design
  2. Accessibility compliance (ARIA labels,
  keyboard navigation)
  3. Performance optimization (lazy loading,
  virtualization)
  4. Type safety with TypeScript interfaces
  5. Component reusability and consistency

  Testing Requirements:
  Include basic TypeScript interfaces and prop
  validation. Focus on functional components with
  clear prop types. Ensure all interactive
  elements have appropriate ARIA labels and
  keyboard navigation support.
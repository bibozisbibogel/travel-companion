# Epic 3: Trip Creation & Daily Itinerary Visualization

**Goal:** Create a streamlined, modern minimal interface that allows users to input comprehensive travel preferences, then visualize their complete trip through an elegant day-by-day itinerary with interactive maps, activity scheduling, and budget tracking.

## Story 3.1: Comprehensive Trip Preferences Input

As a **user**,
I want **an intuitive, comprehensive form to specify all my travel preferences**,
so that **the system can create a personalized trip that matches my exact needs**.

**Acceptance Criteria:**
1. Destination input with autocomplete and validation
2. Origin location input with autocomplete
3. Travel date range picker (start date, end date) with calendar interface
4. Number of travelers input with breakdown (adults, children, infants)
5. Budget input with currency type selector (USD, EUR, GBP, etc.)
6. Dietary restrictions multi-select (vegetarian, vegan, gluten-free, halal, kosher, etc.)
7. Accommodation type preferences (hotel, hostel, apartment, resort, etc.)
8. Activity types multi-select (adventure, cultural, relaxation, dining, nightlife, shopping, etc.)
9. Cuisine preferences multi-select (local, international, specific cuisines)
10. Form validation with helpful error messages and field-level feedback
11. Modern minimal design aesthetic with clean layout and clear visual hierarchy
12. Responsive design for desktop and mobile devices
13. Save draft functionality to allow users to return and complete later
14. Clear call-to-action button to generate trip itinerary

## Story 3.2: Day-by-Day Itinerary Timeline Visualization

As a **user**,
I want **to see my complete trip organized by day with a clear timeline**,
so that **I can understand my daily schedule and flow of activities**.

**Acceptance Criteria:**
1. Calendar/timeline view showing all trip days in sequence
2. Each day card displays: date, day of week, daily summary
3. Activities scheduled by time of day (morning, afternoon, evening, night)
4. Activity cards show: name, duration, estimated time, category icon, brief description
5. Meal recommendations integrated into timeline (breakfast, lunch, dinner)
6. Accommodation information displayed for each day (hotel name, location, check-in/out if applicable)
7. Daily budget breakdown showing estimated costs per day
8. Visual indicators for activity types using color coding or icons
9. Expand/collapse functionality for detailed vs. summary views
10. Modern minimal card-based design with clean typography
11. Smooth transitions and animations for expanding/collapsing content
12. Responsive layout adapting to screen size
13. Print-friendly view option

## Story 3.3: Interactive Map with Daily Route Visualization

As a **visual learner**,
I want **to see my daily activities and locations on an interactive map**,
so that **I can understand the geographic layout and optimize travel between locations**.

**Acceptance Criteria:**
1. Interactive map integration (Google Maps) centered on destination
2. Day selector to filter map view by specific day or show entire trip
3. Accommodation markers with hotel name, rating, and price
4. Activity/restaurant pins with category-based color coding and icons
5. Route visualization showing travel paths between locations for each day
6. Clustering for multiple activities in close proximity
7. Pin click/hover reveals activity details: name, time, duration, brief description
8. Distance and estimated travel time between locations
9. Map controls: zoom, pan, fullscreen, map style toggle (standard, satellite)
10. Mobile-friendly touch interactions
11. Modern minimal map styling consistent with overall design
12. Legend showing activity category colors/icons
13. Current day highlight when viewing timeline

## Story 3.4: Budget Overview & Real-time Tracking

As a **budget-conscious traveler**,
I want **clear visibility into my trip costs with real-time budget tracking**,
so that **I can ensure my trip stays within my financial limits**.

**Acceptance Criteria:**
1. Total trip budget vs. estimated cost comparison with visual progress bar
2. Category breakdown: flights, accommodation, activities, dining, transportation, misc.
3. Daily budget allocation showing cost distribution across trip days
4. Currency display matching user's selected currency type
5. Visual indicators (green/yellow/red) for budget status (under/at/over budget)
6. Cost optimization suggestions when over budget
7. Ability to adjust budget and see updated recommendations
8. Modern minimal design with clear data visualization
9. Mobile-responsive budget cards and charts

## Story 3.5: User Trip List Dashboard ✅ COMPLETED

As a **returning user**,
I want **to see a list of all my trips after logging in**,
so that **I can quickly access my past and planned trips**.

**Acceptance Criteria:**
1. Display list of all user trips after successful login
2. Each trip card shows: trip name, destination, dates, status, and thumbnail/preview
3. Trips sorted by creation date (most recent first)
4. Pagination support for users with many trips (20 trips per page)
5. Filter trips by status (draft, planning, confirmed, completed, cancelled)
6. Search trips by destination or trip name
7. Click on trip card navigates to trip detail page
8. Empty state message when user has no trips with call-to-action to create first trip
9. Loading state while fetching trips from API
10. Error handling with retry functionality if API call fails
11. Modern minimal card-based design consistent with app aesthetic
12. Mobile-responsive grid layout (1 column mobile, 2-3 columns tablet/desktop)

**Status:** ✅ All acceptance criteria completed and tested

**Implementation Highlights:**
- Migrated itinerary page to dynamic route `/trips/[trip_id]`
- Created comprehensive trip list dashboard at `/trips`
- Implemented TripCard, Pagination, and EmptyState reusable components
- Integrated with backend API endpoint `GET /api/v1/trips`
- Added client-side filtering by status and search functionality
- All 34 unit and integration tests passing
- Responsive design with Tailwind CSS grid layout

## Story 3.6: Geocoding Integration for Precise Activity Location Mapping

As a **user viewing trip itineraries**,
I want **activities, accommodations, restaurants, and other locations to appear at their precise geographic coordinates on the map**,
so that **I can accurately understand distances, travel times, and geographic relationships between all trip elements**.

**Acceptance Criteria:**
1. Integrate Google Geocoding API in backend for converting location strings to lat/lng coordinates
2. Geocode all location types during trip generation: activities, accommodations, restaurants, airports, destination city
3. Store geocoded coordinates (latitude, longitude) in database with each location entity
4. Handle geocoding API errors gracefully with fallback behavior
5. Display warning/placeholder marker on map for locations that failed geocoding
6. Return geocoded coordinates in trip API responses for frontend consumption
7. Update InteractiveMap component to use precise coordinates instead of placeholder locations
8. Implement rate limiting and error handling for Google Geocoding API calls
9. Add geocoding retry logic for transient failures
10. Log geocoding failures for monitoring and debugging
11. Include geocoding status field in location data (success, failed, pending)
12. Update data models to include coordinate fields (latitude, longitude, geocoding_status)

**Technical Requirements:**
- **Backend Integration:** Server-side geocoding during trip generation workflow
- **Caching Strategy:** Store geocoded coordinates permanently in database with location entities
- **Error Handling:** Show placeholder/warning marker on map when geocoding fails
- **Scope:** All location types (activities, accommodations, restaurants, airports, destination city)
- **API Configuration:** Use Google Geocoding API with proper authentication and rate limiting
- **Database Schema:** Add latitude, longitude, geocoding_status fields to relevant tables

**Dependencies:**
- Google Geocoding API key configured in backend environment
- Database schema updates for coordinate storage
- Story 3.3 (Interactive Map) completed for map integration

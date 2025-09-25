An AI-powered multi-agent travel planner that helps users plan trips end-to-end: flights, hotels, food, and activities. The assistant uses LangGraph for multi-step reasoning and tool orchestration, with a Python backend exposing APIs and integrating with travel and payment providers.

# Ownership

## David
- "weather_agent"
- "flight_agent"

## Cristi
- "hotel_agent"
- "activity_agent"

## Mihai
- "food_agent"
- "itinerary_agent"

# Testing APIs
Some pytest tests run live API calls and consume credits. 
Use the RUN_EXTERNAL_API_TESTS environment variable to control their execution.
Tests will skip unless this variable is set to "true".

Example: `RUN_EXTERNAL_API_TESTS=true uv run pytest`

# Standalone tests (not part of pytest)
These are tests that can be run to test individual API calls. They are located in a separate folder 'src/test_api'. They must be run from the 'packages/api' folder.

Example: `uv run python src/test_api/test_google_places.py`

# Quick start
  ./scripts/setup.sh      # Initial setup
  ./scripts/dev.sh        # Start development environment  
  ./scripts/test.sh       # Run all tests

  Services available at:
  - 📡 API: http://localhost:8000 (with /docs)
  - 🖥️ Frontend: http://localhost:3000
  - ❤️ Health Check: http://localhost:8000/api/v1/health

# How It Works (Workflow)

User submits request → “7-day trip to Tokyo, budget $2000, focus on food + culture.”

1. LangGraph workflow kicks off:
- Planner Agent parses request
- **Flight Agent → fetches flights ✅ IMPLEMENTED**
  - Searches Amadeus API with circuit breaker protection
  - Compares options using weighted algorithm (price, duration, timing)
  - Provides fallback mock data during API outages
- Hotel Agent → fetches hotels (coming soon)
- Activity Agent → fetches activities (coming soon)
- Weather Agent → fetches weather (coming soon)  
- Food Agent → suggests restaurants (coming soon)
- Itinerary Agent → integrates results and builds schedule (coming soon)
- Final Planner compiles everything into a daily itinerary + budget summary.
- Returns JSON to frontend which displays it in a user-friendly way.

2. Frontend displays:
- Map with itinerary
- Flights: sorted options
- Hotels: top 3 recommendations
- Food: curated list of restaurants
- Itinerary: calendar-style view
- Budget: chart comparing target vs. actual
- Export to PDF for offline use.

# User personas

- Solo Traveler: Budget-conscious, flexible dates.
- Family Planner: Fixed dates, comfort requirements, child-friendly.
- Business Traveler: Tight schedules, loyalty preferences, invoice compliance.

# Tech Stack

## Backend
- Python 3.11+
- LangGraph (workflow engine)
- LangChain (LLM integration if needed for reasoning/explanation)
- FastAPI (expose workflow as REST API)

## Frontend
- Next.js
- React + Tailwind CSS
- TypeScript
- Mapbox or Google Maps API (visualizing itineraries)

## APIs / Data Sources
- Flights: Amadeus API / Skyscanner API
- Hotels: Booking.com / Expedia API / Airbnb / Hotels APIs
- Food & Places: Yelp / Zomato / Google Places API
- Activities: TripAdvisor / Viator / GetYourGuide API
- Maps: Google Maps Directions API or OpenStreetMap

## Database
- Supabase → store user travel plans, preferences, past itineraries, vector embeddings for RAG
- Redis → cache API results (avoid hitting rate limits)

## Other Tools
- Docker (containerize backend)
- GitHub Projects + Issues (team collaboration)

# Implementation Status

## ✅ Completed Features

### Flight Agent & API Integration (Story 2.1)
- **FlightAgent**: AI-powered flight search with Amadeus API integration
- **Circuit Breaker Pattern**: Resilient external API calls with automatic failover  
- **Smart Flight Comparison**: Weighted ranking algorithm (price, duration, timing, stops)
- **Comprehensive Testing**: 90%+ code coverage with unit, integration, and resilience tests
- **Mock Data Fallback**: Graceful degradation during API outages
- **Rate Limit Management**: Automatic throttling and Redis caching optimization

## 🔄 In Progress
- Story 2.2: Additional agent implementations (Hotels, Activities, Weather)
- LangGraph workflow orchestration
- Frontend integration with trip planning interface

## 📋 Upcoming
- User authentication and profile management
- Trip persistence and history
- Payment integration for booking
- Mobile-responsive frontend
- Real-time notifications

# Technical Documentation

- **API Documentation**: `/packages/api/API.md` - Complete API specification
- **Architecture Guide**: `/packages/api/ARCHITECTURE.md` - Technical implementation details  
- **Setup Instructions**: `/packages/api/README.md` - Development environment setup

# GitHub repo
/frontend (Next.js + React)
/packages/api (FastAPI + LangGraph + AI Agents)
/docs (Architecture and story documentation)

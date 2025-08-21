An AI-powered multi-agent travel planner that helps users plan trips end-to-end: flights, hotels, food, and activities. The assistant uses LangGraph for multi-step reasoning and tool orchestration, with a Python backend exposing APIs and integrating with travel and payment providers.

# How It Works (Workflow)

User submits request → “7-day trip to Tokyo, budget $2000, focus on food + culture.”

1. LangGraph workflow kicks off:
- Planner Agent parses request
- Flight Agent → fetches flights
- Hotel Agent → fetches hotels
- Activity Agent → fetches activities
- Weather Agent → fetches weather
- Food Agent → suggests restaurants
- Itinerary Agent → integrates results and builds schedule
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

# GitHub repo
/frontend (Next.js + React)
/backend (FastAPI + LangGraph)
/agents (each agent’s logic)

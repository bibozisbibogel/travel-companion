# Travel Companion

An AI-powered travel planner that uses multi-agent orchestration to generate full trip itineraries — covering flights, hotels, restaurants, activities, and weather — with interactive maps and budget tracking.

## How It Works

The user submits trip preferences (destination, dates, budget, travel style) and the system coordinates multiple specialized AI agents in parallel:

- **Flight Agent** — searches Amadeus API, ranks options by price, duration, and stops
- **Hotel Agent** — finds accommodations via Google Places API
- **Food Agent** — recommends restaurants based on cuisine preferences and location
- **Activity Agent** — suggests attractions and things to do
- **Weather Agent** — fetches forecasts for each day of the trip

All agents run through a central planner built with the **Claude Agent SDK** and exposed via an **MCP server**, returning a day-by-day itinerary with route visualization and a full budget breakdown.

## Tech Stack

**Backend**
- Python 3.11+, FastAPI, Uvicorn
- Claude Agent SDK (multi-agent orchestration)
- MCP Server (tool exposure)
- PostgreSQL (trip persistence), Redis (caching & rate limiting)
- Amadeus API (flights), Google Places API (hotels & restaurants), Geoapify (routing & maps), OpenWeather API (forecasts)

**Frontend**
- Next.js 14, React, TypeScript, Tailwind CSS
- Interactive map with day-by-day route visualization

**Infrastructure**
- Docker, Docker Compose
- Terraform (infrastructure as code)

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- API keys (see below)

### 1. Clone the repo

```bash
git clone https://github.com/bibozisbibogel/travel-companion.git
cd travel-companion
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Fill in the required API keys in `.env`:

| Variable | Where to get it |
|----------|----------------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `AMADEUS_CLIENT_ID` / `AMADEUS_CLIENT_SECRET` | [developers.amadeus.com](https://developers.amadeus.com) |
| `GOOGLE_PLACES_API_KEY` | [console.cloud.google.com](https://console.cloud.google.com) |
| `GEOAPIFY_API_KEY` | [geoapify.com](https://www.geoapify.com) |
| `OPENWEATHER_API_KEY` | [openweathermap.org](https://openweathermap.org/api) |
| `DATABASE_URL` | Local PostgreSQL or Supabase |
| `REDIS_URL` | Local Redis or managed instance |

### 3. Start with Docker (recommended)

```bash
docker-compose up --build
```

Services will be available at:
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

### 4. Start manually (without Docker)

**Backend:**
```bash
cd packages/api
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.travel_companion.main:app --reload --port 8000
```

**Frontend:**
```bash
cd packages/web
npm install
npm run dev
```

## Project Structure

```
travel-companion/
├── packages/
│   ├── api/                    # FastAPI backend
│   │   └── src/travel_companion/
│   │       ├── agents_sdk/     # Multi-agent orchestration
│   │       │   ├── travel_planner_agent.py
│   │       │   ├── mcp_server.py
│   │       │   └── tools/      # Flight, hotel, food, activity, weather tools
│   │       ├── api/            # REST API routes
│   │       └── models/         # Database models
│   └── web/                    # Next.js frontend
├── docker-compose.yml
├── .env.example
└── scripts/
    ├── setup.sh
    ├── dev.sh
    └── test.sh
```

## Running Tests

```bash
cd packages/api
# Unit tests only (no external API calls)
uv run pytest

# Include live API tests (consumes credits)
RUN_EXTERNAL_API_TESTS=true uv run pytest
```

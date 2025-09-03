# Travel Companion API

FastAPI backend service for the Travel Companion application with AI-powered flight search and comparison capabilities.

## Features

- FastAPI-based REST API with comprehensive flight search capabilities
- **Flight Agent Integration**: AI-powered flight search with Amadeus API integration
- **Circuit Breaker Pattern**: Resilient external API calls with automatic failover
- **Flight Comparison Engine**: Sophisticated ranking algorithm based on price, duration, and preferences
- Health check endpoints with dependency monitoring
- Environment configuration management
- Redis caching for API optimization
- Docker containerization support
- Comprehensive testing setup with 90%+ coverage

## Development

### Setup
```bash
# From project root
./scripts/setup.sh

# Or manually for API only
cd packages/api
uv sync --dev
```

### Running
```bash
# From project root
./scripts/dev.sh --service api

# Or manually
cd packages/api
source ../../.venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
uv run uvicorn travel_companion.main:app --reload
```

### Testing
```bash
# From project root
./scripts/test.sh --suite api

# Or manually
cd packages/api
source ../../.venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
uv run pytest
```

## API Endpoints

### Core Endpoints
- `GET /` - Root endpoint
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed health check with dependencies
- `GET /docs` - Interactive API documentation (development only)

### Trip Management
- `POST /api/v1/trips/plan` - Generate comprehensive travel plan with flights, hotels, and activities
- `POST /api/v1/trips/` - Create a new trip
- `GET /api/v1/trips/` - List user trips (paginated)
- `GET /api/v1/trips/{trip_id}` - Get trip details
- `PUT /api/v1/trips/{trip_id}` - Update trip
- `DELETE /api/v1/trips/{trip_id}` - Delete trip

### User Management
- `POST /api/v1/users/register` - User registration
- `POST /api/v1/users/login` - User authentication
- `GET /api/v1/users/profile` - Get user profile
- `PUT /api/v1/users/profile` - Update user profile

## Architecture

The API follows a modular structure with implemented AI agents:

- `core/` - Configuration, database, Redis connections
- `api/` - FastAPI routers and endpoints
- `models/` - Pydantic data models including external API schemas
- `agents/` - **LangGraph AI agents (FlightAgent implemented)**
  - `base.py` - Base agent class with dependency injection
  - `flight_agent.py` - Flight search and comparison agent
- `workflows/` - LangGraph workflows (future implementation)
- `services/` - **External API integrations (Amadeus implemented)**
  - `external_apis/amadeus.py` - Amadeus Travel API client
- `utils/` - Utility functions including circuit breaker pattern

## Key Components

### FlightAgent
- **Flight Search**: Integration with Amadeus API for real-time flight data
- **Smart Comparison**: Weighted ranking algorithm (40% price, 30% duration, 20% departure time, 10% stops)
- **Resilience**: Circuit breaker pattern with automatic failover to mock data
- **Caching**: Redis integration to optimize API usage and respect rate limits

### CircuitBreaker
- **Fault Tolerance**: Prevents cascading failures from external API outages
- **Auto-Recovery**: Configurable thresholds with automatic service recovery testing
- **Monitoring**: Detailed logging and metrics for system reliability

### Amadeus API Integration
- **OAuth 2.0**: Secure authentication with client credentials flow
- **Rate Limiting**: Respects API limits (10 requests/second, 1000/month)
- **Error Handling**: Comprehensive error scenarios with exponential backoff

## Configuration

### Environment Setup

Copy `.env.example` to `.env` and configure the following:

```bash
# Required for Flight Agent functionality
AMADEUS_CLIENT_ID=your-amadeus-client-id
AMADEUS_CLIENT_SECRET=your-amadeus-client-secret

# Required for caching and performance
REDIS_URL=redis://localhost:6379

# Database connection
DATABASE_URL=postgresql://user:pass@localhost:5432/travel_companion
```

### Amadeus API Setup

1. **Create Account**: Sign up at [Amadeus Developers](https://developers.amadeus.com/)
2. **Get Credentials**: Create a new application to get your Client ID and Secret
3. **Test Environment**: Use the test API initially (included in free tier)
4. **Rate Limits**: Free tier provides 10 requests/second, 1000 requests/month

### Development Dependencies

Required services for full functionality:

```bash
# Start Redis (for caching)
docker run -d -p 6379:6379 redis:alpine

# Start PostgreSQL (for data persistence)
docker run -d -p 5432:5432 -e POSTGRES_USER=travel_user -e POSTGRES_PASSWORD=travel_password -e POSTGRES_DB=travel_companion postgres:15

# Or use Docker Compose from project root
docker-compose up -d redis postgres
```

## Testing

### Unit Tests
The implementation includes comprehensive test coverage:

```bash
# Run all tests
uv run pytest

# Run flight agent tests specifically  
uv run pytest src/tests/test_agents/ -v

# Run with coverage report
uv run pytest --cov=src --cov-report=html
```

### Test Features
- **Circuit Breaker Testing**: All states and failure scenarios
- **API Integration Testing**: Mock Amadeus API responses
- **Flight Comparison Testing**: Ranking algorithms and edge cases
- **Error Handling Testing**: Timeout, rate limiting, and fallback scenarios
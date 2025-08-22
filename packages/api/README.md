# Travel Companion API

FastAPI backend service for the Travel Companion application.

## Features

- FastAPI-based REST API
- Health check endpoints
- Environment configuration management
- Docker containerization support
- Comprehensive testing setup

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

- `GET /` - Root endpoint
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed health check with dependencies
- `GET /docs` - Interactive API documentation (development only)

## Architecture

The API follows a modular structure:

- `core/` - Configuration, database, Redis connections
- `api/` - FastAPI routers and endpoints
- `models/` - Pydantic data models
- `agents/` - LangGraph AI agents (future implementation)
- `workflows/` - LangGraph workflows (future implementation)
- `services/` - External API integrations
- `utils/` - Utility functions

## Configuration

See `.env.example` in the project root for required environment variables.
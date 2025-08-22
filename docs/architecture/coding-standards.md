# Coding Standards

## Core Standards
- **Languages & Runtimes:** Python 3.11+, TypeScript 5.3+, strict type checking enabled
- **Style & Linting:** Ruff for Python (Black-compatible), ESLint + Prettier for TypeScript
- **Test Organization:** Tests adjacent to source code, pytest for Python, Vitest for TypeScript

## Naming Conventions
| Element | Convention | Example |
|---------|------------|---------|
| **Python Classes** | PascalCase | `FlightAgent`, `TripPlanningWorkflow` |
| **Python Functions** | snake_case | `search_flights`, `calculate_budget` |
| **TypeScript Interfaces** | PascalCase with I prefix | `IFlightOption`, `ITripRequest` |
| **API Endpoints** | kebab-case | `/api/v1/trips/search-flights` |
| **Database Tables** | snake_case | `flight_options`, `user_preferences` |

## Critical Rules
- **Never log sensitive data:** No API keys, passwords, or PII in logs - use structured logging with redaction
- **All external API calls must use circuit breakers:** Prevent cascade failures from travel API outages
- **Database queries must use repository pattern:** Never direct ORM calls from API handlers
- **All async operations require timeout:** Prevent hanging requests from external services
- **API responses must use standardized wrapper:** Consistent response format with status, data, and error fields

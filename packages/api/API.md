# Travel Companion API Specification

## Authentication

All endpoints (except health checks) require JWT authentication:

```bash
Authorization: Bearer <jwt-token>
```

Obtain tokens via `/api/v1/users/login` endpoint.

## Flight Search Integration

The Flight Agent is integrated into the trip planning workflow. When you create a trip plan, it automatically includes flight searches via the Amadeus API.

### Flight Search Request Model

```json
{
  "origin": "JFK",
  "destination": "CDG", 
  "departure_date": "2024-06-01T00:00:00Z",
  "return_date": "2024-06-08T00:00:00Z",
  "passengers": 2,
  "travel_class": "ECONOMY",
  "currency": "USD",
  "max_results": 50
}
```

### Flight Search Response Model

```json
{
  "status": "success",
  "data": {
    "flights": [
      {
        "flight_id": "uuid-string",
        "external_id": "amadeus-offer-123",
        "airline": "Air France",
        "flight_number": "AF1234",
        "price": 599.99,
        "currency": "USD",
        "departure_time": "2024-06-01T10:30:00Z",
        "arrival_time": "2024-06-01T23:45:00Z", 
        "duration_minutes": 495,
        "stops": 0,
        "origin": "JFK",
        "destination": "CDG",
        "booking_url": "https://amadeus.booking-url",
        "comparison_result": {
          "rank": 1,
          "total_score": 8.5,
          "price_score": 9.0,
          "duration_score": 8.0,
          "departure_time_score": 8.5,
          "stops_score": 10.0,
          "reasoning": "Direct flight with good morning departure time"
        }
      }
    ],
    "search_metadata": {
      "total_results": 15,
      "search_time_ms": 1250,
      "amadeus_api_used": true,
      "cache_hit": false
    }
  },
  "error": null
}
```

## API Endpoints

### Trip Planning with Flight Search

**POST /api/v1/trips/plan**

Generate a comprehensive travel plan including flight options.

```bash
curl -X POST "http://localhost:8000/api/v1/trips/plan" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": {
      "city": "Paris",
      "country": "France", 
      "country_code": "FR",
      "airport_code": "CDG"
    },
    "requirements": {
      "budget": 2000.00,
      "currency": "USD",
      "start_date": "2024-06-01",
      "end_date": "2024-06-08", 
      "travelers": 2,
      "travel_class": "ECONOMY"
    }
  }'
```

**Response**: Includes flight options ranked by the Flight Agent's algorithm.

### Trip Management

**POST /api/v1/trips/**
Create a new trip (without immediate planning).

**GET /api/v1/trips/**
List user trips with pagination.

**GET /api/v1/trips/{trip_id}**
Get specific trip details.

**PUT /api/v1/trips/{trip_id}** 
Update trip information.

**DELETE /api/v1/trips/{trip_id}**
Delete a trip and all associated data.

## Error Responses

### Standard Error Format

```json
{
  "status": "error",
  "data": null,
  "error": {
    "message": "Flight search temporarily unavailable",
    "error_code": "EXTERNAL_API_ERROR",
    "details": {
      "service": "amadeus",
      "circuit_breaker_state": "open",
      "fallback_used": true
    }
  }
}
```

### Common Error Codes

- `VALIDATION_ERROR`: Request validation failed
- `EXTERNAL_API_ERROR`: External API service issue  
- `CIRCUIT_BREAKER_OPEN`: Service temporarily unavailable
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `TRIP_NOT_FOUND`: Trip ID does not exist
- `AUTHENTICATION_REQUIRED`: Missing or invalid JWT token

## Rate Limiting

### External API Limits
- **Amadeus API**: 10 requests/second, 1000 requests/month
- **Circuit Breaker**: Opens after 3 consecutive failures
- **Recovery**: Automatic retry after 30 seconds

### Caching Behavior
- Flight search results cached for 5 minutes
- Cache keys based on search parameters hash
- Cache miss triggers new API call (if circuit allows)

## Health Monitoring

**GET /api/v1/health**
Basic API health check.

**GET /api/v1/health/detailed**
Detailed health including external dependencies:

```json
{
  "status": "healthy",
  "data": {
    "api": "healthy",
    "database": "healthy", 
    "redis": "healthy",
    "amadeus_circuit_breaker": "closed",
    "version": "0.1.0",
    "uptime_seconds": 3600
  }
}
```

## Development and Testing

### Mock Data Mode
When Amadeus API is unavailable or in development:

```bash
# Environment variable to force mock data
AMADEUS_CLIENT_ID=""
AMADEUS_CLIENT_SECRET=""
```

The system automatically falls back to realistic mock flight data for development and testing.

### Test Data
The API includes comprehensive test fixtures with realistic flight offers matching the Amadeus API response format.

---

For detailed implementation examples and integration guides, see the main repository documentation.
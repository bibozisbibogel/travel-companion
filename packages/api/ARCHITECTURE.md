# Travel Companion API Architecture

## Overview

The Travel Companion API is built using FastAPI with a modular, agent-based architecture designed for scalable travel planning services. The system integrates multiple external APIs through resilient agent patterns and provides comprehensive flight search capabilities.

## Core Architecture Patterns

### Agent Pattern
The system uses specialized agents for different travel planning domains:

- **BaseAgent**: Abstract base providing dependency injection, caching, health checks
- **FlightAgent**: Handles flight search, comparison, and ranking operations

### Circuit Breaker Pattern
Implements fault tolerance for external API integrations:

- **Failure Threshold**: Configurable failure count before circuit opens
- **Recovery Testing**: Automatic half-open state testing 
- **Fallback Mechanisms**: Graceful degradation to mock data

### Repository Pattern
Consistent data access layer with entity-specific naming:

- **Entity-specific primary keys**: `flight_id`, `trip_id`, etc.
- **Auto-derivation**: Table names derived from model classes
- **Standardized relationships**: Clear foreign key patterns

## Flight Agent Implementation

### Core Features

```python
class FlightAgent(BaseAgent[FlightSearchResponse]):
    """Agent responsible for flight search and comparison operations."""
    
    # Circuit breaker protection for API calls
    # Weighted ranking algorithm (price 40%, duration 30%, timing 20%, stops 10%)
    # Redis caching for rate limit optimization
    # Fallback to realistic mock data
```

### Search Algorithm

1. **Input Validation**: Airport codes, dates, passenger counts
2. **API Integration**: Amadeus OAuth 2.0 with rate limiting
3. **Result Processing**: Parse and normalize flight offers
4. **Intelligent Ranking**: Multi-factor scoring algorithm
5. **Response Caching**: Redis optimization for repeated searches

### Ranking Criteria

- **Price Weight (40%)**: Lower prices score higher
- **Duration Weight (30%)**: Shorter flights preferred  
- **Departure Time Weight (20%)**: Morning flights prioritized
- **Stops Weight (10%)**: Direct flights receive bonus

## External API Integration

### Amadeus Travel API

```python
class AmadeusClient:
    """OAuth 2.0 authenticated client for Amadeus Travel API."""
    
    # Authentication: Client credentials flow
    # Rate limiting: 10 requests/second, 1000/month  
    # Endpoints: /shopping/flight-offers
    # Error handling: 429 responses with exponential backoff
```

**Configuration Requirements:**
- `AMADEUS_CLIENT_ID`: Application client ID
- `AMADEUS_CLIENT_SECRET`: Application client secret
- Rate limiting handled automatically with semaphore throttling

### Error Handling Strategy

```python
# Custom exception hierarchy
class ExternalAPIError(Exception): ...
class RateLimitError(ExternalAPIError): ...
class CircuitBreakerOpenError(Exception): ...

# Circuit breaker protection
@circuit_breaker.call
async def search_flights(...):
    # Protected external API call
```

## Data Models

### Flight Data Schema

```python
class FlightOption(BaseModel):
    flight_id: UUID = Field(default_factory=uuid4)
    airline: str = Field(..., min_length=1, max_length=100)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int = Field(..., gt=0)
    stops: int = Field(default=0, ge=0)
```

### Amadeus API Models

```python
class AmadeusFlightOffer(BaseModel):
    # Direct mapping to Amadeus API response structure
    # Handles complex nested itinerary data
    # Price conversion to decimal precision
```

## Testing Strategy

### Test Coverage Areas

1. **Unit Tests**: Individual component testing with mocks
   - Flight agent logic (26 test cases)
   - Circuit breaker states (13 test cases) 
   - API client functionality (17 test cases)

2. **Integration Tests**: Multi-component interactions
   - Database operations with test containers
   - Redis caching behavior
   - External API mock responses

3. **Resilience Testing**: Failure scenario validation
   - Circuit breaker state transitions
   - API timeout handling
   - Rate limit response processing

### Test Fixtures

```python
# Realistic flight data for testing
@pytest.fixture
def sample_flight_offers():
    return [
        {
            "id": "amadeus-offer-123",
            "price": {"total": "299.99", "currency": "USD"},
            "itineraries": [...],  # Complex nested structure
        }
    ]
```

## Performance Considerations

### Caching Strategy
- **Redis Integration**: Flight search results cached by request hash
- **TTL Management**: Appropriate cache expiration for price-sensitive data
- **Rate Limit Optimization**: Minimize external API calls

### Asynchronous Operations
- **AsyncIO Integration**: Non-blocking external API calls
- **Concurrent Processing**: Multiple flight option processing
- **Timeout Management**: 30-second default timeout for external calls

## Security Implementation

### API Security
- **Input Validation**: Pydantic models with strict validation
- **Environment Variables**: Secure credential management
- **Rate Limiting**: Protection against abuse

### Error Information
- **Structured Logging**: Detailed error context without sensitive data
- **Exception Sanitization**: Clean error messages for API responses
- **Circuit Breaker Monitoring**: System health visibility

## Deployment Considerations

### Environment Configuration
```bash
# Production readiness checklist
AMADEUS_CLIENT_ID=prod-client-id
AMADEUS_CLIENT_SECRET=secure-secret
REDIS_URL=redis://production-host:6379
DATABASE_URL=postgresql://prod-connection
```

### Monitoring Requirements
- Circuit breaker state monitoring
- External API response time tracking  
- Cache hit rate analysis
- Error rate alerting

## Future Enhancements

### Planned Additions
1. **Hotel Agent**: Similar pattern for accommodation search
2. **Activity Agent**: Attraction and experience recommendations  
3. **Weather Agent**: Destination weather integration
4. **LangGraph Workflows**: Multi-agent orchestration

### Scalability Improvements
- **Database Connection Pooling**: Handle increased load
- **API Response Pagination**: Large result set handling
- **Distributed Caching**: Multi-instance cache coordination
- **Load Balancing**: Horizontal scaling preparation

---

This architecture provides a solid foundation for expanding travel planning capabilities while maintaining reliability, performance, and maintainability standards.
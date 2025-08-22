# Error Handling Strategy

## General Approach
- **Error Model:** Structured exceptions with correlation IDs and context
- **Exception Hierarchy:** Custom domain exceptions inheriting from base TravelPlanningError
- **Error Propagation:** Fail-fast with graceful degradation for non-critical services

## Logging Standards
- **Library:** structlog 23.2+ with JSON formatting
- **Format:** Structured JSON logs with correlation IDs and request context
- **Levels:** DEBUG (development), INFO (business events), WARNING (degraded service), ERROR (failures), CRITICAL (system down)
- **Required Context:**
  - Correlation ID: UUID per request for tracing
  - Service Context: Service name, version, instance ID
  - User Context: User ID (hashed), trip ID, no PII in logs

## Error Handling Patterns

### External API Errors
- **Retry Policy:** Exponential backoff with jitter, max 3 retries
- **Circuit Breaker:** 50% failure rate threshold, 30-second recovery window
- **Timeout Configuration:** 10s for search APIs, 30s for booking APIs
- **Error Translation:** Map API errors to user-friendly messages with fallback options

### Business Logic Errors
- **Custom Exceptions:** `FlightNotFoundError`, `BudgetExceededError`, `InvalidDatesError`
- **User-Facing Errors:** Structured error responses with actionable suggestions
- **Error Codes:** Consistent error code system for frontend handling

### Data Consistency
- **Transaction Strategy:** Database transactions for multi-table operations
- **Compensation Logic:** Saga pattern for distributed operations across APIs
- **Idempotency:** Request idempotency keys for safe retries

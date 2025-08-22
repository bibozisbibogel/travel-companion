# Test Strategy and Standards

## Testing Philosophy
- **Approach:** Test-Driven Development with comprehensive coverage for critical paths
- **Coverage Goals:** 90%+ for business logic, 70%+ overall, 100% for external API integrations
- **Test Pyramid:** 70% unit tests, 20% integration tests, 10% end-to-end tests

## Test Types and Organization

### Unit Tests
- **Framework:** pytest 7.4+ with async support
- **File Convention:** `test_*.py` adjacent to source files
- **Location:** `tests/unit/` mirrors source structure
- **Mocking Library:** pytest-mock with httpx-mock for API calls
- **Coverage Requirement:** 90% for agent logic and business rules

**AI Agent Requirements:**
- Generate tests for all public methods with edge cases
- Cover error conditions and timeout scenarios  
- Follow AAA pattern (Arrange, Act, Assert)
- Mock all external dependencies including Redis and database

### Integration Tests
- **Scope:** Multi-component interactions including database and Redis
- **Location:** `tests/integration/` with Docker test containers
- **Test Infrastructure:**
  - **Database:** Testcontainers PostgreSQL with test data fixtures
  - **Cache:** Testcontainers Redis for caching integration tests
  - **External APIs:** WireMock for stubbing travel APIs with realistic responses

### End-to-End Tests
- **Framework:** Playwright for web UI testing
- **Scope:** Complete user workflows from request to itinerary generation
- **Environment:** Staging environment with test data
- **Test Data:** Synthetic test accounts with predictable travel scenarios

## Test Data Management
- **Strategy:** Factory pattern with realistic travel data fixtures
- **Fixtures:** JSON fixtures for API responses stored in `tests/fixtures/`
- **Factories:** Faker-based factories for generating test users and trips
- **Cleanup:** Automatic test data cleanup with database transactions

## Continuous Testing
- **CI Integration:** GitHub Actions with parallel test execution
- **Performance Tests:** API response time validation <30s for planning workflows
- **Security Tests:** SAST scanning with Bandit, dependency vulnerability scanning

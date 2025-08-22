# Security

## Input Validation
- **Validation Library:** Pydantic v2 with custom validators for travel-specific data
- **Validation Location:** API boundary validation before workflow execution
- **Required Rules:**
  - All external inputs MUST be validated with strict schemas
  - Travel dates must be future dates with reasonable limits (max 2 years)
  - Budget amounts must be positive with currency validation

## Authentication & Authorization
- **Auth Method:** JWT tokens with Supabase Auth integration
- **Session Management:** Stateless JWT with refresh token rotation
- **Required Patterns:**
  - All trip data access requires valid user authentication
  - Row-level security policies prevent cross-user data access
  - API key rotation for external service authentication

## Secrets Management
- **Development:** .env files with example templates (never committed)
- **Production:** AWS Parameter Store for API keys and database credentials
- **Code Requirements:**
  - NEVER hardcode API keys or secrets
  - Access via Pydantic Settings configuration only
  - No secrets in logs, error messages, or API responses

## API Security
- **Rate Limiting:** Redis-based rate limiting per user and IP address
- **CORS Policy:** Restrictive CORS for production, localhost allowed in development
- **Security Headers:** HSTS, CSP, X-Frame-Options via middleware
- **HTTPS Enforcement:** TLS 1.3 minimum, HTTPS redirect in production

## Data Protection
- **Encryption at Rest:** Database encryption via Supabase/PostgreSQL
- **Encryption in Transit:** TLS 1.3 for all external communications
- **PII Handling:** No PII storage beyond email/name, travel preferences anonymized
- **Logging Restrictions:** No personal data, API keys, or booking details in logs

## Dependency Security
- **Scanning Tool:** UV with safety integration for Python, npm audit for TypeScript
- **Update Policy:** Monthly security updates, critical patches within 48 hours
- **Approval Process:** Security review required for new external dependencies

## Security Testing
- **SAST Tool:** Bandit for Python static analysis, ESLint security rules for TypeScript
- **DAST Tool:** OWASP ZAP integration in staging environment
- **Penetration Testing:** Annual third-party security assessment

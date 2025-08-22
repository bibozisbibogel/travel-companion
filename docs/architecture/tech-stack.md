# Tech Stack

## Cloud Infrastructure
- **Provider:** Initially local/Docker, designed for AWS deployment
- **Key Services:** ECS/Fargate for containerized services, ElastiCache for Redis, RDS for Supabase
- **Deployment Regions:** US-East-1 primary, EU-West-1 for international users

## Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| **Language** | Python | 3.11+ | Backend development | Async support, LangGraph compatibility, rich AI/ML ecosystem |
| **Backend Framework** | FastAPI | 0.104+ | API orchestration | High performance, excellent OpenAPI docs, async native |
| **Workflow Engine** | LangGraph | 0.0.40+ | Multi-agent orchestration | Purpose-built for AI agent workflows, state management |
| **Frontend Framework** | Next.js | 14.1+ | Web application | React-based, excellent TypeScript support, SSR capabilities |
| **Language** | TypeScript | 5.3+ | Frontend development | Type safety, excellent tooling, team consistency |
| **Database** | Supabase | Latest | User data & vector embeddings | PostgreSQL with built-in auth, real-time, vector support |
| **Caching** | Redis | 7.2+ | API caching & rate limiting | High performance, pub/sub for real-time updates |
| **Container Platform** | Docker | 24.0+ | Development & deployment | Consistent environments, easy scaling |
| **Process Manager** | UV | 0.1.15+ | Python dependency management | Blazing fast, Rust-based, modern Python tooling |
| **Styling** | Tailwind CSS | 3.4+ | Frontend styling | Utility-first, rapid development, consistent design |
| **Map Integration** | Mapbox | GL JS v2 | Interactive maps | Excellent customization, performance, travel-focused features |
| **HTTP Client** | httpx | 0.25+ | Async API calls | Modern async HTTP client for Python |
| **Validation** | Pydantic | 2.5+ | Data models & validation | Runtime type checking, excellent FastAPI integration |
| **Testing Framework** | pytest | 7.4+ | Backend testing | Industry standard, excellent fixture support |
| **Testing Framework** | Vitest | 1.2+ | Frontend testing | Fast, Vite-based, excellent TypeScript support |

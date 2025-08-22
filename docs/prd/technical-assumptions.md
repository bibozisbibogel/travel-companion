# Technical Assumptions

## Repository Structure: Monorepo
Single repository containing frontend, backend, and agents for streamlined development and deployment coordination.

## Service Architecture
Backend services deployed as containerized applications with FastAPI handling API orchestration and LangGraph managing agent workflows. Frontend deployed as static site with API integration.

## Testing Requirements
Comprehensive testing strategy including unit tests for individual agents, integration tests for workflow orchestration, and end-to-end tests for complete travel planning scenarios.

## Additional Technical Assumptions and Requests
- Python 3.11+ for backend development
- Next.js with TypeScript for frontend development
- Supabase for user data and trip storage with vector embeddings for RAG
- Redis for API response caching and rate limit management
- Docker containerization for consistent deployment
- GitHub Projects for team collaboration and issue tracking

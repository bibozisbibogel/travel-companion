# Multi-stage Dockerfile for Travel Companion API
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install uv

# Set work directory
WORKDIR /app

# Development stage
FROM base as development

# Copy UV configuration files
COPY pyproject.toml ./

# Install dependencies
RUN uv sync --dev

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Command for development
CMD ["uv", "run", "uvicorn", "travel_companion.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

# Copy UV configuration files
COPY pyproject.toml ./

# Install only production dependencies
RUN uv sync --no-dev

# Copy application code
COPY src/ ./src/

# Create non-root user
RUN addgroup --system --gid 1001 fastapi \
    && adduser --system --uid 1001 --gid 1001 fastapi

# Change ownership of the app directory
RUN chown -R fastapi:fastapi /app

# Switch to non-root user
USER fastapi

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Command for production
CMD ["uv", "run", "uvicorn", "travel_companion.main:app", "--host", "0.0.0.0", "--port", "8000"]
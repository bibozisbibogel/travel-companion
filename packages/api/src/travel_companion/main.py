"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from travel_companion.api.v1 import router as api_v1_router
from travel_companion.core.config import get_settings
from travel_companion.models.base import ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    print("Starting Travel Companion API...")
    yield
    # Shutdown
    print("Shutting down Travel Companion API...")


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    error_details = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        error_details.append(
            {
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input"),
            }
        )

    error_response = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message=f"Validation failed for {len(error_details)} field(s)",
        data={"errors": error_details},
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_response.model_dump()
    )


async def pydantic_validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle direct Pydantic validation errors."""
    error_details = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        error_details.append(
            {
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input"),
            }
        )

    error_response = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message=f"Model validation failed for {len(error_details)} field(s)",
        data={"errors": error_details},
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_response.model_dump()
    )


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Travel Companion API",
        description="Multi-agent travel planning and booking platform",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Register exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)  # type: ignore[arg-type]

    # Configure CORS
    cors_origins = settings.get_cors_origins_for_environment()
    cors_methods = settings.get_cors_methods_for_environment()

    # Log CORS configuration in development
    if settings.is_cors_debug_enabled():
        print(f"CORS Debug - Environment: {settings.environment}")
        print(f"CORS Debug - Origins: {cors_origins}")
        print(f"CORS Debug - Methods: {cors_methods}")
        print(f"CORS Debug - Headers: {settings.allowed_headers}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=settings.allow_credentials,
        allow_methods=cors_methods,
        allow_headers=settings.allowed_headers,
        max_age=settings.max_age,
    )

    # Include routers
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Travel Companion API", "version": "0.1.0"}

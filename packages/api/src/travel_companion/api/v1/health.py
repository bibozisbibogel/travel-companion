"""Health check endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends

from travel_companion.api.deps import get_current_settings
from travel_companion.core.config import Settings

router = APIRouter()


@router.get("")
async def health_check(settings: Settings = Depends(get_current_settings)) -> dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": settings.version,
        "service": settings.app_name,
    }


@router.get("/detailed")
async def detailed_health_check(
    settings: Settings = Depends(get_current_settings),
) -> dict[str, Any]:
    """Detailed health check with service dependencies."""
    from travel_companion.core.database import get_database_manager
    from travel_companion.core.redis import get_redis_manager

    # Basic service status
    health_status: dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": settings.version,
        "service": settings.app_name,
        "dependencies": {},
    }

    # Check database connection
    try:
        db_manager = get_database_manager()
        db_healthy = await db_manager.health_check()
        health_status["dependencies"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "configured": bool(settings.supabase_url and settings.supabase_key),
        }
    except Exception as e:
        health_status["dependencies"]["database"] = {
            "status": "error",
            "error": str(e),
            "configured": bool(settings.supabase_url and settings.supabase_key),
        }

    # Check Redis connection
    try:
        redis_manager = get_redis_manager()
        redis_healthy = await redis_manager.ping()
        health_status["dependencies"]["redis"] = {
            "status": "healthy" if redis_healthy else "unhealthy",
            "configured": bool(settings.redis_url),
        }
    except Exception as e:
        health_status["dependencies"]["redis"] = {
            "status": "error",
            "error": str(e),
            "configured": bool(settings.redis_url),
        }

    # Check external API keys configuration
    external_apis = {
        "amadeus": {
            "configured": bool(settings.amadeus_api_key and settings.amadeus_api_secret),
            "api_key_present": bool(settings.amadeus_api_key),
            "api_secret_present": bool(settings.amadeus_api_secret),
        },
        "booking": {
            "configured": bool(settings.booking_api_key),
            "api_key_present": bool(settings.booking_api_key),
        },
        "tripadvisor": {
            "configured": bool(settings.tripadvisor_api_key),
            "api_key_present": bool(settings.tripadvisor_api_key),
        },
        "openai": {
            "configured": bool(settings.openai_api_key),
            "api_key_present": bool(settings.openai_api_key),
        },
    }

    health_status["dependencies"]["external_apis"] = external_apis

    # Overall status determination
    database_ok = health_status["dependencies"]["database"]["status"] in ["healthy", "unhealthy"]
    redis_ok = health_status["dependencies"]["redis"]["status"] in ["healthy", "unhealthy"]

    if not (database_ok and redis_ok):
        health_status["status"] = "degraded"

    return health_status

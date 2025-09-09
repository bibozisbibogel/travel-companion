"""Health check endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends

from travel_companion.api.deps import get_current_settings
from travel_companion.core.config import Settings

router = APIRouter()

# Cache configuration
HEALTH_CACHE_TTL = 30  # seconds
HEALTH_CACHE_KEY = "health_check:detailed"


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
    """Detailed health check with service dependencies and caching."""
    from travel_companion.core.database import get_database_manager
    from travel_companion.core.redis import get_redis_manager

    redis_manager = get_redis_manager()

    # Try to get cached health status first
    try:
        cached_status = await redis_manager.get(HEALTH_CACHE_KEY, json_decode=True)
        if cached_status is not None and isinstance(cached_status, dict):
            # Type cast for MyPy - we've already validated it's a dict
            cached_result: dict[str, Any] = cached_status
            # Update timestamp but keep cached dependency checks
            cached_result["timestamp"] = datetime.now(UTC).isoformat()
            cached_result["cached"] = True
            cached_result["cache_ttl_remaining"] = await redis_manager.ttl(HEALTH_CACHE_KEY)
            return cached_result
    except Exception:
        # If cache fails, continue with fresh check
        pass

    # Basic service status with enhanced reporting
    health_status: dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": settings.version,
        "service": settings.app_name,
        "environment": settings.environment,
        "uptime_check": "running",
        "dependencies": {},
        "cached": False,
        "metrics": {
            "dependencies_checked": 0,
            "healthy_dependencies": 0,
            "unhealthy_dependencies": 0,
            "error_dependencies": 0,
        },
    }

    # Check database connection
    try:
        db_manager = get_database_manager()
        db_healthy = await db_manager.health_check()
        health_status["dependencies"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "configured": bool(
                settings.supabase_url and (settings.supabase_service_key or settings.supabase_key)
            ),
        }
    except Exception as e:
        health_status["dependencies"]["database"] = {
            "status": "error",
            "error": str(e),
            "configured": bool(
                settings.supabase_url and (settings.supabase_service_key or settings.supabase_key)
            ),
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
            "configured": bool(settings.amadeus_client_id and settings.amadeus_client_secret),
            "api_key_present": bool(settings.amadeus_client_id),
            "api_secret_present": bool(settings.amadeus_client_secret),
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

    # Check workflow engine health
    try:
        from travel_companion.workflows.orchestrator import TripPlanningWorkflow

        workflow = TripPlanningWorkflow()
        workflow_health = workflow.get_health_status()

        health_status["dependencies"]["workflow_engine"] = workflow_health

    except Exception as e:
        health_status["dependencies"]["workflow_engine"] = {
            "status": "error",
            "error": str(e),
            "workflow_type": "unknown",
            "graph_built": False,
            "redis_connected": False,
            "node_count": 0,
            "edge_count": 0,
        }

    # Calculate dependency metrics
    dependencies = health_status["dependencies"]
    total_deps = len(dependencies)
    healthy_count = sum(
        1
        for dep in dependencies.values()
        if isinstance(dep, dict) and dep.get("status") == "healthy"
    )
    unhealthy_count = sum(
        1
        for dep in dependencies.values()
        if isinstance(dep, dict) and dep.get("status") == "unhealthy"
    )
    error_count = sum(
        1 for dep in dependencies.values() if isinstance(dep, dict) and dep.get("status") == "error"
    )

    health_status["metrics"] = {
        "dependencies_checked": total_deps,
        "healthy_dependencies": healthy_count,
        "unhealthy_dependencies": unhealthy_count,
        "error_dependencies": error_count,
    }

    # Overall status determination
    database_ok = health_status["dependencies"]["database"]["status"] in ["healthy", "unhealthy"]
    redis_ok = health_status["dependencies"]["redis"]["status"] in ["healthy", "unhealthy"]
    workflow_ok = health_status["dependencies"]["workflow_engine"]["status"] in [
        "healthy",
        "degraded",
    ]

    if not (database_ok and redis_ok and workflow_ok):
        health_status["status"] = "degraded"

    # Cache the health status for performance (only if Redis is working)
    if redis_ok:
        try:
            await redis_manager.set(HEALTH_CACHE_KEY, health_status, expire=HEALTH_CACHE_TTL)
        except Exception:
            # Cache failure should not affect health check response
            pass

    return health_status

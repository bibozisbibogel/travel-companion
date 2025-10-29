"""API v1 router endpoints."""

from fastapi import APIRouter

from . import health, trips, users, workflows

router = APIRouter()

router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(trips.router, prefix="/trips", tags=["trips"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(workflows.router, tags=["workflows"])

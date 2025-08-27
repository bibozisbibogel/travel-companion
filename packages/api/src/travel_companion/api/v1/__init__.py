"""API v1 router endpoints."""

from fastapi import APIRouter

from . import health, users

router = APIRouter()

router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(users.router, prefix="/users", tags=["users"])

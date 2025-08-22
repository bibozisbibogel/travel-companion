"""API v1 router endpoints."""

from fastapi import APIRouter

from . import health

router = APIRouter()

router.include_router(health.router, prefix="/health", tags=["health"])

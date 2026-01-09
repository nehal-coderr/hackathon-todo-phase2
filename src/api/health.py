# Task ID: T017 - Health check endpoint GET /api/v1/health
"""Health check endpoint per contracts/api-v1.yaml."""

from fastapi import APIRouter

from src.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Per contracts/api-v1.yaml:
    - Does not require authentication
    - Returns status and version
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
    }

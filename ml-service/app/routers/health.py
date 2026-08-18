"""
routers/health.py — FastAPI health-check router

GET /health
    Returns the operational status of the ML service.
    The Express backend (and the React dashboard in Phase 1) polls this
    endpoint to confirm the Python service is running.
"""

from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Return service status and current UTC timestamp."""
    return {
        "status":    "ok",
        "service":   "scarlet-ml-service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

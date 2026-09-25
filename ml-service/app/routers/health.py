"""
routers/health.py — FastAPI health-check router

GET /health
    Returns the operational status of the ML service.
    The Express backend (and the React dashboard in Phase 1) polls this
    endpoint to confirm the Python service is running.
"""

from fastapi import APIRouter
from datetime import datetime, timezone
from app.demand_forecasting.model_loader import model_loader

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Return service status including demand model loading state."""
    meta = model_loader.model_metadata or {}
    return {
        "status":        "ok",
        "service":       "scarlet-ml-service",
        "timestamp":     datetime.now(timezone.utc).isoformat(),
        "demand_model": {
            "loaded":  model_loader.is_loaded,
            "version": meta.get("model_version", "not loaded"),
            "type":    meta.get("model_type", "unknown"),
        },
    }

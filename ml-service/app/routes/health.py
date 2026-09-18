"""
routes/health.py — GET /health
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app import db
from app.models.loader import get_artifacts


router = APIRouter()


@router.get("/health")
def health():
    artifacts = get_artifacts()
    db_ok = db.check_connection()

    status = "ok" if artifacts.loaded and db_ok else "degraded"

    return {
        "status": status,
        "service": "ml-service",
        "database": "connected" if db_ok else "error",
        "demand_model": {
            "status": "loaded" if artifacts.loaded else "not_loaded",
            "name": artifacts.model_name if artifacts.loaded else None,
            "version": artifacts.model_version if artifacts.loaded else None,
            "error": artifacts.error,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
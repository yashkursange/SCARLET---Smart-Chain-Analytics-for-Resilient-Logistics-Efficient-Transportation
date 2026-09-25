"""
config.py — environment-driven configuration for the ML service.

All values come from environment variables (loaded from .env by python-dotenv),
matching the "no hard-coded config" rule used by the Express backend.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load ml-service/.env explicitly rather than relying on the current working
# directory, so the service, its scripts and its tests all see the same config
# no matter where they are launched from.
load_dotenv(BASE_DIR / ".env")

# ── Service ──────────────────────────────────────────────────────────────────
ML_SERVICE_PORT = int(os.environ.get("ML_SERVICE_PORT", "8000"))
FRONTEND_URL = os.environ.get("FRONTEND_URL", "*")

# ── Database (same PostgreSQL instance/credentials the Express backend uses) ──
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ.get("DB_NAME", "scarlet")
DB_USER = os.environ.get("DB_USER", "scarlet_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

# ── Demand model artifacts ──────────────────────────────────────────────────
# Resolved against the ml-service directory when a relative path is given, so
# the service and its scripts/tests work regardless of the current working
# directory they are launched from.
_model_dir = Path(os.environ.get("DEMAND_MODEL_DIR", "models/demand"))
DEMAND_MODEL_DIR = _model_dir if _model_dir.is_absolute() else (BASE_DIR / _model_dir).resolve()

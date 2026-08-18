"""
app/main.py — FastAPI application entry point

Architecture note:
    The ML service is a separate process from the Node/Express backend.
    Express will call this service for ML inference and simulation tasks
    (Phase 2+).  In Phase 1 it exposes only a health-check endpoint.
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health

# Load environment variables from .env (if present).
# In production these come from the environment directly.
load_dotenv()

app = FastAPI(
    title="SCARLET ML Service",
    description="AI / ML / Simulation service for the SCARLET Supply Chain Digital Twin",
    version="0.1.0",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# In Phase 1 the Express backend calls this service, so we allow all origins
# for development convenience.  Restrict to the Express URL in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(health.router)

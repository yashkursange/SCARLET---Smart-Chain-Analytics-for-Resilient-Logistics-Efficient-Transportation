"""
main.py — FastAPI application entry point for the SCARLET ML service.

Run with:  uvicorn app.main:app --reload --port 8000   (from the ml-service/ directory)
"""
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.models.loader import load_demand_model
from app.routes import health as health_routes
from app.routes import demand as demand_routes
from app.routes import inventory as inventory_routes

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("scarlet.ml.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Model loader: load once at startup, never per-request (see app/models/loader.py).
    artifacts = load_demand_model()
    if artifacts.loaded:
        logger.info("Startup complete — demand model %s v%s ready.",
                     artifacts.model_name, artifacts.model_version)
    else:
        logger.error("Startup complete — demand model FAILED to load: %s", artifacts.error)
    yield


app = FastAPI(title="SCARLET ML Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL] if config.FRONTEND_URL != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_routes.router)
app.include_router(demand_routes.router, prefix="/api/ml/demand")
app.include_router(inventory_routes.router, prefix="/api/ml/inventory")

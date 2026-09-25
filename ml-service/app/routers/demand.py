"""
routers/demand.py — FastAPI router for demand forecasting.

POST /api/ml/demand/forecast
    Runs the recursive multi-step XGBoost demand forecast.
    The model is loaded once at startup; this endpoint is stateless.
"""

from fastapi import APIRouter, HTTPException
from app.demand_forecasting.schemas import ForecastRequest, ForecastResponse, ForecastPoint
from app.demand_forecasting.model_loader import model_loader
from app.demand_forecasting.predictor import run_forecast
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/forecast", response_model=ForecastResponse)
async def forecast_demand(request: ForecastRequest):
    """Generate a recursive multi-step demand forecast using the trained XGBoost model."""

    if not model_loader.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="Demand forecasting model is not loaded. Check model artifacts.",
        )

    try:
        raw_forecast = run_forecast(
            product_id=request.product_id,
            market_id=request.market_id,
            start_date=request.forecast_date,
            horizon=request.horizon,
        )

        return ForecastResponse(
            success=True,
            model_version=model_loader.model_metadata.get("model_version", "unknown"),
            product_id=request.product_id,
            market_id=request.market_id,
            forecast=[ForecastPoint(**p) for p in raw_forecast],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Demand forecast failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal forecasting error. See service logs.")


@router.get("/model-info")
async def model_info():
    """Returns metadata and performance metrics of the loaded demand model."""
    if not model_loader.is_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded.")

    return {
        "model_metadata": model_loader.model_metadata,
        "metrics": model_loader.metrics,
        "feature_count": len(model_loader.feature_columns),
        "features": model_loader.feature_columns,
    }

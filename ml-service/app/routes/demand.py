"""
routes/demand.py — POST /api/ml/demand/forecast

This exact path is what backend/src/routes/forecast.js already proxies to
(ML_SERVICE_URL + '/api/ml/demand/forecast'), so no backend route changes
were needed to wire this up.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import db
from app.models.loader import get_artifacts
from app.ml.demand.history import (
    ForecastInputError,
    get_daily_demand_history,
    get_product_market_context,
)
from app.ml.demand.predictor import MAX_HORIZON_DAYS, recursive_forecast

logger = logging.getLogger("scarlet.ml.routes.demand")
router = APIRouter()


class ForecastRequest(BaseModel):
    product_id: str
    market_id: str
    forecast_date: Optional[date] = Field(
        default=None,
        description="First date to forecast. Defaults to the day after the latest "
                    "available demand history for this product/market.",
    )
    horizon: int = Field(default=7, ge=1, le=MAX_HORIZON_DAYS)


def _error_response(status_code: int, code: str, message: str):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=status_code, content={
        "success": False,
        "error_code": code,
        "error": message,
    })


def _persist_forecast(product_id: str, market_id: str, model_version: str, forecast: list[dict]):
    """Best-effort persistence to demand_forecasts. A failure here must never
    fail the API response — the prediction was already computed correctly."""
    try:
        for row in forecast:
            db.execute(
                """
                INSERT INTO demand_forecasts (product_id, market_id, forecast_date, predicted_demand, model_version)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (product_id, market_id, forecast_date, model_version)
                DO UPDATE SET predicted_demand = EXCLUDED.predicted_demand, generated_at = NOW()
                """,
                (product_id, market_id, row["date"], row["predicted_demand"], model_version),
            )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to persist forecast rows (non-fatal)")


@router.post("/forecast")
def forecast_demand(req: ForecastRequest):
    artifacts = get_artifacts()
    if not artifacts.loaded:
        return _error_response(503, "model_not_loaded",
                                f"Demand model is not loaded: {artifacts.error}")

    try:
        ctx = get_product_market_context(req.product_id, req.market_id)
        history = get_daily_demand_history(
            req.product_id, req.market_id,
            as_of=(req.forecast_date - timedelta(days=1)) if req.forecast_date else date.today(),
        )
        forecast = recursive_forecast(artifacts, ctx, history, req.horizon, start_date=req.forecast_date)
    except ForecastInputError as exc:
        status_map = {
            "product_not_found": 404,
            "market_not_found": 404,
            "product_not_mapped": 422,
            "market_not_mapped": 422,
            "insufficient_history": 422,
            "unknown_model_vocabulary": 422,
        }
        return _error_response(status_map.get(exc.code, 422), exc.code, exc.message)
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error generating forecast")
        return _error_response(500, "prediction_failed", "Failed to generate demand forecast.")

    _persist_forecast(ctx.product_id, ctx.market_id, artifacts.model_version, forecast)

    recent_history = [
        {"date": d.isoformat(), "actual_demand": v}
        for d, v in list(history.items())[-28:]
    ]
    avg_recent = sum(v for _, v in list(history.items())[-28:]) / min(28, len(history))
    avg_forecast = sum(r["predicted_demand"] for r in forecast) / len(forecast)
    demand_change_pct = (
        round((avg_forecast - avg_recent) / avg_recent * 100, 1) if avg_recent > 0 else None
    )

    return {
        "success": True,
        "product_id": ctx.product_id,
        "product_name": ctx.product_name,
        "market_id": ctx.market_id,
        "model": {
            "name": artifacts.model_name,
            "version": artifacts.model_version,
            "metrics": artifacts.metrics.get("test_metrics", {}),
        },
        "model_version": artifacts.model_version,
        "forecast_horizon": req.horizon,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "history": recent_history,
        "forecast": forecast,
        "demand_change_pct": demand_change_pct,
    }

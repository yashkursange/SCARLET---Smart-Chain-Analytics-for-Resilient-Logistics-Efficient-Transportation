"""
routes/inventory.py — POST /api/ml/inventory/projection

Feeds the REAL demand forecast into inventory projection and stockout-risk
classification, wiring the trained model into SCARLET's decision pipeline:

    trained demand model -> forecast -> inventory projection -> stockout risk
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import db
from app.models.loader import get_artifacts
from app.ml.demand.history import (
    ForecastInputError,
    get_daily_demand_history,
    get_product_market_context,
)
from app.ml.demand.predictor import MAX_HORIZON_DAYS, recursive_forecast
from app.ml.demand.inventory import project_inventory

logger = logging.getLogger("scarlet.ml.routes.inventory")
router = APIRouter()


class ProjectionRequest(BaseModel):
    product_id: str
    market_id: str
    forecast_date: Optional[date] = None
    horizon: int = Field(default=7, ge=1, le=MAX_HORIZON_DAYS)


def _error_response(status_code: int, code: str, message: str):
    return JSONResponse(status_code=status_code, content={
        "success": False, "error_code": code, "error": message,
    })


@router.post("/projection")
def inventory_projection(req: ProjectionRequest):
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
        forecast = recursive_forecast(artifacts, ctx, history, req.horizon,
                                       start_date=req.forecast_date)

        # The market's stocking location is the node the market belongs to.
        market_row = db.fetch_one("SELECT node_id FROM markets WHERE id = %s", (req.market_id,))
        node_id = str(market_row["node_id"])

        projection = project_inventory(ctx.product_id, node_id, forecast)
    except ForecastInputError as exc:
        status_map = {
            "product_not_found": 404, "market_not_found": 404,
            "product_not_mapped": 422, "market_not_mapped": 422,
            "insufficient_history": 422, "unknown_model_vocabulary": 422,
            "no_inventory_record": 422, "empty_forecast": 422,
        }
        return _error_response(status_map.get(exc.code, 422), exc.code, exc.message)
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error generating inventory projection")
        return _error_response(500, "projection_failed",
                                "Failed to generate inventory projection.")

    return {
        "success": True,
        "product_id": ctx.product_id,
        "product_name": ctx.product_name,
        "market_id": ctx.market_id,
        "node_id": node_id,
        "model": {"name": artifacts.model_name, "version": artifacts.model_version},
        "forecast_horizon": req.horizon,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **projection,
    }

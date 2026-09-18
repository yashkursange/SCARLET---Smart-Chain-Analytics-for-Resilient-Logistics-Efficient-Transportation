"""schemas.py — Pydantic request/response models for the demand forecasting API."""

from pydantic import BaseModel, Field
from typing import List


class ForecastRequest(BaseModel):
    product_id: str = Field(..., description="SCARLET product UUID")
    market_id: str = Field(..., description="SCARLET market UUID")
    forecast_date: str = Field(..., description="Start date for the forecast (YYYY-MM-DD)")
    horizon: int = Field(default=7, ge=1, le=28, description="Number of days to forecast (1–28)")


class ForecastPoint(BaseModel):
    date: str
    predicted_demand: float


class ForecastResponse(BaseModel):
    success: bool
    model_version: str
    product_id: str
    market_id: str
    forecast: List[ForecastPoint]

"""
predictor.py — Recursive multi-step demand forecasting.

The trained XGBoost model is fundamentally a one-step (daily) model.
For a horizon of N days we use recursive forecasting:
    1. Build features for day T using real historical demand
    2. Predict demand for day T
    3. Append that prediction to the simulated history
    4. Build features for day T+1 using updated history
    5. Repeat

This mirrors exactly how the notebook evaluated multi-step forecasting.
Future actual demand is NEVER used — each step only sees its own past.
"""

import pandas as pd
import numpy as np
from datetime import timedelta

from app.demand_forecasting.feature_engineering import (
    get_historical_data,
    engineer_features,
)
from app.demand_forecasting.model_loader import model_loader


def run_forecast(
    product_id: str,
    market_id: str,
    start_date: str,
    horizon: int,
) -> list[dict]:
    """
    Generates a recursive multi-step forecast.

    Args:
        product_id:  SCARLET product UUID string
        market_id:   SCARLET market UUID string
        start_date:  ISO date string "YYYY-MM-DD" for the first forecast day
        horizon:     Number of days to forecast (1–28)

    Returns:
        List of {"date": "YYYY-MM-DD", "predicted_demand": float}

    Raises:
        RuntimeError:  If the model is not loaded.
        ValueError:    If horizon is out of range.
    """
    if not model_loader.is_loaded:
        raise RuntimeError("Demand forecasting model is not loaded.")

    if not (1 <= horizon <= 28):
        raise ValueError(f"Horizon must be between 1 and 28 days, got {horizon}.")

    current_date = pd.Timestamp(start_date)

    # Fetch real historical demand up to (but not including) start_date
    historical_df = get_historical_data(product_id, market_id, current_date)

    # Carry forward last known price and SKU for recursive steps
    if historical_df.empty:
        last_price = 0.0
        last_sku = "FOODS_3_038"   # default to a known M5 item
    else:
        last_price = float(historical_df["sell_price"].iloc[-1])
        last_sku = str(historical_df["sku"].iloc[-1])

    # Working copy — we'll append synthetic rows as we forecast forward
    sim_history = historical_df.copy()

    predictions = []

    for step in range(horizon):
        # Build feature vector for the current forecast date
        features_df = engineer_features(
            product_id=product_id,
            market_id=market_id,
            current_date=current_date,
            historical_df=sim_history,
            model_loader=model_loader,
        )

        # Predict — ensure non-negative (demand cannot be negative)
        raw_pred = float(model_loader.model.predict(features_df)[0])
        pred = max(0.0, raw_pred)

        predictions.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "predicted_demand": round(pred, 4),
        })

        # Append the prediction to simulated history for the next recursive step
        new_row = pd.DataFrame([{
            "date":       current_date,
            "sales":      pred,
            "sell_price": last_price,
            "sku":        last_sku,
        }])
        sim_history = pd.concat([sim_history, new_row], ignore_index=True)

        current_date += timedelta(days=1)

    return predictions

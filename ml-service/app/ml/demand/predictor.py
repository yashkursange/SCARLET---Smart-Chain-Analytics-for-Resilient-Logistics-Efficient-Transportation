"""
predictor.py — recursive multi-day forecasting, matching the notebook's
`recursive_forecast` helper (Section 16) exactly: walk forward one day at a
time, and for every day beyond the first, feed the model's OWN previous
prediction back in as the new "actual" sales value for lag/rolling purposes.
This is a genuine blind multi-step forecast — never a real future demand
value, since none exists yet at prediction time.
"""
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from app.models.loader import DemandModelArtifacts
from app.ml.demand.features import build_feature_row
from app.ml.demand.history import ProductMarketContext, get_department_avg_price

MAX_HORIZON_DAYS = 28  # matches model_metadata.json["forecast_horizon_days"]


def recursive_forecast(artifacts: DemandModelArtifacts, ctx: ProductMarketContext,
                        history: pd.Series, horizon_days: int,
                        start_date: Optional[date] = None) -> list[dict]:
    if horizon_days < 1 or horizon_days > MAX_HORIZON_DAYS:
        raise ValueError(f"forecast_horizon must be between 1 and {MAX_HORIZON_DAYS}")

    dept_avg_price = get_department_avg_price(ctx.ml_dept_id, exclude_product_id=ctx.product_id)

    sales_history = history.to_numpy(dtype=float).copy()
    as_of = history.index.max()
    first_forecast_date = start_date or (as_of + timedelta(days=1))

    results = []
    for i in range(horizon_days):
        forecast_date = first_forecast_date + timedelta(days=i)

        X_row = build_feature_row(
            artifacts, forecast_date, sales_history,
            unit_price=ctx.unit_price, dept_avg_price=dept_avg_price,
            item_id=ctx.ml_item_id, dept_id=ctx.ml_dept_id, cat_id=ctx.ml_cat_id,
            store_id=ctx.ml_store_id, state_id=ctx.ml_state_id,
        )
        raw_pred = float(artifacts.model.predict(X_row)[0])
        pred = float(np.clip(raw_pred, 0, None))  # demand cannot be negative

        results.append({"date": forecast_date.isoformat(), "predicted_demand": round(pred, 4)})

        # Feed the prediction back in as the new most-recent "observation"
        # for subsequent days' lag/rolling features (recursive forecasting).
        sales_history = np.append(sales_history, pred)

    return results

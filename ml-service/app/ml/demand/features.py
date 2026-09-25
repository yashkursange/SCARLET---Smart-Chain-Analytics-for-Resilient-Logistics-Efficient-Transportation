"""
features.py — reproduces the EXACT feature engineering used in
SCARLET_Demand_Forecasting.ipynb (Section 9 training / Section 16 recursive
forecast), so a request scored here uses the same feature definitions,
column order, and leakage-safety rules as training:

    - date features: computed straight from the calendar date (pandas .dt
      accessors, identical to the notebook).
    - lag features (lag_1/7/14/28): the actual value N days before the day
      being scored, taken from real demand history (or, for days beyond the
      first prediction, from the model's own prior predictions — see
      predictor.py's recursive walk, which mirrors the notebook's
      `recursive_forecast` helper exactly).
    - rolling features: computed on a `shift(1)`-equivalent window (i.e. the
      window ends the day BEFORE the day being scored) — never includes the
      current day, matching the notebook's leakage-prevention rule.
    - price features: SCARLET stores a single current `unit_price` per
      product rather than the M5 dataset's daily per-store price history, so
      `price_lag_1 == sell_price` and `price_change(_pct) == 0` by
      construction here — a disclosed simplification, not a fabricated
      history (see README "Known limitations" in ml-service).
    - event/SNAP features: SCARLET's schema has no calendar/holiday/SNAP
      table yet, so these are always 0 ("no event modeled") rather than
      guessed. This is a disclosed gap, tracked as a follow-up integration
      item.
    - categorical features: integer codes come from the model's own
      cat_code_maps.json (reverse-looked-up from the product/market's mapped
      vocabulary labels) — never re-derived or invented.
"""
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from app.models.loader import DemandModelArtifacts
from app.ml.demand.history import ForecastInputError

EVENT_TYPE_COLUMNS = ["event_religious", "event_national", "event_cultural", "event_sporting"]


def date_features(d: date) -> dict:
    ts = pd.Timestamp(d)
    return {
        "day_of_week": int(ts.dayofweek),
        "day_of_month": int(ts.day),
        "day_of_year": int(ts.dayofyear),
        "week_of_year": int(ts.isocalendar().week),
        "quarter": int(ts.quarter),
        "is_weekend": int(ts.dayofweek >= 5),
        "is_month_start": int(ts.is_month_start),
        "is_month_end": int(ts.is_month_end),
        # No calendar/holiday/SNAP table exists in SCARLET yet (see module
        # docstring) — these default to "no event", not a guess.
        "has_event": 0,
        "event_religious": 0,
        "event_national": 0,
        "event_cultural": 0,
        "event_sporting": 0,
        "snap": 0,
    }


def categorical_codes(artifacts: DemandModelArtifacts, item_id: str, dept_id: str,
                       cat_id: str, store_id: str, state_id: str) -> dict:
    codes = {}
    for col, label in [("item_id", item_id), ("dept_id", dept_id), ("cat_id", cat_id),
                        ("store_id", store_id), ("state_id", state_id)]:
        code = artifacts.label_to_code(col, label)
        if code is None:
            raise ForecastInputError(
                "unknown_model_vocabulary",
                f"'{label}' is not part of the trained model's {col} vocabulary. "
                "Check the ml_* mapping columns on products/markets.",
            )
        codes[f"{col}_enc"] = code
    return codes


def lag_and_rolling_features(sales_history: np.ndarray) -> dict:
    """`sales_history` must be ordered oldest -> newest, ending the day BEFORE
    the day being scored (i.e. already shifted) — the same convention as the
    notebook's shift(1)-then-roll rule, so no future value can leak in."""
    s = sales_history
    n = len(s)

    def lag(k):
        return float(s[-k]) if n >= k else np.nan

    def roll_mean(w):
        window = s[-w:] if n >= w else s
        return float(window.mean()) if len(window) else np.nan

    def roll_std(w):
        window = s[-w:] if n >= w else s
        return float(window.std()) if len(window) else 0.0

    return {
        "lag_1": lag(1), "lag_7": lag(7), "lag_14": lag(14), "lag_28": lag(28),
        "rolling_mean_7": roll_mean(7), "rolling_std_7": roll_std(7),
        "rolling_mean_14": roll_mean(14), "rolling_std_14": roll_std(14),
        "rolling_mean_28": roll_mean(28), "rolling_std_28": roll_std(28),
        "rolling_min_28": float((s[-28:] if n >= 28 else s).min()),
        "rolling_max_28": float((s[-28:] if n >= 28 else s).max()),
    }


def price_features(unit_price: float, dept_avg_price: Optional[float]) -> dict:
    """See module docstring — SCARLET has no daily price history, so price
    is treated as constant (price_lag_1 == current price, no change)."""
    rel = (unit_price / dept_avg_price) if dept_avg_price else 1.0
    return {
        "sell_price": float(unit_price),
        "price_lag_1": float(unit_price),
        "price_change": 0.0,
        "price_change_pct": 0.0,
        "price_rel_to_dept": float(rel),
    }


def build_feature_row(artifacts: DemandModelArtifacts, forecast_date: date,
                       sales_history: np.ndarray, unit_price: float,
                       dept_avg_price: Optional[float],
                       item_id: str, dept_id: str, cat_id: str,
                       store_id: str, state_id: str) -> pd.DataFrame:
    feat = {}
    feat.update(date_features(forecast_date))
    feat.update(lag_and_rolling_features(sales_history))
    feat.update(price_features(unit_price, dept_avg_price))
    feat.update(categorical_codes(artifacts, item_id, dept_id, cat_id, store_id, state_id))

    row = pd.DataFrame([feat])
    missing = [c for c in artifacts.feature_columns if c not in row.columns]
    if missing:
        # Should be unreachable if this module stays in sync with the notebook,
        # but fail loudly rather than silently mis-ordering columns.
        raise RuntimeError(f"Feature engineering is missing columns the model expects: {missing}")
    return row[artifacts.feature_columns].fillna(0.0)

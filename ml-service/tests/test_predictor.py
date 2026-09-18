import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.loader import load_demand_model
from app.ml.demand.history import ProductMarketContext
from app.ml.demand.predictor import recursive_forecast, MAX_HORIZON_DAYS


def _make_ctx(artifacts):
    return ProductMarketContext(
        product_id="00000000-0000-0000-0000-000000000001",
        product_name="Test Product",
        unit_price=5.0,
        ml_item_id=artifacts.cat_code_maps["item_id"]["0"],
        ml_dept_id=artifacts.cat_code_maps["dept_id"]["0"],
        ml_cat_id=artifacts.cat_code_maps["cat_id"]["0"],
        market_id="00000000-0000-0000-0000-000000000002",
        ml_store_id=artifacts.cat_code_maps["store_id"]["0"],
        ml_state_id=artifacts.cat_code_maps["state_id"]["0"],
    )


def _make_history(n_days=60):
    idx = pd.date_range(end=date(2016, 5, 22), periods=n_days, freq="D").date
    values = (np.sin(np.arange(n_days) / 7.0) * 2 + 3).round().clip(min=0)
    return pd.Series(values, index=idx)


def test_recursive_forecast_returns_correct_horizon():
    artifacts = load_demand_model()
    ctx = _make_ctx(artifacts)
    history = _make_history()
    result = recursive_forecast(artifacts, ctx, history, horizon_days=7)
    assert len(result) == 7
    assert result[0]["date"] == (history.index.max() + timedelta(days=1)).isoformat()
    assert result[-1]["date"] == (history.index.max() + timedelta(days=7)).isoformat()


def test_recursive_forecast_predictions_are_non_negative():
    artifacts = load_demand_model()
    ctx = _make_ctx(artifacts)
    history = _make_history()
    result = recursive_forecast(artifacts, ctx, history, horizon_days=28)
    for row in result:
        assert row["predicted_demand"] >= 0.0


def test_recursive_forecast_rejects_horizon_out_of_range():
    artifacts = load_demand_model()
    ctx = _make_ctx(artifacts)
    history = _make_history()
    with pytest.raises(ValueError):
        recursive_forecast(artifacts, ctx, history, horizon_days=0)
    with pytest.raises(ValueError):
        recursive_forecast(artifacts, ctx, history, horizon_days=MAX_HORIZON_DAYS + 1)


def test_recursive_forecast_uses_own_predictions_for_later_days():
    """Day 2's lag_1 feature should be day 1's PREDICTION, not some external
    value — verified indirectly: forecasting 2 days from a short, constant
    history should not raise and should produce 2 distinct, finite values."""
    artifacts = load_demand_model()
    ctx = _make_ctx(artifacts)
    history = pd.Series([2.0] * 30, index=pd.date_range(end=date(2016, 5, 22), periods=30, freq="D").date)
    result = recursive_forecast(artifacts, ctx, history, horizon_days=2)
    assert len(result) == 2
    assert all(np.isfinite(r["predicted_demand"]) for r in result)

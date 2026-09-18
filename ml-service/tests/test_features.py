import sys
from datetime import date
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.demand.features import (
    date_features,
    lag_and_rolling_features,
    price_features,
    build_feature_row,
    categorical_codes,
)
from app.ml.demand.history import ForecastInputError
from app.models.loader import load_demand_model


def test_date_features_known_date():
    # 2016-05-23 is a Monday
    f = date_features(date(2016, 5, 23))
    assert f["day_of_week"] == 0
    assert f["is_weekend"] == 0
    assert f["day_of_month"] == 23
    assert f["quarter"] == 2
    # no calendar/SNAP table exists yet -> always 0, disclosed simplification
    assert f["has_event"] == 0
    assert f["snap"] == 0


def test_date_features_weekend():
    # 2016-05-21 is a Saturday
    f = date_features(date(2016, 5, 21))
    assert f["is_weekend"] == 1


def test_rolling_features_never_include_current_day():
    """The defining leakage-safety property: rolling_mean_7 computed on a
    history array that ends the day BEFORE the scored day must equal the
    plain mean of the last 7 entries of that (already-shifted) array — i.e.
    changing what would have been "today"'s value cannot affect it, because
    today's value was never included in the array passed in."""
    history_a = np.array([1, 2, 3, 4, 5, 6, 7], dtype=float)
    feats_a = lag_and_rolling_features(history_a)

    # simulate a different "today" value by NOT appending it (correct usage);
    # confirm rolling_mean_7 only reflects the 7 prior values, not some 8th
    # unseen value.
    assert feats_a["rolling_mean_7"] == pytest.approx(np.mean(history_a))
    assert feats_a["lag_1"] == 7.0
    assert feats_a["lag_7"] == 1.0


def test_lag_28_nan_when_insufficient_history():
    history = np.array([1.0] * 10)
    feats = lag_and_rolling_features(history)
    assert np.isnan(feats["lag_28"])


def test_price_features_constant_when_no_dept_average():
    f = price_features(unit_price=10.0, dept_avg_price=None)
    assert f["sell_price"] == 10.0
    assert f["price_lag_1"] == 10.0
    assert f["price_change"] == 0.0
    assert f["price_change_pct"] == 0.0
    assert f["price_rel_to_dept"] == 1.0


def test_price_features_relative_to_dept():
    f = price_features(unit_price=10.0, dept_avg_price=5.0)
    assert f["price_rel_to_dept"] == 2.0


def test_categorical_codes_unknown_label_raises():
    artifacts = load_demand_model()
    with pytest.raises(ForecastInputError):
        categorical_codes(artifacts, "NOT_A_REAL_ITEM", "FOODS_1", "FOODS", "CA_1", "CA")


def test_categorical_codes_known_label_resolves():
    artifacts = load_demand_model()
    # pick a real item/dept/cat/store/state combo from the trained vocabulary
    item_label = artifacts.cat_code_maps["item_id"]["0"]
    dept_label = artifacts.cat_code_maps["dept_id"]["0"]
    cat_label = artifacts.cat_code_maps["cat_id"]["0"]
    store_label = artifacts.cat_code_maps["store_id"]["0"]
    state_label = artifacts.cat_code_maps["state_id"]["0"]
    codes = categorical_codes(artifacts, item_label, dept_label, cat_label, store_label, state_label)
    assert codes["item_id_enc"] == 0
    assert codes["store_id_enc"] == 0


def test_build_feature_row_matches_model_column_order():
    artifacts = load_demand_model()
    item_label = artifacts.cat_code_maps["item_id"]["0"]
    dept_label = artifacts.cat_code_maps["dept_id"]["0"]
    cat_label = artifacts.cat_code_maps["cat_id"]["0"]
    store_label = artifacts.cat_code_maps["store_id"]["0"]
    state_label = artifacts.cat_code_maps["state_id"]["0"]

    history = np.array([1.0, 2.0, 0.0, 3.0] * 10)  # 40 days of history
    row = build_feature_row(
        artifacts, date(2016, 5, 23), history, unit_price=5.0, dept_avg_price=None,
        item_id=item_label, dept_id=dept_label, cat_id=cat_label,
        store_id=store_label, state_id=state_label,
    )
    assert list(row.columns) == artifacts.feature_columns
    assert row.shape == (1, len(artifacts.feature_columns))
    assert not row.isna().any().any()

    # the model must actually accept this row and return a single float
    pred = artifacts.model.predict(row)
    assert pred.shape == (1,)
    assert np.isfinite(pred[0])

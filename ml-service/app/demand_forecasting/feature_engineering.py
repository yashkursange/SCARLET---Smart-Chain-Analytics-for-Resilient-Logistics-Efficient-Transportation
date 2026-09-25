"""
feature_engineering.py — Builds the exact feature vector expected by the trained XGBoost model.

The model was trained on M5 Walmart data. SCARLET's products/markets are mapped to M5
identifiers via the SKU field (e.g. FOODS_3_038__CA_1) or falling back to defaults.

Feature order is strictly determined by feature_columns.json.
Cat encodings come from cat_code_maps.json — NO new encoders are fitted at inference time.
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from sqlalchemy import text
from app.ml.data_loader import get_engine


def get_historical_data(product_id: str, market_id: str, as_of_date: pd.Timestamp) -> pd.DataFrame:
    """
    Fetches up to 60 days of historical demand for this product+market combo,
    ending strictly before as_of_date (no data leakage).
    Returns a DataFrame with columns: date, sales, sell_price, sku
    """
    engine = get_engine()
    start_date = as_of_date - timedelta(days=60)

    query = text("""
        SELECT
            d.period_start::date        AS date,
            d.demand_quantity           AS sales,
            p.unit_price                AS sell_price,
            p.sku                       AS sku
        FROM demand d
        JOIN products p ON d.product_id = p.id
        WHERE d.product_id = :product_id
          AND d.market_id  = :market_id
          AND d.period_start >= :start_date
          AND d.period_start <  :as_of_date
        ORDER BY d.period_start ASC
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {
            "product_id": product_id,
            "market_id": market_id,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "as_of_date": as_of_date.strftime('%Y-%m-%d'),
        })
        rows = result.fetchall()
        cols = result.keys()
        df = pd.DataFrame(rows, columns=list(cols))

    if df.empty:
        return df

    df['date'] = pd.to_datetime(df['date']).dt.normalize()
    df['sales'] = pd.to_numeric(df['sales'], errors='coerce').fillna(0.0)
    df['sell_price'] = pd.to_numeric(df['sell_price'], errors='coerce').fillna(0.0)
    return df


def _extract_m5_ids(sku: str):
    """
    Parses an M5-style SKU like FOODS_3_038 or FOODS_3_038__CA_1.
    Returns (item_id, dept_id, cat_id, store_id, state_id) — all as strings.

    SCARLET convention: if the SKU contains a double-underscore, the part after
    it is treated as the M5 store_id (e.g. CA_1).
    Falls back to sensible defaults for unknown items.
    """
    store_id = "CA_1"
    state_id = "CA"

    if "__" in sku:
        parts = sku.split("__", 1)
        item_part = parts[0]
        store_id = parts[1] if parts[1] else store_id
        state_id = store_id.split("_")[0] if "_" in store_id else state_id
    else:
        item_part = sku

    segs = item_part.split("_")
    if len(segs) >= 2:
        dept_id = f"{segs[0]}_{segs[1]}"
        cat_id = segs[0]
    else:
        dept_id = "FOODS_1"
        cat_id = "FOODS"

    return item_part, dept_id, cat_id, store_id, state_id


def _encode(value: str, code_map: dict) -> int:
    """
    Reverse-lookup in the saved cat_code_maps (format: {int_code: label}).
    Returns 0 if the value is unknown (safe default — do not silently break).
    """
    for k, v in code_map.items():
        if v == value:
            return int(k)
    return 0  # unknown category — graceful fallback


def engineer_features(
    product_id: str,
    market_id: str,
    current_date: pd.Timestamp,
    historical_df: pd.DataFrame,
    model_loader,
) -> pd.DataFrame:
    """
    Constructs a single-row DataFrame matching the exact column order in
    feature_columns.json.  Uses the cat_code_maps.json for integer encoding.
    No new encoders are fitted.

    Args:
        product_id:     SCARLET product UUID
        market_id:      SCARLET market UUID
        current_date:   The date being forecast (must NOT appear in historical_df)
        historical_df:  DataFrame with columns [date, sales, sell_price, sku]
        model_loader:   Loaded DemandModelLoader instance

    Returns:
        pd.DataFrame with exactly one row matching FEATURE_COLS order.
    """
    dt = pd.Timestamp(current_date)

    # ── Calendar features ──────────────────────────────────────────────────────
    row = {
        "day_of_week":    int(dt.dayofweek),
        "day_of_month":   int(dt.day),
        "day_of_year":    int(dt.dayofyear),
        "week_of_year":   int(dt.isocalendar().week),
        "quarter":        int(dt.quarter),
        "is_weekend":     int(dt.dayofweek >= 5),
        "is_month_start": int(dt.is_month_start),
        "is_month_end":   int(dt.is_month_end),
        # Events: we don't have a calendar table in SCARLET yet, so set to 0.
        # This is the CORRECT approach — do not fabricate event data.
        "has_event":      0,
        "event_religious": 0,
        "event_national":  0,
        "event_cultural":  0,
        "event_sporting":  0,
        # SNAP: Supplemental Nutrition Assistance Program — US-specific,
        # not available in SCARLET schema, set to 0.
        "snap": 0,
    }

    # ── Sales history → lag / rolling features ─────────────────────────────────
    if historical_df.empty:
        sales_arr = np.zeros(35)
        sell_price = 0.0
        sku = "FOODS_3_038"  # dummy fallback to a known M5 item
    else:
        sales_arr = historical_df['sales'].values.astype(float)
        sell_price = float(historical_df['sell_price'].iloc[-1])
        sku = str(historical_df['sku'].iloc[-1])

    # Pad if we don't have enough history (model still gives a prediction, just less precise)
    if len(sales_arr) < 28:
        sales_arr = np.pad(sales_arr, (28 - len(sales_arr), 0), mode='constant')

    row["lag_1"]  = float(sales_arr[-1])
    row["lag_7"]  = float(sales_arr[-7])
    row["lag_14"] = float(sales_arr[-14])
    row["lag_28"] = float(sales_arr[-28])

    row["rolling_mean_7"]  = float(np.mean(sales_arr[-7:]))
    row["rolling_std_7"]   = float(np.std(sales_arr[-7:]))
    row["rolling_mean_14"] = float(np.mean(sales_arr[-14:]))
    row["rolling_std_14"]  = float(np.std(sales_arr[-14:]))
    row["rolling_mean_28"] = float(np.mean(sales_arr[-28:]))
    row["rolling_std_28"]  = float(np.std(sales_arr[-28:]))
    row["rolling_min_28"]  = float(np.min(sales_arr[-28:]))
    row["rolling_max_28"]  = float(np.max(sales_arr[-28:]))

    # ── Price features ─────────────────────────────────────────────────────────
    if len(historical_df) >= 2:
        prev_price = float(historical_df['sell_price'].iloc[-2])
    else:
        prev_price = sell_price

    price_change     = sell_price - prev_price
    price_change_pct = (price_change / prev_price) if prev_price > 0 else 0.0
    # price_rel_to_dept: ratio of item price to avg dept price.
    # Without a full dept price table we default to 1.0 (neutral).
    price_rel_to_dept = 1.0

    row["sell_price"]        = sell_price
    row["price_lag_1"]       = prev_price
    row["price_change"]      = price_change
    row["price_change_pct"]  = price_change_pct
    row["price_rel_to_dept"] = price_rel_to_dept

    # ── Categorical encoding ────────────────────────────────────────────────────
    item_id, dept_id, cat_id, store_id, state_id = _extract_m5_ids(sku)
    maps = model_loader.cat_code_maps

    row["item_id_enc"]  = _encode(item_id,  maps.get("item_id",  {}))
    row["dept_id_enc"]  = _encode(dept_id,  maps.get("dept_id",  {}))
    row["cat_id_enc"]   = _encode(cat_id,   maps.get("cat_id",   {}))
    row["store_id_enc"] = _encode(store_id, maps.get("store_id", {}))
    row["state_id_enc"] = _encode(state_id, maps.get("state_id", {}))

    # Return in exact FEATURE_COLS order — this prevents column-order mismatch
    return pd.DataFrame([row], columns=model_loader.feature_columns)

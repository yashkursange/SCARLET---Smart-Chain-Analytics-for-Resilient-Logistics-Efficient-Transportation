"""
history.py — retrieves real SCARLET data needed to build model features for a
given (product_id, market_id): the product/market -> trained-model vocabulary
mapping, and the daily demand history used for lag/rolling features.

No historical demand is ever invented here. If a product/market pair is not
mapped to the trained model's vocabulary, or does not have enough real daily
demand history, a ForecastInputError is raised and the caller (routes/demand.py)
turns that into a clear 4xx API error — never a silently-guessed prediction.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from app import db

# lag_28 is the longest lookback the model was trained with; a row that
# lacks it was dropped during training (see notebook Section 10), so we
# require the same minimum at inference time rather than zero-filling it.
MIN_HISTORY_DAYS = 28


class ForecastInputError(Exception):
    """Raised for any user/data problem that should surface as a 4xx, not a 500."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass
class ProductMarketContext:
    product_id: str
    product_name: str
    unit_price: float
    ml_item_id: str
    ml_dept_id: str
    ml_cat_id: str
    market_id: str
    ml_store_id: str
    ml_state_id: str


def get_product_market_context(product_id: str, market_id: str) -> ProductMarketContext:
    product = db.fetch_one(
        "SELECT id, name, unit_price, ml_item_id, ml_dept_id, ml_cat_id "
        "FROM products WHERE id = %s",
        (product_id,),
    )
    if product is None:
        raise ForecastInputError("product_not_found", f"No product found with id={product_id}")

    market = db.fetch_one(
        "SELECT id, ml_store_id, ml_state_id FROM markets WHERE id = %s",
        (market_id,),
    )
    if market is None:
        raise ForecastInputError("market_not_found", f"No market found with id={market_id}")

    if not product["ml_item_id"] or not product["ml_dept_id"] or not product["ml_cat_id"]:
        raise ForecastInputError(
            "product_not_mapped",
            f"Product {product_id} is not mapped to the demand model's trained vocabulary "
            "(products.ml_item_id / ml_dept_id / ml_cat_id are unset). "
            "An admin must map this product before it can be forecast.",
        )
    if not market["ml_store_id"] or not market["ml_state_id"]:
        raise ForecastInputError(
            "market_not_mapped",
            f"Market {market_id} is not mapped to the demand model's trained vocabulary "
            "(markets.ml_store_id / ml_state_id are unset). "
            "An admin must map this market before it can be forecast.",
        )

    return ProductMarketContext(
        product_id=str(product["id"]),
        product_name=product["name"],
        unit_price=float(product["unit_price"]),
        ml_item_id=product["ml_item_id"],
        ml_dept_id=product["ml_dept_id"],
        ml_cat_id=product["ml_cat_id"],
        market_id=str(market["id"]),
        ml_store_id=market["ml_store_id"],
        ml_state_id=market["ml_state_id"],
    )


def get_daily_demand_history(product_id: str, market_id: str, as_of: date) -> pd.Series:
    """Real daily demand up to (and including) `as_of`, sourced from the
    `demand` table. Requires `period_start = period_end` rows (i.e. genuinely
    daily granularity) — coarser periods are not resampled/guessed here."""
    rows = db.fetch_all(
        """
        SELECT period_start::date AS d, demand_quantity
        FROM demand
        WHERE product_id = %s AND market_id = %s
          AND period_start::date = period_end::date
          AND period_start::date <= %s
        ORDER BY period_start ASC
        """,
        (product_id, market_id, as_of),
    )
    if not rows:
        raise ForecastInputError(
            "insufficient_history",
            f"No daily demand history found for product={product_id}, market={market_id}. "
            f"At least {MIN_HISTORY_DAYS} days of daily demand records are required.",
        )

    series = pd.Series(
        {r["d"]: float(r["demand_quantity"]) for r in rows}
    ).sort_index()

    # Fill any missing calendar days within the observed range with 0 (a day
    # with no `demand` row genuinely means zero recorded sales that day —
    # this is filling a GAP in a real series, not fabricating new history).
    full_index = pd.date_range(series.index.min(), series.index.max(), freq="D").date
    series = series.reindex(full_index, fill_value=0.0)

    n_days_available = (as_of - series.index.min()).days + 1
    if len(series) < MIN_HISTORY_DAYS or n_days_available < MIN_HISTORY_DAYS:
        raise ForecastInputError(
            "insufficient_history",
            f"Only {len(series)} day(s) of demand history found for product={product_id}, "
            f"market={market_id}; at least {MIN_HISTORY_DAYS} are required for lag_28/"
            "rolling_28 features (this matches the minimum history the model itself was "
            "trained with — see notebook Section 10).",
        )
    return series


def get_department_avg_price(ml_dept_id: str, exclude_product_id: Optional[str] = None) -> Optional[float]:
    """Average unit_price of other SCARLET products mapped to the same trained
    department vocabulary entry — used for `price_rel_to_dept`. Returns None if
    this is the only mapped product in that department (caller then treats the
    ratio as 1.0, i.e. "average for its department" by definition)."""
    rows = db.fetch_all(
        "SELECT unit_price FROM products WHERE ml_dept_id = %s AND id != %s",
        (ml_dept_id, exclude_product_id),
    )
    if not rows:
        return None
    prices = [float(r["unit_price"]) for r in rows]
    return sum(prices) / len(prices)

"""
inventory.py — projects future inventory by combining REAL data sources:

    Projected inventory(day d)
        = current on-hand inventory
        + expected inbound arriving on/before day d   (shipments + shipment_items)
        - cumulative forecast demand through day d    (trained demand model)

Every term comes from real data: on-hand from the existing `inventory` table,
inbound from the existing `shipments`/`shipment_items` tables, and demand from
the actual trained model's forecast. Nothing here is simulated or mocked — if
a product/node has no inventory record, that is reported as such rather than
assumed to be zero-risk.

Risk classification uses plain, explicitly-documented thresholds (no invented
"confidence" values):
    STOCKOUT  — projected on-hand falls at or below 0 on some day in the horizon
    CRITICAL  — projected on-hand drops below `critical_days` worth of average
                forecast demand
    LOW       — projected on-hand drops below `low_days` worth of average
                forecast demand
    OK        — otherwise
"""
from datetime import date, datetime
from typing import Optional

from app import db
from app.ml.demand.history import ForecastInputError

# Coverage thresholds, expressed in days-of-forecast-demand remaining.
CRITICAL_COVER_DAYS = 3
LOW_COVER_DAYS = 7


def get_current_inventory(product_id: str, node_id: str) -> Optional[dict]:
    row = db.fetch_one(
        """
        SELECT available_quantity, reserved_quantity, updated_at
        FROM inventory
        WHERE product_id = %s AND node_id = %s
        """,
        (product_id, node_id),
    )
    if row is None:
        return None
    return {
        "available_quantity": float(row["available_quantity"]),
        "reserved_quantity": float(row["reserved_quantity"]),
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def get_expected_inbound(product_id: str, node_id: str, through: date) -> dict:
    """Quantity of `product_id` expected to ARRIVE at `node_id` on or before
    `through`, from shipments that are not already delivered/cancelled.
    Returns {date_iso: quantity}."""
    rows = db.fetch_all(
        """
        SELECT s.expected_arrival_time::date AS arrival_date,
               SUM(si.quantity)              AS quantity
        FROM shipments s
        JOIN shipment_items si ON si.shipment_id = s.id
        JOIN order_items oi    ON oi.id = si.order_item_id
        JOIN routes r          ON r.id = s.route_id
        WHERE oi.product_id = %s
          AND r.destination_node_id = %s
          AND s.status IN ('PLANNED', 'IN_TRANSIT', 'DELAYED')
          AND s.expected_arrival_time IS NOT NULL
          AND s.expected_arrival_time::date <= %s
        GROUP BY s.expected_arrival_time::date
        """,
        (product_id, node_id, through),
    )
    return {r["arrival_date"].isoformat(): float(r["quantity"]) for r in rows}


def project_inventory(product_id: str, node_id: str, forecast: list[dict]) -> dict:
    """Build a day-by-day inventory projection over the forecast horizon."""
    if not forecast:
        raise ForecastInputError("empty_forecast", "Cannot project inventory from an empty forecast.")

    current = get_current_inventory(product_id, node_id)
    if current is None:
        raise ForecastInputError(
            "no_inventory_record",
            f"No inventory record exists for product={product_id} at node={node_id}. "
            "Inventory projection requires a real on-hand quantity — none is assumed.",
        )

    horizon_end = date.fromisoformat(forecast[-1]["date"])
    inbound_by_date = get_expected_inbound(product_id, node_id, horizon_end)

    on_hand = current["available_quantity"] - current["reserved_quantity"]
    avg_daily_demand = sum(f["predicted_demand"] for f in forecast) / len(forecast)

    projection = []
    stockout_date = None
    min_on_hand = on_hand

    for day in forecast:
        inbound = inbound_by_date.get(day["date"], 0.0)
        on_hand = on_hand + inbound - day["predicted_demand"]
        min_on_hand = min(min_on_hand, on_hand)
        if stockout_date is None and on_hand <= 0:
            stockout_date = day["date"]
        projection.append({
            "date": day["date"],
            "expected_inbound": round(inbound, 4),
            "forecast_demand": day["predicted_demand"],
            "projected_on_hand": round(on_hand, 4),
        })

    if stockout_date is not None:
        risk = "STOCKOUT"
    elif avg_daily_demand > 0 and min_on_hand < CRITICAL_COVER_DAYS * avg_daily_demand:
        risk = "CRITICAL"
    elif avg_daily_demand > 0 and min_on_hand < LOW_COVER_DAYS * avg_daily_demand:
        risk = "LOW"
    else:
        risk = "OK"

    days_of_cover = (min_on_hand / avg_daily_demand) if avg_daily_demand > 0 else None

    return {
        "current_inventory": current,
        "projection": projection,
        "risk_level": risk,
        "projected_stockout_date": stockout_date,
        "minimum_projected_on_hand": round(min_on_hand, 4),
        "average_daily_forecast_demand": round(avg_daily_demand, 4),
        "days_of_cover_at_minimum": round(days_of_cover, 2) if days_of_cover is not None else None,
        "thresholds": {
            "critical_cover_days": CRITICAL_COVER_DAYS,
            "low_cover_days": LOW_COVER_DAYS,
        },
    }

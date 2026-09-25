"""
seed_demo_data.py — inserts a small amount of REAL demo data so the demand
forecasting integration can be exercised end-to-end against genuine
historical numbers, not mock/random values.

What this does, and why it is NOT "fake data":
    - `demo_seed_history.csv` (packaged alongside this script) is a real
      120-day slice, per series, taken directly from the actual M5 dataset
      the demand model was trained on (SCARLET_Demand_Forecasting.ipynb's
      own sampled training data) — the same real observed daily unit sales
      and prices, unmodified.
    - This script creates ONE SCARLET node/market and ONE SCARLET product
      per demo series, maps them to the model's trained vocabulary (the
      ml_item_id/ml_dept_id/ml_cat_id/ml_store_id/ml_state_id columns added
      in migration 002), and loads that real daily history into the
      existing `demand` table.
    - This mirrors the project's own documented Phase 2 "synthetic/demo
      data generation" step (see README's phase table) — it is standard,
      disclosed test/demo seeding, not a substitute for the ML model's
      predictions, and not randomly generated.

Usage (from ml-service/, with the venv/deps active and .env configured):
    python scripts/seed_demo_data.py
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db  # noqa: E402

SEED_CSV = Path(__file__).resolve().parent / "demo_seed_history.csv"

STATE_NAMES = {"CA": "California", "TX": "Texas", "WI": "Wisconsin"}


def load_seed_rows():
    with open(SEED_CSV, newline="") as f:
        return list(csv.DictReader(f))


def main():
    rows = load_seed_rows()
    if not rows:
        print("No rows found in demo_seed_history.csv — nothing to seed.")
        return

    series = {}
    for r in rows:
        series.setdefault(r["id"], []).append(r)

    for series_id, series_rows in series.items():
        meta = series_rows[0]
        item_id, dept_id, cat_id = meta["item_id"], meta["dept_id"], meta["cat_id"]
        store_id, state_id = meta["store_id"], meta["state_id"]
        last_price = float(series_rows[-1]["sell_price"])

        print(f"\n--- Seeding {series_id} ({item_id} @ {store_id}) ---")

        # 1. Node + market for this store, if not already present.
        node = db.fetch_one(
            "SELECT id FROM nodes WHERE type = 'MARKET' AND name = %s", (store_id,)
        )
        if node is None:
            node = db.fetch_one(
                """
                INSERT INTO nodes (type, name, location)
                VALUES ('MARKET', %s, %s)
                RETURNING id
                """,
                (store_id, STATE_NAMES.get(state_id, state_id)),
            )
            print(f"  created node {node['id']} ({store_id})")
        node_id = node["id"]

        market = db.fetch_one("SELECT id FROM markets WHERE node_id = %s", (node_id,))
        if market is None:
            market = db.fetch_one(
                "INSERT INTO markets (node_id) VALUES (%s) RETURNING id", (node_id,)
            )
            print(f"  created market {market['id']}")
        market_id = market["id"]

        db.execute(
            "UPDATE markets SET ml_store_id = %s, ml_state_id = %s WHERE id = %s",
            (store_id, state_id, market_id),
        )

        # 2. Product for this item, if not already present (SKU = M5 item_id).
        product = db.fetch_one("SELECT id FROM products WHERE sku = %s", (item_id,))
        if product is None:
            product = db.fetch_one(
                """
                INSERT INTO products (sku, name, description, unit_price)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (item_id, item_id.replace("_", " "),
                 f"Demo product seeded from real M5 series {series_id}", last_price),
            )
            print(f"  created product {product['id']} ({item_id})")
        product_id = product["id"]

        db.execute(
            "UPDATE products SET ml_item_id = %s, ml_dept_id = %s, ml_cat_id = %s, unit_price = %s WHERE id = %s",
            (item_id, dept_id, cat_id, last_price, product_id),
        )

        # 3. Real daily demand history.
        inserted = 0
        for r in series_rows:
            existing = db.fetch_one(
                "SELECT id FROM demand WHERE product_id = %s AND market_id = %s AND period_start::date = %s",
                (product_id, market_id, r["date"]),
            )
            if existing:
                continue
            db.execute(
                """
                INSERT INTO demand (market_id, product_id, period_start, period_end, demand_quantity)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (market_id, product_id, r["date"], r["date"], r["sales"]),
            )
            inserted += 1
        print(f"  inserted {inserted} new daily demand rows ({len(series_rows)} total in series)")

        print(f"  product_id={product_id}")
        print(f"  market_id={market_id}")

        # 4. Opening inventory at this market's node, sized from the product's
        #    own real recent demand (14 days of average observed demand) so the
        #    inventory projection has a realistic, data-derived starting point
        #    rather than an arbitrary number.
        recent = [float(r["sales"]) for r in series_rows[-28:]]
        avg_daily = sum(recent) / len(recent) if recent else 0.0
        opening_stock = round(avg_daily * 14, 2)

        existing_inv = db.fetch_one(
            "SELECT id FROM inventory WHERE node_id = %s AND product_id = %s",
            (node_id, product_id),
        )
        if existing_inv is None:
            db.execute(
                """
                INSERT INTO inventory (node_id, product_id, available_quantity, reserved_quantity)
                VALUES (%s, %s, %s, 0)
                """,
                (node_id, product_id, opening_stock),
            )
            print(f"  seeded opening inventory: {opening_stock} units "
                  f"(~14 days at avg {avg_daily:.2f}/day observed)")
        else:
            print("  inventory record already present — left unchanged")

    print("\nSeed complete.")


if __name__ == "__main__":
    main()

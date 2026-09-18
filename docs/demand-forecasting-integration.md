# Demand Forecasting Integration — Architecture

How SCARLET's trained demand-forecasting model is wired into the running
application. Complements `docs/architecture.md` (Phase 1 foundation).

---

## Request flow

```
                USER (browser)
                      │
                      ▼
        React  frontend/src/pages/DemandForecast.jsx
                      │  POST /api/forecast/demand
                      │  POST /api/forecast/inventory-projection
                      ▼
        Express  backend/src/routes/forecast.js
                      │  POST /api/ml/demand/forecast
                      │  POST /api/ml/inventory/projection
                      ▼
        FastAPI  ml-service/app/routes/{demand,inventory}.py
                      │
        ┌─────────────┴──────────────┐
        ▼                            ▼
  PostgreSQL                  Trained model
  (products, markets,         models/demand/demand_model.pkl
   demand, inventory,         loaded ONCE at startup
   shipments)                 (app/models/loader.py)
        │                            │
        └─────────────┬──────────────┘
                      ▼
              DEMAND FORECAST
                      │
                      ▼
          INVENTORY PROJECTION
          (app/ml/demand/inventory.py)
                      │
                      ▼
              STOCKOUT RISK
          OK / LOW / CRITICAL / STOCKOUT
```

React never calls the ML service directly — including for health status, which
is proxied through Express at `GET /api/health/ml`.

---

## Module responsibilities (ml-service)

| Module | Responsibility |
|---|---|
| `app/models/loader.py` | Load + validate the five artifacts **once** at startup; expose model, feature schema, category maps, metadata, metrics |
| `app/ml/demand/history.py` | Resolve product/market → model vocabulary; fetch real daily demand from PostgreSQL; raise typed errors for missing/unmapped/insufficient data |
| `app/ml/demand/features.py` | Reproduce the notebook's feature engineering exactly, in the model's own column order |
| `app/ml/demand/predictor.py` | Recursive multi-day forecasting (the notebook's approach) |
| `app/ml/demand/inventory.py` | Project inventory from the forecast; classify stockout risk |
| `app/routes/*.py` | HTTP layer, validation, typed error → HTTP status mapping |

---

## Inference correctness

Two properties must hold for production inference to match training:

**1. Identical feature construction.** Feature *names and order* come from
`feature_columns.json` itself (the file the notebook exported), not from a
hand-maintained list. Categorical integer codes are reverse-looked-up from
`cat_code_maps.json`. A missing or extra feature raises rather than silently
mis-aligning the vector.

**2. No leakage.** Every lag/rolling feature is computed from a history array
that ends at `t-1`. Rolling windows are taken over that already-shifted array, so
the day being predicted is never inside its own window — the same rule the
notebook enforces with `shift(1)` before `.rolling()`.

For multi-day horizons the model's own prediction for day *n* becomes the
most-recent observation for day *n+1*. No future actual demand is ever read.

---

## Database integration

Migration `002_ml_demand_forecasting.sql`:

| Change | Why |
|---|---|
| `products.ml_item_id`, `ml_dept_id`, `ml_cat_id` | Map a SCARLET product to the entry in the model's trained vocabulary it should be scored as |
| `markets.ml_store_id`, `ml_state_id` | Same, for the store/state features |
| `demand_forecasts` table | Persist generated forecasts (avoids recompute, gives "last generated at", gives inventory logic one place to read the latest forecast) |

All columns are **nullable and additive**. No existing table was altered
destructively and no existing column changed type. Unmapped rows produce a clear
422, never a guessed prediction.

Existing tables read (never duplicated): `products`, `markets`, `demand`,
`inventory`, `shipments`, `shipment_items`, `order_items`, `routes`, `nodes`.

---

## Inventory projection

```
projected_on_hand(d) = on_hand(d-1) + expected_inbound(d) − forecast_demand(d)

on_hand(start)   = inventory.available_quantity − inventory.reserved_quantity
expected_inbound = Σ shipment_items.quantity
                     for shipments arriving on d at this market's node
                     (status PLANNED / IN_TRANSIT / DELAYED)
forecast_demand  = the trained model's prediction for d
```

Risk thresholds (explicit, documented, no invented confidence scores):

| Level | Condition |
|---|---|
| `STOCKOUT` | projected on-hand ≤ 0 on some day in the horizon |
| `CRITICAL` | minimum projected on-hand < 3 × average daily forecast demand |
| `LOW` | minimum projected on-hand < 7 × average daily forecast demand |
| `OK` | otherwise |

---

## Health and failure modes

`GET /health` distinguishes three independent conditions, so a partial outage is
never reported as healthy:

- ML service reachable
- `demand_model`: `loaded` / `not_loaded` (+ the load error)
- `database`: `connected` / `error`

Express degrades independently: if the ML service is down, forecasting returns
503 while `GET /api/health` and the rest of the app stay fully operational.
Structured ML-service errors (404/422) are forwarded verbatim with their
`error_code`, so the UI can show a specific, actionable message.

---

## Not yet implemented (genuine dependencies)

**Digital Twin / simulation integration is not implemented because there is no
Digital Twin or simulation engine in the codebase.** `backend/src/` contains only
`app.js`, `config/db.js`, `routes/health.js` and `routes/forecast.js`; there is no
`TwinState`, SimPy process, or NetworkX graph anywhere in the repository — these
appear in the README only as Phase 4+ plans. Rather than fabricate one, the
forecast is exposed through a clean API and persisted to `demand_forecasts`, so a
future Digital Twin can consume it directly:

```python
# Future twin state hydration
forecast = requests.post(f"{ML_SERVICE_URL}/api/ml/demand/forecast",
                         json={"product_id": ..., "market_id": ..., "horizon": 28}).json()
twin_state.set_expected_demand(forecast["forecast"])
```

The inventory-projection endpoint already implements the
`forecast → inventory projection → stockout risk` half of that target pipeline;
only the simulation/ripple-effect half awaits the Twin itself.

See `ml-service/README.md` for the other disclosed limitations (calendar/SNAP
features, price history).

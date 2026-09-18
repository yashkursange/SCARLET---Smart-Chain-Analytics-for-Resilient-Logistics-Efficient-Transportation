# SCARLET ML Service

Python FastAPI service hosting SCARLET's trained **demand forecasting model**
and the forecast-driven **inventory projection / stockout risk** logic.

```
React ──> Express ──> FastAPI (this service) ──> trained model
                            │
                            └──> PostgreSQL (existing SCARLET data)
```

---

## The model

The artifacts in `models/demand/` are the **exact, unmodified files exported by
`SCARLET_Demand_Forecasting.ipynb` (Section 20)**. Nothing here retrains,
re-tunes, or substitutes the model.

| | |
|---|---|
| Model | `XGBRegressor` (tuned via Optuna in the notebook) |
| Version | `scarlet-demand-v1.0` |
| Features | 36 (see `models/demand/feature_columns.json`) |
| Max horizon | 28 days |
| Test MAE | 0.9812 |
| Test RMSE | 1.8177 |
| Test sMAPE | 138.05 % |
| Test WAPE | 69.50 % |

All metrics come from `models/demand/metrics.json` and are surfaced through the
API — never hard-coded in the backend or frontend.

### Artifacts

| File | Purpose |
|---|---|
| `demand_model.pkl` | The fitted model (joblib) |
| `feature_columns.json` | Exact feature names **and order** the model expects |
| `cat_code_maps.json` | Integer ↔ label maps for the categorical features |
| `model_metadata.json` | Model type, hyperparameters, versions, horizon |
| `metrics.json` | Validation/test metrics + baseline comparison |

All five are required; the service reports `demand_model.status = "not_loaded"`
on `/health` if any is missing, rather than starting up pretending to be healthy.

---

## Setup

```bash
cd ml-service
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp ../.env.example .env          # then edit DB_* values
uvicorn app.main:app --reload --port 8000
```

Seed the real demo data used for end-to-end testing (see "Demo data" below):

```bash
python scripts/seed_demo_data.py
```

Run tests:

```bash
pytest                           # 27 tests
```

---

## Endpoints

### `GET /health`

```json
{
  "status": "ok",
  "service": "ml-service",
  "database": "connected",
  "demand_model": { "status": "loaded", "name": "XGBRegressor",
                    "version": "scarlet-demand-v1.0", "error": null }
}
```

`status` is `"degraded"` if either the database or the model is unavailable.

### `POST /api/ml/demand/forecast`

```json
{ "product_id": "<uuid>", "market_id": "<uuid>", "horizon": 7,
  "forecast_date": "2016-05-23" }
```

Returns the forecast, the recent history it was built from, real model metadata
and metrics, and the percentage change vs. recent demand.

### `POST /api/ml/inventory/projection`

Same input. Runs the forecast, then projects inventory day by day:

```
projected on hand = current on hand + expected inbound − forecast demand
```

and classifies risk as `OK` / `LOW` / `CRITICAL` / `STOCKOUT`.

### Error codes

| Code | HTTP | Meaning |
|---|---|---|
| `product_not_found` / `market_not_found` | 404 | No such row |
| `product_not_mapped` / `market_not_mapped` | 422 | Missing `ml_*` model-vocabulary mapping |
| `insufficient_history` | 422 | < 28 days of daily demand |
| `unknown_model_vocabulary` | 422 | Mapped label isn't in the trained vocabulary |
| `no_inventory_record` | 422 | No `inventory` row to project from |
| `model_not_loaded` | 503 | Artifacts failed to load |

No request ever falls back to a guessed or mocked prediction.

---

## Inference correctness

`app/ml/demand/features.py` reproduces the notebook's feature engineering
exactly: the same feature names, the same column order (taken from
`feature_columns.json` itself, not re-listed), the same categorical codes (read
from `cat_code_maps.json`), and the same leakage rule — every rolling window is
computed on a series that has already been shifted by one day, so it **ends at
`t-1` and never includes the day being predicted**.

Multi-day forecasts use the notebook's recursive approach
(`app/ml/demand/predictor.py`): each day beyond the first feeds the model's own
previous prediction back in as the new most-recent observation. No future actual
demand is ever read.

---

## Known limitations

These are genuine, disclosed gaps — not hidden behind fabricated values.

1. **Calendar / event / SNAP features are always 0.** The model was trained with
   `has_event`, the four event-type flags, and `snap`, but SCARLET's schema has
   no calendar/holiday/SNAP table. Rather than invent holiday data, these are
   sent as "no event". Closing this gap means adding a calendar table and
   populating those features from it.

2. **Price is treated as constant.** SCARLET stores one current `unit_price` per
   product, not the daily per-store price history the model trained on. So
   `price_lag_1 == sell_price` and `price_change`/`price_change_pct` are `0`.
   `price_rel_to_dept` *is* real, computed from other products mapped to the same
   department. Closing this gap means adding a price-history table.

3. **Products/markets must be mapped to the model's vocabulary.** The model's
   categorical features were trained on the M5 dataset's item/store vocabulary,
   which has no inherent link to SCARLET's UUID catalog. Migration
   `002_ml_demand_forecasting.sql` adds `ml_item_id`, `ml_dept_id`, `ml_cat_id`
   on `products` and `ml_store_id`, `ml_state_id` on `markets` for this. Unmapped
   rows return `product_not_mapped` / `market_not_mapped` instead of a guess.

4. **Retraining is out of scope for this service.** It loads and serves the
   notebook's model. To change the model, re-run the notebook and replace
   `models/demand/`.

---

## Demo data

`scripts/seed_demo_data.py` loads `scripts/demo_seed_history.csv`: a real
120-day-per-series slice of the actual M5 data the model was trained on
(unmodified observed daily unit sales and prices), for two series. It creates the
matching SCARLET node/market/product rows, sets their `ml_*` mappings, loads the
real daily history into `demand`, and seeds an opening `inventory` quantity
derived from each product's own observed average demand (≈14 days of cover).

This is disclosed demo/test seeding so the pipeline can be exercised end to end.
It is **not** a substitute for model predictions — every forecast still comes
from the trained model. The script is idempotent.

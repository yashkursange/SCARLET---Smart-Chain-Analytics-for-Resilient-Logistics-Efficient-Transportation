-- =============================================================================
-- SCARLET — Migration 002: Demand Forecasting ML Integration
-- =============================================================================
--
-- WHY THIS MIGRATION EXISTS
--
-- The trained demand model (ml-service/models/demand/) was trained on the
-- public M5 Walmart dataset. Its categorical features (item/department/
-- category/store/state) were integer-encoded against that dataset's own
-- vocabulary (see ml-service/models/demand/cat_code_maps.json) — a fixed
-- vocabulary the model already knows, that has no natural correspondence to
-- SCARLET's own arbitrary UUID product/market catalog.
--
-- To let a SCARLET `products` row be scored by this model, we need to tell
-- the ML service which entry in the model's trained vocabulary that product
-- (and its market/store) should be treated as. That mapping is genuine
-- integration configuration — not invented data — and is the smallest
-- reasonable schema change that makes exact-feature-reproduction possible
-- per product, as required by the integration brief.
--
-- Unmapped products/markets are NOT guessed at inference time: the ML
-- service returns a clear 422 error instead (see
-- ml-service/app/ml/demand/features.py::require_mapping).
-- =============================================================================

-- Product -> trained-model item/department/category vocabulary.
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS ml_item_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS ml_dept_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS ml_cat_id  VARCHAR(64);

COMMENT ON COLUMN products.ml_item_id IS
    'Trained demand-model item_id vocabulary entry this product is mapped to (nullable = not yet mapped, forecasting unavailable for this product).';
COMMENT ON COLUMN products.ml_dept_id IS
    'Trained demand-model dept_id vocabulary entry for this product.';
COMMENT ON COLUMN products.ml_cat_id IS
    'Trained demand-model cat_id vocabulary entry for this product.';

-- Market -> trained-model store/state vocabulary.
ALTER TABLE markets
    ADD COLUMN IF NOT EXISTS ml_store_id VARCHAR(16),
    ADD COLUMN IF NOT EXISTS ml_state_id VARCHAR(8);

COMMENT ON COLUMN markets.ml_store_id IS
    'Trained demand-model store_id vocabulary entry this market is mapped to (nullable = not yet mapped).';
COMMENT ON COLUMN markets.ml_state_id IS
    'Trained demand-model state_id vocabulary entry for this market.';

-- Forecast persistence — lets the API avoid recomputing on every dashboard
-- load, gives "last generated at" for the UI, and gives the inventory
-- projection logic a single real source for "latest forecast per product".
CREATE TABLE IF NOT EXISTS demand_forecasts (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id        UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    market_id         UUID NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    forecast_date     DATE NOT NULL,
    predicted_demand  NUMERIC NOT NULL CHECK (predicted_demand >= 0),
    model_version     VARCHAR(64) NOT NULL,
    generated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (product_id, market_id, forecast_date, model_version)
);

CREATE INDEX IF NOT EXISTS idx_demand_forecasts_product_market
    ON demand_forecasts(product_id, market_id);
CREATE INDEX IF NOT EXISTS idx_demand_forecasts_generated_at
    ON demand_forecasts(generated_at);

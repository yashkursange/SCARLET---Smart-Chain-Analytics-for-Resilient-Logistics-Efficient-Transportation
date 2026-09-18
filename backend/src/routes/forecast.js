/**
 * routes/forecast.js — proxies demand-forecast requests to the Python ML service.
 *
 * Architecture: React → Express → FastAPI → trained model.
 * React never calls the ML service directly (see docs/architecture.md).
 */
const express = require('express');
const router = express.Router();
const axios = require('axios');

const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:8000';

/**
 * Forward an ML-service error to the client while PRESERVING its status code
 * and structured error_code. Without this, meaningful 404/422 responses
 * (product not found, product not mapped, insufficient history) would be
 * flattened into an unhelpful generic 500.
 */
function forwardError(error, res, fallbackMessage) {
  if (error.response) {
    const status = error.response.status;
    const body = error.response.data;

    // 503 from the ML service means the model itself isn't loaded.
    if (status === 503) {
      return res.status(503).json(
        body && body.error ? body : { error: 'Demand forecasting service is currently unavailable.' }
      );
    }
    // Pass through the ML service's own structured client errors verbatim.
    if (status >= 400 && status < 500 && body) {
      return res.status(status).json(body);
    }
    return res.status(status >= 500 ? 502 : status).json({ error: fallbackMessage });
  }

  // No response at all — the ML service is unreachable (down, wrong URL, timeout).
  if (error.code === 'ECONNREFUSED' || error.code === 'ETIMEDOUT' || error.code === 'ECONNABORTED') {
    return res.status(503).json({ error: 'Demand forecasting service is currently unavailable.' });
  }

  return res.status(500).json({ error: fallbackMessage });
}

function validateBody(req, res) {
  const { product_id, market_id, horizon } = req.body || {};
  if (!product_id || !market_id) {
    res.status(400).json({
      error_code: 'invalid_request',
      error: 'Both product_id and market_id are required.',
    });
    return null;
  }
  if (horizon !== undefined && (!Number.isInteger(horizon) || horizon < 1 || horizon > 28)) {
    res.status(400).json({
      error_code: 'invalid_request',
      error: 'horizon must be an integer between 1 and 28.',
    });
    return null;
  }
  return { product_id, market_id, forecast_date: req.body.forecast_date, horizon: horizon || 7 };
}

// POST /api/forecast/demand — demand forecast from the trained model.
router.post('/demand', async (req, res) => {
  const payload = validateBody(req, res);
  if (!payload) return;

  try {
    const response = await axios.post(`${ML_SERVICE_URL}/api/ml/demand/forecast`, payload);
    res.json(response.data);
  } catch (error) {
    console.error('[forecast] Demand forecast failed:', error.message);
    forwardError(error, res, 'Failed to generate demand forecast.');
  }
});

// POST /api/forecast/inventory-projection — forecast-driven inventory projection
// and stockout-risk classification.
router.post('/inventory-projection', async (req, res) => {
  const payload = validateBody(req, res);
  if (!payload) return;

  try {
    const response = await axios.post(`${ML_SERVICE_URL}/api/ml/inventory/projection`, payload);
    res.json(response.data);
  } catch (error) {
    console.error('[forecast] Inventory projection failed:', error.message);
    forwardError(error, res, 'Failed to generate inventory projection.');
  }
});

module.exports = router;

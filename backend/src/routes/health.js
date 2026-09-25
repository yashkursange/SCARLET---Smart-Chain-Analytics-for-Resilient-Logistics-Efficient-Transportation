/**
 * routes/health.js — Express health-check route
 *
 * GET /api/health
 *   Returns the operational status of the Express service and its
 *   PostgreSQL connection.  The React frontend polls this endpoint to
 *   display service-status cards on the dashboard.
 */

const express = require('express');
const axios   = require('axios');
const pool    = require('../config/db');

const router = express.Router();

router.get('/', async (req, res) => {
  let dbStatus = 'connected';

  try {
    // Lightweight query: just confirms the DB is reachable and the user
    // has SELECT permission.  No application tables are read here.
    await pool.query('SELECT 1');
  } catch (err) {
    console.error('[health] Database check failed:', err.message);
    dbStatus = 'error';
  }

  const status = dbStatus === 'connected' ? 'ok' : 'degraded';

  res.status(status === 'ok' ? 200 : 503).json({
    status,
    service:   'scarlet-backend',
    database:  dbStatus,
    timestamp: new Date().toISOString(),
  });
});

/**
 * GET /api/health/ml
 *   Proxies the Python ML service's health endpoint, so the React dashboard
 *   can show ML-service + demand-model status while still only ever talking
 *   to Express (see the architecture rule in docs/architecture.md: React
 *   never calls the ML service directly).
 */
router.get('/ml', async (req, res) => {
  const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:8000';
  try {
    const response = await axios.get(`${ML_SERVICE_URL}/health`, { timeout: 5000 });
    res.status(200).json(response.data);
  } catch (err) {
    console.error('[health] ML service check failed:', err.message);
    // If the ML service replied but is degraded, pass its own body through.
    if (err.response && err.response.data) {
      return res.status(503).json(err.response.data);
    }
    res.status(503).json({
      status: 'error',
      service: 'ml-service',
      database: 'unknown',
      demand_model: { status: 'not_loaded', name: null, version: null,
                       error: 'ML service unreachable' },
      timestamp: new Date().toISOString(),
    });
  }
});

module.exports = router;
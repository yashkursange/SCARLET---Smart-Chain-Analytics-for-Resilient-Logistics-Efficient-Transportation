/**
 * routes/health.js — Express health-check route
 *
 * GET /api/health
 *   Returns the operational status of the Express service and its
 *   PostgreSQL connection.  The React frontend polls this endpoint to
 *   display service-status cards on the dashboard.
 */

const express = require('express');
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

  res.status(200).json({
    status,
    service:   'scarlet-backend',
    database:  dbStatus,
    timestamp: new Date().toISOString(),
  });
});

module.exports = router;

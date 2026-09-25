/**
 * app.js — Express application factory
 *
 * Separating app creation from server.listen() lets tests import `app`
 * without binding to a port, which keeps tests fast and port-conflict-free.
 */

const express      = require('express');
const cors         = require('cors');
const healthRouter = require('./routes/health');

const app = express();

// ── Middleware ────────────────────────────────────────────────────────────────

// Allow the React dev server (and future production origin) to call this API.
app.use(cors({
  origin: process.env.FRONTEND_URL || '*',
}));

app.use(express.json());

// ── Routes ────────────────────────────────────────────────────────────────────

// Architecture note:
//   All API routes are prefixed with /api so they are clearly distinguished
//   from any future static-file serving or proxy paths.
app.use('/api/health', healthRouter);
const forecastRouter = require('./routes/forecast');
app.use('/api/forecast', forecastRouter);

// 404 catch-all for undefined routes.
app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

module.exports = app;

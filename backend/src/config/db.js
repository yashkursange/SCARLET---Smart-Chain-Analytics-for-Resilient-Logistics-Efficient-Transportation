/**
 * db.js — PostgreSQL connection pool
 *
 * Architecture note:
 *   All database access goes through this single pool instance.
 *   The pool is created once at startup and reused across requests.
 *   Connection credentials come exclusively from environment variables.
 */

const { Pool } = require('pg');

const pool = new Pool({
  host:     process.env.DB_HOST,
  port:     parseInt(process.env.DB_PORT, 10),
  database: process.env.DB_NAME,
  user:     process.env.DB_USER,
  password: process.env.DB_PASSWORD,
});

// Log connection errors so they surface in the console without crashing.
pool.on('error', (err) => {
  console.error('[db] Unexpected pool error:', err.message);
});

module.exports = pool;

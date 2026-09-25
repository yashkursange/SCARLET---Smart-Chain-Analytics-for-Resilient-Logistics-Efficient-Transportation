/**
 * api/health.js — HTTP helpers for health-check endpoints
 *
 * Architecture note:
 *   React calls Express at VITE_API_URL — never PostgreSQL, and never the
 *   Python ML service, directly. ML-service status is proxied through
 *   Express at /api/health/ml.
 */

import axios from 'axios'

const expressClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 5000,
})

/**
 * Fetch the Express backend health status.
 * @returns {{ status: string, database: string, timestamp: string }}
 */
export async function fetchBackendHealth() {
  const { data } = await expressClient.get('/api/health')
  return data
}

/**
 * Fetch the Python FastAPI ML service health status (proxied via Express).
 * @returns {{ status: string, service: string, database: string,
 *             demand_model: { status: string, name: string|null,
 *                             version: string|null, error: string|null },
 *             timestamp: string }}
 */
export async function fetchMlServiceHealth() {
  const { data } = await expressClient.get('/api/health/ml')
  return data
}

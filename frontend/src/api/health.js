/**
 * api/health.js — HTTP helpers for health-check endpoints
 *
 * Architecture note:
 *   React calls Express at VITE_API_URL — never PostgreSQL directly.
 *   The ML service URL is called directly in Phase 1 only for dashboard
 *   status visibility; in production all ML calls should be proxied via Express.
 */

import axios from 'axios'

const expressClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 5000,
})

const mlClient = axios.create({
  baseURL: import.meta.env.VITE_ML_SERVICE_URL,
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
 * Fetch the Python FastAPI ML service health status.
 * @returns {{ status: string, service: string, timestamp: string }}
 */
export async function fetchMlServiceHealth() {
  const { data } = await mlClient.get('/health')
  return data
}

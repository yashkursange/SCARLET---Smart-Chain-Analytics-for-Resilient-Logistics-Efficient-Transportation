/**
 * App.jsx — SCARLET Phase 1 Dashboard
 *
 * Displays real-time status for:
 *   1. Frontend (always "ok" — if this renders, React is working)
 *   2. Express API (fetched from /api/health)
 *   3. PostgreSQL (reported inside the Express health response)
 *   4. Python FastAPI ML service (fetched from /health)
 *
 * Polls every 30 seconds so the dashboard stays current without WebSockets.
 */

import { useState, useEffect, useCallback } from 'react'
import { fetchBackendHealth, fetchMlServiceHealth } from './api/health'
import StatusCard from './components/StatusCard'

const POLL_INTERVAL_MS = 30_000

export default function App() {
  // ── State ─────────────────────────────────────────────────────────────────
  const [backendStatus,  setBackendStatus]  = useState('loading')
  const [databaseStatus, setDatabaseStatus] = useState('loading')
  const [mlStatus,       setMlStatus]       = useState('loading')
  const [lastChecked,    setLastChecked]     = useState(null)

  // ── Data fetching ─────────────────────────────────────────────────────────
  const checkHealth = useCallback(async () => {
    // Express + PostgreSQL
    try {
      const backendData = await fetchBackendHealth()
      setBackendStatus(backendData.status === 'ok' ? 'ok' : 'error')
      setDatabaseStatus(backendData.database === 'connected' ? 'ok' : 'error')
    } catch {
      setBackendStatus('error')
      setDatabaseStatus('error')
    }

    // Python ML service
    try {
      const mlData = await fetchMlServiceHealth()
      setMlStatus(mlData.status === 'ok' ? 'ok' : 'error')
    } catch {
      setMlStatus('error')
    }

    setLastChecked(new Date())
  }, [])

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [checkHealth])

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans antialiased">

      {/* ── Header ── */}
      <header className="border-b border-slate-800/70 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Logo mark */}
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-red-500 to-rose-700 flex items-center justify-center shadow-lg shadow-red-900/40">
            <span className="text-sm font-black text-white tracking-tight">S</span>
          </div>
          <span className="text-sm font-bold tracking-widest uppercase text-slate-200">
            SCARLET
          </span>
        </div>
        <span className="text-xs text-slate-500">Phase 1 — Foundation</span>
      </header>

      {/* ── Hero ── */}
      <main className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight leading-tight mb-3">
          Supply Chain{' '}
          <span className="bg-gradient-to-r from-red-400 to-rose-500 bg-clip-text text-transparent">
            Digital Twin
          </span>
        </h1>
        <p className="text-slate-400 text-base mb-12 max-w-xl leading-relaxed">
          Smart Supply Chain Analytics for Resilience &amp; Logistics —
          real-time service health overview.
        </p>

        {/* ── Status grid ── */}
        <section aria-label="Service status">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-4">
            System Status
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <StatusCard
              id="status-frontend"
              title="Frontend"
              status="ok"
              detail="React + Vite running"
            />
            <StatusCard
              id="status-backend"
              title="Express API"
              status={backendStatus}
              detail={backendStatus === 'loading' ? undefined : `http://localhost:4000/api/health`}
            />
            <StatusCard
              id="status-database"
              title="PostgreSQL"
              status={databaseStatus}
              detail={databaseStatus === 'loading' ? undefined : 'Reported by Express health check'}
            />
            <StatusCard
              id="status-ml-service"
              title="Python ML Service"
              status={mlStatus}
              detail={mlStatus === 'loading' ? undefined : `http://localhost:8000/health`}
            />
          </div>
        </section>

        {/* ── Last checked ── */}
        {lastChecked && (
          <p className="mt-6 text-xs text-slate-600">
            Last checked: {lastChecked.toLocaleTimeString()} — polls every 30 s
          </p>
        )}

        {/* ── Manual refresh ── */}
        <button
          id="btn-refresh"
          onClick={checkHealth}
          className="mt-4 text-xs text-slate-500 hover:text-red-400 transition-colors underline underline-offset-2"
        >
          Refresh now
        </button>
      </main>
    </div>
  )
}

# SCARLET — Architecture Overview

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT (Browser)                      │
│                React + Vite + Tailwind                   │
│                     Port: 5173                           │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTP/JSON
                          ▼
┌─────────────────────────────────────────────────────────┐
│               APPLICATION API (Express)                  │
│                    Node.js 20+                           │
│                     Port: 4000                           │
│                                                          │
│  Routes:                                                 │
│   GET /api/health   → DB connectivity check             │
└──────────────┬──────────────────────────┬───────────────┘
               │ SQL (pg pool)            │ HTTP/JSON (future)
               ▼                          ▼
┌──────────────────────┐    ┌─────────────────────────────┐
│  PostgreSQL 15+      │    │   ML / AI Service (FastAPI)  │
│  Port: 5432          │    │   Python 3.12+               │
│  Database: scarlet   │    │   Port: 8000                 │
│                      │    │                              │
│  Phase 1: health     │    │  Routes:                     │
│  check table only    │    │   GET /health                │
└──────────────────────┘    └─────────────────────────────┘
```

## Service Responsibilities

### Frontend (`/frontend`)
- Renders the SCARLET dashboard
- Polls status endpoints to display service health
- Makes all API calls through Express — never touches PostgreSQL directly

### Backend API (`/backend`)
- Single source of truth for business logic
- Manages PostgreSQL connection pool
- Will proxy ML/simulation requests to FastAPI (Phase 2+)

### ML Service (`/ml-service`)
- Stateless inference and simulation service
- Called only by Express, never by the frontend
- Houses all Python ML, simulation, and optimisation code

### Database (`/database`)
- PostgreSQL schema definitions and migration scripts
- `init.sql` is the single authoritative schema source

## Data Flow (Phase 1)

```
Browser → GET / → React renders status page
        → React calls Express GET /api/health
        → Express queries PostgreSQL (SELECT 1)
        → Express returns { status, database, timestamp }
        → React calls FastAPI GET /health (via proxy or direct for Phase 1)
        → FastAPI returns { status, service }
        → React renders all status cards
```

## Environment Variable Strategy

All service URLs, ports and credentials live in `.env` files.
No value is hard-coded in source. See `.env.example` at the repo root.

## Phase 1 Scope

Phase 1 establishes only:
- Repository structure
- Working dev servers for all three services
- PostgreSQL connection validation
- Health-check endpoints
- Basic test suites
- This documentation

**Not in Phase 1:** ML models, simulation, optimisation, auth, Docker, WebSockets.

---

## Update — Demand Forecasting Integration

The demand-forecasting model is now integrated and serving real predictions.
This changes two Phase 1 statements above:

1. **React no longer calls FastAPI directly.** ML-service status is proxied
   through Express at `GET /api/health/ml`, so React only ever talks to Express.
2. **The ML service is no longer health-check only.** It loads the trained model
   at startup and serves `/api/ml/demand/forecast` and
   `/api/ml/inventory/projection`.

See [`demand-forecasting-integration.md`](demand-forecasting-integration.md) for
the full request flow, inference-correctness rules, schema changes, and the
honestly-documented gaps (no Digital Twin exists yet in the codebase).

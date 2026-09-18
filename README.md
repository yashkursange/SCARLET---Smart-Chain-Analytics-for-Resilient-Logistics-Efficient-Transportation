# SCARLET

**Smart Supply Chain Analytics for Resilience & Logistics**

A research project building an AI-driven Supply Chain Digital Twin.

---

## Project Objective

SCARLET represents a multi-echelon supply chain as a living digital twin that:

1. **Represents** — models a multi-echelon supply chain topology
2. **Predicts** — forecasts demand and disruption likelihood (ML)
3. **Simulates** — propagates disruption ripple effects (SimPy + NetworkX)
4. **Evaluates** — quantifies disruption impact and resilience metrics
5. **Optimises** — recommends recovery strategies (OR-Tools)
6. **Visualises** — provides an interactive web dashboard (React)

---

## Architecture

```
React Frontend  (Vite + Tailwind)
      │  HTTP / JSON
      ▼
Node / Express API  (port 4000)
      │  HTTP / JSON
      ├─────────────────────────────────────────┐
      ▼                                         ▼
PostgreSQL  (port 5432)  <────>  Python FastAPI ML Service  (port 8000)
                                        │
                                  Trained demand model
                                  (XGBoost, exported from the notebook)
                                        │
                                  SimPy / NetworkX / OR-Tools  (Phase 4+)
```

**Key design rules:**
- React only talks to Express; never directly to PostgreSQL.
- Express proxies ML/simulation requests to FastAPI.
- All configuration via environment variables — no hard-coded secrets.

---

## Repository Structure

```
SCARLET/
├── frontend/        React + Vite + Tailwind dashboard
├── backend/         Node.js + Express API
├── ml-service/      Python FastAPI AI/ML service
│   ├── app/         FastAPI app: routes, model loader, feature engineering
│   ├── models/
│   │   └── demand/  Trained demand-model artifacts (from the notebook)
│   └── scripts/     Demo data seeding
├── database/        SQL schema and migration scripts
│   ├── init.sql
│   └── migrations/  Incremental schema changes
├── data/
│   ├── raw/         Original, unmodified source data
│   ├── processed/   Cleaned and transformed data
│   └── synthetic/   Synthetically generated datasets
├── docs/            Extended documentation and architecture diagrams
└── tests/           Cross-service integration tests (future phases)
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, Recharts, React Flow |
| Backend API | Node.js, Express.js |
| Database | PostgreSQL |
| ML Service | Python 3.12+, FastAPI, Pandas, NumPy, Scikit-learn, XGBoost |
| Simulation | SimPy, NetworkX *(Phase 3+)* |
| Optimisation | OR-Tools *(Phase 4+)* |
| Deep Learning | PyTorch *(Phase 3+)* |

---

## Prerequisites

| Tool | Version |
|---|---|
| Node.js | 20+ |
| npm | 10+ |
| Python | 3.12+ |
| PostgreSQL | 15+ |

---

## Quick Start

### 1 — Clone and configure environment

```bash
git clone <repo-url>
cd SCARLET

# Copy the example env file and fill in your values
cp .env.example .env
```

Edit `.env` with your PostgreSQL credentials and preferred ports.

### 2 — Set up the database

```bash
psql -U postgres -c "CREATE DATABASE scarlet;"
psql -U postgres -c "CREATE USER scarlet_user WITH ENCRYPTED PASSWORD 'your_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE scarlet TO scarlet_user;"
psql -U scarlet_user -d scarlet -f database/init.sql

# Apply migrations (adds demand-model mapping columns + demand_forecasts table)
psql -U scarlet_user -d scarlet -f database/migrations/002_ml_demand_forecasting.sql
```

### 3 — Start the Express backend

```bash
cd backend
cp ../.env.example .env   # edit with your values
npm install
npm run dev
# → http://localhost:4000/api/health
```

### 4 — Start the Python ML service

```bash
cd ml-service
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cp ../.env.example .env     # edit with your values
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/health

# Optional: seed real demo data so forecasting can be exercised end-to-end
python scripts/seed_demo_data.py
```

The trained demand model is loaded once at startup from
`ml-service/models/demand/`. If those artifacts are missing, `/health` reports
`demand_model.status = "not_loaded"` rather than falsely reporting healthy.

### 5 — Start the React frontend

```bash
cd frontend
npm install
# VITE_API_URL is already set in frontend/.env
npm run dev
# → http://localhost:5173
```

### 6 — Run tests

```bash
# Backend tests
cd backend && npm test

# ML service tests (27 tests)
cd ml-service && pytest

# End-to-end UI test — drives the real React app in a headless browser and
# asserts the displayed numbers match the trained model's own output.
# Requires all four services running plus the demo seed data.
pip install playwright && python -m playwright install chromium
python tests/e2e_ui_test.py <product_id> <market_id>
```

---

## Environment Variables

See [`.env.example`](.env.example) for the full variable reference.

| Variable | Service | Description |
|---|---|---|
| `DB_HOST` | backend | PostgreSQL host |
| `DB_PORT` | backend | PostgreSQL port |
| `DB_NAME` | backend | Database name |
| `DB_USER` | backend | Database user |
| `DB_PASSWORD` | backend | Database password |
| `BACKEND_PORT` | backend | Express listen port |
| `VITE_API_URL` | frontend | Express base URL |
| `ML_SERVICE_PORT` | ml-service | FastAPI listen port |
| `ML_SERVICE_URL` | backend | FastAPI base URL (future) |

---

## Health Endpoints

| Endpoint | Service | Expected response |
|---|---|---|
| `GET /api/health` | Express | `{ status: "ok", database: "connected" \| "error" }` |
| `GET /api/health/ml` | Express → FastAPI | ML service + demand-model status (proxied) |
| `GET /health` | FastAPI | `{ status, service, database, demand_model: { status, name, version } }` |

### Demand forecasting endpoints

| Endpoint | Service | Purpose |
|---|---|---|
| `POST /api/forecast/demand` | Express → FastAPI | Demand forecast from the trained model |
| `POST /api/forecast/inventory-projection` | Express → FastAPI | Forecast-driven inventory projection + stockout risk |

Request body: `{ "product_id": "<uuid>", "market_id": "<uuid>", "horizon": 7 }`

See [`ml-service/README.md`](ml-service/README.md) for the model details, the
full error-code table, and the service's known limitations.

---

## Development Phases

| Phase | Focus | Status |
|---|---|---|
| **1** | Foundation — repo, services, health checks, DB connectivity | ✅ Current |
| 2 | Synthetic data generation, DB schema, REST API scaffolding | ⬜ |
| 3 | ML models — demand forecasting ✅, disruption prediction ⬜ | 🟨 Partial |
| 4 | Digital Twin simulation (SimPy + NetworkX) | ⬜ |
| 5 | Optimisation (OR-Tools) + advanced dashboard | ⬜ |

---

## Contributing

Follow the branching strategy: `main` ← `develop` ← `feature/<name>`.

---

*SCARLET — Final Year Research Project*

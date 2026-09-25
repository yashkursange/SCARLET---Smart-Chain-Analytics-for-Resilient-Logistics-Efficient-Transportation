"""
test_api.py — integration tests against a REAL running PostgreSQL database
(the same one Express uses), exercising the actual /health and
/api/ml/demand/forecast endpoints end-to-end.

These require the demo seed data to be present (see scripts/seed_demo_data.py)
and DB_* env vars pointing at a reachable database — they are integration
tests, not unit tests, matching item 11 ("Python API") and item 4-6 ("historical
data retrieval", "feature generation", "single prediction") of the
integration test checklist.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db
from app.main import app

client = TestClient(app)


def _get_seeded_product_market(sku: str):
    product = db.fetch_one("SELECT id, sku FROM products WHERE sku = %s", (sku,))
    if product is None:
        pytest.skip(f"Demo seed data not present (product sku={sku}) — run scripts/seed_demo_data.py first.")
    market = db.fetch_one(
        """
        SELECT m.id FROM markets m
        JOIN demand d ON d.market_id = m.id
        WHERE d.product_id = %s LIMIT 1
        """,
        (product["id"],),
    )
    return str(product["id"]), str(market["id"])


def test_health_endpoint_reports_model_and_db():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "ml-service"
    assert body["demand_model"]["status"] == "loaded"
    assert body["database"] == "connected"


def test_forecast_real_seeded_product():
    product_id, market_id = _get_seeded_product_market("HOBBIES_1_150")
    resp = client.post("/api/ml/demand/forecast", json={
        "product_id": product_id, "market_id": market_id, "horizon": 7,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["forecast"]) == 7
    assert all(f["predicted_demand"] >= 0 for f in body["forecast"])
    assert body["model"]["name"] == "XGBRegressor"
    assert "MAE" in body["model"]["metrics"]


def test_forecast_multi_day_horizon_28():
    product_id, market_id = _get_seeded_product_market("FOODS_1_031")
    resp = client.post("/api/ml/demand/forecast", json={
        "product_id": product_id, "market_id": market_id, "horizon": 28,
    })
    assert resp.status_code == 200
    assert len(resp.json()["forecast"]) == 28


def test_forecast_invalid_product_returns_404():
    _, market_id = _get_seeded_product_market("HOBBIES_1_150")
    resp = client.post("/api/ml/demand/forecast", json={
        "product_id": "00000000-0000-0000-0000-000000000000",
        "market_id": market_id, "horizon": 7,
    })
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "product_not_found"


def test_forecast_invalid_market_returns_404():
    product_id, _ = _get_seeded_product_market("HOBBIES_1_150")
    resp = client.post("/api/ml/demand/forecast", json={
        "product_id": product_id,
        "market_id": "00000000-0000-0000-0000-000000000000", "horizon": 7,
    })
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "market_not_found"


def test_forecast_unmapped_product_returns_422():
    product = db.fetch_one(
        "SELECT id FROM products WHERE sku = %s", ("_TEST_UNMAPPED_PYTEST",)
    )
    if product is None:
        product = db.fetch_one(
            "INSERT INTO products (sku, name, unit_price) VALUES (%s, %s, %s) RETURNING id",
            ("_TEST_UNMAPPED_PYTEST", "Pytest Unmapped", 1.0),
        )
    _, market_id = _get_seeded_product_market("HOBBIES_1_150")
    resp = client.post("/api/ml/demand/forecast", json={
        "product_id": str(product["id"]), "market_id": market_id, "horizon": 7,
    })
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "product_not_mapped"
    db.execute("DELETE FROM products WHERE sku = %s", ("_TEST_UNMAPPED_PYTEST",))


def test_forecast_horizon_out_of_range_returns_422():
    product_id, market_id = _get_seeded_product_market("HOBBIES_1_150")
    resp = client.post("/api/ml/demand/forecast", json={
        "product_id": product_id, "market_id": market_id, "horizon": 100,
    })
    assert resp.status_code == 422

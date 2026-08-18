"""
tests/test_health.py — FastAPI health endpoint tests

Uses httpx's AsyncClient to make real requests against the FastAPI app
without binding to a port.  pytest-asyncio drives the async test runner.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_returns_ok():
    """GET /health → 200 with expected JSON structure."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"]  == "ok"
    assert body["service"] == "scarlet-ml-service"
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_unknown_route_returns_404():
    """Unknown paths should return 404."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/unknown")

    assert response.status_code == 404

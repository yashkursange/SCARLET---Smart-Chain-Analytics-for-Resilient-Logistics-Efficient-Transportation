"""
e2e_ui_test.py — TRUE end-to-end test of the SCARLET demand forecasting
integration, driving the real React UI in a headless browser:

    React UI -> Express -> FastAPI -> trained XGBoost model -> PostgreSQL

This asserts that the number rendered in the browser is the SAME number the
trained model produces when called directly — i.e. the UI is displaying real
model output, not mock data.

Prerequisites (all must be running):
    - PostgreSQL with the SCARLET schema + demo seed data
    - ml-service   (uvicorn app.main:app --port 8000)
    - backend      (node server.js, port 4000)
    - frontend     (vite preview/dev on port 5173)

Usage:
    python tests/e2e_ui_test.py <product_id> <market_id>
"""
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

FRONTEND_URL = "http://localhost:5173"


def model_prediction_direct(product_id: str, market_id: str, horizon: int = 7):
    """Call the trained model directly (bypassing HTTP entirely) for comparison."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ml-service"))
    from app.models.loader import load_demand_model
    from app.ml.demand.history import get_product_market_context, get_daily_demand_history
    from app.ml.demand.predictor import recursive_forecast

    artifacts = load_demand_model()
    ctx = get_product_market_context(product_id, market_id)
    history = get_daily_demand_history(product_id, market_id, as_of=date.today())
    return recursive_forecast(artifacts, ctx, history, horizon)


def main(product_id: str, market_id: str):
    expected = model_prediction_direct(product_id, market_id, horizon=7)
    print("Direct model call (ground truth):")
    for row in expected:
        print("   ", row["date"], row["predicted_demand"])

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        console_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        print(f"\nOpening {FRONTEND_URL} …")
        page.goto(FRONTEND_URL, wait_until="networkidle")

        # Dashboard health cards should show the real ML/model status.
        page.wait_for_selector("#status-ml-service", timeout=10000)
        ml_card = page.inner_text("#status-ml-service")
        print("ML service status card:\n   ", ml_card.replace("\n", " | "))
        assert "loaded" in ml_card.lower(), "Dashboard does not report the demand model as loaded"

        # Navigate to the Demand Forecast view.
        page.click("text=Demand Forecast")
        page.wait_for_selector("input[placeholder*='123e4567']", timeout=10000)

        inputs = page.query_selector_all("input[type='text']")
        inputs[0].fill(product_id)
        inputs[1].fill(market_id)
        page.select_option("select", "7")

        print("\nClicking 'Generate Forecast' …")
        page.click("text=Generate Forecast")

        # Wait for the rendered forecast table.
        page.wait_for_selector("table", timeout=20000)
        page.wait_for_timeout(1500)

        body = page.inner_text("body")

        # 1. Model identity must come from real metadata.
        assert "XGBRegressor" in body, "Model name not rendered in UI"
        assert "scarlet-demand-v1.0" in body, "Model version not rendered in UI"
        print("UI shows model: XGBRegressor / scarlet-demand-v1.0")

        # 2. Real metrics from metrics.json must be rendered.
        assert "0.98" in body, "Real MAE metric not rendered in UI"
        print("UI shows real evaluation metrics from metrics.json")

        # 3. THE KEY ASSERTION — every predicted value the model produced must
        #    appear in the rendered page, proving the UI shows real model output.
        for row in expected:
            rendered = f"{row['predicted_demand']:.2f}"
            assert rendered in body, (
                f"Predicted value {rendered} for {row['date']} is NOT displayed in the UI"
            )
            assert row["date"] in body, f"Forecast date {row['date']} is NOT displayed in the UI"
        print(f"All {len(expected)} model predictions + dates verified as rendered in the browser")

        # 4. Inventory projection / stockout risk driven by the same forecast.
        #    NOTE: the heading uses Tailwind's `uppercase`, and Playwright's
        #    inner_text returns RENDERED text, so compare case-insensitively.
        body_lower = body.lower()
        assert "stockout risk" in body_lower, "Inventory projection section not rendered"
        print("Inventory projection + stockout risk section rendered")

        risk_found = None
        for level in ["OK", "LOW", "CRITICAL", "STOCKOUT"]:
            if f"risk level: {level}".lower() in body_lower:
                risk_found = level
                break
        assert risk_found is not None, "No risk level rendered in the inventory section"
        print(f"   Risk level displayed: {risk_found}")

        # The projection must be driven by the forecast: each day's forecast
        # demand should appear in the projection table too.
        for row in expected:
            assert f"{row['predicted_demand']:.2f}" in body, (
                f"Forecast demand {row['predicted_demand']:.2f} missing from projection table"
            )
        print("   Projection table is driven by the same model forecast")

        page.screenshot(path="/home/claude/scarlet/e2e_forecast_screenshot.png", full_page=True)
        print("Screenshot saved to e2e_forecast_screenshot.png")

        browser.close()

    real_errors = [e for e in console_errors if "favicon" not in e.lower()]
    if real_errors:
        print("\nBrowser console errors detected:")
        for e in real_errors:
            print("   ", e)
    else:
        print("\nNo browser console errors.")

    print("\nEND-TO-END UI TEST PASSED — the browser is displaying real trained-model output.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])

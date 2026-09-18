import pytest
import pandas as pd
import datetime
from unittest.mock import patch
from app.ml.risk import analyze_risk, determine_risk_level

@pytest.fixture
def mock_forecast():
    today = pd.Timestamp.now().normalize()
    return pd.DataFrame([
        {'market_id': 'm1', 'product_id': 'p1', 'forecast_date': today, 'predicted_demand': 10},
        {'market_id': 'm1', 'product_id': 'p1', 'forecast_date': today + datetime.timedelta(days=1), 'predicted_demand': 15},
        {'market_id': 'm1', 'product_id': 'p1', 'forecast_date': today + datetime.timedelta(days=2), 'predicted_demand': 20}
    ])

@pytest.fixture
def mock_inventory():
    return pd.DataFrame([
        {'market_id': 'm1', 'product_id': 'p1', 'current_inventory': 20}
    ])

@pytest.fixture
def mock_inbound():
    today = pd.Timestamp.now().normalize()
    return pd.DataFrame([
        {'market_id': 'm1', 'product_id': 'p1', 'arrival_date': today + datetime.timedelta(days=1), 'expected_inbound': 20}
    ])

@patch('app.ml.risk.ForecastService')
@patch('app.ml.risk.get_inventory')
@patch('app.ml.risk.get_inbound_supply')
def test_risk_analysis(mock_inbound_func, mock_inventory_func, mock_forecast_cls, 
                       mock_inbound, mock_inventory, mock_forecast):
    
    mock_inbound_func.return_value = mock_inbound
    mock_inventory_func.return_value = mock_inventory
    mock_forecast_cls.return_value.get_forecast.return_value = mock_forecast
    
    results = analyze_risk(horizon=3)
    assert len(results) == 1
    
    res = results[0]
    assert res['market_id'] == 'm1'
    assert res['product_id'] == 'p1'
    assert res['total_forecast_demand'] == 45
    assert res['current_inventory'] == 20
    assert res['expected_inbound'] == 20
    
    # Day 0: inv=20, demand=10 -> inv=10
    # Day 1: inv=10, inbound=20, demand=15 -> inv=15
    # Day 2: inv=15, demand=20 -> inv=-5
    assert res['projected_ending_inventory'] == -5
    assert res['shortage_quantity'] == 5
    
    # Stockout on day 2 => 2 days until stockout => CRITICAL
    assert res['risk_level'] == 'CRITICAL'

def test_determine_risk_level():
    assert determine_risk_level(None) == 'LOW'
    assert determine_risk_level(2) == 'CRITICAL'
    assert determine_risk_level(5) == 'HIGH'
    assert determine_risk_level(10) == 'MEDIUM'
    assert determine_risk_level(20) == 'LOW'

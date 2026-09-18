import pytest
import pandas as pd
import numpy as np
from datetime import timedelta

from app.ml.features import create_features
from app.ml.baselines import NaiveForecast
from app.ml.train import get_chronological_splits

@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2026-01-01', periods=100)
    
    # 2 markets, 2 products
    data = []
    for m in [1, 2]:
        for p in [1, 2]:
            for d in dates:
                data.append({
                    'market_id': m,
                    'product_id': p,
                    'demand_date': d,
                    'actual_quantity': np.random.randint(10, 100)
                })
                
    return pd.DataFrame(data)

def test_chronological_split(sample_data):
    df = sample_data.sort_values('demand_date').reset_index(drop=True)
    train, val, test = get_chronological_splits(df)
    
    assert len(train) == int(len(df) * 0.7)
    assert len(val) == int(len(df) * 0.15)
    
    # Check max date of train is <= min date of val
    assert train['demand_date'].max() <= val['demand_date'].min()
    assert val['demand_date'].max() <= test['demand_date'].min()

def test_feature_engineering_lags(sample_data):
    df = sample_data[
        (sample_data['market_id'] == 1) & 
        (sample_data['product_id'] == 1)
    ].copy()
    
    df = df.sort_values('demand_date').reset_index(drop=True)
    original_len = len(df)
    
    # Expected value at day 29 for lag 28 is the value at day 1
    val_day_1 = df.loc[0, 'actual_quantity']
    
    df_features = create_features(df)
    
    # With lag 28, we lose 28 days of data
    assert len(df_features) == original_len - 28
    
    # Check lag 28 for the first available row
    assert df_features.loc[0, 'lag_28'] == val_day_1

def test_naive_baseline(sample_data):
    df = create_features(sample_data)
    naive = NaiveForecast()
    preds = naive.predict(df)
    
    # Naive pred should be lag_1
    np.testing.assert_array_equal(preds, df['lag_1'].values)

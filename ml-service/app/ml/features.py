import pandas as pd
import numpy as np

def create_features(df):
    print("--- Feature Engineering ---")
    
    # We must operate per market-product series
    # Ensure data is sorted
    df = df.sort_values(by=['market_id', 'product_id', 'demand_date']).reset_index(drop=True)
    
    # Datetime features
    df['day_of_week'] = df['demand_date'].dt.dayofweek
    df['day_of_month'] = df['demand_date'].dt.day
    df['month'] = df['demand_date'].dt.month
    df['week_of_year'] = df['demand_date'].dt.isocalendar().week.astype(int)
    
    # Lags
    groups = df.groupby(['market_id', 'product_id'])
    for lag in [1, 7, 14, 28]:
        df[f'lag_{lag}'] = groups['actual_quantity'].shift(lag)
        
    # Rolling means (exclude current day, so shift(1) first)
    shifted = groups['actual_quantity'].shift(1)
    # We can't do shifted.rolling() directly easily on grouped data without grouping again.
    # Actually, we can use df.groupby again on the shifted values if we assign it back, but it's simpler:
    
    # We can just use the transform method
    def rolling_mean_func(x, window):
        return x.shift(1).rolling(window=window).mean()
        
    def rolling_std_func(x, window):
        return x.shift(1).rolling(window=window).std()
        
    for window in [7, 14, 28]:
        df[f'rolling_mean_{window}'] = groups['actual_quantity'].transform(lambda x: rolling_mean_func(x, window))
        
    for window in [7, 28]:
        df[f'rolling_std_{window}'] = groups['actual_quantity'].transform(lambda x: rolling_std_func(x, window))
    
    # Drop rows with NaN in features (due to lags and rolling calculations)
    initial_len = len(df)
    subset = [f'lag_{lag}' for lag in [1, 7, 14, 28]] + [f'rolling_mean_{window}' for window in [7, 14, 28]] + [f'rolling_std_{window}' for window in [7, 28]]
    df = df.dropna(subset=subset).reset_index(drop=False)
    # If the index reset created 'index' or 'level_0', drop it, but keep market_id and product_id
    cols_to_drop = [c for c in df.columns if c in ['index', 'level_0', 'level_1'] and c not in ['market_id', 'product_id']]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
    print(f"Rows dropped due to feature engineering (NaNs): {initial_len - len(df)}")
    
    print("---------------------------")
    return df

import pandas as pd

def validate_and_preprocess(df):
    print("--- Data Validation Summary ---")
    
    # Check missing values
    missing = df.isnull().sum()
    print(f"Missing values:\n{missing[missing > 0] if missing.sum() > 0 else 'None'}")
    
    # Check duplicate demand records
    duplicates = df.duplicated(subset=['market_id', 'product_id', 'demand_date']).sum()
    print(f"Duplicate records: {duplicates}")
    if duplicates > 0:
        df = df.drop_duplicates(subset=['market_id', 'product_id', 'demand_date'])
        
    # Check invalid quantities
    invalid_quantities = (df['actual_quantity'] < 0).sum()
    print(f"Invalid actual quantities (negative): {invalid_quantities}")
    if invalid_quantities > 0:
        df = df[df['actual_quantity'] >= 0]
        
    # Check missing dates
    print(f"Total records after validation: {len(df)}")
    print(f"Date range: {df['demand_date'].min()} to {df['demand_date'].max()}")
    
    # Check insufficient history per market-product series
    series_lengths = df.groupby(['market_id', 'product_id']).size()
    short_series = series_lengths[series_lengths < 30]
    print(f"Series with <30 observations: {len(short_series)}")
    
    print("-------------------------------")
    
    return df

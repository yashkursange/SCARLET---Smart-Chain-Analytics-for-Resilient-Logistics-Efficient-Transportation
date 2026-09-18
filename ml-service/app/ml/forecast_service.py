import json
import pandas as pd
import datetime
from xgboost import XGBRegressor
from app.ml.features import create_features
from app.ml.data_loader import load_data

class ForecastService:
    def __init__(self, model_path='models/demand_xgboost.json', schema_path='models/schema.json'):
        self.model = XGBRegressor()
        self.model.load_model(model_path)
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)
            
    def get_forecast(self, horizon_days=7):
        # We need historical data to calculate lags
        df_hist = load_data()
        if df_hist.empty:
            return pd.DataFrame()
        
        # Get the latest date
        last_date = df_hist['demand_date'].max()
        
        # Keep only the last 30 days for each market-product to speed up processing
        cutoff_date = last_date - datetime.timedelta(days=35)
        df_hist = df_hist[df_hist['demand_date'] >= cutoff_date].copy()
        
        market_products = df_hist[['market_id', 'product_id']].drop_duplicates()
        
        forecasts = []
        
        # For a simple iterative rollout, we append 1 day at a time
        current_df = df_hist.copy()
        
        for i in range(1, horizon_days + 1):
            next_date = last_date + datetime.timedelta(days=i)
            
            # Create placeholder rows for the next day
            next_day_rows = []
            for _, row in market_products.iterrows():
                next_day_rows.append({
                    'id': 'temp',
                    'market_id': row['market_id'],
                    'product_id': row['product_id'],
                    'demand_date': next_date,
                    'actual_quantity': 0  # placeholder
                })
            
            next_day_df = pd.DataFrame(next_day_rows)
            current_df = pd.concat([current_df, next_day_df], ignore_index=True)
            
            # Generate features for everything
            features_df = create_features(current_df)
            
            # Predict for the next day
            target_mask = features_df['demand_date'] == next_date
            X = features_df.loc[target_mask, self.schema['features']]
            if X.empty:
                # No rows have enough history to produce features for this date; skip prediction
                continue
            
            preds = self.model.predict(X)
            
            # Create a mapping DataFrame
            preds_df = features_df.loc[target_mask, ['market_id', 'product_id']].copy()
            preds_df['predicted_quantity'] = preds
            
            # Update current_df with predictions
            for _, row in preds_df.iterrows():
                mask = (current_df['market_id'] == row['market_id']) & (current_df['product_id'] == row['product_id']) & (current_df['demand_date'] == next_date)
                current_df.loc[mask, 'actual_quantity'] = row['predicted_quantity']
            
            # Record forecasts for rows where prediction was made
            for idx, row in preds_df.iterrows():
                forecasts.append({
                    'market_id': row['market_id'],
                    'product_id': row['product_id'],
                    'forecast_date': next_date,
                    'predicted_demand': max(0, row['predicted_quantity'])
                })
        
        return pd.DataFrame(forecasts)

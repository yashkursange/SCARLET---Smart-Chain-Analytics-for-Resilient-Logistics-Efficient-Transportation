import json
import argparse
import pandas as pd
from xgboost import XGBRegressor
from app.ml.features import create_features
from app.ml.risk import analyze_risk

class DemandPredictor:
    def __init__(self, model_path='models/demand_xgboost.json', schema_path='models/schema.json'):
        self.model = XGBRegressor()
        self.model.load_model(model_path)
        
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)
            
    def predict(self, df):
        df_features = create_features(df)
        X = df_features[self.schema['features']]
        
        predictions = self.model.predict(X)
        df_features['projected_quantity'] = predictions
        
        return df_features[['market_id', 'product_id', 'demand_date', 'projected_quantity']]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Forecast and Risk Analysis")
    parser.add_argument("--horizon", type=int, default=7, help="Forecast horizon in days (default: 7)")
    
    args = parser.parse_args()
    print(f"Running Forecast Analysis for horizon: {args.horizon} days...\n")
    
    results = analyze_risk(horizon=args.horizon)
    
    if not results:
        print("No historical data available to generate forecast.")
    else:
        print(f"{'MARKET':<36} | {'PRODUCT':<36} | {'DEMAND':<10} | {'INVENTORY':<10} | {'SHORTAGE':<10} | {'RISK'}")
        print("-" * 125)
        for r in results:
            print(f"{str(r['market_id']):<36} | {str(r['product_id']):<36} | {r['total_forecast_demand']:<10.2f} | {r['current_inventory']:<10.2f} | {r['shortage_quantity']:<10.2f} | {r['risk_level']}")

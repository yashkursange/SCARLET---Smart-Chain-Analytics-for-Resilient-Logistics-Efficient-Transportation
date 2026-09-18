import os
import json
import joblib
from datetime import datetime
from xgboost import XGBRegressor

from .data_loader import load_data
from .preprocessing import validate_and_preprocess
from .features import create_features
from .baselines import NaiveForecast, SeasonalNaiveForecast
from .evaluate import calculate_metrics, print_metrics_table, get_feature_importance

def get_chronological_splits(df):
    total = len(df)
    train_end = int(total * 0.7)
    val_end = train_end + int(total * 0.15)
    
    train_df = df.iloc[:train_end]
    val_df = df.iloc[train_end:val_end]
    test_df = df.iloc[val_end:]
    
    print("--- Data Splits ---")
    print(f"Train: {train_df['demand_date'].min().date()} to {train_df['demand_date'].max().date()} ({len(train_df)} rows)")
    print(f"Validation: {val_df['demand_date'].min().date()} to {val_df['demand_date'].max().date()} ({len(val_df)} rows)")
    print(f"Test: {test_df['demand_date'].min().date()} to {test_df['demand_date'].max().date()} ({len(test_df)} rows)")
    print("-------------------")
    
    return train_df, val_df, test_df

def run_pipeline():
    df = load_data()
    df = validate_and_preprocess(df)
    df = create_features(df)
    
    # Sort globally by date to do a proper chronological split
    df = df.sort_values('demand_date').reset_index(drop=True)
    
    train_df, val_df, test_df = get_chronological_splits(df)
    
    features = [
        'lag_1', 'lag_7', 'lag_14', 'lag_28', 
        'rolling_mean_7', 'rolling_mean_14', 'rolling_mean_28',
        'rolling_std_7', 'rolling_std_28',
        'day_of_week', 'day_of_month', 'month', 'week_of_year'
    ]
    target = 'actual_quantity'
    
    X_train, y_train = train_df[features], train_df[target]
    X_val, y_val = val_df[features], val_df[target]
    X_test, y_test = test_df[features], test_df[target]
    
    results = {}
    
    # Baselines
    naive = NaiveForecast()
    y_pred_naive = naive.predict(test_df)
    results['Naive'] = calculate_metrics(y_test, y_pred_naive)
    
    s_naive = SeasonalNaiveForecast()
    y_pred_s_naive = s_naive.predict(test_df)
    results['Seasonal Naive'] = calculate_metrics(y_test, y_pred_s_naive)
    
    # XGBoost
    xgb_params = {
        'objective': 'reg:squarederror',
        'n_estimators': 100,
        'learning_rate': 0.1,
        'max_depth': 5,
        'random_state': 42,
        'early_stopping_rounds': 10
    }
    
    xgb = XGBRegressor(**xgb_params)
    xgb.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    
    y_pred_xgb = xgb.predict(X_test)
    results['XGBoost'] = calculate_metrics(y_test, y_pred_xgb)
    
    print_metrics_table(results)
    
    # Feature importance
    importance_df = get_feature_importance(xgb, features)
    print("Feature Importance:")
    print(importance_df)
    
    # Save model and artifacts
    os.makedirs('models', exist_ok=True)
    model_path = 'models/demand_xgboost.json'
    xgb.save_model(model_path)
    
    schema = {
        'features': features,
        'target': target
    }
    with open('models/schema.json', 'w') as f:
        json.dump(schema, f)
        
    # Experiment log
    os.makedirs('experiments', exist_ok=True)
    experiment_log = {
        'timestamp': datetime.now().isoformat(),
        'model': 'XGBRegressor',
        'features': features,
        'training_date_range': [str(train_df['demand_date'].min().date()), str(train_df['demand_date'].max().date())],
        'validation_date_range': [str(val_df['demand_date'].min().date()), str(val_df['demand_date'].max().date())],
        'test_date_range': [str(test_df['demand_date'].min().date()), str(test_df['demand_date'].max().date())],
        'hyperparameters': xgb_params,
        'metrics': results['XGBoost']
    }
    
    log_file = 'experiments/experiment_log.json'
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            logs = json.load(f)
    else:
        logs = []
        
    logs.append(experiment_log)
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=4)
        
    print(f"Model saved to {model_path}")
    print(f"Experiment logged to {log_file}")

if __name__ == "__main__":
    run_pipeline()

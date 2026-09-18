import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

def smape(y_true, y_pred):
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    diff = np.abs(y_true - y_pred)
    return np.mean(np.where(denominator == 0, 0, diff / denominator)) * 100

def calculate_metrics(y_true, y_pred):
    return {
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": np.sqrt(mean_squared_error(y_true, y_pred)),
        "sMAPE": smape(y_true, y_pred)
    }

def print_metrics_table(results_dict):
    print("\n--- Model Comparison ---")
    print(f"{'Model':<15} | {'MAE':<10} | {'RMSE':<10} | {'sMAPE':<10}")
    print("-" * 55)
    for model_name, metrics in results_dict.items():
        print(f"{model_name:<15} | {metrics['MAE']:<10.4f} | {metrics['RMSE']:<10.4f} | {metrics['sMAPE']:<10.4f}")
    print("------------------------\n")
    
def get_feature_importance(model, feature_names):
    importance = model.feature_importances_
    return pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)

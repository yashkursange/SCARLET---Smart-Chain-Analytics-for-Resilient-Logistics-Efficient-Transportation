import argparse
import json
import numpy as np
import pandas as pd
from .features import compute_features
from .labels import assign_labels
from .validator import validate_dataset
from .dataset import save_dataset

def generate(seed: int, months: int, output_path: str):
    rng = np.random.RandomState(seed)
    # Enumerate entities from DB (placeholder functions)
    # In real implementation, fetch IDs via SQLAlchemy engine
    entities = ['supplier_1', 'factory_1', 'warehouse_1', 'route_1', 'vehicle_1']
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=months*30)
    rows = []
    for entity in entities:
        for date in dates:
            row = {
                'entity_id': entity,
                'date': date,
                'utilization': rng.beta(2, 5),
                'delay_minutes': rng.exponential(scale=10),
                'temperature': rng.normal(20, 5),
            }
            rows.append(row)
    df = pd.DataFrame(rows)
    df = compute_features(df)
    df = assign_labels(df, rng)
    validate_dataset(df)
    save_dataset(df, output_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Synthetic disruption dataset generator')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--months', type=int, default=12)
    parser.add_argument('--output', type=str, default='data/synthetic/disruption_history.csv')
    args = parser.parse_args()
    generate(args.seed, args.months, args.output)

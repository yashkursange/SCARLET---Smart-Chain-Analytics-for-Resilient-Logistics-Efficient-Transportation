import os
import json
import joblib

class DemandModelLoader:
    def __init__(self):
        self.model = None
        self.feature_columns = None
        self.cat_code_maps = None
        self.model_metadata = None
        self.metrics = None
        self.is_loaded = False

    def load_artifacts(self, artifact_dir: str = "../scarlet_demand_model"):
        """
        Loads the trained model and associated JSON artifacts.
        DO NOT load them on every API request. This should run once at startup.
        """
        try:
            model_path = os.path.join(artifact_dir, "demand_model.pkl")
            features_path = os.path.join(artifact_dir, "feature_columns.json")
            cats_path = os.path.join(artifact_dir, "cat_code_maps.json")
            meta_path = os.path.join(artifact_dir, "model_metadata.json")
            metrics_path = os.path.join(artifact_dir, "metrics.json")

            self.model = joblib.load(model_path)
            
            with open(features_path, 'r') as f:
                self.feature_columns = json.load(f)
                
            with open(cats_path, 'r') as f:
                self.cat_code_maps = json.load(f)
                
            with open(meta_path, 'r') as f:
                self.model_metadata = json.load(f)
                
            with open(metrics_path, 'r') as f:
                self.metrics = json.load(f)
                
            self.is_loaded = True
            print("Successfully loaded demand model artifacts.")
        except Exception as e:
            print(f"Failed to load demand model artifacts: {e}")
            self.is_loaded = False
            # We don't raise here to allow the service to start, but requests will fail.
            # If strict startup failure is preferred, we could raise e.


model_loader = DemandModelLoader()

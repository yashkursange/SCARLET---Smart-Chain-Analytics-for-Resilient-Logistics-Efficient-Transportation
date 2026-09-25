"""
Scarlet demand model loader.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from xgboost import XGBRegressor

from app.ml.demand.history import ForecastInputError

logger = logging.getLogger("scarlet.ml.loader")


REQUIRED_FILES = [
    "demand_model.pkl",
    "feature_columns.json",
    "cat_code_maps.json",
    "model_metadata.json",
    "metrics.json",
]


@dataclass
class DemandModelArtifacts:
    model: Optional[Any] = None
    feature_columns: list[str] = field(default_factory=list)
    cat_code_maps: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    loaded: bool = False
    error: Optional[str] = None

    @property
    def model_name(self):
        return (self.metadata or {}).get("selected_model", "XGBoost")

    @property
    def model_version(self):
        return (self.metadata or {}).get("model_version", "unknown")

    def label_to_code(self, column: str, label: str) -> int:
        mapping = self.cat_code_maps.get(column, {})

        for code, stored_label in mapping.items():
            if stored_label == label:
                return int(code)

        raise ForecastInputError(
    		column,
    		f"Unknown label '{label}' for categorical column '{column}'"
)


_artifacts_cache: Optional[DemandModelArtifacts] = None


class CompatibleXGBModel:
    """
    Adapts the application's 36-feature schema to the available
    native 13-feature XGBoost model.
    """

    MODEL_FEATURES = [
        "lag_1",
        "lag_7",
        "lag_14",
        "lag_28",
        "rolling_mean_7",
        "rolling_mean_14",
        "rolling_mean_28",
        "rolling_std_7",
        "rolling_std_28",
        "day_of_week",
        "day_of_month",
        "month",
        "week_of_year",
    ]

    def __init__(self, model):
        self._model = model

    def predict(self, X):
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)

        X = X.copy()

        if "month" not in X.columns:
            if "day_of_year" in X.columns:
                doy = (
                    pd.to_numeric(
                        X["day_of_year"],
                        errors="coerce",
                    )
                    .fillna(1)
                    .clip(1, 365)
                    .astype(int)
                )

                dates = pd.to_datetime(
                    "2015-01-01"
                ) + pd.to_timedelta(
                    doy - 1,
                    unit="D",
                )

                X["month"] = dates.dt.month
            else:
                X["month"] = 1

        for column in self.MODEL_FEATURES:
            if column not in X.columns:
                X[column] = 0

        X_model = X[self.MODEL_FEATURES].copy()

        for column in self.MODEL_FEATURES:
            X_model[column] = pd.to_numeric(
                X_model[column],
                errors="coerce",
            ).fillna(0)

        return self._model.predict(X_model)


def _default_model_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "models" / "demand"


def load_demand_model(
    model_dir: Optional[Path] = None,
) -> DemandModelArtifacts:

    global _artifacts_cache

    model_dir = Path(
        model_dir
        if model_dir is not None
        else _default_model_dir()
    )

    native_model_path = model_dir.parent / "demand_xgboost.json"

    required_artifacts = [
        "feature_columns.json",
        "cat_code_maps.json",
        "model_metadata.json",
        "metrics.json",
    ]

    missing = [
        filename
        for filename in required_artifacts
        if not (model_dir / filename).exists()
    ]

    if not native_model_path.exists():
        if "demand_model.pkl" not in missing:
            missing.insert(0, "demand_model.pkl")

    if missing:
        error = (
            f"Missing required artifact file(s) in "
            f"{model_dir}: {missing}"
        )

        logger.error(error)

        artifacts = DemandModelArtifacts(
            loaded=False,
            error=error,
        )

        _artifacts_cache = artifacts
        return artifacts

    try:
        native_model = XGBRegressor()
        native_model.load_model(str(native_model_path))

        model = CompatibleXGBModel(native_model)

        with open(
            model_dir / "feature_columns.json",
            encoding="utf-8",
        ) as file:
            feature_columns = json.load(file)

        with open(
            model_dir / "cat_code_maps.json",
            encoding="utf-8",
        ) as file:
            cat_code_maps = json.load(file)

        with open(
            model_dir / "model_metadata.json",
            encoding="utf-8",
        ) as file:
            metadata = json.load(file)

        with open(
            model_dir / "metrics.json",
            encoding="utf-8",
        ) as file:
            metrics = json.load(file)

        artifacts = DemandModelArtifacts(
            model=model,
            feature_columns=feature_columns,
            cat_code_maps=cat_code_maps,
            metadata=metadata,
            metrics=metrics,
            loaded=True,
            error=None,
        )

        _artifacts_cache = artifacts

        return artifacts

    except Exception as exc:
        logger.exception(
            "Failed to load demand model artifacts"
        )

        artifacts = DemandModelArtifacts(
            loaded=False,
            error=str(exc),
        )

        _artifacts_cache = artifacts

        return artifacts


def get_artifacts() -> DemandModelArtifacts:
    global _artifacts_cache

    if _artifacts_cache is None:
        _artifacts_cache = load_demand_model()

    return _artifacts_cache
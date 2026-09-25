import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.loader import load_demand_model, REQUIRED_FILES


def test_loads_real_artifacts():
    artifacts = load_demand_model()
    assert artifacts.loaded is True
    assert artifacts.error is None
    assert artifacts.model is not None
    assert hasattr(artifacts.model, "predict")


def test_feature_columns_present():
    artifacts = load_demand_model()
    assert len(artifacts.feature_columns) > 0
    assert "lag_1" in artifacts.feature_columns
    assert "item_id_enc" in artifacts.feature_columns


def test_cat_code_maps_present():
    artifacts = load_demand_model()
    for col in ["item_id", "dept_id", "cat_id", "store_id", "state_id"]:
        assert col in artifacts.cat_code_maps
        assert len(artifacts.cat_code_maps[col]) > 0


def test_metadata_and_metrics_present():
    artifacts = load_demand_model()
    assert artifacts.model_name
    assert artifacts.model_version
    assert "test_metrics" in artifacts.metrics
    assert "MAE" in artifacts.metrics["test_metrics"]


def test_label_to_code_roundtrip():
    artifacts = load_demand_model()
    # every value in the map should reverse-lookup to its own key
    for col, mapping in artifacts.cat_code_maps.items():
        for code_str, label in list(mapping.items())[:5]:
            assert artifacts.label_to_code(col, label) == int(code_str)


def test_missing_directory_reports_error_not_exception(tmp_path):
    empty_dir = tmp_path / "does_not_exist"
    artifacts = load_demand_model(model_dir=empty_dir)
    assert artifacts.loaded is False
    assert artifacts.error is not None
    assert artifacts.model is None


def test_missing_single_file_reports_error(tmp_path):
    partial_dir = tmp_path / "partial"
    partial_dir.mkdir()
    (partial_dir / "feature_columns.json").write_text("[]")
    artifacts = load_demand_model(model_dir=partial_dir)
    assert artifacts.loaded is False
    assert "demand_model.pkl" in artifacts.error

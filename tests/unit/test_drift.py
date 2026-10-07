from pathlib import Path

import pandas as pd
import pytest

from weather_mlops.monitoring import drift


def _sample_frame(n: int = 300) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Location": (["Sydney"] * (n // 2)) + (["Perth"] * (n - n // 2)),
            "MinTemp": [12.0 + (i % 8) for i in range(n)],
            "Humidity3pm": [40.0 + (i % 6) for i in range(n)],
            "Pressure3pm": [1012.0 + (i % 3) for i in range(n)],
            "RainToday": (["No"] * (2 * n // 3)) + (["Yes"] * (n - 2 * n // 3)),
        }
    )


def test_explode_prediction_features_builds_a_frame() -> None:
    rows = [
        {"features": {"Location": "Sydney", "Humidity3pm": 40.0}, "probability": 0.2},
        {"features": {"Location": "Perth", "Humidity3pm": 55.0}, "probability": 0.7},
    ]

    frame = drift.explode_prediction_features(rows)

    assert list(frame["Location"]) == ["Sydney", "Perth"]
    assert frame["Humidity3pm"].tolist() == [40.0, 55.0]


def test_identical_frames_are_not_drifted() -> None:
    reference = _sample_frame()

    summary = drift.run_feature_drift(reference, reference.copy())

    assert summary["drift_detected"] is False
    assert summary["drifted_columns"] == []
    assert summary["scope"] == "feature_drift"


def test_simulated_humidity_and_location_shift_is_detected() -> None:
    reference = _sample_frame()
    current = drift.simulate_feature_drift(reference)

    summary = drift.run_feature_drift(reference, current)

    assert "Humidity3pm" in summary["drifted_columns"]
    assert "Location" in summary["drifted_columns"]
    assert summary["drift_detected"] is True
    assert summary["column_metrics"]["Humidity3pm"]["drifted"] is True
    assert summary["column_metrics"]["MinTemp"]["drifted"] is False


def test_sparse_serving_rows_against_x_train_do_not_crash_psi() -> None:
    x_train = Path(__file__).resolve().parents[2] / "data/processed/X_train.csv"
    if not x_train.exists():
        pytest.skip("local X_train.csv is not available")
    reference = pd.read_csv(x_train).head(4000)
    current = pd.DataFrame(
        {
            "Location": ["Sydney", "Melbourne", "Albury", "Perth", "Darwin"],
            "MinTemp": [12.0] * 5,
            "MaxTemp": [22.0] * 5,
            "Rainfall": [0.0] * 5,
            "Evaporation": [None] * 5,
            "Sunshine": [None] * 5,
            "WindGustDir": ["NNW"] * 5,
            "WindGustSpeed": [31.0] * 5,
            "WindDir9am": ["N"] * 5,
            "WindDir3pm": ["W"] * 5,
            "WindSpeed9am": [10.0] * 5,
            "WindSpeed3pm": [13.0] * 5,
            "Humidity9am": [71.0] * 5,
            "Humidity3pm": [42.0] * 5,
            "Pressure9am": [1012.0] * 5,
            "Pressure3pm": [1009.0] * 5,
            "Cloud9am": [None] * 5,
            "Cloud3pm": [None] * 5,
            "Temp9am": [17.0] * 5,
            "Temp3pm": [21.0] * 5,
            "RainToday": ["No"] * 5,
        }
    )

    summary = drift.run_feature_drift(reference, current)

    assert summary["scope"] == "feature_drift"
    assert "Location" in summary["column_metrics"]
    assert "WindGustDir" not in summary["column_metrics"]


def test_low_recall_recommends_retrain() -> None:
    decision = drift.performance_decision(
        {"recall": 0.40, "roc_auc": 0.90},
        champion_roc_auc=0.88,
    )

    assert decision["retrain"] is True
    assert decision["scope"] == "performance"


def test_healthy_delayed_metrics_do_not_retrain() -> None:
    decision = drift.performance_decision(
        {"recall": 0.80, "roc_auc": 0.89},
        champion_roc_auc=0.88,
    )

    assert decision["retrain"] is False


def test_store_drift_report_inserts_catalog_row() -> None:
    class FakeQuery:
        def __init__(self) -> None:
            self.row = None

        def insert(self, row):
            self.row = row
            return self

        def execute(self):
            return self

    class FakeClient:
        def __init__(self) -> None:
            self.table_name = None
            self.query = FakeQuery()

        def table(self, name: str) -> FakeQuery:
            self.table_name = name
            return self.query

    client = FakeClient()

    drift.store_drift_report(
        {
            "scope": "feature_drift",
            "reference_dataset": "sha-ref",
            "current_dataset": "serving",
            "drift_detected": True,
            "metrics": {"drifted_columns": ["Humidity3pm"]},
            "report_html_path": "s3://weather-mlops-mlflow/reports/x.html",
        },
        client=client,
    )

    assert client.table_name == "drift_reports"
    assert client.query.row["scope"] == "feature_drift"
    assert client.query.row["drift_detected"] is True


def test_simulate_cli_writes_html(tmp_path: Path, monkeypatch) -> None:
    reference_path = tmp_path / "X_train.csv"
    _sample_frame().to_csv(reference_path, index=False)
    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(drift.settings, "x_train_path", reference_path)
    monkeypatch.setattr(drift.settings, "evidently_reports_dir", reports_dir)
    monkeypatch.setattr(drift.settings, "supabase_url", None)
    monkeypatch.setattr(drift.settings, "supabase_key", None)

    result = drift.run_drift_job(simulate=True, reference_path=reference_path)

    html = reports_dir / "feature_drift.html"
    assert html.exists()
    assert "Humidity3pm" in result["feature_drift"]["drifted_columns"]
    assert result["feature_drift"]["drift_detected"] is True
    assert result["performance"] is None


def test_singapore_csv_is_drifted(tmp_path: Path, monkeypatch) -> None:
    reference_path = tmp_path / "X_train.csv"
    _sample_frame().to_csv(reference_path, index=False)

    # fake rainy city with more humidty
    rainy = _sample_frame()
    rainy["Location"] = "Singapore"
    rainy["Humidity3pm"] = rainy["Humidity3pm"] + 35
    rainy["RainToday"] = "Yes"
    current_path = tmp_path / "singapore.csv"
    rainy.to_csv(current_path, index=False)

    monkeypatch.setattr(drift.settings, "evidently_reports_dir", tmp_path / "reports")
    monkeypatch.setattr(drift.settings, "supabase_url", None)
    monkeypatch.setattr(drift.settings, "supabase_key", None)

    result = drift.run_drift_job(reference_path=reference_path, current_path=current_path)

    assert result["feature_drift"]["drift_detected"] is True
    assert "Location" in result["feature_drift"]["drifted_columns"]
    assert "Humidity3pm" in result["feature_drift"]["drifted_columns"]


def test_real_singapore_csv_is_drifted(tmp_path: Path, monkeypatch) -> None:
    x_train = Path("data/processed/X_train.csv")
    singapore = Path("data/raw/weatherSingapore_current.csv")
    # skip if the data is not downloded
    if not x_train.exists() or not singapore.exists():
        pytest.skip("data not available")

    monkeypatch.setattr(drift.settings, "evidently_reports_dir", tmp_path / "reports")
    monkeypatch.setattr(drift.settings, "supabase_url", None)
    monkeypatch.setattr(drift.settings, "supabase_key", None)

    result = drift.run_drift_job(reference_path=x_train, current_path=singapore)

    assert result["feature_drift"]["drift_detected"] is True


def test_monitoring_metrics_flatten_drift_and_delayed_performance() -> None:
    feature = {
        "drift_detected": True,
        "share": 0.4,
        "count": 2,
        "column_metrics": {"Humidity3pm": {"drift_score": 0.31, "drifted": True}},
    }
    performance = {
        "retrain": True,
        "labeled_predictions": 42,
        "metrics": {"recall": 0.61, "roc_auc": 0.77},
    }

    metrics = drift.monitoring_metrics(feature, performance)

    assert metrics["feature_drift_detected"] == 1.0
    assert metrics["drifted_column_share"] == 0.4
    assert metrics["psi_Humidity3pm"] == 0.31
    assert metrics["retrain_requested"] == 1.0
    assert metrics["labeled_predictions"] == 42.0
    assert metrics["delayed_recall"] == 0.61
    assert "delayed_recall" not in drift.monitoring_metrics(feature, None)


def test_monitoring_run_is_skipped_without_tracking_uri(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(drift.settings, "mlflow_tracking_uri", None)

    run_id = drift.log_monitoring_run(
        {"current_dataset": "serving", "reference_dataset": "X_train.csv"},
        None,
        reference_path=tmp_path / "X_train.csv",
        html_path=tmp_path / "feature_drift.html",
    )

    assert run_id is None


def test_unreachable_tracking_does_not_stop_the_report(tmp_path: Path, monkeypatch) -> None:
    def unreachable(_name):
        raise ConnectionError("mlflow is down")

    monkeypatch.setattr(drift.settings, "mlflow_tracking_uri", "http://mlflow:8080")
    monkeypatch.setattr("mlflow.set_experiment", unreachable)

    run_id = drift.log_monitoring_run(
        {"current_dataset": "serving", "reference_dataset": "X_train.csv"},
        None,
        reference_path=tmp_path / "X_train.csv",
        html_path=tmp_path / "feature_drift.html",
    )

    assert run_id is None


def test_drift_job_logs_report_in_mlflow_with_training_dataset_hash(
    tmp_path: Path, monkeypatch
) -> None:
    from mlflow.tracking import MlflowClient

    reference_path = tmp_path / "processed" / "X_train.csv"
    reference_path.parent.mkdir()
    _sample_frame().to_csv(reference_path, index=False)
    (reference_path.parent / "manifest.json").write_text('{"sha256": "train-sha"}\n')
    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(drift.settings, "mlflow_tracking_uri", tracking_uri)
    monkeypatch.setattr(drift.settings, "mlflow_monitoring_experiment_name", "monitoring-test")
    monkeypatch.setattr(drift.settings, "evidently_reports_dir", tmp_path / "reports")
    monkeypatch.setattr(drift.settings, "supabase_url", None)
    monkeypatch.setattr(drift.settings, "supabase_key", None)

    result = drift.run_drift_job(simulate=True, reference_path=reference_path)

    client = MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(result["mlflow_run_id"])
    assert run.data.tags["stage"] == "monitoring"
    assert run.data.tags["dataset_sha256"] == "train-sha"
    assert run.data.tags["current_dataset"] == "simulated"
    assert run.data.tags["model_alias"] == "none"
    assert run.data.metrics["feature_drift_detected"] == 1.0
    assert run.data.metrics["psi_Humidity3pm"] >= drift.PSI_THRESHOLD
    artifacts = {artifact.path for artifact in client.list_artifacts(run.info.run_id, "evidently")}
    assert artifacts == {"evidently/feature_drift.html", "evidently/summary.json"}


def test_serving_model_tags_name_the_champion_and_its_training_data() -> None:
    from types import SimpleNamespace

    class FakeClient:
        def get_model_version_by_alias(self, name, alias):
            assert alias == "champion"
            return SimpleNamespace(version="3", run_id="champion-run")

        def get_run(self, run_id):
            assert run_id == "champion-run"
            return SimpleNamespace(data=SimpleNamespace(tags={"dataset_sha256": "kaggle-sha"}))

    tags = drift.serving_model_tags(FakeClient())

    assert tags["model_alias"] == "champion"
    assert tags["model_version"] == "3"
    assert tags["model_run_id"] == "champion-run"
    assert tags["model_dataset_sha256"] == "kaggle-sha"


def test_serving_model_tags_without_a_champion() -> None:
    class EmptyRegistry:
        def get_model_version_by_alias(self, name, alias):
            raise LookupError("alias not found")

    assert drift.serving_model_tags(EmptyRegistry()) == {"model_alias": "none"}

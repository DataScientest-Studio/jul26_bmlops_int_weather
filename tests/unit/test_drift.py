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

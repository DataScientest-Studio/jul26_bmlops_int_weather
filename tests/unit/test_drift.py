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
    assert decision["auc_failed"] is False


def test_auc_drop_below_champion_recommends_retrain() -> None:
    decision = drift.performance_decision(
        {"recall": 0.80, "roc_auc": 0.84},
        champion_roc_auc=0.88,
    )

    assert decision["retrain"] is True
    assert decision["recall_failed"] is False
    assert decision["auc_failed"] is True


def test_champion_validation_roc_auc_reads_the_alias() -> None:
    class Version:
        run_id = "champ-run"

    class Run:
        class data:
            metrics = {"validation_roc_auc": 0.871}

    class Client:
        def get_model_version_by_alias(self, name: str, alias: str) -> Version:
            assert name == "weather-rainfall-classifier"
            assert alias == "champion"
            return Version()

        def get_run(self, run_id: str) -> Run:
            assert run_id == "champ-run"
            return Run()

    assert drift.champion_validation_roc_auc(Client()) == 0.871


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
    monkeypatch.setattr(drift.settings, "mlflow_tracking_uri", None)

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
    monkeypatch.setattr(drift.settings, "mlflow_tracking_uri", None)

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
    monkeypatch.setattr(drift.settings, "mlflow_tracking_uri", None)

    result = drift.run_drift_job(reference_path=x_train, current_path=singapore)

    assert result["feature_drift"]["drift_detected"] is True


def test_live_gate_compares_delayed_auc_with_champion(tmp_path: Path, monkeypatch) -> None:
    reference_path = tmp_path / "X_train.csv"
    _sample_frame().to_csv(reference_path, index=False)
    monkeypatch.setattr(drift.settings, "evidently_reports_dir", tmp_path / "reports")
    monkeypatch.setattr(drift.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(drift.settings, "supabase_key", "key")
    monkeypatch.setattr(drift.settings, "pushgateway_url", None)
    monkeypatch.setattr(drift.settings, "mlflow_tracking_uri", "http://mlflow:8080")

    rows = [
        {
            "features": {"Location": "Sydney", "Humidity3pm": 40.0},
            "observed_label": "No",
            "predicted_class": "No",
            "probability": 0.2,
        }
    ]
    stored: list[dict] = []
    monkeypatch.setattr(drift, "load_serving_feature_rows", lambda client=None: rows)
    monkeypatch.setattr(
        drift, "delayed_performance", lambda _rows: {"recall": 0.80, "roc_auc": 0.80}
    )
    monkeypatch.setattr(drift, "load_champion_roc_auc", lambda: 0.88)
    monkeypatch.setattr(
        drift, "store_drift_report", lambda payload, client=None: stored.append(payload)
    )
    monkeypatch.setattr(drift, "log_drift_to_mlflow", lambda result, html_path: "run-abc")

    result = drift.run_drift_job(reference_path=reference_path)

    assert result["performance"]["retrain"] is True
    assert result["performance"]["auc_failed"] is True
    assert result["performance"]["champion_roc_auc"] == 0.88
    assert result["mlflow_run_id"] == "run-abc"
    assert {row["scope"] for row in stored} == {"feature_drift", "performance"}
    assert all(row["mlflow_run_id"] == "run-abc" for row in stored)


def test_simulate_defense_drift_arms_the_gate_without_training(monkeypatch) -> None:
    captured = {}

    def fake_job(**kwargs):
        captured.update(kwargs)
        return {
            "feature_drift": {
                "drift_detected": True,
                "drifted_columns": ["Humidity3pm", "Location"],
                "share": 0.4,
            },
            "performance": kwargs["performance_override"],
            "mlflow_run_id": "run-1",
        }

    pushed = {}

    def fake_push(result, *, gateway_url):
        pushed["retrain"] = result["performance"]["retrain"]
        pushed["url"] = gateway_url

    monkeypatch.setattr(drift, "run_drift_job", fake_job)
    monkeypatch.setattr(drift, "load_champion_roc_auc", lambda: 0.88)
    monkeypatch.setattr(drift.settings, "pushgateway_url", "http://pushgateway:9091")
    monkeypatch.setattr(
        "weather_mlops.monitoring.metrics.push_monitoring_metrics",
        fake_push,
    )

    summary = drift.simulate_defense_drift()

    assert captured["simulate"] is True
    assert captured["push"] is False
    assert captured["performance_override"]["simulated"] is True
    assert summary["retrain"] is True
    assert summary["drifted_columns"] == ["Humidity3pm", "Location"]
    assert summary["mlflow_run_id"] == "run-1"
    assert pushed == {"retrain": True, "url": "http://pushgateway:9091"}


def test_log_drift_to_mlflow_skips_when_tracking_is_unset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(drift.settings, "mlflow_tracking_uri", None)

    run_id = drift.log_drift_to_mlflow(
        {"feature_drift": {}, "performance": None},
        tmp_path / "x.html",
    )

    assert run_id is None


def test_log_drift_to_mlflow_writes_report_metrics(tmp_path: Path, monkeypatch) -> None:
    import sys

    html = tmp_path / "feature_drift.html"
    html.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(drift.settings, "mlflow_tracking_uri", "http://mlflow:8080")
    calls: dict = {}

    class FakeRun:
        class info:
            run_id = "run-1"

    class FakeContext:
        def __enter__(self):
            return FakeRun()

        def __exit__(self, *args):
            return False

    class FakeMLflow:
        @staticmethod
        def set_tracking_uri(uri: str) -> None:
            calls["uri"] = uri

        @staticmethod
        def set_experiment(name: str) -> None:
            calls["experiment"] = name

        @staticmethod
        def start_run(run_name: str | None = None):
            calls["run_name"] = run_name
            return FakeContext()

        @staticmethod
        def set_tags(tags: dict) -> None:
            calls["tags"] = tags

        @staticmethod
        def log_metrics(metrics: dict) -> None:
            calls["metrics"] = metrics

        @staticmethod
        def log_artifact(path: str, artifact_path: str | None = None) -> None:
            calls["artifact"] = (path, artifact_path)

    monkeypatch.setitem(sys.modules, "mlflow", FakeMLflow)

    run_id = drift.log_drift_to_mlflow(
        {
            "feature_drift": {"drift_detected": True, "share": 0.4},
            "performance": {
                "retrain": True,
                "champion_roc_auc": 0.88,
                "metrics": {"recall": 0.7, "roc_auc": 0.8},
            },
        },
        html,
    )

    assert run_id == "run-1"
    assert calls["experiment"] == "weather-rainfall-drift"
    assert calls["run_name"] == "evidently-monitor"
    assert calls["tags"]["stage"] == "monitoring"
    assert calls["metrics"]["delayed_roc_auc"] == 0.8
    assert calls["metrics"]["champion_roc_auc"] == 0.88
    assert calls["artifact"][1] == "evidently"

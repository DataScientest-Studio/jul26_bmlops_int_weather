from types import SimpleNamespace

import mlflow

from weather_mlops.models import comparison


class FakeClient:
    def __init__(self) -> None:
        self.tags: dict[tuple[str, str, str], str] = {}
        self.metrics: list[tuple[str, str, float]] = []

    def get_model_version(self, name, version):
        return SimpleNamespace(name=name, version=version)

    def search_model_versions(self, filter_string):
        return []

    def log_metric(self, run_id, key, value):
        self.metrics.append((run_id, key, value))

    def set_model_version_tag(self, name, version, key, value):
        self.tags[(name, str(version), key)] = value


def test_first_model_is_tagged_best(tmp_path, monkeypatch) -> None:
    model_path = tmp_path / "rain_classifier.joblib"
    best_path = tmp_path / "best_model.joblib"
    model_path.write_bytes(b"model")
    metadata = tmp_path / "mlflow_run.json"
    metadata.write_text(
        '{"run_id": "run-1", "model_name": "weather-rainfall-classifier", "model_version": "1"}\n',
        encoding="utf-8",
    )
    metrics = tmp_path / "validation.json"
    metrics.write_text('{"validation_f1": 0.8, "validation_recall": 0.7}\n', encoding="utf-8")

    monkeypatch.setattr(comparison.settings, "model_path", model_path)
    monkeypatch.setattr(comparison.settings, "best_model_path", best_path)
    monkeypatch.setattr(comparison.settings, "mlflow_tracking_uri", "http://mlflow:8080")
    monkeypatch.setattr(comparison.settings, "validation_metrics_path", metrics)
    monkeypatch.setattr(
        "weather_mlops.models.comparison.load_mlflow_run_metadata",
        lambda: {
            "run_id": "run-1",
            "model_name": "weather-rainfall-classifier",
            "model_version": "1",
        },
    )
    fake = FakeClient()
    monkeypatch.setattr(mlflow, "set_tracking_uri", lambda _uri: None)
    monkeypatch.setattr(mlflow, "MlflowClient", lambda: fake)

    comparison.compare_models()

    assert best_path.read_bytes() == b"model"
    assert fake.tags[("weather-rainfall-classifier", "1", "status")] == "best"
    assert ("run-1", "validation_f1", 0.8) in fake.metrics

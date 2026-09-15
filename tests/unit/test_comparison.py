import json
from types import SimpleNamespace

from mlflow.exceptions import MlflowException
from mlflow.protos.databricks_pb2 import INVALID_PARAMETER_VALUE

from weather_mlops.data.versioning import hash_file
from weather_mlops.models import comparison


class FakeClient:
    def __init__(self, champion=None, alias_error=None) -> None:
        self.tags: dict[tuple[str, str, str], str] = {}
        self.metrics: list[tuple[str, str, float]] = []
        self.aliases: dict[tuple[str, str], str] = {}
        self.champion = champion
        self.alias_error = alias_error
        self.runs: dict[str, SimpleNamespace] = {
            "run-1": SimpleNamespace(
                info=SimpleNamespace(run_id="run-1"),
                data=SimpleNamespace(metrics={}),
            )
        }

    def get_run(self, run_id):
        if run_id not in self.runs:
            self.runs[run_id] = SimpleNamespace(
                info=SimpleNamespace(run_id=run_id),
                data=SimpleNamespace(metrics={}),
            )
        return self.runs[run_id]

    def get_model_version_by_alias(self, name, alias):
        if self.alias_error is not None:
            raise self.alias_error
        if self.champion is None:
            raise MlflowException(
                "Registered model alias champion not found.",
                error_code=INVALID_PARAMETER_VALUE,
            )
        return self.champion

    def log_metric(self, run_id, key, value):
        self.metrics.append((run_id, key, value))

    def set_model_version_tag(self, name, version, key, value):
        self.tags[(name, str(version), key)] = value

    def set_registered_model_alias(self, name, alias, version):
        self.aliases[(name, alias)] = str(version)


def _metrics(model_path, **extra) -> str:
    payload = {
        "validation_roc_auc": extra.pop("validation_roc_auc", 0.88),
        "validation_recall": extra.pop("validation_recall", 0.76),
        "model_sha256": extra.pop("model_sha256", hash_file(model_path, "sha256")),
        "run_id": extra.pop("run_id", "run-1"),
        **extra,
    }
    return json.dumps(payload) + "\n"


def _patch_compare(tmp_path, monkeypatch, metrics_text: str, metadata: dict, fake: FakeClient):
    model_path = tmp_path / "rain_classifier.joblib"
    best_path = tmp_path / "best_model.joblib"
    if not model_path.exists():
        model_path.write_bytes(b"model")
    metrics = tmp_path / "validation.json"
    metrics.write_text(metrics_text, encoding="utf-8")
    monkeypatch.setattr(comparison.settings, "model_path", model_path)
    monkeypatch.setattr(comparison.settings, "best_model_path", best_path)
    monkeypatch.setattr(comparison.settings, "mlflow_tracking_uri", "http://mlflow:8080")
    monkeypatch.setattr(comparison.settings, "validation_metrics_path", metrics)
    monkeypatch.setattr(
        comparison.settings,
        "processed_manifest_path",
        tmp_path / "missing-manifest.json",
    )
    monkeypatch.setattr(
        "weather_mlops.models.comparison.load_mlflow_run_metadata",
        lambda: metadata,
    )
    monkeypatch.setattr(comparison, "MlflowClient", lambda tracking_uri=None: fake)
    return model_path, best_path


def test_first_model_is_promoted_when_recall_passes(tmp_path, monkeypatch) -> None:
    fake = FakeClient()
    model_path = tmp_path / "rain_classifier.joblib"
    model_path.write_bytes(b"model")
    _patch_compare(
        tmp_path,
        monkeypatch,
        _metrics(model_path),
        {"run_id": "run-1", "model_version": "1"},
        fake,
    )

    result = comparison.compare_models()

    assert result["promoted"] is True
    assert result["decision"] == "promoted"
    assert (tmp_path / "best_model.joblib").read_bytes() == b"model"
    assert fake.tags[("weather-rainfall-classifier", "1", "stage")] == "champion"
    assert fake.aliases[("weather-rainfall-classifier", "champion")] == "1"
    assert ("run-1", "validation_roc_auc", 0.88) in fake.metrics


def test_first_model_is_rejected_when_recall_is_below_guardrail(tmp_path, monkeypatch) -> None:
    fake = FakeClient()
    model_path = tmp_path / "rain_classifier.joblib"
    model_path.write_bytes(b"model")
    _patch_compare(
        tmp_path,
        monkeypatch,
        _metrics(model_path, validation_roc_auc=0.90, validation_recall=0.70),
        {"run_id": "run-1", "model_version": "1"},
        fake,
    )

    result = comparison.compare_models()

    assert result["promoted"] is False
    assert result["decision"] == "rejected_recall"
    assert not (tmp_path / "best_model.joblib").exists()
    assert fake.aliases == {}
    assert fake.tags[("weather-rainfall-classifier", "1", "stage")] == "candidate"


def test_compare_keeps_champion_when_roc_auc_does_not_improve(tmp_path, monkeypatch) -> None:
    champion = SimpleNamespace(run_id="run-0", version="1")
    fake = FakeClient(champion=champion)
    fake.runs["run-0"] = SimpleNamespace(
        info=SimpleNamespace(run_id="run-0"),
        data=SimpleNamespace(metrics={"validation_roc_auc": 0.90}),
    )
    model_path = tmp_path / "rain_classifier.joblib"
    model_path.write_bytes(b"model")
    _model_path, best_path = _patch_compare(
        tmp_path,
        monkeypatch,
        _metrics(model_path, validation_roc_auc=0.85, validation_recall=0.80),
        {"run_id": "run-1", "model_version": "2"},
        fake,
    )
    best_path.write_bytes(b"champ")

    result = comparison.compare_models()

    assert result["promoted"] is False
    assert result["decision"] == "kept_previous"
    assert best_path.read_bytes() == b"champ"
    assert fake.aliases == {}


def test_compare_refuses_stale_run_metadata(tmp_path, monkeypatch) -> None:
    fake = FakeClient()
    model_path = tmp_path / "rain_classifier.joblib"
    model_path.write_bytes(b"model")
    _patch_compare(
        tmp_path,
        monkeypatch,
        _metrics(model_path),
        {"run_id": "run-old", "model_version": "1", "model_sha256": "not-this-file"},
        fake,
    )

    try:
        comparison.compare_models()
        raise AssertionError("stale metadata must fail")
    except RuntimeError as exc:
        assert "does not match" in str(exc)
    assert fake.metrics == []
    assert not (tmp_path / "best_model.joblib").exists()


def test_compare_refuses_stale_validation_metrics(tmp_path, monkeypatch) -> None:
    fake = FakeClient()
    model_path = tmp_path / "rain_classifier.joblib"
    model_path.write_bytes(b"model-b")
    _patch_compare(
        tmp_path,
        monkeypatch,
        _metrics(model_path, model_sha256="hash-of-model-a", run_id="run-a"),
        {"run_id": "run-b", "model_version": "2"},
        fake,
    )

    try:
        comparison.compare_models()
        raise AssertionError("stale validation metrics must fail")
    except RuntimeError as exc:
        assert "current joblib" in str(exc)
    assert fake.aliases == {}
    assert fake.metrics == []


def test_compare_stops_when_champion_lookup_fails(tmp_path, monkeypatch) -> None:
    fake = FakeClient(alias_error=ConnectionError("mlflow down"))
    model_path = tmp_path / "rain_classifier.joblib"
    model_path.write_bytes(b"model")
    _patch_compare(
        tmp_path,
        monkeypatch,
        _metrics(model_path, validation_roc_auc=0.60, validation_recall=0.80),
        {"run_id": "run-1", "model_version": "1"},
        fake,
    )

    try:
        comparison.compare_models()
        raise AssertionError("registry errors must not authorize promotion")
    except ConnectionError:
        pass
    assert fake.aliases == {}
    assert not (tmp_path / "best_model.joblib").exists()


def test_compare_rejects_other_invalid_parameter_values(tmp_path, monkeypatch) -> None:
    fake = FakeClient(
        alias_error=MlflowException(
            "Invalid model name.",
            error_code=INVALID_PARAMETER_VALUE,
        )
    )
    model_path = tmp_path / "rain_classifier.joblib"
    model_path.write_bytes(b"model")
    _patch_compare(
        tmp_path,
        monkeypatch,
        _metrics(model_path),
        {"run_id": "run-1", "model_version": "1"},
        fake,
    )

    try:
        comparison.compare_models()
        raise AssertionError("unrelated invalid parameters must not authorize promotion")
    except MlflowException as exc:
        assert "Invalid model name" in str(exc)
    assert fake.aliases == {}


def test_compare_rejects_stale_processed_csvs(tmp_path, monkeypatch) -> None:
    from weather_mlops.data.manifest import (
        PROCESSED_FILES,
        build_processed_manifest,
        write_processed_manifest,
    )

    fake = FakeClient()
    model_path = tmp_path / "rain_classifier.joblib"
    model_path.write_bytes(b"model")
    for name in PROCESSED_FILES:
        (tmp_path / name).write_text(f"{name}\n", encoding="utf-8")
    manifest = build_processed_manifest(
        tmp_path,
        parent_sha256="rawsha",
        train_fraction=0.7,
        validation_fraction=0.15,
    )
    write_processed_manifest(manifest, tmp_path / "manifest.json")
    _patch_compare(
        tmp_path,
        monkeypatch,
        _metrics(model_path, dataset_sha256=manifest["sha256"]),
        {"run_id": "run-1", "model_version": "1"},
        fake,
    )
    monkeypatch.setattr(comparison.settings, "processed_manifest_path", tmp_path / "manifest.json")
    (tmp_path / "X_validation.csv").write_text("tampered\n", encoding="utf-8")

    try:
        comparison.compare_models()
        raise AssertionError("stale processed CSVs must fail")
    except ValueError as exc:
        assert "do not match" in str(exc)
    assert fake.aliases == {}

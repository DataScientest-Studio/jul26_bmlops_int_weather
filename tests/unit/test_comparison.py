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

    def get_model_version(self, _name, _version):
        return SimpleNamespace(run_id="run-1")

    def list_artifacts(self, _run_id):
        paths = {
            "model",
            "joblib/rain_classifier.joblib",
            "metrics/train.json",
            "dataset/manifest.json",
            "lineage/release.json",
        }
        return [SimpleNamespace(path=path) for path in paths]


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
    metadata.setdefault(
        "release",
        {
            "run_id": metadata["run_id"],
            "model_version": metadata["model_version"],
            "model_uri": metadata.get("model_uri", "models:/weather-rainfall-classifier/1"),
            "artifact_uri": "runs:/run-1/model",
            "model_sha256": hash_file(model_path, "sha256"),
            "dataset_sha256": "dataset-sha",
            "git_commit": "abc123",
            "preprocessing_version": "2026.09.15",
            "split": {},
        },
    )
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
    monkeypatch.setattr(comparison.settings, "supabase_url", None)
    monkeypatch.setattr(comparison.settings, "supabase_key", None)
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
    assert result["current_best"] is None
    comparison_payload = json.loads((tmp_path / "comparison.json").read_text(encoding="utf-8"))
    assert comparison_payload["candidate_recall"] == 0.76
    assert comparison_payload["decision"] == "promoted"
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
    assert result["candidate_recall"] == 0.70
    assert not (tmp_path / "best_model.joblib").exists()
    assert fake.aliases == {}
    assert fake.tags[("weather-rainfall-classifier", "1", "stage")] == "candidate"


def test_baseline_bootstrap_promotes_the_first_refit_without_candidate_guardrails(
    tmp_path, monkeypatch
) -> None:
    fake = FakeClient()
    model_path = tmp_path / "rain_classifier.joblib"
    model_path.write_bytes(b"model")
    _patch_compare(
        tmp_path,
        monkeypatch,
        _metrics(model_path, validation_roc_auc=0.71, validation_recall=0.50),
        {"run_id": "run-1", "model_version": "1"},
        fake,
    )

    result = comparison.promote_baseline_champion()

    assert result["promoted"] is True
    assert result["decision"] == "baseline_bootstrap"
    assert (tmp_path / "best_model.joblib").read_bytes() == b"model"
    assert fake.aliases[("weather-rainfall-classifier", "champion")] == "1"
    assert fake.tags[("weather-rainfall-classifier", "1", "stage")] == "champion"
    assert (
        fake.tags[("weather-rainfall-classifier", "1", "promotion_reason")] == "baseline_bootstrap"
    )


def test_baseline_bootstrap_uses_the_explicit_refit_release_metadata(tmp_path, monkeypatch) -> None:
    fake = FakeClient()
    model_path = tmp_path / "rain_classifier.joblib"
    model_path.write_bytes(b"model")
    _patch_compare(
        tmp_path,
        monkeypatch,
        _metrics(model_path, run_id="refit-run"),
        {"run_id": "stale-run", "model_version": "1"},
        fake,
    )
    refit_metadata = {
        "run_id": "refit-run",
        "model_version": "2",
        "model_sha256": hash_file(model_path, "sha256"),
        "release": {
            "run_id": "refit-run",
            "model_version": "2",
            "model_uri": "models:/weather-rainfall-classifier/2",
            "artifact_uri": "runs:/refit-run/model",
            "model_sha256": hash_file(model_path, "sha256"),
            "dataset_sha256": "dataset-sha",
            "git_commit": "abc123",
            "preprocessing_version": "2026.09.15",
            "split": {},
        },
    }
    fake.get_model_version = lambda _name, _version: SimpleNamespace(run_id="refit-run")

    result = comparison.promote_baseline_champion(run_metadata=refit_metadata)

    assert result["run_id"] == "refit-run"
    assert fake.aliases[("weather-rainfall-classifier", "champion")] == "2"


def test_catalog_prefers_the_registered_model_training_snapshot(monkeypatch) -> None:
    captured = {}
    monkeypatch.setattr(
        comparison,
        "catalog_registered_model",
        lambda **kwargs: captured.update(kwargs),
    )

    comparison._catalog_model_version(
        run_metadata={
            "run_id": "refit-run",
            "model_version": "2",
            "model_uri": "models:/weather-rainfall-classifier/2",
            "release": {"dataset_sha256": "full-refit-sha"},
        },
        metrics={},
        payload={"dataset_sha256": "evaluation-split-sha"},
        stage="champion",
        run=SimpleNamespace(data=SimpleNamespace(params={})),
        catalog_client=object(),
    )

    assert captured["dataset_sha256"] == "full-refit-sha"


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
        split={},
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


class _CatalogClient:
    def __init__(self) -> None:
        self.table_name = None
        self.row = None
        self.on_conflict = None
        self.updates: list[dict] = []

    def table(self, name: str):
        self.table_name = name
        return self

    def upsert(self, row, on_conflict=None):
        self.row = row
        self.on_conflict = on_conflict
        return self

    def update(self, row):
        self.updates.append(row)
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def neq(self, *_args, **_kwargs):
        return self

    def execute(self):
        return self


def test_compare_writes_champion_row_to_model_versions(tmp_path, monkeypatch) -> None:
    from weather_mlops.data.manifest import (
        PROCESSED_FILES,
        build_processed_manifest,
        write_processed_manifest,
    )

    fake = FakeClient()
    catalog = _CatalogClient()
    model_path = tmp_path / "rain_classifier.joblib"
    model_path.write_bytes(b"model")
    for name in PROCESSED_FILES:
        (tmp_path / name).write_text(f"{name}\n", encoding="utf-8")
    x_train = tmp_path / "X_train.csv"
    x_train.write_text("Location,MinTemp\nSydney,12.0\n", encoding="utf-8")
    manifest = build_processed_manifest(
        tmp_path,
        parent_sha256="rawsha",
        split={},
    )
    write_processed_manifest(manifest, tmp_path / "manifest.json")
    _patch_compare(
        tmp_path,
        monkeypatch,
        _metrics(model_path, dataset_sha256=manifest["sha256"]),
        {
            "run_id": "run-1",
            "model_version": "1",
            "model_uri": "models:/weather-rainfall-classifier/1",
            "release": {
                "run_id": "run-1",
                "model_version": "1",
                "model_uri": "models:/weather-rainfall-classifier/1",
                "artifact_uri": "runs:/run-1/model",
                "model_sha256": hash_file(model_path, "sha256"),
                "dataset_sha256": manifest["sha256"],
                "git_commit": "abc123",
                "preprocessing_version": "2026.09.15",
                "split": {},
            },
        },
        fake,
    )
    monkeypatch.setattr(comparison.settings, "processed_manifest_path", tmp_path / "manifest.json")
    monkeypatch.setattr(comparison.settings, "x_train_path", x_train)

    result = comparison.compare_models(catalog_client=catalog)

    assert result["promoted"] is True
    assert catalog.row["stage"] == "champion"
    assert catalog.row["mlflow_run_id"] == "run-1"
    assert catalog.row["dataset_sha256"] == manifest["sha256"]
    assert catalog.row["metrics"]["validation_roc_auc"] == 0.88
    assert catalog.row["feature_schema"]["columns"] == ["Location", "MinTemp"]
    assert catalog.row["mlflow_model_version"] == "1"
    assert catalog.on_conflict == "mlflow_run_id"


def test_compare_writes_candidate_when_recall_fails(tmp_path, monkeypatch) -> None:
    fake = FakeClient()
    catalog = _CatalogClient()
    model_path = tmp_path / "rain_classifier.joblib"
    model_path.write_bytes(b"model")
    _patch_compare(
        tmp_path,
        monkeypatch,
        _metrics(model_path, validation_roc_auc=0.90, validation_recall=0.70),
        {"run_id": "run-1", "model_version": "1"},
        fake,
    )

    result = comparison.compare_models(catalog_client=catalog)

    assert result["promoted"] is False
    assert catalog.row["stage"] == "candidate"
    assert catalog.row["mlflow_run_id"] == "run-1"

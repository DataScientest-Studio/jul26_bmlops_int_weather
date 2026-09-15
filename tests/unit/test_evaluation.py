import json

import joblib
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier

from weather_mlops.data.manifest import (
    PROCESSED_FILES,
    build_processed_manifest,
    write_processed_manifest,
)
from weather_mlops.data.versioning import hash_file
from weather_mlops.models.evaluation import evaluate_model


def _write_processed(tmp_path, features: pd.DataFrame, labels: pd.DataFrame) -> dict:
    for name in PROCESSED_FILES:
        if name == "X_validation.csv":
            features.to_csv(tmp_path / name, index=False)
        elif name == "y_validation.csv":
            labels.to_csv(tmp_path / name, index=False)
        else:
            (tmp_path / name).write_text(f"{name}\n", encoding="utf-8")
    manifest = build_processed_manifest(
        tmp_path,
        parent_sha256="rawsha",
        train_fraction=0.7,
        validation_fraction=0.15,
    )
    write_processed_manifest(manifest, tmp_path / "manifest.json")
    return manifest


def test_evaluate_model_records_model_and_dataset_hashes(tmp_path, monkeypatch) -> None:
    features = pd.DataFrame({"a": [0, 1, 0, 1]})
    labels = pd.DataFrame({"RainTomorrow": [0, 1, 0, 1]})
    model = DummyClassifier(strategy="most_frequent").fit(features, labels["RainTomorrow"])
    model_path = tmp_path / "model.joblib"
    joblib.dump(model, model_path)
    manifest = _write_processed(tmp_path, features, labels)
    run_path = tmp_path / "mlflow_run.json"
    run_path.write_text('{"run_id": "run-1"}\n', encoding="utf-8")
    monkeypatch.setattr(
        "weather_mlops.models.tracking.settings.mlflow_run_metadata_path",
        run_path,
    )
    output = tmp_path / "validation.json"

    evaluate_model(
        tmp_path / "X_validation.csv",
        tmp_path / "y_validation.csv",
        model_path,
        output,
        "validation",
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["model_sha256"] == hash_file(model_path, "sha256")
    assert payload["dataset_sha256"] == manifest["sha256"]
    assert payload["run_id"] == "run-1"
    assert "validation_roc_auc" in payload


def test_evaluate_model_rejects_stale_processed_csv(tmp_path) -> None:
    features = pd.DataFrame({"a": [0, 1, 0, 1]})
    labels = pd.DataFrame({"RainTomorrow": [0, 1, 0, 1]})
    model = DummyClassifier(strategy="most_frequent").fit(features, labels["RainTomorrow"])
    model_path = tmp_path / "model.joblib"
    joblib.dump(model, model_path)
    _write_processed(tmp_path, features, labels)
    (tmp_path / "X_validation.csv").write_text("tampered\n", encoding="utf-8")
    output = tmp_path / "validation.json"

    with pytest.raises(ValueError, match="do not match"):
        evaluate_model(
            tmp_path / "X_validation.csv",
            tmp_path / "y_validation.csv",
            model_path,
            output,
            "validation",
        )
    assert not output.exists()

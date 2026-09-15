from pathlib import Path

from weather_mlops.models.tracking import (
    clear_mlflow_run_metadata,
    log_training_run,
    save_mlflow_run_metadata,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_log_training_run_skips_when_tracking_uri_is_unset(tmp_path, monkeypatch) -> None:
    stale = tmp_path / "mlflow_run.json"
    stale.write_text('{"run_id": "old"}\n', encoding="utf-8")
    monkeypatch.setattr(
        "weather_mlops.models.tracking.settings.mlflow_tracking_uri",
        None,
    )
    monkeypatch.setattr(
        "weather_mlops.models.tracking.settings.mlflow_run_metadata_path",
        stale,
    )

    run_id = log_training_run(
        pipeline=object(),
        metrics={"f1": 0.5},
        manifest={"sha256": "abc"},
        n_estimators=10,
        max_depth=2,
        learning_rate=0.1,
        subsample=1.0,
        colsample_bytree=1.0,
        train_rows=4,
        scale_pos_weight=1.0,
        negative_count=3,
        positive_count=1,
        model_path=tmp_path / "model.joblib",
        metrics_path=tmp_path / "train.json",
    )

    assert run_id is None
    assert not stale.exists()


def test_clear_mlflow_run_metadata_deletes_stale_file(tmp_path) -> None:
    path = tmp_path / "mlflow_run.json"
    path.write_text("{}\n", encoding="utf-8")

    clear_mlflow_run_metadata(path)

    assert not path.exists()


def test_save_mlflow_run_metadata_writes_json(tmp_path, monkeypatch) -> None:
    path = tmp_path / "mlflow_run.json"
    monkeypatch.setattr(
        "weather_mlops.models.tracking.settings.mlflow_run_metadata_path",
        path,
    )

    save_mlflow_run_metadata(
        run_id="run-1",
        model_version="3",
        model_uri="runs:/run-1/model",
        model_sha256="abc123",
    )

    text = path.read_text(encoding="utf-8")
    assert "run-1" in text
    assert '"model_version": "3"' in text
    assert '"model_sha256": "abc123"' in text


def test_training_logs_joblib_lineage_and_git_tags() -> None:
    source = (PROJECT_ROOT / "src" / "weather_mlops" / "models" / "tracking.py").read_text(
        encoding="utf-8"
    )

    assert "mlflow.log_dict(" in source
    assert 'artifact_path="joblib"' in source
    assert 'artifact_path="metrics"' in source
    assert 'key="dataset_sha256"' in source
    assert 'key="git_commit"' in source
    assert "clear_mlflow_run_metadata()" in source
    assert "skops_trusted_types" in source
    assert "xgboost.core.Booster" in source
    assert "xgboost.sklearn.XGBClassifier" in source
    assert "numpy.dtype" in source


def test_sklearn_save_model_roundtrips_preprocessor_and_xgboost(tmp_path) -> None:
    import mlflow.sklearn
    import pandas as pd
    from sklearn.pipeline import Pipeline
    from xgboost import XGBClassifier

    from weather_mlops.data.preprocess import build_preprocessor
    from weather_mlops.models.tracking import SKOPS_TRUSTED_TYPES

    features = pd.DataFrame(
        {
            "MinTemp": [10.0, 12.0, 11.0, 13.0],
            "Humidity3pm": [40.0, 50.0, 45.0, 55.0],
            "Location": ["Sydney", "Sydney", "Perth", "Perth"],
            "WindGustDir": ["N", "S", "E", "W"],
        }
    )
    labels = [0, 1, 0, 1]
    pipeline = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor(features)),
            ("classifier", XGBClassifier(n_estimators=2, max_depth=1, verbosity=0)),
        ]
    )
    pipeline.fit(features, labels)
    model_dir = tmp_path / "sklearn-model"

    mlflow.sklearn.save_model(
        pipeline,
        model_dir,
        skops_trusted_types=SKOPS_TRUSTED_TYPES,
    )
    loaded = mlflow.sklearn.load_model(model_dir)

    assert loaded.predict(features).tolist() == pipeline.predict(features).tolist()

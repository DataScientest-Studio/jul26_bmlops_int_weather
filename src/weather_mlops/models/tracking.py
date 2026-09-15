"""Optional MLflow logging for a completed training run.

Skipped when MLFLOW_TRACKING_URI is unset or the server is not reachable, so
POST /train still writes the local joblib without a running MLflow.
"""

from __future__ import annotations

import json
from pathlib import Path

from sklearn.pipeline import Pipeline

from weather_mlops.config.settings import settings
from weather_mlops.data.catalog import current_git_commit


def save_mlflow_run_metadata(run_id, model_name, model_version) -> None:
    output_path = settings.mlflow_run_metadata_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "model_name": model_name,
                "model_version": str(model_version),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"MLflow run metadata saved to: {output_path}")


def log_training_run(
    *,
    pipeline: Pipeline,
    metrics: dict[str, float],
    manifest: dict,
    n_estimators: int,
    max_depth: int,
    learning_rate: float,
    subsample: float,
    colsample_bytree: float,
    train_rows: int,
    scale_pos_weight: float,
    negative_count: int,
    positive_count: int,
) -> str | None:
    """Register the run. Returns the run id, or None if MLflow was skipped."""

    tracking_uri = settings.mlflow_tracking_uri
    if not tracking_uri:
        return None

    import mlflow
    import mlflow.sklearn
    from mlflow.tracking import MlflowClient

    mlflow.set_tracking_uri(tracking_uri)
    try:
        mlflow.set_experiment(settings.mlflow_experiment_name)
    except Exception as exc:
        print(f"MLflow unreachable at {tracking_uri}: {exc}. Skipping tracking.")
        return None

    git_commit = manifest.get("git_commit")
    training_commit = current_git_commit()

    with mlflow.start_run() as run:
        run_id = run.info.run_id
        params = {
            "dataset_sha256": manifest.get("sha256"),
            "parent_sha256": manifest.get("parent_sha256"),
            "preprocessing_version": manifest.get("preprocessing_version"),
            "preprocess_git_commit": manifest.get("git_commit"),
            "git_commit": training_commit or git_commit,
            "train_rows": train_rows,
            "negative_samples": negative_count,
            "positive_samples": positive_count,
            "scale_pos_weight": scale_pos_weight,
            "model_type": "XGBClassifier",
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "random_state": settings.random_state,
        }
        mlflow.log_params({key: str(value) for key, value in params.items() if value is not None})
        mlflow.log_metrics({f"train_{name}": float(value) for name, value in metrics.items()})
        mlflow.sklearn.log_model(
            pipeline,
            name="model",
            registered_model_name=settings.mlflow_model_name,
            skops_trusted_types=[
                "numpy.dtype",
                "xgboost.core.Booster",
                "xgboost.sklearn.XGBClassifier",
            ],
        )
        client = MlflowClient()
        model_versions = list(
            client.search_model_versions(filter_string=f"name='{settings.mlflow_model_name}'")
        )
        if not model_versions:
            raise RuntimeError(
                f"Model '{settings.mlflow_model_name}' was registered, "
                "but no model versions were returned."
            )
        new_model_version = max(model_versions, key=lambda version: int(version.version))
        version_number = str(new_model_version.version)
        client.set_model_version_tag(
            name=settings.mlflow_model_name,
            version=version_number,
            key="status",
            value="candidate",
        )
        client.set_model_version_tag(
            name=settings.mlflow_model_name,
            version=version_number,
            key="dataset_sha256",
            value=str(manifest.get("sha256") or ""),
        )
        if training_commit:
            client.set_model_version_tag(
                name=settings.mlflow_model_name,
                version=version_number,
                key="git_commit",
                value=training_commit,
            )
        save_mlflow_run_metadata(
            run_id=run_id,
            model_name=settings.mlflow_model_name,
            model_version=version_number,
        )
        print(
            f"MLflow run: {run_id}\n"
            f"Registered model: {settings.mlflow_model_name}\n"
            f"Model version: {version_number}"
        )
        return run_id


def load_mlflow_run_metadata(path: Path | None = None) -> dict:
    metadata_path = path or settings.mlflow_run_metadata_path
    return json.loads(metadata_path.read_text(encoding="utf-8"))

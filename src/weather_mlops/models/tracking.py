"""Log training runs to MLflow and keep a local pointer to the current run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import mlflow
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from weather_mlops.config.settings import settings
from weather_mlops.data.catalog import current_git_commit

# MLflow 3.16 skops refuses these types unless they are explicit.
SKOPS_TRUSTED_TYPES = [
    "xgboost.core.Booster",
    "xgboost.sklearn.XGBClassifier",
    "numpy.dtype",
]


def _tracking_reachable() -> bool:
    uri = settings.mlflow_tracking_uri
    if not uri:
        return False
    try:
        mlflow.set_tracking_uri(uri)
        mlflow.get_experiment_by_name(settings.mlflow_experiment_name)
        return True
    except Exception:
        return False


def clear_mlflow_run_metadata(path: Path | None = None) -> None:
    """Drop stale run identity so later compare cannot mix models."""
    metadata_path = path or settings.mlflow_run_metadata_path
    if metadata_path.exists():
        metadata_path.unlink()


def save_mlflow_run_metadata(
    *,
    run_id: str,
    model_version: str | None,
    model_uri: str | None,
    model_sha256: str | None = None,
    path: Path | None = None,
) -> None:
    metadata_path = path or settings.mlflow_run_metadata_path
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "model_version": model_version,
        "model_uri": model_uri,
        "model_sha256": model_sha256,
        "model_name": settings.mlflow_model_name,
    }
    metadata_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_mlflow_run_metadata(path: Path | None = None) -> dict[str, Any]:
    metadata_path = path or settings.mlflow_run_metadata_path
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def log_training_run(
    *,
    pipeline: Any,
    metrics: dict[str, float],
    manifest: dict[str, Any],
    n_estimators: int,
    max_depth: int,
    learning_rate: float,
    subsample: float,
    colsample_bytree: float,
    train_rows: int,
    scale_pos_weight: float,
    negative_count: int,
    positive_count: int,
    model_path: Path,
    metrics_path: Path,
    model_sha256: str | None = None,
) -> dict[str, Any] | None:
    """Start a run, log params/metrics/artifacts, register a candidate version.

    Unset or unreachable tracking skips MLflow. Stale run metadata is always
    removed first so compare cannot attach new metrics to an old model.
    """
    clear_mlflow_run_metadata()
    if not settings.mlflow_tracking_uri:
        print("MLflow tracking URI is not set; skipping run logging.")
        return None
    if not _tracking_reachable():
        print(
            f"MLflow tracking URI {settings.mlflow_tracking_uri} is unreachable; "
            "skipping run logging."
        )
        return None

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment_name)

    dataset_sha256 = manifest.get("sha256")
    git_commit = current_git_commit()
    params = {
        "n_estimators": n_estimators,
        "max_depth": max_depth,
        "learning_rate": learning_rate,
        "subsample": subsample,
        "colsample_bytree": colsample_bytree,
        "random_state": settings.random_state,
        "train_rows": train_rows,
        "scale_pos_weight": scale_pos_weight,
        "negative_count": negative_count,
        "positive_count": positive_count,
    }

    with mlflow.start_run() as run:
        mlflow.log_params({key: str(value) for key, value in params.items()})
        mlflow.log_metrics({f"train_{name}": float(value) for name, value in metrics.items()})
        mlflow.set_tags(
            {
                "stage": "candidate",
                "dataset_sha256": dataset_sha256 or "",
                "git_commit": git_commit or "",
                "parent_sha256": manifest.get("parent_sha256") or "",
                "preprocessing_version": manifest.get("preprocessing_version") or "",
            }
        )
        mlflow.log_artifact(str(metrics_path), artifact_path="metrics")
        if Path(model_path).exists():
            mlflow.log_artifact(str(model_path), artifact_path="joblib")
        if dataset_sha256:
            mlflow.log_dict(manifest, "dataset/manifest.json")
        model_info = mlflow.sklearn.log_model(
            sk_model=pipeline,
            name="model",
            registered_model_name=settings.mlflow_model_name,
            skops_trusted_types=SKOPS_TRUSTED_TYPES,
        )
        client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
        versions = [
            version
            for version in client.search_model_versions(
                filter_string=f"name='{settings.mlflow_model_name}'"
            )
            if version.run_id == run.info.run_id
        ]
        if not versions:
            raise MlflowException(
                f"Model '{settings.mlflow_model_name}' was registered, "
                f"but no version exists for run {run.info.run_id}."
            )
        model_version = max(versions, key=lambda item: int(item.version))
        client.set_model_version_tag(
            name=settings.mlflow_model_name,
            version=model_version.version,
            key="dataset_sha256",
            value=dataset_sha256 or "",
        )
        client.set_model_version_tag(
            name=settings.mlflow_model_name,
            version=model_version.version,
            key="git_commit",
            value=git_commit or "",
        )
        client.set_registered_model_alias(
            name=settings.mlflow_model_name,
            alias="candidate",
            version=model_version.version,
        )
        save_mlflow_run_metadata(
            run_id=run.info.run_id,
            model_version=str(model_version.version),
            model_uri=model_info.model_uri,
            model_sha256=model_sha256,
        )
        print(
            f"Registered model: {settings.mlflow_model_name}\n"
            f"  run_id: {run.info.run_id}\n"
            f"  version: {model_version.version}\n"
            f"  uri: {model_info.model_uri}"
        )
        return {
            "run_id": run.info.run_id,
            "model_version": str(model_version.version),
            "model_uri": model_info.model_uri,
            "model_sha256": model_sha256,
        }

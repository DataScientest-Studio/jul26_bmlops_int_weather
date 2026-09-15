"""Promote a candidate to champion when it beats the current best on ROC-AUC."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from weather_mlops.config.settings import settings
from weather_mlops.data.manifest import verify_processed_manifest
from weather_mlops.data.versioning import hash_file
from weather_mlops.models.tracking import load_mlflow_run_metadata


def _load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _numeric_metrics(payload: dict[str, Any]) -> dict[str, float]:
    return {key: float(value) for key, value in payload.items() if isinstance(value, (int, float))}


def _recall(metrics: dict[str, float]) -> float:
    return float(metrics.get(settings.mlflow_recall_metric, 0.0))


def _primary(metrics: dict[str, float]) -> float:
    return float(metrics.get(settings.mlflow_primary_metric, 0.0))


def meets_promotion_guardrails(metrics: dict[str, float]) -> bool:
    return _recall(metrics) >= settings.mlflow_min_recall


def _copy_champion_joblib(model_source_path: Path) -> None:
    source = Path(model_source_path)
    if not source.exists():
        raise FileNotFoundError(f"No trained model at {source}. Train first.")
    settings.best_model_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, settings.best_model_path)


def _is_missing_champion_alias(exc: BaseException) -> bool:
    """SQLite registries report a missing alias as INVALID_PARAMETER_VALUE."""
    if not isinstance(exc, MlflowException):
        return False
    if exc.error_code == "RESOURCE_DOES_NOT_EXIST":
        return True
    message = str(exc).lower()
    return (
        exc.error_code == "INVALID_PARAMETER_VALUE"
        and "alias" in message
        and "not found" in message
    )


def _current_dataset_sha256() -> str | None:
    manifest_path = settings.processed_manifest_path
    if not manifest_path.exists():
        return None
    stored = verify_processed_manifest(manifest_path.parent)
    return str(stored["sha256"])


def _require_matching_run(model_source_path: Path) -> dict:
    metadata = load_mlflow_run_metadata()
    expected = metadata.get("model_sha256")
    actual = hash_file(Path(model_source_path), "sha256")
    if expected and expected != actual:
        raise RuntimeError(
            "mlflow_run.json does not match the current joblib. "
            "Retrain with MLflow reachable so validation cannot attach to an old run."
        )
    return metadata


def _require_matching_evaluation(
    payload: dict[str, Any],
    model_source_path: Path,
    run_metadata: dict[str, Any],
) -> None:
    recorded_model = payload.get("model_sha256")
    actual_model = hash_file(Path(model_source_path), "sha256")
    if not recorded_model:
        raise RuntimeError("validation.json has no model_sha256. Re-run make validate.")
    if recorded_model != actual_model:
        raise RuntimeError(
            "validation.json was not produced for the current joblib. Re-run make validate."
        )
    recorded_run = payload.get("run_id")
    if recorded_run and recorded_run != run_metadata.get("run_id"):
        raise RuntimeError(
            "validation.json belongs to a different MLflow run. Re-run make validate."
        )
    recorded_dataset = payload.get("dataset_sha256")
    if recorded_dataset:
        current_dataset = _current_dataset_sha256()
        if not current_dataset:
            raise RuntimeError("Processed dataset cannot be verified. Re-run make validate.")
        if recorded_dataset != current_dataset:
            raise RuntimeError(
                "validation.json was not produced for the current dataset. Re-run make validate."
            )


def _load_champion(client: MlflowClient):
    try:
        return client.get_model_version_by_alias(
            settings.mlflow_model_name,
            settings.mlflow_champion_alias,
        )
    except MlflowException as exc:
        if _is_missing_champion_alias(exc):
            return None
        raise


def compare_models(
    metrics_path: Path | None = None,
    model_source_path: Path | None = None,
) -> dict:
    """Keep champion unless the candidate has higher ROC-AUC and recall ≥ 0.75."""
    metrics_path = Path(metrics_path or settings.validation_metrics_path)
    model_source_path = Path(model_source_path or settings.model_path)
    if not metrics_path.exists():
        raise FileNotFoundError(f"No validation metrics at {metrics_path}. Validate first.")
    if not settings.mlflow_tracking_uri:
        raise RuntimeError("MLFLOW_TRACKING_URI is not set.")
    if not model_source_path.exists():
        raise FileNotFoundError(f"No trained model at {model_source_path}. Train first.")

    run_metadata = _require_matching_run(model_source_path)
    payload = _load_payload(metrics_path)
    _require_matching_evaluation(payload, model_source_path, run_metadata)
    metrics = _numeric_metrics(payload)
    client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
    run = client.get_run(run_metadata["run_id"])
    for name, value in metrics.items():
        client.log_metric(run.info.run_id, name, value)

    candidate_score = _primary(metrics)
    candidate_recall = _recall(metrics)
    passed_guardrail = meets_promotion_guardrails(metrics)
    current_best: float | None = None
    champion = _load_champion(client)
    if champion is not None:
        champion_run = client.get_run(champion.run_id)
        current_best = float(champion_run.data.metrics.get(settings.mlflow_primary_metric) or 0.0)

    promote = passed_guardrail and (champion is None or candidate_score > current_best)
    if promote:
        client.set_registered_model_alias(
            name=settings.mlflow_model_name,
            alias=settings.mlflow_champion_alias,
            version=run_metadata["model_version"],
        )
        client.set_model_version_tag(
            name=settings.mlflow_model_name,
            version=run_metadata["model_version"],
            key="stage",
            value="champion",
        )
        _copy_champion_joblib(model_source_path)
        decision = "promoted"
    else:
        client.set_model_version_tag(
            name=settings.mlflow_model_name,
            version=run_metadata["model_version"],
            key="stage",
            value="candidate",
        )
        if not passed_guardrail:
            decision = "rejected_recall"
        else:
            decision = "kept_previous"

    result = {
        "run_id": run_metadata["run_id"],
        "model_version": run_metadata["model_version"],
        "metric": settings.mlflow_primary_metric,
        "candidate_score": candidate_score,
        "candidate_recall": candidate_recall,
        "current_best": current_best,
        "promoted": promote,
        "decision": decision,
    }
    print(
        f"Compare: {decision} "
        f"({settings.mlflow_primary_metric}={candidate_score:.4f}, "
        f"{settings.mlflow_recall_metric}={candidate_recall:.4f}, "
        f"best={current_best})"
    )
    return result


def main() -> None:
    compare_models()


if __name__ == "__main__":
    main()

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from weather_mlops.config.settings import settings
from weather_mlops.data.manifest import verify_processed_manifest
from weather_mlops.data.versioning import hash_file


def evaluate_classifier(
    y_true: Any,
    y_pred: Any,
    y_probability: Any,
) -> dict[str, float]:
    """Calculate classification metrics."""

    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, y_probability),
    }


def _dataset_sha256(x_data_path: Path, y_data_path: Path) -> str:
    output_dir = x_data_path.parent
    manifest_path = output_dir / "manifest.json"
    if manifest_path.exists():
        stored = verify_processed_manifest(output_dir)
        return str(stored["sha256"])
    digest = hashlib.sha256()
    digest.update(hash_file(x_data_path, "sha256").encode())
    digest.update(hash_file(y_data_path, "sha256").encode())
    return digest.hexdigest()


def _evaluation_run_id() -> str | None:
    from weather_mlops.models.tracking import load_mlflow_run_metadata

    try:
        return load_mlflow_run_metadata().get("run_id")
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _log_report_artifact(metrics_output_path: Path, run_id: str | None) -> None:
    if not run_id or not settings.mlflow_tracking_uri:
        return
    try:
        from mlflow.tracking import MlflowClient

        MlflowClient(tracking_uri=settings.mlflow_tracking_uri).log_artifact(
            run_id, str(metrics_output_path), artifact_path="metrics"
        )
    except Exception as exc:
        print(
            f"MLflow tracking URI {settings.mlflow_tracking_uri} is unreachable; "
            f"skipping report logging ({exc})."
        )


def evaluate_model(
    x_data_path: Path,
    y_data_path: Path,
    model_path: Path,
    metrics_output_path: Path,
    split_name: str = "test",
) -> dict[str, float]:
    from weather_mlops.data.preprocess import TARGET_COLUMN

    dataset_sha256 = _dataset_sha256(x_data_path, y_data_path)
    X_data = pd.read_csv(x_data_path)
    y_data = pd.read_csv(y_data_path)[TARGET_COLUMN]

    model = joblib.load(model_path)

    predictions = model.predict(X_data)
    probabilities = model.predict_proba(X_data)[:, 1]
    metrics = evaluate_classifier(y_data, predictions, probabilities)

    run_id = _evaluation_run_id()

    metrics_output_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_output_path.write_text(
        json.dumps(
            {
                f"{split_name}_rows": len(X_data),
                **{f"{split_name}_{name}": value for name, value in metrics.items()},
                "model_sha256": hash_file(model_path, "sha256"),
                "dataset_sha256": dataset_sha256,
                "run_id": run_id,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Evaluation metrics saved to: {metrics_output_path}")
    for name, value in metrics.items():
        print(f"  {name:<10}: {value:.4f}")

    _log_report_artifact(metrics_output_path, run_id)

    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a trained rainfall classifier.")
    parser.add_argument("--x-data", type=Path, default=settings.x_test_path)
    parser.add_argument("--y-data", type=Path, default=settings.y_test_path)
    parser.add_argument("--model-path", type=Path, default=settings.model_path)
    parser.add_argument("--metrics-output", type=Path, default=settings.evaluation_metrics_path)
    parser.add_argument("--split-name", default="test")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evaluate_model(args.x_data, args.y_data, args.model_path, args.metrics_output, args.split_name)


if __name__ == "__main__":
    main()

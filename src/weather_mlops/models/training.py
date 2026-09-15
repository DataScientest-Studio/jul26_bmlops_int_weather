import argparse
import json
import tempfile
import threading
from pathlib import Path

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from weather_mlops.config.settings import settings
from weather_mlops.data.catalog import current_git_commit
from weather_mlops.data.manifest import verify_processed_manifest
from weather_mlops.data.preprocess import TARGET_COLUMN, build_preprocessor
from weather_mlops.models.evaluation import evaluate_classifier
from weather_mlops.models.tracking import log_training_run

_TRAIN_LOCK = threading.Lock()


def load_verified_training_inputs(
    x_train_path=settings.x_train_path,
    y_train_path=settings.y_train_path,
) -> tuple[Path, Path, dict]:
    """Require a matching processed manifest before any model fit.

    The six CSVs and manifest.json are one input set. A missing or stale
    manifest is rejected so training cannot record an old dataset identity.
    """

    x_train_path = Path(x_train_path)
    y_train_path = Path(y_train_path)
    processed_dir = x_train_path.parent
    if y_train_path.parent.resolve() != processed_dir.resolve():
        raise FileNotFoundError("X_train and y_train must live next to manifest.json")
    if x_train_path.name != "X_train.csv" or y_train_path.name != "y_train.csv":
        raise ValueError(
            "Training files must be X_train.csv and y_train.csv next to the verified manifest"
        )
    manifest = verify_processed_manifest(processed_dir)
    return x_train_path, y_train_path, manifest


def train_model(
    x_train_path=settings.x_train_path,
    y_train_path=settings.y_train_path,
    model_output_path=settings.model_path,
    metrics_output_path=settings.train_metrics_path,
    n_estimators: int = 250,
    max_depth: int = 4,
    learning_rate: float = 0.05,
    subsample: float = 0.9,
    colsample_bytree: float = 0.9,
) -> tuple[Pipeline, dict[str, float]]:
    """Train and evaluate the XGBoost rainfall classifier."""

    with _TRAIN_LOCK:
        return _train_model_unlocked(
            x_train_path=x_train_path,
            y_train_path=y_train_path,
            model_output_path=model_output_path,
            metrics_output_path=metrics_output_path,
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
        )


def _train_model_unlocked(
    *,
    x_train_path,
    y_train_path,
    model_output_path,
    metrics_output_path,
    n_estimators: int,
    max_depth: int,
    learning_rate: float,
    subsample: float,
    colsample_bytree: float,
) -> tuple[Pipeline, dict[str, float]]:
    x_train_path, y_train_path, manifest = load_verified_training_inputs(
        x_train_path,
        y_train_path,
    )
    X_train = pd.read_csv(x_train_path)
    y_train = pd.read_csv(y_train_path)[TARGET_COLUMN]

    print(f"Training samples: {len(X_train):,}")

    preprocessor = build_preprocessor(X_train)

    negative_count = int((y_train == 0).sum())
    positive_count = int((y_train == 1).sum())
    scale_pos_weight = negative_count / positive_count if positive_count else 1.0

    model = XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        objective="binary:logistic",
        eval_metric="logloss",
        scale_pos_weight=scale_pos_weight,
        random_state=settings.random_state,
        n_jobs=-1,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", model),
        ]
    )

    print("Training XGBoost model...")
    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_train)
    probabilities = pipeline.predict_proba(X_train)[:, 1]
    metrics = evaluate_classifier(
        y_true=y_train,
        y_pred=predictions,
        y_probability=probabilities,
    )

    print("\nEvaluation:")
    for name, value in metrics.items():
        print(f"  {name:<10}: {value:.4f}")

    model_output_path = Path(model_output_path)
    metrics_output_path = Path(metrics_output_path)
    model_output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=model_output_path.parent,
        suffix=".joblib.tmp",
        delete=False,
    ) as handle:
        tmp_path = Path(handle.name)
    try:
        joblib.dump(pipeline, tmp_path)
        tmp_path.replace(model_output_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    metrics_output_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_output_path.write_text(
        json.dumps(
            {
                "train_rows": len(X_train),
                "scale_pos_weight": scale_pos_weight,
                "dataset_sha256": manifest["sha256"],
                "parent_sha256": manifest.get("parent_sha256"),
                "preprocessing_version": manifest.get("preprocessing_version"),
                "preprocess_git_commit": manifest.get("git_commit"),
                "git_commit": current_git_commit(),
                **{f"train_{name}": value for name, value in metrics.items()},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"\nModel saved to: {model_output_path}")
    print(f"Training metrics saved to: {metrics_output_path}")

    log_training_run(
        pipeline=pipeline,
        metrics=metrics,
        manifest=manifest,
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        train_rows=len(X_train),
        scale_pos_weight=scale_pos_weight,
        negative_count=negative_count,
        positive_count=positive_count,
    )

    return pipeline, metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the rainfall classifier.")
    parser.add_argument("--x-train", default=settings.x_train_path, type=Path)
    parser.add_argument("--y-train", default=settings.y_train_path, type=Path)
    parser.add_argument("--model-output", default=settings.model_path, type=Path)
    parser.add_argument(
        "--metrics-output",
        default=settings.train_metrics_path,
        type=Path,
    )
    parser.add_argument("--n-estimators", type=int, default=250)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--subsample", type=float, default=0.9)
    parser.add_argument("--colsample-bytree", type=float, default=0.9)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_model(
        x_train_path=args.x_train,
        y_train_path=args.y_train,
        model_output_path=args.model_output,
        metrics_output_path=args.metrics_output,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        learning_rate=args.learning_rate,
        subsample=args.subsample,
        colsample_bytree=args.colsample_bytree,
    )


if __name__ == "__main__":
    main()

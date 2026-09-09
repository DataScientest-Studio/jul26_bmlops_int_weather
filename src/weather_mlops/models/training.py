import argparse
import json
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.tracking import MlflowClient
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from weather_mlops.config.settings import settings
from weather_mlops.data.preprocess import TARGET_COLUMN, build_preprocessor
from weather_mlops.models.evaluation import evaluate_classifier

mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

MLFLOW_EXPERIMENT_NAME = settings.mlflow_experiment_name
MLFLOW_MODEL_NAME = settings.mlflow_model_name


def load_dataset_metadata() -> dict:
    with settings.dataset_metadata_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_mlflow_run_metadata(run_id, model_name, model_version) -> None:
    """
    Save the MLflow run/model version
    """

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

    X_train = pd.read_csv(x_train_path)
    y_train = pd.read_csv(y_train_path)[TARGET_COLUMN]

    print(f"Training samples: {len(X_train):,}")

    dataset_metadata = load_dataset_metadata()

    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    with mlflow.start_run() as run:
        run_id = run.info.run_id

        mlflow.log_params(
            {
                "dataset_name": dataset_metadata["dataset_name"],
                "dataset_sha256": dataset_metadata["sha256"],
                "dataset_size_bytes": dataset_metadata["size_bytes"],
                "train_rows": len(X_train),
            }
        )

        negative_count = int((y_train == 0).sum())
        positive_count = int((y_train == 1).sum())

        scale_pos_weight = negative_count / positive_count if positive_count else 1.0

        mlflow.log_params(
            {
                "negative_samples": negative_count,
                "positive_samples": positive_count,
                "scale_pos_weight": scale_pos_weight,
            }
        )

        mlflow.log_params(
            {
                "model_type": "XGBClassifier",
                "n_estimators": n_estimators,
                "max_depth": max_depth,
                "learning_rate": learning_rate,
                "subsample": subsample,
                "colsample_bytree": colsample_bytree,
                "random_state": settings.random_state,
            }
        )

        preprocessor = build_preprocessor(X_train)

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

        mlflow.log_metrics({f"train_{name}": float(value) for name, value in metrics.items()})

        model_output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        joblib.dump(pipeline, model_output_path)

        metrics_output_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_output_path.write_text(
            json.dumps(
                {
                    "train_rows": len(X_train),
                    "scale_pos_weight": scale_pos_weight,
                    **{f"train_{name}": value for name, value in metrics.items()},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        # Log local model as an MLflow artifact and register it
        print("Registering model with MLflow...")

        mlflow.sklearn.log_model(
            pipeline,
            name="model",
            registered_model_name=MLFLOW_MODEL_NAME,
            skops_trusted_types=[
                "numpy.dtype",
                "xgboost.core.Booster",
                "xgboost.sklearn.XGBClassifier",
            ],
        )

        client = MlflowClient()

        model_versions = list(
            client.search_model_versions(filter_string=f"name='{MLFLOW_MODEL_NAME}'")
        )

        if not model_versions:
            raise RuntimeError(
                f"Model '{MLFLOW_MODEL_NAME}' was registered, but no model versions were returned."
            )

        new_model_version = max(
            model_versions,
            key=lambda version: int(version.version),
        )

        print(f"Registered model version: {new_model_version.version}")

        version_number = str(new_model_version.version)

        client.set_model_version_tag(
            name=MLFLOW_MODEL_NAME,
            version=version_number,
            key="status",
            value="candidate",
        )

        client.set_model_version_tag(
            name=MLFLOW_MODEL_NAME,
            version=version_number,
            key="dataset_sha256",
            value=dataset_metadata["sha256"],
        )

        client.set_model_version_tag(
            name=MLFLOW_MODEL_NAME,
            version=version_number,
            key="model_type",
            value="XGBClassifier",
        )

        save_mlflow_run_metadata(
            run_id=run_id,
            model_name=MLFLOW_MODEL_NAME,
            model_version=version_number,
        )

        print(
            f"MLflow run: {run_id}\n"
            f"Registered model: {MLFLOW_MODEL_NAME}\n"
            f"Model version: {version_number}"
        )

        print(f"\nModel saved to: {model_output_path}")
        print(f"Training metrics saved to: {metrics_output_path}")

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

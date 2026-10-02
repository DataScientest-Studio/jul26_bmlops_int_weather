"""Bootstrap the first production rainfall model from the Kaggle seed data."""

from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path
from typing import Any

import mlflow
import pandas as pd
import yaml
from mlflow.tracking import MlflowClient
from sklearn.model_selection import ParameterSampler
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from weather_mlops.config.settings import PROJECT_ROOT, settings
from weather_mlops.data.catalog import current_git_commit
from weather_mlops.data.manifest import (
    build_processed_manifest,
    verify_processed_manifest,
    write_processed_manifest,
)
from weather_mlops.data.preprocess import (
    TARGET_COLUMN,
    build_preprocessor,
    build_split_metadata,
    clean_dataframe,
    split_features_target,
    temporal_train_validation_test_split,
)
from weather_mlops.data.snapshots import register_local_snapshot, register_processed_snapshot
from weather_mlops.data.versioning import hash_file
from weather_mlops.models.comparison import promote_baseline_champion
from weather_mlops.models.evaluation import evaluate_classifier, evaluate_model
from weather_mlops.models.tracking import load_mlflow_run_metadata
from weather_mlops.models.training import train_model


def _write_processed_split(
    output_dir: Path,
    *,
    X_train: pd.DataFrame,
    X_validation: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_validation: pd.Series,
    y_test: pd.Series,
    parent_sha256: str,
    split: dict[str, Any],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "X_train.csv": X_train,
        "X_validation.csv": X_validation,
        "X_test.csv": X_test,
        "y_train.csv": y_train.to_frame(),
        "y_validation.csv": y_validation.to_frame(),
        "y_test.csv": y_test.to_frame(),
    }
    for name, frame in outputs.items():
        frame.to_csv(output_dir / name, index=False)
    manifest = build_processed_manifest(
        output_dir,
        parent_sha256=parent_sha256,
        split=split,
    )
    write_processed_manifest(manifest, output_dir / "manifest.json")
    return manifest


def prepare_baseline_splits(
    *,
    raw_path: Path,
    selection_dir: Path,
    refit_dir: Path,
    validation_window_days: int,
    test_window_days: int,
) -> dict[str, str]:
    """Create a frozen selection split and a full-Kaggle refit split.

    Parameter selection sees only the rows before the validation period.  The
    full-data refit is linked back to that immutable selection manifest, while
    retaining the frozen validation/test rows for auditable evaluation.
    """

    raw_path = Path(raw_path)
    cleaned = clean_dataframe(pd.read_csv(raw_path))
    parent_sha256 = hash_file(raw_path, "sha256")
    X_train, X_validation, X_test, y_train, y_validation, y_test = (
        temporal_train_validation_test_split(
            cleaned,
            training_window_days=None,
            validation_window_days=validation_window_days,
            test_window_days=test_window_days,
        )
    )
    selection_split = build_split_metadata(
        cleaned,
        training_window_days=None,
        validation_window_days=validation_window_days,
        test_window_days=test_window_days,
    )
    selection_split["strategy"] = "baseline_hyperparameter_selection"
    selection_manifest = _write_processed_split(
        Path(selection_dir),
        X_train=X_train,
        X_validation=X_validation,
        X_test=X_test,
        y_train=y_train,
        y_validation=y_validation,
        y_test=y_test,
        parent_sha256=parent_sha256,
        split=selection_split,
    )

    X_full, y_full = split_features_target(cleaned)
    refit_split = {
        "strategy": "baseline_full_kaggle_refit",
        "fit_scope": "all_kaggle_rows",
        "selection_manifest_sha256": selection_manifest["sha256"],
        "validation_start": selection_split["validation_start"],
        "validation_end": selection_split["validation_end"],
        "test_start": selection_split["test_start"],
        "test_end": selection_split["test_end"],
    }
    refit_manifest = _write_processed_split(
        Path(refit_dir),
        X_train=X_full,
        X_validation=X_validation,
        X_test=X_test,
        y_train=y_full,
        y_validation=y_validation,
        y_test=y_test,
        parent_sha256=parent_sha256,
        split=refit_split,
    )
    return {
        "selection_manifest_sha256": str(selection_manifest["sha256"]),
        "refit_manifest_sha256": str(refit_manifest["sha256"]),
    }


def write_selected_parameters(
    path: Path,
    *,
    params: dict[str, int | float],
    selection_manifest_sha256: str,
    selection_run_id: str | None,
) -> Path:
    """Write the selected configuration as a release artifact, not source config.

    A training run must keep a clean Git revision.  Updating ``params.yaml``
    during a run would make that provenance dirty, so the selected settings
    live in the run's immutable evidence instead.
    """

    lines = ["model:"]
    lines.extend(f"  {name}: {value}" for name, value in params.items())
    lines.extend(
        [
            "selection:",
            f"  selection_manifest_sha256: {selection_manifest_sha256}",
            f"  selection_run_id: {selection_run_id or ''}",
        ]
    )
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def _search_space_size(search_space: dict[str, list[int | float]]) -> int:
    if not search_space or any(not values for values in search_space.values()):
        raise ValueError("The hyperparameter search space must contain non-empty value lists.")
    return len(list(product(*search_space.values())))


def _fit_pipeline(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    params: dict[str, int | float],
) -> Pipeline:
    positive_count = int((y_train == 1).sum())
    negative_count = int((y_train == 0).sum())
    scale_pos_weight = negative_count / positive_count if positive_count else 1.0
    classifier = XGBClassifier(
        **params,
        objective="binary:logistic",
        eval_metric="logloss",
        scale_pos_weight=scale_pos_weight,
        random_state=settings.random_state,
        n_jobs=-1,
    )
    pipeline = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor(X_train)),
            ("classifier", classifier),
        ]
    )
    pipeline.fit(X_train, y_train)
    return pipeline


def run_random_search(
    *,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_validation: pd.DataFrame,
    y_validation: pd.Series,
    search_space: dict[str, list[int | float]],
    n_iter: int,
    random_state: int,
) -> dict[str, Any]:
    """Evaluate sampled XGBoost settings solely against the validation split."""

    search_space_size = _search_space_size(search_space)
    if n_iter < 1 or n_iter > search_space_size:
        raise ValueError(
            "n_iter must be between 1 and at most "
            f"{search_space_size} for this discrete search space."
        )

    trials: list[dict[str, Any]] = []
    for index, raw_params in enumerate(
        ParameterSampler(search_space, n_iter=n_iter, random_state=random_state), start=1
    ):
        params = {
            name: int(value) if name in {"n_estimators", "max_depth"} else float(value)
            for name, value in raw_params.items()
        }
        pipeline = _fit_pipeline(X_train, y_train, params)
        metrics = evaluate_classifier(
            y_validation,
            pipeline.predict(X_validation),
            pipeline.predict_proba(X_validation)[:, 1],
        )
        trials.append(
            {
                "trial": index,
                "params": params,
                "validation_metrics": metrics,
            }
        )

    best = max(
        trials,
        key=lambda trial: (
            float(trial["validation_metrics"]["roc_auc"]),
            float(trial["validation_metrics"]["recall"]),
        ),
    )
    return {
        "search_strategy": "randomized_discrete",
        "random_state": random_state,
        "trials": trials,
        "best_params": best["params"],
        "best_validation_metrics": best["validation_metrics"],
    }


def log_hyperparameter_search(
    *,
    search_result: dict[str, Any],
    selection_manifest: dict[str, Any],
) -> str:
    """Persist reproducible selection evidence in a parent MLflow run."""

    if not settings.mlflow_tracking_uri:
        raise RuntimeError("MLFLOW_TRACKING_URI is required for baseline selection.")
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment_name)
    with mlflow.start_run(run_name="baseline-hyperparameter-selection") as parent:
        mlflow.set_tags(
            {
                "stage": "baseline_selection",
                "dataset_sha256": str(selection_manifest["sha256"]),
                "selection_strategy": str(search_result["search_strategy"]),
            }
        )
        mlflow.log_params(
            {
                "search_random_state": str(search_result["random_state"]),
                "search_trials": str(len(search_result["trials"])),
                **{
                    f"best_{name}": str(value)
                    for name, value in search_result["best_params"].items()
                },
            }
        )
        mlflow.log_metrics(
            {
                f"best_validation_{name}": float(value)
                for name, value in search_result["best_validation_metrics"].items()
            }
        )
        mlflow.log_dict(selection_manifest, "selection/manifest.json")
        mlflow.log_dict(search_result, "selection/search.json")
        for trial in search_result["trials"]:
            with mlflow.start_run(
                nested=True,
                run_name=f"baseline-search-trial-{trial['trial']}",
            ):
                mlflow.set_tag("stage", "baseline_search_trial")
                mlflow.set_tag("selection_manifest_sha256", str(selection_manifest["sha256"]))
                mlflow.log_params({name: str(value) for name, value in trial["params"].items()})
                mlflow.log_metrics(
                    {
                        f"validation_{name}": float(value)
                        for name, value in trial["validation_metrics"].items()
                    }
                )
        return parent.info.run_id


def _load_features_and_target(processed_dir: Path, split: str) -> tuple[pd.DataFrame, pd.Series]:
    return (
        pd.read_csv(processed_dir / f"X_{split}.csv"),
        pd.read_csv(processed_dir / f"y_{split}.csv")[TARGET_COLUMN],
    )


def _link_refit_to_selection(
    *,
    model_run_id: str,
    selected_params_path: Path,
    selection_run_id: str,
    selection_manifest_sha256: str,
) -> None:
    client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
    client.set_tag(model_run_id, "baseline_selection_run_id", selection_run_id)
    client.set_tag(
        model_run_id,
        "baseline_selection_manifest_sha256",
        selection_manifest_sha256,
    )
    client.log_artifact(model_run_id, str(selected_params_path), artifact_path="selection")


def register_baseline_snapshots(
    *,
    raw_path: Path,
    selection_dir: Path,
    refit_dir: Path,
) -> None:
    """Store the raw Kaggle input and both immutable processed snapshots."""

    register_local_snapshot(raw_path, source="weatherAUS-kaggle")
    register_processed_snapshot(selection_dir, source="weatherAUS-kaggle-selection")
    register_processed_snapshot(refit_dir, source="weatherAUS-kaggle-full-refit")


def load_baseline_config(path: Path) -> dict[str, Any]:
    """Read and validate the reproducible bootstrap search configuration."""

    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    baseline = payload.get("baseline")
    if not isinstance(baseline, dict):
        raise ValueError("params.yaml must contain a baseline mapping.")
    search = baseline.get("search")
    if not isinstance(search, dict):
        raise ValueError("params.yaml baseline.search must be a mapping.")
    parameter_space = search.get("parameter_space")
    required = {
        "n_estimators",
        "max_depth",
        "learning_rate",
        "subsample",
        "colsample_bytree",
    }
    if not isinstance(parameter_space, dict) or set(parameter_space) != required:
        raise ValueError(f"baseline.search.parameter_space must define exactly {sorted(required)}.")
    search_space = {
        name: list(values) if isinstance(values, list) else []
        for name, values in parameter_space.items()
    }
    _search_space_size(search_space)
    n_iter = search.get("n_iter")
    random_state = search.get("random_state")
    validation_window_days = baseline.get("validation_window_days")
    test_window_days = baseline.get("test_window_days")
    if not all(
        isinstance(value, int) and value > 0
        for value in (
            n_iter,
            random_state,
            validation_window_days,
            test_window_days,
        )
    ):
        raise ValueError("Baseline windows, n_iter, and random_state must be positive integers.")
    if n_iter > _search_space_size(search_space):
        raise ValueError("baseline.search.n_iter exceeds the discrete parameter-space size.")
    return {
        "validation_window_days": validation_window_days,
        "test_window_days": test_window_days,
        "n_iter": n_iter,
        "random_state": random_state,
        "search_space": search_space,
    }


def run_baseline(
    *,
    raw_path: Path,
    selection_dir: Path,
    refit_dir: Path,
    selected_params_path: Path,
    model_output_path: Path,
    train_metrics_path: Path,
    validation_metrics_path: Path,
    test_metrics_path: Path,
    validation_window_days: int,
    test_window_days: int,
    search_space: dict[str, list[int | float]],
    n_iter: int,
    random_state: int,
    register_snapshots: bool = True,
) -> dict[str, Any]:
    """Tune on an immutable Kaggle snapshot, refit all rows, then bootstrap.

    The frozen validation/test snapshot is never included in hyperparameter
    selection.  Its manifest is recorded in both the search run and the final
    registered full-data refit.
    """

    git_commit = current_git_commit()
    if not git_commit or git_commit.endswith("-dirty"):
        raise RuntimeError(
            "Baseline releases require a clean committed Git revision. Commit the pipeline first."
        )
    prepare_baseline_splits(
        raw_path=raw_path,
        selection_dir=selection_dir,
        refit_dir=refit_dir,
        validation_window_days=validation_window_days,
        test_window_days=test_window_days,
    )
    selection_dir = Path(selection_dir)
    refit_dir = Path(refit_dir)
    if register_snapshots:
        register_baseline_snapshots(
            raw_path=Path(raw_path),
            selection_dir=selection_dir,
            refit_dir=refit_dir,
        )
    selection_manifest = verify_processed_manifest(selection_dir)
    X_train, y_train = _load_features_and_target(selection_dir, "train")
    X_validation, y_validation = _load_features_and_target(selection_dir, "validation")
    search_result = run_random_search(
        X_train=X_train,
        y_train=y_train,
        X_validation=X_validation,
        y_validation=y_validation,
        search_space=search_space,
        n_iter=n_iter,
        random_state=random_state,
    )
    selection_run_id = log_hyperparameter_search(
        search_result=search_result,
        selection_manifest=selection_manifest,
    )
    selected_params_path = write_selected_parameters(
        selected_params_path,
        params=search_result["best_params"],
        selection_manifest_sha256=str(selection_manifest["sha256"]),
        selection_run_id=selection_run_id,
    )

    train_model(
        x_train_path=refit_dir / "X_train.csv",
        y_train_path=refit_dir / "y_train.csv",
        model_output_path=model_output_path,
        metrics_output_path=train_metrics_path,
        **search_result["best_params"],
    )
    model_metadata = load_mlflow_run_metadata()
    model_run_id = str(model_metadata["run_id"])
    _link_refit_to_selection(
        model_run_id=model_run_id,
        selected_params_path=selected_params_path,
        selection_run_id=selection_run_id,
        selection_manifest_sha256=str(selection_manifest["sha256"]),
    )
    evaluate_model(
        selection_dir / "X_validation.csv",
        selection_dir / "y_validation.csv",
        model_output_path,
        validation_metrics_path,
        split_name="validation",
    )
    evaluate_model(
        selection_dir / "X_test.csv",
        selection_dir / "y_test.csv",
        model_output_path,
        test_metrics_path,
        split_name="test",
    )
    promotion = promote_baseline_champion(
        metrics_path=validation_metrics_path,
        model_source_path=model_output_path,
        selection_processed_dir=selection_dir,
        run_metadata=model_metadata,
    )
    return {
        "selection_run_id": selection_run_id,
        "model_run_id": model_run_id,
        "selection_manifest_sha256": str(selection_manifest["sha256"]),
        **promotion,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tune the Kaggle baseline, refit all rows, and bootstrap the first champion."
    )
    parser.add_argument("--params", type=Path, default=PROJECT_ROOT / "params.yaml")
    parser.add_argument("--raw", type=Path, default=settings.seed_raw_data_path)
    parser.add_argument("--selection-dir", type=Path, default=settings.processed_data_dir)
    parser.add_argument(
        "--refit-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "baseline" / "refit",
    )
    parser.add_argument(
        "--selected-params-output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "baseline" / "selected_params.yaml",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_baseline_config(args.params)
    receipt = run_baseline(
        raw_path=args.raw,
        selection_dir=args.selection_dir,
        refit_dir=args.refit_dir,
        selected_params_path=args.selected_params_output,
        model_output_path=settings.model_path,
        train_metrics_path=settings.train_metrics_path,
        validation_metrics_path=settings.validation_metrics_path,
        test_metrics_path=settings.evaluation_metrics_path,
        **config,
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()

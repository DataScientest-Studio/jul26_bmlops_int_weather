"""Evidently batch checks: feature drift (warning) and delayed performance (retrain)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from weather_mlops.config.settings import settings

DRIFT_COLUMNS = (
    "Location",
    "MinTemp",
    "Humidity3pm",
    "Pressure3pm",
    "RainToday",
)
PSI_THRESHOLD = 0.1
DRIFT_SHARE = 0.3


def explode_prediction_features(rows: list[dict[str, Any]]) -> pd.DataFrame:
    records = []
    for row in rows:
        features = row.get("features") or {}
        if isinstance(features, str):
            features = json.loads(features)
        if isinstance(features, dict):
            records.append(features)
    if not records:
        return pd.DataFrame()
    return pd.DataFrame.from_records(records)


def simulate_feature_drift(frame: pd.DataFrame) -> pd.DataFrame:
    """Shift humidity and collapse location — a loud, reproducible synthetic drift."""

    current = frame.copy()
    if "Humidity3pm" in current.columns:
        current["Humidity3pm"] = pd.to_numeric(current["Humidity3pm"], errors="coerce") + 40
    if "Location" in current.columns:
        current["Location"] = "Darwin"
    return current


MAX_DRIFT_ROWS = 4000


def _cap_frame(frame: pd.DataFrame, n: int = MAX_DRIFT_ROWS) -> pd.DataFrame:
    if len(frame) <= n:
        return frame
    return frame.sample(n=n, random_state=settings.random_state).reset_index(drop=True)


CATEGORICAL_DRIFT_COLUMNS = ("Location", "RainToday")
NUMERIC_DRIFT_COLUMNS = ("MinTemp", "Humidity3pm", "Pressure3pm")


def _column_list(reference: pd.DataFrame, current: pd.DataFrame) -> list[str]:
    return [
        column
        for column in DRIFT_COLUMNS
        if column in reference.columns and column in current.columns
    ]


def prepare_drift_frames(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    columns: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    selected = columns or _column_list(reference, current)
    ref = pd.DataFrame()
    cur = pd.DataFrame()
    kept: list[str] = []
    for column in selected:
        if column not in reference.columns or column not in current.columns:
            continue
        kept.append(column)
        if column in NUMERIC_DRIFT_COLUMNS:
            ref[column] = pd.to_numeric(reference[column], errors="coerce")
            cur[column] = pd.to_numeric(current[column], errors="coerce")
        else:
            ref[column] = reference[column].astype("string").astype("category")
            cur[column] = current[column].astype("string").astype("category")
    return ref, cur, kept


def summarize_feature_snapshot(snapshot: Any, drift_share: float = DRIFT_SHARE) -> dict[str, Any]:
    drifted: list[str] = []
    column_metrics: dict[str, dict[str, Any]] = {}
    share = 0.0
    count = 0.0
    for metric in snapshot.dict().get("metrics", []):
        name = str(metric.get("metric_name") or "")
        config = metric.get("config") or {}
        value = metric.get("value")
        if "DriftedColumnsCount" in name and isinstance(value, dict):
            count = float(value.get("count") or 0)
            share = float(value.get("share") or 0)
        if "ValueDrift" in name:
            column = config.get("column")
            score = float(value)
            is_drifted = score >= PSI_THRESHOLD
            if column:
                column_metrics[str(column)] = {"drift_score": score, "drifted": is_drifted}
                if is_drifted:
                    drifted.append(str(column))
    return {
        "scope": "feature_drift",
        "drift_detected": share >= drift_share,
        "drifted_columns": drifted,
        "column_metrics": column_metrics,
        "share": share,
        "count": count,
    }


def evaluate_feature_drift(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    *,
    columns: list[str] | None = None,
) -> tuple[dict[str, Any], Any]:
    from evidently import DataDefinition, Dataset, Report
    from evidently.presets import DataDriftPreset

    ref, cur, selected = prepare_drift_frames(reference, current, columns)
    if not selected:
        raise ValueError("No overlapping drift columns between reference and current data.")
    schema = DataDefinition(
        numerical_columns=[c for c in selected if c in NUMERIC_DRIFT_COLUMNS],
        categorical_columns=[c for c in selected if c in CATEGORICAL_DRIFT_COLUMNS],
    )
    report = Report(
        [
            DataDriftPreset(
                columns=selected,
                method="psi",
                drift_share=DRIFT_SHARE,
            )
        ]
    )
    snapshot = report.run(
        Dataset.from_pandas(cur, data_definition=schema),
        Dataset.from_pandas(ref, data_definition=schema),
    )
    return summarize_feature_snapshot(snapshot), snapshot


def run_feature_drift(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    *,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    summary, _snapshot = evaluate_feature_drift(reference, current, columns=columns)
    return summary


def performance_decision(
    metrics: dict[str, float],
    champion_roc_auc: float | None = None,
) -> dict[str, Any]:
    recall = float(metrics.get("recall") or 0.0)
    roc_auc = float(metrics.get("roc_auc") or 0.0)
    retrain = recall < settings.mlflow_min_recall
    if champion_roc_auc is not None:
        retrain = retrain or roc_auc < float(champion_roc_auc) - 0.02
    return {
        "scope": "performance",
        "retrain": retrain,
        "metrics": metrics,
        "champion_roc_auc": champion_roc_auc,
    }


def store_drift_report(
    payload: dict[str, Any],
    client: Any | None = None,
) -> None:
    from weather_mlops.data.database import get_supabase_client

    if client is None and not (settings.supabase_url and settings.supabase_key):
        return
    supabase = client or get_supabase_client()
    row = {key: value for key, value in payload.items() if value is not None}
    supabase.table(settings.supabase_drift_reports_table).insert(row).execute()


def reference_dataset_sha256(reference_path: Path) -> str | None:
    """Hash of the processed split the reference rows come from, when it has a manifest."""

    from weather_mlops.data.manifest import read_processed_manifest

    manifest = read_processed_manifest(Path(reference_path).parent / "manifest.json")
    if manifest is None or not manifest.get("sha256"):
        return None
    return str(manifest["sha256"])


def monitoring_metrics(
    feature: dict[str, Any],
    performance: dict[str, Any] | None,
) -> dict[str, float]:
    """Flatten one batch into MLflow metrics: drift per feature, then delayed performance."""

    metrics = {
        "feature_drift_detected": float(bool(feature.get("drift_detected"))),
        "drifted_column_share": float(feature.get("share") or 0),
        "drifted_column_count": float(feature.get("count") or 0),
    }
    for column, values in (feature.get("column_metrics") or {}).items():
        metrics[f"psi_{column}"] = float(values["drift_score"])
    if performance:
        metrics["labeled_predictions"] = float(performance.get("labeled_predictions") or 0)
        metrics["retrain_requested"] = float(bool(performance.get("retrain")))
        for name, value in (performance.get("metrics") or {}).items():
            metrics[f"delayed_{name}"] = float(value)
    return metrics


def serving_model_tags(client: Any) -> dict[str, str]:
    """Which model made the monitored predictions: the version holding @champion.

    model_dataset_sha256 is the champion's own training data. When it differs from
    dataset_sha256, the report compared against another split than the served model's.
    """

    try:
        version = client.get_model_version_by_alias(
            settings.mlflow_model_name, settings.mlflow_champion_alias
        )
    except Exception:  # noqa: BLE001 - no champion yet: the API serves its local file
        return {"model_alias": "none"}
    tags = {
        "model_name": settings.mlflow_model_name,
        "model_alias": settings.mlflow_champion_alias,
        "model_version": str(version.version),
        "model_run_id": str(version.run_id),
    }
    model_dataset = client.get_run(version.run_id).data.tags.get("dataset_sha256")
    if model_dataset:
        tags["model_dataset_sha256"] = model_dataset
    return tags


def log_monitoring_run(
    feature: dict[str, Any],
    performance: dict[str, Any] | None,
    *,
    reference_path: Path,
    html_path: Path,
) -> str | None:
    """Track one Evidently batch in MLflow, tagged with the training split's dataset hash."""

    if not settings.mlflow_tracking_uri:
        print("MLflow tracking URI is not set; skipping monitoring run logging.")
        return None
    try:
        import mlflow
        from mlflow.tracking import MlflowClient

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_monitoring_experiment_name)
        model_tags = serving_model_tags(MlflowClient(tracking_uri=settings.mlflow_tracking_uri))
        with mlflow.start_run(run_name=f"evidently-{feature['current_dataset']}") as run:
            mlflow.set_tags(
                {
                    "stage": "monitoring",
                    "dataset_sha256": reference_dataset_sha256(reference_path) or "",
                    "reference_dataset": str(feature["reference_dataset"]),
                    "current_dataset": str(feature["current_dataset"]),
                    **model_tags,
                }
            )
            mlflow.log_metrics(monitoring_metrics(feature, performance))
            mlflow.log_artifact(str(html_path), artifact_path="evidently")
            summary = {"feature_drift": feature, "performance": performance}
            mlflow.log_dict(json.loads(json.dumps(summary, default=str)), "evidently/summary.json")
            return run.info.run_id
    except Exception as exc:  # noqa: BLE001 - a registry outage must not stop the report
        print(
            f"MLflow tracking URI {settings.mlflow_tracking_uri} is unreachable; "
            f"skipping monitoring run logging ({exc})."
        )
        return None


def load_serving_feature_rows(client: Any | None = None) -> list[dict[str, Any]]:
    from weather_mlops.data.database import get_supabase_client

    if client is None and not (settings.supabase_url and settings.supabase_key):
        return []
    supabase = client or get_supabase_client()
    response = (
        supabase.table(settings.supabase_predictions_table)
        .select("features,predicted_class,probability,observed_label")
        .limit(5000)
        .execute()
    )
    return list(response.data or [])


def delayed_performance(rows: list[dict[str, Any]]) -> dict[str, float] | None:
    labeled = [
        row
        for row in rows
        if row.get("observed_label") in {"Yes", "No"}
        and row.get("predicted_class") in {"Yes", "No"}
        and row.get("probability") is not None
    ]
    if len(labeled) < 30:
        return None
    from weather_mlops.models.evaluation import evaluate_classifier

    y_true = [1 if row["observed_label"] == "Yes" else 0 for row in labeled]
    y_pred = [1 if row["predicted_class"] == "Yes" else 0 for row in labeled]
    y_prob = [float(row["probability"]) for row in labeled]
    return evaluate_classifier(y_true, y_pred, y_prob)


def run_drift_job(
    *,
    simulate: bool = False,
    catalog_client: Any | None = None,
    reference_path: Path | None = None,
    current_path: Path | None = None,
) -> dict[str, Any]:
    path = Path(reference_path or settings.x_train_path)
    if not path.exists():
        raise FileNotFoundError(f"No reference features at {path}. Train or dvc-pull first.")
    reference = _cap_frame(pd.read_csv(path))
    serving_rows: list[dict[str, Any]] = []
    if simulate:
        current = simulate_feature_drift(reference)
        current_label = "simulated"
    elif current_path:
        # compare with a real csv, for exemple singapore
        current = _cap_frame(pd.read_csv(current_path))
        current_label = str(current_path)
    else:
        serving_rows = load_serving_feature_rows(client=catalog_client)
        current = explode_prediction_features(serving_rows)
        current = _cap_frame(current)
        current_label = "serving"
        if current.empty:
            raise RuntimeError(
                "No prediction features logged. Call /predict or re-run with --simulate."
            )

    summary, snapshot = evaluate_feature_drift(reference, current)
    reports_dir = Path(settings.evidently_reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    html_path = reports_dir / "feature_drift.html"
    snapshot.save_html(str(html_path))
    summary["report_html_path"] = str(html_path)
    summary["current_dataset"] = current_label
    summary["reference_dataset"] = str(path)

    performance = None
    if not simulate:
        metrics = delayed_performance(serving_rows)
        if metrics is not None:
            performance = performance_decision(metrics)
            performance["labeled_predictions"] = sum(
                row.get("observed_label") in {"Yes", "No"} for row in serving_rows
            )

    # MLflow first, so both Postgres rows can point at the run that holds the report
    mlflow_run_id = log_monitoring_run(
        summary,
        performance,
        reference_path=path,
        html_path=html_path,
    )

    store_drift_report(
        {
            "scope": "feature_drift",
            "reference_dataset": summary["reference_dataset"],
            "current_dataset": current_label,
            "drift_detected": summary["drift_detected"],
            "metrics": {
                "drifted_columns": summary["drifted_columns"],
                "column_metrics": summary["column_metrics"],
                "share": summary["share"],
            },
            "report_html_path": str(html_path),
            "mlflow_run_id": mlflow_run_id,
        },
        client=catalog_client,
    )
    if performance is not None:
        store_drift_report(
            {
                "scope": "performance",
                "reference_dataset": summary["reference_dataset"],
                "current_dataset": current_label,
                "drift_detected": performance["retrain"],
                "metrics": performance,
                "mlflow_run_id": mlflow_run_id,
            },
            client=catalog_client,
        )

    result = {"feature_drift": summary, "performance": performance, "mlflow_run_id": mlflow_run_id}
    if settings.pushgateway_url:
        from weather_mlops.monitoring.metrics import push_monitoring_metrics

        push_monitoring_metrics(result, gateway_url=settings.pushgateway_url)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Evidently feature-drift and delayed-performance checks."
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Shift Humidity3pm and Location on X_train instead of reading predictions.",
    )
    parser.add_argument(
        "--current-path",
        type=Path,
        help="CSV file to compare against X_train.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_drift_job(simulate=args.simulate, current_path=args.current_path)
    print(json.dumps(result, indent=2, default=str))
    if result["feature_drift"]["drift_detected"]:
        print("Feature drift: WARNING (do not auto-retrain from this alone).")
    performance = result.get("performance")
    if performance and performance.get("retrain"):
        print("Delayed performance: RETRAIN GATE.")


if __name__ == "__main__":
    main()

"""Archive and clear experimental model-lineage state before a new baseline.

Raw Kaggle data, the Australian weather-observation table, and the Singapore
out-of-distribution fixture are deliberately outside this reset scope.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from weather_mlops.config.settings import PROJECT_ROOT, settings
from weather_mlops.data.database import get_supabase_client
from weather_mlops.data.schema_migrate import normalize_dsn
from weather_mlops.security.vault import S3_SETTINGS, hydrate_runtime_secrets

CONFIRMATION_TOKEN = "RESET_PREBASELINE_EXPERIMENTS"
CATALOG_TABLES = (
    "predictions",
    "drift_reports",
    "model_versions",
    "dataset_versions",
    "ingestion_batches",
)
LOCAL_RESET_PATHS = (
    Path("models/best_model.joblib"),
    Path("models/rain_classifier.joblib"),
    Path("reports/metrics/train.json"),
    Path("reports/metrics/validation.json"),
    Path("reports/metrics/evaluation.json"),
    Path("reports/metrics/comparison.json"),
    Path("reports/mlflow_run.json"),
    Path("reports/evidently"),
    Path("data/raw/weatherAUS_current.csv"),
    Path("data/processed/X_train.csv"),
    Path("data/processed/X_validation.csv"),
    Path("data/processed/X_test.csv"),
    Path("data/processed/y_train.csv"),
    Path("data/processed/y_validation.csv"),
    Path("data/processed/y_test.csv"),
    Path("data/processed/manifest.json"),
    Path("mlflow-data"),
)


def require_confirmation(value: str | None) -> None:
    if value != CONFIRMATION_TOKEN:
        raise ValueError(
            f"Reset requires explicit confirmation: --confirm {CONFIRMATION_TOKEN}; "
            "no data was changed."
        )


def reset_catalog(connection: Any) -> None:
    """Clear only catalog rows derived from pre-baseline experiments."""

    connection.execute(
        "TRUNCATE TABLE public.predictions, public.drift_reports, public.model_versions, "
        "public.dataset_versions, public.ingestion_batches RESTART IDENTITY;"
    )


def snapshot_catalog(client: Any, backup_dir: Path) -> None:
    catalog_dir = backup_dir / "catalog"
    catalog_dir.mkdir(parents=True, exist_ok=False)
    for table in CATALOG_TABLES:
        rows = client.table(table).select("*").execute().data or []
        (catalog_dir / f"{table}.json").write_text(
            json.dumps(rows, indent=2, default=str) + "\n",
            encoding="utf-8",
        )


def _incremental_paths(project_root: Path) -> list[Path]:
    incremental_dir = project_root / "data/raw/incremental"
    return sorted(incremental_dir.glob("open_meteo_*")) if incremental_dir.exists() else []


def snapshot_local_artifacts(project_root: Path, backup_dir: Path) -> None:
    """Copy generated local artifacts without modifying their source paths."""

    local_dir = backup_dir / "local"
    local_dir.mkdir(parents=True, exist_ok=False)
    for relative_path in LOCAL_RESET_PATHS:
        source = project_root / relative_path
        if not source.exists():
            continue
        destination = local_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)

    for source in _incremental_paths(project_root):
        destination = local_dir / "data/raw/incremental" / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def remove_local_artifacts(project_root: Path) -> None:
    """Remove only generated artifacts that were already copied into a backup."""

    for relative_path in LOCAL_RESET_PATHS:
        source = project_root / relative_path
        if source.is_dir():
            shutil.rmtree(source)
        elif source.exists():
            source.unlink()
    for source in _incremental_paths(project_root):
        source.unlink()


def snapshot_mlflow_artifacts(client: Any, bucket: str, backup_dir: Path) -> list[str]:
    """Download every MLflow artifact before any remote deletion occurs."""

    objects = [
        item["Key"]
        for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket)
        for item in page.get("Contents", [])
    ]
    artifact_dir = backup_dir / "mlflow-s3"
    for key in objects:
        relative = Path(key)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe MLflow artifact key: {key}")
        destination = artifact_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        client.download_file(bucket, key, str(destination))
    (artifact_dir / "objects.json").write_text(
        json.dumps(objects, indent=2) + "\n",
        encoding="utf-8",
    )
    return objects


def clear_mlflow_artifacts(
    client: Any,
    bucket: str,
    objects: list[str],
    progress_path: Path,
    *,
    max_objects: int,
) -> bool:
    """Delete a bounded batch and persist progress for safe resumption."""

    deleted = set()
    if progress_path.exists():
        deleted = set(json.loads(progress_path.read_text(encoding="utf-8")))
    pending = [key for key in objects if key not in deleted]
    for key in pending[:max_objects]:
        client.delete_object(Bucket=bucket, Key=key)
        deleted.add(key)
        progress_path.write_text(json.dumps(sorted(deleted), indent=2) + "\n", encoding="utf-8")
    return len(deleted) == len(objects)


def _catalog_connection():
    hydrate_runtime_secrets(names=("SUPABASE_DB_URL",), required=("SUPABASE_DB_URL",))
    import psycopg

    return psycopg.connect(normalize_dsn(settings.supabase_db_url or ""), autocommit=True)


def _mlflow_s3_client():
    hydrate_runtime_secrets(
        names=tuple(name for name, _attr in S3_SETTINGS),
        required=("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"),
    )
    if not settings.supabase_s3_endpoint:
        raise RuntimeError("Supabase S3 endpoint could not be derived")
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.supabase_s3_endpoint,
        region_name=settings.aws_default_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def prepare_backup_dir(path: Path, *, resume: bool) -> Path:
    backup_dir = path.resolve()
    if backup_dir.exists():
        if not resume:
            raise FileExistsError(f"Backup directory already exists: {backup_dir}")
        return backup_dir
    backup_dir.mkdir(parents=True)
    return backup_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive and reset pre-baseline model lineage. Raw data is preserved."
    )
    parser.add_argument("--backup-dir", required=True, type=Path)
    parser.add_argument("--confirm")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-mlflow-deletes", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dry_run:
        print("Would archive and clear:")
        print("  local MLflow/model/report/processed artifacts")
        print("  Supabase catalog tables: " + ", ".join(CATALOG_TABLES))
        print("Would preserve: raw Kaggle, Singapore fixture, weather_observations, DVC blobs.")
        return
    require_confirmation(args.confirm)
    if args.max_mlflow_deletes < 1:
        raise ValueError("--max-mlflow-deletes must be positive")
    backup_dir = prepare_backup_dir(args.backup_dir, resume=args.resume)

    client = get_supabase_client()
    if not (backup_dir / "catalog").exists():
        snapshot_catalog(client, backup_dir)
    if not (backup_dir / "local").exists():
        snapshot_local_artifacts(PROJECT_ROOT, backup_dir)
    s3_client = _mlflow_s3_client()
    mlflow_backup = backup_dir / "mlflow-s3"
    if (mlflow_backup / "objects.json").exists():
        mlflow_objects = json.loads((mlflow_backup / "objects.json").read_text(encoding="utf-8"))
    else:
        mlflow_objects = snapshot_mlflow_artifacts(
            s3_client, settings.supabase_mlflow_bucket, backup_dir
        )
    with _catalog_connection() as connection:
        reset_catalog(connection)
    completed = clear_mlflow_artifacts(
        s3_client,
        settings.supabase_mlflow_bucket,
        mlflow_objects,
        mlflow_backup / "deleted.json",
        max_objects=args.max_mlflow_deletes,
    )
    if not completed:
        print(
            "MLflow cleanup batch complete. Re-run with --resume to continue; "
            "local artifacts were preserved."
        )
        return
    remove_local_artifacts(PROJECT_ROOT)
    print(f"Pre-baseline reset complete. Recovery snapshot: {backup_dir}")


if __name__ == "__main__":
    main()

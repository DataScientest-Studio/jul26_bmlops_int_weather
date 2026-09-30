import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from supabase import Client, create_client
from weather_mlops.config.settings import settings
from weather_mlops.data.versioning import DatasetMetadata

COLUMN_RENAMES = {
    "Date": "date",
    "Location": "location",
    "MinTemp": "min_temp",
    "MaxTemp": "max_temp",
    "Rainfall": "rainfall",
    "Evaporation": "evaporation",
    "Sunshine": "sunshine",
    "WindGustDir": "wind_gust_dir",
    "WindGustSpeed": "wind_gust_speed",
    "WindDir9am": "wind_dir_9am",
    "WindDir3pm": "wind_dir_3pm",
    "WindSpeed9am": "wind_speed_9am",
    "WindSpeed3pm": "wind_speed_3pm",
    "Humidity9am": "humidity_9am",
    "Humidity3pm": "humidity_3pm",
    "Pressure9am": "pressure_9am",
    "Pressure3pm": "pressure_3pm",
    "Cloud9am": "cloud_9am",
    "Cloud3pm": "cloud_3pm",
    "Temp9am": "temp_9am",
    "Temp3pm": "temp_3pm",
    "RainToday": "rain_today",
    "RainTomorrow": "rain_tomorrow",
}


def get_supabase_client() -> Client:
    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env.")

    return create_client(settings.supabase_url, settings.supabase_key)


def expected_weather_columns() -> list[str]:
    return ["source_row_number", *COLUMN_RENAMES.values()]


def normalize_weather_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    missing_columns = set(COLUMN_RENAMES) - set(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Dataset is missing required columns: {missing}")

    normalized = df.rename(columns=COLUMN_RENAMES).copy()
    normalized.insert(0, "source_row_number", range(1, len(normalized) + 1))
    normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    return normalized


def dataframe_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    normalized = normalize_weather_dataframe(df)
    normalized = normalized.astype(object).where(pd.notna(normalized), None)

    return normalized.to_dict(orient="records")


def chunk_records(
    records: list[dict[str, Any]],
    batch_size: int,
) -> Iterable[list[dict[str, Any]]]:
    if batch_size < 1:
        raise ValueError("batch_size must be positive.")

    for start in range(0, len(records), batch_size):
        yield records[start : start + batch_size]


def store_weather_observations(
    df: pd.DataFrame,
    batch_size: int = 1000,
    client: Client | None = None,
) -> int:
    supabase = client or get_supabase_client()
    records = dataframe_to_records(df)

    for batch in chunk_records(records, batch_size):
        supabase.table(settings.supabase_weather_table).upsert(
            batch,
            on_conflict="date,location",
        ).execute()

    return len(records)


def _existing_dataset_row(client: Client, dataset_name: str, sha256: str) -> dict[str, Any] | None:
    response = (
        client.table(settings.supabase_dataset_versions_table)
        .select(
            "storage_uri,created_at,git_commit,preprocessing_version,"
            "parent_sha256,created_by,source,version_kind,path,size_bytes,md5"
        )
        .eq("dataset_name", dataset_name)
        .eq("sha256", sha256)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def store_dataset_metadata(
    metadata: DatasetMetadata,
    client: Client | None = None,
) -> None:
    """Upsert catalog identity. Never replace a stored URI with null.

    Repeat loads keep the original created_at, path, size_bytes, md5, and fill
    only blank lineage fields. Conflicting git_commit, parent_sha256,
    preprocessing_version, storage_uri, or version_kind for the same sha256 is
    rejected so identical CSVs cannot rewrite snapshot lineage.
    """

    supabase = client or get_supabase_client()
    payload: dict[str, Any] = {
        "dataset_name": metadata.dataset_name,
        "path": metadata.path,
        "size_bytes": metadata.size_bytes,
        "md5": metadata.md5,
        "sha256": metadata.sha256,
        "created_at": metadata.created_at or datetime.now(UTC).isoformat(),
        "version_kind": metadata.version_kind,
        "storage_uri": metadata.storage_uri,
        "git_commit": metadata.git_commit,
        "preprocessing_version": metadata.preprocessing_version,
        "parent_sha256": metadata.parent_sha256,
        "source": metadata.source,
        "created_by": metadata.created_by,
    }
    existing = _existing_dataset_row(supabase, metadata.dataset_name, metadata.sha256)
    if existing:
        if existing.get("created_at"):
            payload["created_at"] = existing["created_at"]
        locked = (
            "storage_uri",
            "git_commit",
            "preprocessing_version",
            "parent_sha256",
            "version_kind",
        )
        for field in locked:
            existing_value = existing.get(field)
            new_value = payload.get(field)
            if existing_value and new_value and existing_value != new_value:
                raise ValueError(
                    f"Catalog lineage conflict for {metadata.dataset_name} "
                    f"{metadata.sha256}: {field} is {existing_value!r} but "
                    f"registration has {new_value!r}. Identical CSVs keep the "
                    "original snapshot lineage."
                )
            if not payload.get(field) and existing_value:
                payload[field] = existing_value
        for field in ("created_by", "source"):
            if not payload.get(field) and existing.get(field):
                payload[field] = existing[field]
        for field in ("path", "size_bytes", "md5"):
            if existing.get(field) not in (None, ""):
                payload[field] = existing[field]

    supabase.table(settings.supabase_dataset_versions_table).upsert(
        payload,
        on_conflict="dataset_name,sha256",
    ).execute()


def store_ingestion_batch(
    *,
    batch_date: str,
    storage_uri: str,
    sha256: str,
    location_count: int | None = None,
    source: str = "open-meteo",
    git_commit: str | None = None,
    client: Client | None = None,
) -> None:
    supabase = client or get_supabase_client()
    supabase.table(settings.supabase_ingestion_batches_table).upsert(
        {
            "batch_date": batch_date,
            "location_count": location_count,
            "storage_uri": storage_uri,
            "sha256": sha256,
            "source": source,
            "git_commit": git_commit,
        },
        on_conflict="batch_date,sha256",
    ).execute()


def feature_schema_from_csv(path: Path) -> dict[str, Any] | None:
    """Column names and dtypes from the champion training matrix, not the rows."""

    csv_path = Path(path)
    if not csv_path.exists():
        return None
    frame = pd.read_csv(csv_path, nrows=5)
    return {
        "columns": [str(column) for column in frame.columns],
        "dtypes": {str(column): str(dtype) for column, dtype in frame.dtypes.items()},
    }


def store_model_version(
    payload: dict[str, Any],
    client: Client | None = None,
) -> None:
    """Upsert a compare/promote row. Unique key is mlflow_run_id.

    A new champion demotes other catalog rows still tagged champion.
    Skip when neither a client nor Supabase credentials are available.
    """

    if client is None and not (settings.supabase_url and settings.supabase_key):
        return
    supabase = client or get_supabase_client()
    row = {key: value for key, value in payload.items() if value is not None}
    supabase.table(settings.supabase_model_versions_table).upsert(
        row,
        on_conflict="mlflow_run_id",
    ).execute()
    run_id = row.get("mlflow_run_id")
    if row.get("stage") != "champion" or not run_id:
        return
    supabase.table(settings.supabase_model_versions_table).update({"stage": "previous"}).eq(
        "stage", "champion"
    ).neq("mlflow_run_id", run_id).execute()


def catalog_registered_model(
    *,
    run_id: str,
    model_version: str | None,
    model_uri: str | None,
    dataset_sha256: str | None = None,
    params: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    stage: str = "candidate",
    client: Client | None = None,
) -> None:
    """Mirror an MLflow-registered model into Postgres. Blobs stay in Storage."""

    version = str(model_version) if model_version is not None else None
    uri = model_uri or (f"models:/{settings.mlflow_model_name}/{version}" if version else None)
    store_model_version(
        {
            "mlflow_run_id": run_id,
            "mlflow_model_version": version,
            "mlflow_model_uri": uri,
            "artifact_path": uri,
            "dataset_sha256": dataset_sha256,
            "name": settings.mlflow_model_name,
            "stage": stage,
            "metrics": metrics or {},
            "params": params or {},
            "feature_schema": feature_schema_from_csv(settings.x_train_path),
        },
        client=client,
    )


def lookup_model_version_id(
    serving: dict[str, Any] | None,
    client: Client,
) -> int | None:
    serving = serving or {}
    name = serving.get("name") or settings.mlflow_model_name
    version = serving.get("version")
    table = settings.supabase_model_versions_table
    if version:
        response = (
            client.table(table)
            .select("id")
            .eq("name", name)
            .eq("mlflow_model_version", str(version))
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if rows:
            return rows[0].get("id")
    response = (
        client.table(table).select("id").eq("name", name).eq("stage", "champion").limit(1).execute()
    )
    rows = response.data or []
    if not rows:
        return None
    return rows[0].get("id")


def store_prediction(
    payload: dict[str, Any],
    client: Client | None = None,
) -> None:
    if client is None and not (settings.supabase_url and settings.supabase_key):
        return
    supabase = client or get_supabase_client()
    row = {key: value for key, value in payload.items() if value is not None}
    supabase.table(settings.supabase_predictions_table).insert(row).execute()


def log_serving_prediction(
    *,
    endpoint: str,
    features: dict[str, Any],
    result: dict[str, Any],
    observation_date: str | None = None,
    location: str | None = None,
    latency_ms: int | None = None,
    request_id: str | None = None,
    client: Client | None = None,
) -> None:
    """Insert one serving row. Never raises: a catalog miss must not 500 /predict."""

    try:
        if client is None and not (settings.supabase_url and settings.supabase_key):
            return
        supabase = client or get_supabase_client()
        serving = result.get("model") if isinstance(result.get("model"), dict) else {}
        predicted = result.get("rain_tomorrow")
        predicted_class = None
        if predicted is True:
            predicted_class = "Yes"
        elif predicted is False:
            predicted_class = "No"
        store_prediction(
            {
                "model_version_id": lookup_model_version_id(serving, supabase),
                "features": features,
                "predicted_class": predicted_class,
                "probability": result.get("probability"),
                "observation_date": observation_date,
                "location": location,
                "endpoint": endpoint,
                "latency_ms": latency_ms,
                "request_id": request_id,
            },
            client=supabase,
        )
    except Exception:
        logging.getLogger(__name__).exception("predictions catalog write failed")
